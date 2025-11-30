"""
N8N Integration Router - FIXED VERSION
Handles webhook JWT validation and proxies n8n requests to avoid CORS
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import uuid
import json
import os
from jose import JWTError, jwt
import secrets
import hashlib
import httpx

from config import settings
from database import get_db
from sqlalchemy.orm import Session
from utils.auth import get_current_user
from models.user import User
from utils.redis_client import redis_client

router = APIRouter(prefix="/api/n8n", tags=["n8n"])


# ==================== Schemas ====================

class QuestionnaireStartRequest(BaseModel):
    template_type: int = Field(default=1, description="Questionnaire template type")


class QuestionnaireStartResponse(BaseModel):
    success: bool
    session_id: str
    jwt_token: str
    expires_at: str


class N8NWebhookValidationRequest(BaseModel):
    jwt: str
    action: str
    session_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class N8NWebhookKeyGenRequest(BaseModel):
    description: str = "n8n webhook key"
    expires_in_days: int = Field(default=30, ge=1, le=365)


class N8NWebhookKey(BaseModel):
    key_id: str
    api_key: str
    created_at: str
    expires_at: str
    description: str


# ==================== JWT for N8N Webhooks ====================

# N8N specific JWT settings
N8N_JWT_SECRET = os.getenv("N8N_JWT_SECRET", settings.SECRET_KEY)
N8N_JWT_ALGORITHM = "HS256"
N8N_JWT_EXPIRE_MINUTES = 60


def create_n8n_jwt(user_uuid: str, session_id: str, expires_delta: Optional[timedelta] = None) -> tuple[str, datetime]:
    """Create a JWT token specifically for n8n webhook calls"""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=N8N_JWT_EXPIRE_MINUTES)
    
    payload = {
        "sub": user_uuid,
        "session_id": session_id,
        "type": "n8n_webhook",
        "iat": datetime.utcnow(),
        "exp": expire,
        "jti": str(uuid.uuid4())
    }
    
    token = jwt.encode(payload, N8N_JWT_SECRET, algorithm=N8N_JWT_ALGORITHM)
    return token, expire


def verify_n8n_jwt(token: str) -> Dict[str, Any]:
    """Verify JWT token - accepts both n8n_webhook and access tokens"""
    try:
        # Try n8n secret first (for n8n_webhook tokens)
        try:
            payload = jwt.decode(token, N8N_JWT_SECRET, algorithms=[N8N_JWT_ALGORITHM])
            if payload.get("type") == "n8n_webhook":
                return payload
        except JWTError:
            pass
        
        # Try regular access token (from login) with main SECRET_KEY
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[N8N_JWT_ALGORITHM])
            if payload.get("type") == "access":
                return payload
        except JWTError:
            pass
        
        raise HTTPException(status_code=401, detail="Invalid token")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")


def create_n8n_proxy_token(user_uuid: str) -> str:
    """Create a short-lived JWT for proxying to n8n, signed with N8N_JWT_SECRET"""
    expire = datetime.utcnow() + timedelta(minutes=5)  # Short lived
    payload = {
        "sub": user_uuid,
        "type": "n8n_webhook",
        "iat": datetime.utcnow(),
        "exp": expire,
        "jti": str(uuid.uuid4())
    }
    return jwt.encode(payload, N8N_JWT_SECRET, algorithm=N8N_JWT_ALGORITHM)


# ==================== Helper Functions ====================

def get_n8n_webhook_url(webhook_path: str) -> str:
    """Get full n8n webhook URL"""
    n8n_base_url = os.getenv("N8N_WEBHOOK_BASE_URL", "http://localhost:5678/webhook")
    return f"{n8n_base_url}/{webhook_path}"


async def proxy_to_n8n(webhook_path: str, data: Dict[str, Any], user_uuid: str = None) -> Dict[str, Any]:
    """
    Proxy request to n8n webhook
    Creates a new n8n-specific JWT signed with N8N_JWT_SECRET
    IMPORTANT: Always adds userUuid to request body for n8n to use
    """
    url = get_n8n_webhook_url(webhook_path)
    
    headers = {"Content-Type": "application/json"}
    
    # CRITICAL: Add user_uuid to data BEFORE sending to n8n
    if user_uuid:
        n8n_token = create_n8n_proxy_token(user_uuid)
        headers["Authorization"] = f"Bearer {n8n_token}"
        data["jwt"] = n8n_token
        data["userUuid"] = user_uuid  # <-- THIS IS CRITICAL for n8n to get the user
    
    # Debug logging
    print(f"[n8n proxy] POST {url}")
    print(f"[n8n proxy] user_uuid being sent: {user_uuid}")
    print(f"[n8n proxy] Request data: {json.dumps(data, default=str)[:500]}")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(url, json=data, headers=headers)
            
            print(f"[n8n proxy] Response status: {response.status_code}")
            print(f"[n8n proxy] Response body (first 500 chars): {response.text[:500]}")
            
            response.raise_for_status()
            
            # Check if response has content before parsing JSON
            if not response.text or response.text.strip() == "":
                raise HTTPException(
                    status_code=502,
                    detail="n8n returned empty response. Make sure n8n workflow returns JSON."
                )
            
            # Try to parse JSON
            try:
                return response.json()
            except json.JSONDecodeError as e:
                raise HTTPException(
                    status_code=502,
                    detail=f"n8n returned invalid JSON: {response.text[:200]}... Error: {str(e)}"
                )
                
        except httpx.ConnectError:
            raise HTTPException(
                status_code=503,
                detail="Cannot connect to n8n. Is n8n running at " + url + "?"
            )
        except httpx.TimeoutException:
            raise HTTPException(
                status_code=504,
                detail="n8n request timed out after 30 seconds"
            )
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"n8n error ({e.response.status_code}): {e.response.text[:200]}"
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"n8n webhook error: {type(e).__name__}: {str(e)}"
            )


# ==================== Endpoints ====================

@router.post("/questionnaire/start", response_model=QuestionnaireStartResponse)
async def start_questionnaire(
    request: QuestionnaireStartRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Start a new questionnaire session
    Returns JWT token and session info (NO direct n8n URL)
    """
    # Generate session ID (pure UUID for database compatibility)
    session_id = str(uuid.uuid4())
    
    # Create n8n-specific JWT
    n8n_token, expires_at = create_n8n_jwt(
        str(current_user.user_uuid),
        session_id,
        timedelta(hours=2)
    )
    
    # Store session in Redis
    session_data = {
        "user_uuid": str(current_user.user_uuid),
        "template_type": request.template_type,
        "started_at": datetime.utcnow().isoformat(),
        "status": "in_progress"
    }
    
    await redis_client.redis.setex(
        f"questionnaire_session:{session_id}",
        7200,  # 2 hours TTL
        json.dumps(session_data)
    )
    
    return QuestionnaireStartResponse(
        success=True,
        session_id=session_id,
        jwt_token=n8n_token,
        expires_at=expires_at.isoformat()
    )


