from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional
import uuid

from database import get_db
from models.user import User, UserProfile, RefreshToken
from schemas.auth import (
    UserRegister, UserLogin, PhoneLogin, WeChatLogin,
    SMSCodeRequest, TokenRefresh, PasswordReset, PasswordChange,
    LoginResponse, MessageResponse, UserResponse, Token
)
from utils.auth import (
    get_password_hash, verify_password, create_access_token,
    create_refresh_token, decode_token, hash_token,
    get_current_user, create_user_session_with_redis
)
from utils.redis_client import redis_client
from utils.wechat import wechat_oauth
from utils.sms import create_sms_verification, verify_sms_code, send_sms_code
from config import settings

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


def get_client_info(request: Request) -> dict:
    """Extract client information from request"""
    return {
        "ip_address": request.client.host,
        "user_agent": request.headers.get("user-agent", ""),
        "device_info": {}
    }


@router.post("/register", response_model=LoginResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegister,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Register new user with username/phone and password
    """
    # Validate that at least username or phone is provided
    if not user_data.username and not user_data.phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名或手机号必须提供一个"
        )
    
    # SMS verification temporarily disabled for development
    # if user_data.phone:
    #     if not user_data.sms_code:
    #         raise HTTPException(
    #             status_code=status.HTTP_400_BAD_REQUEST,
    #             detail="手机注册需要提供短信验证码"
    #         )
    #     verify_sms_code(db, user_data.phone, user_data.sms_code, "register")
    
    # Check if user already exists
    existing_user = db.query(User).filter(
        (User.username == user_data.username) if user_data.username else False |
        (User.phone == user_data.phone) if user_data.phone else False
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名或手机号已被注册"
        )
    
    # Create user
    new_user = User(
        username=user_data.username,
        phone=user_data.phone,
        password_hash=get_password_hash(user_data.password),
        role=user_data.role,
        is_verified=bool(user_data.phone and user_data.sms_code),  # Auto-verify if phone + SMS
        last_login_at=datetime.utcnow()
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Create user profile
    profile = UserProfile(user_uuid=new_user.user_uuid)
    db.add(profile)
    db.commit()
    
    # Generate tokens
    access_token, access_jti = create_access_token({"sub": str(new_user.user_uuid)})
    refresh_token, refresh_jti = create_refresh_token({"sub": str(new_user.user_uuid)})
    
    # Create session
    client_info = get_client_info(request)
    session = await create_user_session_with_redis(
        db=db,
        user_uuid=new_user.user_uuid,
        access_jti=access_jti,
        refresh_jti=refresh_jti,
        ip_address=client_info["ip_address"],
        user_agent=client_info["user_agent"],
        device_info=client_info["device_info"],
        expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    
    # Store refresh token
    refresh_token_record = RefreshToken(
        user_uuid=new_user.user_uuid,
        session_uuid=session.session_uuid,
        token_hash=hash_token(refresh_token),
        expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    db.add(refresh_token_record)
    db.commit()
    
    return LoginResponse(
        user=UserResponse.from_orm(new_user),
        token=Token(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
    )


@router.post("/login", response_model=LoginResponse)
async def login(
    credentials: UserLogin,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Login with username/phone and password
    """
    # Get identifier for rate limiting
    identifier = credentials.username or credentials.phone
    
    # Check if account is locked due to too many failed attempts
    if await redis_client.is_account_locked(identifier):
        remaining_time = settings.LOCKOUT_DURATION_MINUTES
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"账户已被锁定，请{remaining_time}分钟后重试"
        )
    
    # Find user
    user = db.query(User).filter(
        (User.username == credentials.username) if credentials.username else False |
        (User.phone == credentials.phone) if credentials.phone else False
    ).first()
    
    if not user or not verify_password(credentials.password, user.password_hash):
        # Increment failed login attempts
        attempts = await redis_client.increment_login_attempts(identifier)
        remaining = settings.MAX_LOGIN_ATTEMPTS - attempts
        
        if remaining <= 0:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"用户名/手机号或密码错误，账户已被锁定{settings.LOCKOUT_DURATION_MINUTES}分钟"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"用户名/手机号或密码错误，剩余尝试次数：{remaining}"
            )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账户已被禁用"
        )
    
    # Reset failed login attempts on successful login
    await redis_client.reset_login_attempts(identifier)
    
    # Update last login
    user.last_login_at = datetime.utcnow()
    
    # Generate tokens
    access_token, access_jti = create_access_token({"sub": str(user.user_uuid)})
    refresh_token, refresh_jti = create_refresh_token({"sub": str(user.user_uuid)})
    
    # Create session
    client_info = get_client_info(request)
    session = await create_user_session_with_redis(
        db=db,
        user_uuid=user.user_uuid,
        access_jti=access_jti,
        refresh_jti=refresh_jti,
        ip_address=client_info["ip_address"],
        user_agent=client_info["user_agent"],
        device_info=client_info["device_info"],
        expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    
    # Store refresh token
    refresh_token_record = RefreshToken(
        user_uuid=user.user_uuid,
        session_uuid=session.session_uuid,
        token_hash=hash_token(refresh_token),
        expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    db.add(refresh_token_record)
    db.commit()
    
    return LoginResponse(
        user=UserResponse.from_orm(user),
        token=Token(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
    )


@router.post("/login/phone", response_model=LoginResponse)
async def phone_login(
    credentials: PhoneLogin,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Login with phone and SMS verification code (SMS verification disabled)
    """
    # SMS verification temporarily disabled for development
    # verify_sms_code(db, credentials.phone, credentials.sms_code, "login")
    
    # Find or create user
    user = db.query(User).filter(User.phone == credentials.phone).first()
    
    if not user:
        # Auto-register user with phone
        user = User(
            phone=credentials.phone,
            role="user",
            is_verified=True,
            last_login_at=datetime.utcnow()
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # Create profile
        profile = UserProfile(user_uuid=user.user_uuid)
        db.add(profile)
        db.commit()
    else:
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="账户已被禁用"
            )
        user.last_login_at = datetime.utcnow()
        user.is_verified = True
    
    # Generate tokens
    access_token, access_jti = create_access_token({"sub": str(user.user_uuid)})
    refresh_token, refresh_jti = create_refresh_token({"sub": str(user.user_uuid)})
    
    # Create session
    client_info = get_client_info(request)
    session = await create_user_session_with_redis(
        db=db,
        user_uuid=user.user_uuid,
        access_jti=access_jti,
        refresh_jti=refresh_jti,
        ip_address=client_info["ip_address"],
        user_agent=client_info["user_agent"],
        device_info=client_info["device_info"],
        expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    
    # Store refresh token
    refresh_token_record = RefreshToken(
        user_uuid=user.user_uuid,
        session_uuid=session.session_uuid,
        token_hash=hash_token(refresh_token),
        expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    db.add(refresh_token_record)
    db.commit()
    
    return LoginResponse(
        user=UserResponse.from_orm(user),
        token=Token(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
    )


@router.post("/login/wechat", response_model=LoginResponse)
async def wechat_login(
    credentials: WeChatLogin,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Login with WeChat OAuth code
    """
    # Authenticate with WeChat
    wechat_user = await wechat_oauth.authenticate(credentials.code)
    
    openid = wechat_user.get("openid")
    unionid = wechat_user.get("unionid")
    
    if not openid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="微信授权失败"
        )
    
    # Find or create user by openid or unionid
    user = None
    if unionid:
        user = db.query(User).filter(User.wechat_unionid == unionid).first()
    if not user and openid:
        user = db.query(User).filter(User.wechat_openid == openid).first()
    
    if not user:
        # Auto-register user with WeChat info
        user = User(
            wechat_openid=openid,
            wechat_unionid=unionid,
            role="user",
            is_verified=True,
            last_login_at=datetime.utcnow()
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # Create profile with WeChat info
        profile = UserProfile(
            user_uuid=user.user_uuid,
            nickname=wechat_user.get("nickname"),
            avatar_url=wechat_user.get("avatar"),
            gender="male" if wechat_user.get("gender") == 1 else "female" if wechat_user.get("gender") == 2 else "other",
            city_name=wechat_user.get("city"),
            province_name=wechat_user.get("province")
        )
        db.add(profile)
        db.commit()
    else:
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="账户已被禁用"
            )
        user.last_login_at = datetime.utcnow()
        # Update WeChat IDs if needed
        if unionid and not user.wechat_unionid:
            user.wechat_unionid = unionid
        if openid and not user.wechat_openid:
            user.wechat_openid = openid
        db.commit()
    
    # Generate tokens
    access_token, access_jti = create_access_token({"sub": str(user.user_uuid)})
    refresh_token, refresh_jti = create_refresh_token({"sub": str(user.user_uuid)})
    
    # Create session
    client_info = get_client_info(request)
    session = await create_user_session_with_redis(
        db=db,
        user_uuid=user.user_uuid,
        access_jti=access_jti,
        refresh_jti=refresh_jti,
        ip_address=client_info["ip_address"],
        user_agent=client_info["user_agent"],
        device_info=client_info["device_info"],
        expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    
    # Store refresh token
    refresh_token_record = RefreshToken(
        user_uuid=user.user_uuid,
        session_uuid=session.session_uuid,
        token_hash=hash_token(refresh_token),
        expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    db.add(refresh_token_record)
    db.commit()
    
    return LoginResponse(
        user=UserResponse.from_orm(user),
        token=Token(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
    )


@router.post("/sms/send", response_model=MessageResponse)
async def send_sms(
    sms_request: SMSCodeRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Send SMS verification code with rate limiting
    """
    # Rate limiting: 1 SMS per minute per phone
    rate_limit_key = f"sms_rate:{sms_request.phone}"
    if not await redis_client.check_rate_limit(rate_limit_key, 1, 60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="发送过于频繁，请1分钟后重试"
        )
    
    client_info = get_client_info(request)
    
    # Create verification record
    verification = create_sms_verification(
        db=db,
        phone=sms_request.phone,
        purpose=sms_request.purpose,
        ip_address=client_info["ip_address"]
    )
    
    # Store verification code in Redis as well
    await redis_client.store_sms_code(
        sms_request.phone,
        verification.verification_code,
        settings.SMS_CODE_EXPIRE_MINUTES * 60
    )
    
    # Send SMS
    success = await send_sms_code(
        phone=sms_request.phone,
        code=verification.verification_code,
        purpose=sms_request.purpose
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="短信发送失败"
        )
    
    return MessageResponse(message="验证码已发送")


@router.post("/token/refresh", response_model=Token)
async def refresh_access_token(
    token_data: TokenRefresh,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token with Redis validation
    """
    try:
        payload = decode_token(token_data.refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的刷新令牌"
            )
        
        user_uuid = payload.get("sub")
        refresh_jti = payload.get("jti")
        
        # Check Redis first (fast validation)
        redis_user_uuid = await redis_client.get_refresh_token(refresh_jti)
        if redis_user_uuid is None or redis_user_uuid != user_uuid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="刷新令牌已被撤销"
            )
        
        # Verify refresh token in database
        token_hash_value = hash_token(token_data.refresh_token)
        refresh_record = db.query(RefreshToken).filter(
            RefreshToken.token_hash == token_hash_value,
            RefreshToken.is_revoked == False,
            RefreshToken.expires_at > datetime.utcnow()
        ).first()
        
        if not refresh_record:
            # Token expired in DB, remove from Redis
            await redis_client.revoke_refresh_token(refresh_jti)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="刷新令牌已失效"
            )
        
        # Get the session
        session = db.query(UserSession).filter(
            UserSession.refresh_token_jti == refresh_jti
        ).first()
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="会话不存在"
            )
        
        # Revoke old access token from Redis
        await redis_client.revoke_access_token(session.access_token_jti)
        
        # Generate new access token
        access_token, access_jti = create_access_token({"sub": user_uuid})
        
        # Store new access token in Redis
        await redis_client.store_access_token(
            access_jti,
            user_uuid,
            settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        
        # Update session with new access token JTI
        session.access_token_jti = access_jti
        session.last_activity_at = datetime.utcnow()
        db.commit()
        
        return Token(
            access_token=access_token,
            refresh_token=token_data.refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌刷新失败"
        )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Logout and revoke current session with Redis cleanup
    """
    # Get current token JTI
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.replace("Bearer ", "")
        try:
            payload = decode_token(token)
            current_jti = payload.get("jti")
            
            # Find and revoke current session
            session = db.query(UserSession).filter(
                UserSession.access_token_jti == current_jti
            ).first()
            
            if session:
                # Revoke tokens in Redis
                await redis_client.revoke_access_token(session.access_token_jti)
                if session.refresh_token_jti:
                    await redis_client.revoke_refresh_token(session.refresh_token_jti)
                
                # Remove from user's active sessions
                await redis_client.remove_user_session(
                    str(current_user.user_uuid),
                    str(session.session_uuid)
                )
                
                # Mark session as inactive
                session.is_active = False
                
                # Revoke refresh token in database
                db.query(RefreshToken).filter(
                    RefreshToken.session_uuid == session.session_uuid,
                    RefreshToken.is_revoked == False
                ).update({
                    "is_revoked": True,
                    "revoked_at": datetime.utcnow(),
                    "revoked_reason": "logout"
                })
        except:
            pass
    
    db.commit()
    
    return MessageResponse(message="退出登录成功")


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user information
    """
    return UserResponse.from_orm(current_user)


@router.post("/password/reset", response_model=MessageResponse)
async def reset_password(
    reset_data: PasswordReset,
    db: Session = Depends(get_db)
):
    """
    Reset password with phone and SMS code (SMS verification disabled)
    """
    # SMS verification temporarily disabled for development
    # verify_sms_code(db, reset_data.phone, reset_data.sms_code, "reset_password")
    
    # Find user
    user = db.query(User).filter(User.phone == reset_data.phone).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    # Update password
    user.password_hash = get_password_hash(reset_data.new_password)
    
    # Revoke all sessions
    db.query(UserSession).filter(
        UserSession.user_uuid == user.user_uuid
    ).update({"is_active": False})
    
    db.query(RefreshToken).filter(
        RefreshToken.user_uuid == user.user_uuid,
        RefreshToken.is_revoked == False
    ).update({
        "is_revoked": True,
        "revoked_at": datetime.utcnow(),
        "revoked_reason": "password_reset"
    })
    
    db.commit()
    
    return MessageResponse(message="密码重置成功")


@router.post("/password/change", response_model=MessageResponse)
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Change password for authenticated user
    """
    # Verify old password
    if not verify_password(password_data.old_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="原密码错误"
        )
    
    # Update password
    current_user.password_hash = get_password_hash(password_data.new_password)
    db.commit()
    
    return MessageResponse(message="密码修改成功")