@router.post("/questionnaire/webhook/start")
async def questionnaire_webhook_start(request: Request):
    """
    PROXY: Forward questionnaire start request to n8n
    This endpoint is called by the frontend instead of calling n8n directly
    """
    try:
        data = await request.json()
        
        # Get JWT from Authorization header
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            jwt_token = auth_header[7:]
        else:
            jwt_token = data.get("jwt")  # fallback to body
        
        if not jwt_token:
            raise HTTPException(status_code=401, detail="JWT token required")
        
        # Verify the token and get user info
        payload = verify_n8n_jwt(jwt_token)
        user_uuid = payload.get("sub")
        
        # DEBUG: Print what we got
        print(f"[webhook/start] JWT payload: {payload}")
        print(f"[webhook/start] Extracted user_uuid: {user_uuid}")
        
        if not user_uuid:
            raise HTTPException(status_code=401, detail="No user_uuid in token")
        
        # Proxy to n8n (this will add userUuid to the data)
        result = await proxy_to_n8n("questionnaire-start", data, user_uuid)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[webhook/start] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/questionnaire/webhook/answer")
async def questionnaire_webhook_answer(request: Request):
    """
    PROXY: Forward questionnaire answer to n8n
    """
    try:
        data = await request.json()
        
        # Get JWT from Authorization header
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            jwt_token = auth_header[7:]
        else:
            jwt_token = data.get("jwt")  # fallback to body
        
        if not jwt_token:
            raise HTTPException(status_code=401, detail="JWT token required")
        
        payload = verify_n8n_jwt(jwt_token)
        user_uuid = payload.get("sub")
        
        # Verify session
        session_id = data.get("sessionId")
        if session_id:
            session_data = await redis_client.redis.get(f"questionnaire_session:{session_id}")
            if not session_data:
                raise HTTPException(status_code=401, detail="Session expired")
            
            session = json.loads(session_data)
            if session.get("user_uuid") != user_uuid:
                raise HTTPException(status_code=403, detail="Session user mismatch")
        
        # Proxy to n8n (this will add userUuid to the data)
        result = await proxy_to_n8n("questionnaire-answer", data, user_uuid)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/questionnaire/webhook/file-upload")
async def questionnaire_webhook_file_upload(request: Request):
    """
    PROXY: Forward file upload to n8n
    """
    try:
        data = await request.json()
        
        # Get JWT from Authorization header
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            jwt_token = auth_header[7:]
        else:
            jwt_token = data.get("jwt")  # fallback to body
        
        if not jwt_token:
            raise HTTPException(status_code=401, detail="JWT token required")
        
        payload = verify_n8n_jwt(jwt_token)
        user_uuid = payload.get("sub")
        
        # Proxy to n8n
        result = await proxy_to_n8n("questionnaire-file-upload", data, user_uuid)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/questionnaire/webhook/summary-regenerate")
async def questionnaire_webhook_summary_regenerate(request: Request):
    """
    PROXY: Forward summary regeneration request to n8n
    """
    try:
        data = await request.json()
        
        # Get JWT from Authorization header
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            jwt_token = auth_header[7:]
        else:
            jwt_token = data.get("jwt")  # fallback to body
        
        if not jwt_token:
            raise HTTPException(status_code=401, detail="JWT token required")
        
        payload = verify_n8n_jwt(jwt_token)
        user_uuid = payload.get("sub")
        
        # Proxy to n8n
        result = await proxy_to_n8n("questionnaire-summary-regenerate", data, user_uuid)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Validation Endpoint ====================

@router.post("/webhook/validate")
async def validate_webhook_jwt(request: N8NWebhookValidationRequest):
    """
    Endpoint for n8n to validate JWT tokens
    Called by n8n workflow to verify user authentication
    """
    try:
        payload = verify_n8n_jwt(request.jwt)
        
        # Check session if provided
        if request.session_id:
            session_data = await redis_client.redis.get(f"questionnaire_session:{request.session_id}")
            if not session_data:
                return JSONResponse(
                    status_code=401,
                    content={"valid": False, "error": "Session expired or invalid"}
                )
            
            session = json.loads(session_data)
            if session.get("user_uuid") != payload.get("sub"):
                return JSONResponse(
                    status_code=401,
                    content={"valid": False, "error": "Session user mismatch"}
                )
        
        return {
            "valid": True,
            "user_uuid": payload.get("sub"),
            "session_id": payload.get("session_id"),
            "expires_at": datetime.fromtimestamp(payload.get("exp")).isoformat()
        }
        
    except HTTPException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={"valid": False, "error": e.detail}
        )


# ==================== Session Management ====================

@router.get("/questionnaire/session/{session_id}")
async def get_questionnaire_session(
    session_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get questionnaire session status"""
    session_data = await redis_client.redis.get(f"questionnaire_session:{session_id}")
    
    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = json.loads(session_data)
    
    if session.get("user_uuid") != str(current_user.user_uuid):
        raise HTTPException(status_code=403, detail="Access denied")
    
    return {
        "session_id": session_id,
        **session
    }


@router.post("/questionnaire/session/{session_id}/update")
async def update_questionnaire_session(
    session_id: str,
    update_data: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """Update questionnaire session data"""
    session_key = f"questionnaire_session:{session_id}"
    session_data = await redis_client.redis.get(session_key)
    
    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = json.loads(session_data)
    
    if session.get("user_uuid") != str(current_user.user_uuid):
        raise HTTPException(status_code=403, detail="Access denied")
    
    session.update(update_data)
    session["updated_at"] = datetime.utcnow().isoformat()
    
    ttl = await redis_client.redis.ttl(session_key)
    if ttl > 0:
        await redis_client.redis.setex(session_key, ttl, json.dumps(session))
    
    return {"success": True, "session": session}


@router.delete("/questionnaire/session/{session_id}")
async def delete_questionnaire_session(
    session_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete/cancel a questionnaire session"""
    session_key = f"questionnaire_session:{session_id}"
    session_data = await redis_client.redis.get(session_key)
    
    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = json.loads(session_data)
    
    if session.get("user_uuid") != str(current_user.user_uuid):
        raise HTTPException(status_code=403, detail="Access denied")
    
    await redis_client.redis.delete(session_key)
    
    return {"success": True, "message": "Session deleted"}


# ==================== Admin Endpoints ====================

async def generate_api_key() -> str:
    """Generate a secure API key"""
    return secrets.token_urlsafe(32)


async def hash_api_key(api_key: str) -> str:
    """Hash API key for storage"""
    return hashlib.sha256(api_key.encode()).hexdigest()


@router.post("/admin/webhook-key/generate", response_model=N8NWebhookKey)
async def generate_webhook_key(
    request: N8NWebhookKeyGenRequest,
    current_user: User = Depends(get_current_user)
):
    """Generate API key for n8n webhook authentication (Admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    api_key = await generate_api_key()
    key_id = f"n8n_key_{uuid.uuid4().hex[:8]}"
    
    created_at = datetime.utcnow()
    expires_at = created_at + timedelta(days=request.expires_in_days)
    
    key_data = {
        "key_id": key_id,
        "hashed_key": await hash_api_key(api_key),
        "created_at": created_at.isoformat(),
        "expires_at": expires_at.isoformat(),
        "description": request.description,
        "created_by": str(current_user.user_uuid)
    }
    
    await redis_client.redis.setex(
        f"n8n_api_key:{key_id}",
        request.expires_in_days * 24 * 60 * 60,
        json.dumps(key_data)
    )
    
    return N8NWebhookKey(
        key_id=key_id,
        api_key=api_key,
        created_at=created_at.isoformat(),
        expires_at=expires_at.isoformat(),
        description=request.description
    )


@router.get("/admin/webhook-keys")
async def list_webhook_keys(current_user: User = Depends(get_current_user)):
    """List all n8n webhook API keys (Admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    keys = []
    cursor = 0
    
    while True:
        cursor, key_names = await redis_client.redis.scan(
            cursor, match="n8n_api_key:*", count=100
        )
        
        for key_name in key_names:
            key_data = await redis_client.redis.get(key_name)
            if key_data:
                data = json.loads(key_data)
                keys.append({
                    "key_id": data.get("key_id"),
                    "created_at": data.get("created_at"),
                    "expires_at": data.get("expires_at"),
                    "description": data.get("description")
                })
        
        if cursor == 0:
            break
    
    return {"keys": keys}


@router.delete("/admin/webhook-key/{key_id}")
async def revoke_webhook_key(
    key_id: str,
    current_user: User = Depends(get_current_user)
):
    """Revoke an n8n webhook API key (Admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    deleted = await redis_client.redis.delete(f"n8n_api_key:{key_id}")
    
    if not deleted:
        raise HTTPException(status_code=404, detail="Key not found")
    
    return {"success": True, "message": f"Key {key_id} revoked"}


@router.get("/workflow/status")
async def get_workflow_status(current_user: User = Depends(get_current_user)):
    """Get n8n workflow connection status"""
    n8n_base_url = os.getenv("N8N_WEBHOOK_BASE_URL", "http://localhost:5678/webhook")
    
    return {
        "n8n_configured": True,
        "webhook_base_url": n8n_base_url,
        "available_workflows": [
            {
                "name": "Traffic Accident Questionnaire",
                "webhook_path": "/questionnaire-start",
                "description": "交通事故法律咨询问卷"
            }
        ]
    }
