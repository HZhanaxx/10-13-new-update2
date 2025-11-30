from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime, timedelta
from typing import List, Optional
from pydantic import BaseModel
from decimal import Decimal
import uuid as uuid_lib
import os

from database import get_db
from models.user import User, UserSession, RefreshToken, UserProfile, Professional, AdminLog, Case, ProfessionalVerification, Document
from utils.auth import get_current_user
from utils.redis_client import redis_client

router = APIRouter(prefix="/api/admin", tags=["Admin"])

# Define how long a session is considered "online" (in minutes)
ONLINE_THRESHOLD_MINUTES = 5


async def log_admin_action(
    db: Session,
    admin_uuid: str,
    action_type: str,
    request: Request,
    target_table: Optional[str] = None,
    target_uuid: Optional[str] = None,
    details: Optional[dict] = None
):
    """Helper function to log admin actions"""
    log = AdminLog(
        admin_user_uuid=admin_uuid,
        action_type=action_type,
        target_table_name=target_table,
        target_record_uuid=target_uuid,
        action_details=details,
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent", "")
    )
    db.add(log)
    db.commit()


class UserListItem(BaseModel):
    user_uuid: str
    username: Optional[str]
    phone: Optional[str]
    role: str
    is_active: bool
    is_verified: bool
    last_login_at: Optional[str]
    created_at: str
    
    class Config:
        from_attributes = True


class SessionInfo(BaseModel):
    session_uuid: str
    user_uuid: str
    username: Optional[str]
    role: str
    ip_address: Optional[str]
    user_agent: Optional[str]
    is_active: bool
    is_online: bool  # New field to indicate if truly online
    created_at: str
    last_activity_at: str
    expires_at: str


class ActivityLog(BaseModel):
    user_uuid: str
    username: Optional[str]
    action: str
    timestamp: str
    ip_address: Optional[str]


class AdminStats(BaseModel):
    total_users: int
    active_users: int
    total_professionals: int
    active_sessions: int
    online_users: int  # New field for truly online users
    total_sessions_today: int


def require_admin(current_user: User = Depends(get_current_user)):
    """Dependency to ensure user is admin"""
    if current_user.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    return current_user


def is_session_online(session: UserSession) -> bool:
    """
    Check if a session is truly online based on recent activity
    A session is considered online if last_activity_at is within the threshold
    """
    if not session.is_active or session.expires_at <= datetime.utcnow():
        return False
    
    threshold = datetime.utcnow() - timedelta(minutes=ONLINE_THRESHOLD_MINUTES)
    return session.last_activity_at >= threshold


@router.get("/stats")
async def get_admin_stats(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get admin dashboard statistics
    Returns data in camelCase for frontend compatibility
    """
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    total_professionals = db.query(User).filter(User.role == 'professional').count()
    
    # Count all active sessions (not expired)
    active_sessions = db.query(UserSession).filter(
        UserSession.is_active == True,
        UserSession.expires_at > datetime.utcnow()
    ).count()
    
    # Count truly online users (recent activity)
    online_threshold = datetime.utcnow() - timedelta(minutes=ONLINE_THRESHOLD_MINUTES)
    online_users = db.query(UserSession).filter(
        UserSession.is_active == True,
        UserSession.expires_at > datetime.utcnow(),
        UserSession.last_activity_at >= online_threshold
    ).count()
    
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    total_sessions_today = db.query(UserSession).filter(
        UserSession.created_at >= today_start
    ).count()
    
    # Count total cases
    total_cases = db.query(Case).count()
    
    # Count pending verifications
    pending_verifications = db.query(ProfessionalVerification).filter(
        ProfessionalVerification.status == 'pending'
    ).count()
    
    # Return in camelCase for frontend
    return {
        "totalUsers": total_users,
        "activeUsers": active_users,
        "totalProfessionals": total_professionals,
        "activeSessions": active_sessions,
        "onlineUsers": online_users,
        "totalSessionsToday": total_sessions_today,
        "totalCases": total_cases,
        "pendingVerifications": pending_verifications
    }


@router.get("/users", response_model=List[UserListItem])
async def get_all_users(
    skip: int = 0,
    limit: int = 100,
    role: Optional[str] = None,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get list of all users with optional filtering
    """
    query = db.query(User)
    
    if role:
        query = query.filter(User.role == role)
    
    users = query.order_by(desc(User.created_at)).offset(skip).limit(limit).all()
    
    return [
        UserListItem(
            user_uuid=str(user.user_uuid),
            username=user.username,
            phone=user.phone,
            role=user.role,
            is_active=user.is_active,
            is_verified=user.is_verified,
            last_login_at=user.last_login_at.isoformat() if user.last_login_at else None,
            created_at=user.created_at.isoformat()
        )
        for user in users
    ]


@router.get("/sessions/online", response_model=List[SessionInfo])
async def get_online_sessions(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get only truly online user sessions (with recent activity)
    This shows who is CURRENTLY using the application
    """
    online_threshold = datetime.utcnow() - timedelta(minutes=ONLINE_THRESHOLD_MINUTES)
    
    sessions = db.query(UserSession, User).join(
        User, UserSession.user_uuid == User.user_uuid
    ).filter(
        UserSession.is_active == True,
        UserSession.expires_at > datetime.utcnow(),
        UserSession.last_activity_at >= online_threshold
    ).order_by(desc(UserSession.last_activity_at)).all()
    
    return [
        SessionInfo(
            session_uuid=str(session.session_uuid),
            user_uuid=str(session.user_uuid),
            username=user.username,
            role=user.role,
            ip_address=str(session.ip_address) if session.ip_address else None,
            user_agent=session.user_agent,
            is_active=session.is_active,
            is_online=True,  # All sessions here are online
            created_at=session.created_at.isoformat(),
            last_activity_at=session.last_activity_at.isoformat(),
            expires_at=session.expires_at.isoformat()
        )
        for session, user in sessions
    ]


@router.get("/sessions/active", response_model=List[SessionInfo])
async def get_active_sessions(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get all active user sessions (not expired, but may be idle)
    """
    online_threshold = datetime.utcnow() - timedelta(minutes=ONLINE_THRESHOLD_MINUTES)
    
    sessions = db.query(UserSession, User).join(
        User, UserSession.user_uuid == User.user_uuid
    ).filter(
        UserSession.is_active == True,
        UserSession.expires_at > datetime.utcnow()
    ).order_by(desc(UserSession.last_activity_at)).all()
    
    return [
        SessionInfo(
            session_uuid=str(session.session_uuid),
            user_uuid=str(session.user_uuid),
            username=user.username,
            role=user.role,
            ip_address=str(session.ip_address) if session.ip_address else None,
            user_agent=session.user_agent,
            is_active=session.is_active,
            is_online=session.last_activity_at >= online_threshold,  # Check if online
            created_at=session.created_at.isoformat(),
            last_activity_at=session.last_activity_at.isoformat(),
            expires_at=session.expires_at.isoformat()
        )
        for session, user in sessions
    ]


@router.get("/sessions/all", response_model=List[SessionInfo])
async def get_all_sessions(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get all sessions (active and inactive) - for audit logs
    """
    online_threshold = datetime.utcnow() - timedelta(minutes=ONLINE_THRESHOLD_MINUTES)
    
    sessions = db.query(UserSession, User).join(
        User, UserSession.user_uuid == User.user_uuid
    ).order_by(desc(UserSession.created_at)).offset(skip).limit(limit).all()
    
    return [
        SessionInfo(
            session_uuid=str(session.session_uuid),
            user_uuid=str(session.user_uuid),
            username=user.username,
            role=user.role,
            ip_address=str(session.ip_address) if session.ip_address else None,
            user_agent=session.user_agent,
            is_active=session.is_active,
            is_online=(session.is_active and 
                      session.expires_at > datetime.utcnow() and
                      session.last_activity_at >= online_threshold),
            created_at=session.created_at.isoformat(),
            last_activity_at=session.last_activity_at.isoformat(),
            expires_at=session.expires_at.isoformat()
        )
        for session, user in sessions
    ]


@router.post("/sessions/cleanup")
async def cleanup_expired_sessions(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Cleanup expired sessions and mark them as inactive
    This can be called manually or set up as a scheduled task
    """
    # Find expired sessions
    expired_sessions = db.query(UserSession).filter(
        UserSession.is_active == True,
        UserSession.expires_at <= datetime.utcnow()
    ).all()
    
    cleanup_count = 0
    for session in expired_sessions:
        # Revoke tokens in Redis
        await redis_client.revoke_access_token(session.access_token_jti)
        if session.refresh_token_jti:
            await redis_client.revoke_refresh_token(session.refresh_token_jti)
        
        # Remove from user's active sessions in Redis
        await redis_client.remove_user_session(
            str(session.user_uuid),
            str(session.session_uuid)
        )
        
        # Mark session as inactive
        session.is_active = False
        
        # Revoke associated refresh tokens
        db.query(RefreshToken).filter(
            RefreshToken.session_uuid == session.session_uuid,
            RefreshToken.is_revoked == False
        ).update({
            "is_revoked": True,
            "revoked_at": datetime.utcnow(),
            "revoked_reason": "expired"
        })
        
        cleanup_count += 1
    
    db.commit()
    
    return {
        "message": f"已清理 {cleanup_count} 个过期会话",
        "cleaned_sessions": cleanup_count
    }


@router.post("/users/{user_uuid}/deactivate")
async def deactivate_user(
    user_uuid: str,
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Deactivate a user account
    """
    user = db.query(User).filter(User.user_uuid == user_uuid).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    if user.role == 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无法停用管理员账户"
        )
    
    user.is_active = False
    db.commit()
    
    # Log action
    await log_admin_action(
        db=db,
        admin_uuid=str(current_user.user_uuid),
        action_type="deactivate_user",
        request=request,
        target_table="users",
        target_uuid=user_uuid,
        details={"username": user.username, "role": user.role}
    )
    
    return {"message": f"用户 {user.username or user.phone} 已被停用"}


@router.post("/users/{user_uuid}/activate")
async def activate_user(
    user_uuid: str,
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Activate a user account
    """
    user = db.query(User).filter(User.user_uuid == user_uuid).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    user.is_active = True
    db.commit()
    
    # Log action
    await log_admin_action(
        db=db,
        admin_uuid=str(current_user.user_uuid),
        action_type="activate_user",
        request=request,
        target_table="users",
        target_uuid=user_uuid,
        details={"username": user.username, "role": user.role}
    )
    
    return {"message": f"用户 {user.username or user.phone} 已激活"}


@router.post("/sessions/{session_uuid}/revoke")
async def revoke_session(
    session_uuid: str,
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Manually revoke a specific session
    """
    from uuid import UUID
    
    try:
        session_uuid_obj = UUID(session_uuid)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的会话ID"
        )
    
    session = db.query(UserSession).filter(
        UserSession.session_uuid == session_uuid_obj
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在"
        )
    
    # Revoke tokens in Redis
    await redis_client.revoke_access_token(session.access_token_jti)
    if session.refresh_token_jti:
        await redis_client.revoke_refresh_token(session.refresh_token_jti)
    
    # Remove from user's active sessions
    await redis_client.remove_user_session(
        str(session.user_uuid),
        str(session.session_uuid)
    )
    
    # Mark session as inactive
    session.is_active = False
    
    # Revoke refresh token in database
    db.query(RefreshToken).filter(
        RefreshToken.session_uuid == session_uuid_obj,
        RefreshToken.is_revoked == False
    ).update({
        "is_revoked": True,
        "revoked_at": datetime.utcnow(),
        "revoked_reason": "admin_revoked"
    })
    
    db.commit()
    
    # Log action
    await log_admin_action(
        db=db,
        admin_uuid=str(current_user.user_uuid),
        action_type="revoke_session",
        request=request,
        target_table="user_sessions",
        target_uuid=session_uuid,
        details={"user_uuid": str(session.user_uuid)}
    )
    
    return {"message": "会话已被撤销"}


@router.post("/users/{user_uuid}/revoke-all-sessions")
async def revoke_all_user_sessions(
    user_uuid: str,
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Revoke all sessions for a specific user
    """
    user = db.query(User).filter(User.user_uuid == user_uuid).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    # Get all active sessions for this user
    sessions = db.query(UserSession).filter(
        UserSession.user_uuid == user_uuid,
        UserSession.is_active == True
    ).all()
    
    revoked_count = 0
    for session in sessions:
        # Revoke tokens in Redis
        await redis_client.revoke_access_token(session.access_token_jti)
        if session.refresh_token_jti:
            await redis_client.revoke_refresh_token(session.refresh_token_jti)
        
        # Mark session as inactive
        session.is_active = False
        revoked_count += 1
    
    # Remove all user sessions from Redis
    await redis_client.revoke_all_user_sessions(user_uuid)
    
    # Revoke all refresh tokens
    db.query(RefreshToken).filter(
        RefreshToken.user_uuid == user_uuid,
        RefreshToken.is_revoked == False
    ).update({
        "is_revoked": True,
        "revoked_at": datetime.utcnow(),
        "revoked_reason": "admin_revoke_all"
    })
    
    db.commit()
    
    # Log action
    await log_admin_action(
        db=db,
        admin_uuid=str(current_user.user_uuid),
        action_type="revoke_all_sessions",
        request=request,
        target_table="users",
        target_uuid=user_uuid,
        details={
            "username": user.username,
            "sessions_revoked": revoked_count
        }
    )
    
    return {
        "message": f"已撤销用户 {user.username or user.phone} 的所有会话",
        "sessions_revoked": revoked_count
    }


class ProfessionalListItem(BaseModel):
    professional_uuid: str
    user_uuid: str
    username: Optional[str]
    full_name: Optional[str]
    license_number: str
    law_firm_name: Optional[str]
    specialty_areas: Optional[List[str]]
    years_of_experience: Optional[int]
    average_rating: Optional[Decimal]
    total_cases_handled: int
    success_rate: Optional[Decimal]
    account_status: str
    is_verified: bool
    verified_at: Optional[str]
    created_at: str


class ProfessionalStatsUpdate(BaseModel):
    average_rating: Optional[Decimal] = None
    total_cases_handled: Optional[int] = None
    success_rate: Optional[Decimal] = None
    account_status: Optional[str] = None


class AdminLogItem(BaseModel):
    log_uuid: str
    admin_username: Optional[str]
    action_type: str
    target_table_name: Optional[str]
    target_record_uuid: Optional[str]
    action_details: Optional[dict]
    ip_address: Optional[str]
    performed_at: str


@router.get("/professionals", response_model=List[ProfessionalListItem])
async def get_all_professionals(
    skip: int = 0,
    limit: int = 100,
    verified_only: bool = False,
    request: Request = None,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get list of all professionals with their details
    """
    query = db.query(Professional, User, UserProfile).join(
        User, Professional.user_uuid == User.user_uuid
    ).outerjoin(
        UserProfile, User.user_uuid == UserProfile.user_uuid
    )
    
    if verified_only:
        query = query.filter(Professional.is_verified == True)
    
    professionals = query.order_by(desc(Professional.created_at)).offset(skip).limit(limit).all()
    
    return [
        ProfessionalListItem(
            professional_uuid=str(prof.professional_uuid),
            user_uuid=str(user.user_uuid),
            username=user.username,
            full_name=profile.full_name if profile else None,
            license_number=prof.license_number,
            law_firm_name=prof.law_firm_name,
            specialty_areas=prof.specialty_areas,
            years_of_experience=prof.years_of_experience,
            average_rating=prof.average_rating,
            total_cases_handled=prof.total_cases_handled,
            success_rate=prof.success_rate,
            account_status=prof.account_status,
            is_verified=prof.is_verified,
            verified_at=prof.verified_at.isoformat() if prof.verified_at else None,
            created_at=prof.created_at.isoformat()
        )
        for prof, user, profile in professionals
    ]


@router.post("/professionals/{professional_uuid}/verify")
async def verify_professional(
    professional_uuid: str,
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Verify a professional's credentials
    """
    professional = db.query(Professional).filter(
        Professional.professional_uuid == professional_uuid
    ).first()
    
    if not professional:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="专业人士不存在"
        )
    
    professional.is_verified = True
    professional.verified_at = datetime.utcnow()
    professional.verified_by_admin_uuid = current_user.user_uuid
    professional.account_status = 'active'
    
    db.commit()
    
    # Log action
    await log_admin_action(
        db=db,
        admin_uuid=str(current_user.user_uuid),
        action_type="verify_professional",
        request=request,
        target_table="professionals",
        target_uuid=professional_uuid,
        details={"license_number": professional.license_number}
    )
    
    return {"message": f"专业人士 {professional.license_number} 已通过验证"}


@router.post("/professionals/{professional_uuid}/unverify")
async def unverify_professional(
    professional_uuid: str,
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Revoke professional verification
    """
    professional = db.query(Professional).filter(
        Professional.professional_uuid == professional_uuid
    ).first()
    
    if not professional:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="专业人士不存在"
        )
    
    professional.is_verified = False
    professional.verified_at = None
    professional.verified_by_admin_uuid = None
    professional.account_status = 'pending'
    
    db.commit()
    
    # Log action
    await log_admin_action(
        db=db,
        admin_uuid=str(current_user.user_uuid),
        action_type="unverify_professional",
        request=request,
        target_table="professionals",
        target_uuid=professional_uuid,
        details={"license_number": professional.license_number}
    )
    
    return {"message": f"已撤销专业人士 {professional.license_number} 的验证"}


@router.put("/professionals/{professional_uuid}/stats")
async def update_professional_stats(
    professional_uuid: str,
    stats: ProfessionalStatsUpdate,
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Update professional's performance statistics
    (Admin-only fields)
    """
    professional = db.query(Professional).filter(
        Professional.professional_uuid == professional_uuid
    ).first()
    
    if not professional:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="专业人士不存在"
        )
    
    update_details = {}
    
    if stats.average_rating is not None:
        if stats.average_rating < 0 or stats.average_rating > 5:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="评分必须在 0-5 之间"
            )
        professional.average_rating = stats.average_rating
        update_details['average_rating'] = float(stats.average_rating)
    
    if stats.total_cases_handled is not None:
        professional.total_cases_handled = stats.total_cases_handled
        update_details['total_cases_handled'] = stats.total_cases_handled
    
    if stats.success_rate is not None:
        if stats.success_rate < 0 or stats.success_rate > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="成功率必须在 0-100 之间"
            )
        professional.success_rate = stats.success_rate
        update_details['success_rate'] = float(stats.success_rate)
    
    if stats.account_status is not None:
        valid_statuses = ['active', 'pending', 'suspended', 'inactive']
        if stats.account_status not in valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"账户状态必须是: {', '.join(valid_statuses)}"
            )
        professional.account_status = stats.account_status
        update_details['account_status'] = stats.account_status
    
    db.commit()
    
    # Log action
    await log_admin_action(
        db=db,
        admin_uuid=str(current_user.user_uuid),
        action_type="update_professional_stats",
        request=request,
        target_table="professionals",
        target_uuid=professional_uuid,
        details=update_details
    )
    
    return {"message": "专业人士统计信息已更新", "updates": update_details}


@router.get("/logs", response_model=List[AdminLogItem])
async def get_admin_logs(
    skip: int = 0,
    limit: int = 100,
    action_type: Optional[str] = None,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get admin action logs
    """
    query = db.query(AdminLog, User).outerjoin(
        User, AdminLog.admin_user_uuid == User.user_uuid
    )
    
    if action_type:
        query = query.filter(AdminLog.action_type == action_type)
    
    logs = query.order_by(desc(AdminLog.performed_at)).offset(skip).limit(limit).all()
    
    return [
        AdminLogItem(
            log_uuid=str(log.log_uuid),
            admin_username=admin.username if admin else None,
            action_type=log.action_type,
            target_table_name=log.target_table_name,
            target_record_uuid=str(log.target_record_uuid) if log.target_record_uuid else None,
            action_details=log.action_details,
            ip_address=str(log.ip_address) if log.ip_address else None,
            performed_at=log.performed_at.isoformat()
        )
        for log, admin in logs
    ]


class CaseListItem(BaseModel):
    case_uuid: str
    user_uuid: str
    professional_uuid: Optional[str]
    title: str
    description: str
    case_category: Optional[str]
    priority: str
    case_status: str
    budget_cny: Optional[Decimal]
    created_at: str
    updated_at: str
    accepted_at: Optional[str]
    completed_at: Optional[str]

    class Config:
        from_attributes = True


@router.get("/all-cases", response_model=List[CaseListItem])
async def get_all_cases(
    skip: int = 0,
    limit: int = 1000,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    category: Optional[str] = None,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get all cases in the system for admin monitoring
    """
    query = db.query(Case)
    
    # Apply filters if provided
    if status:
        query = query.filter(Case.case_status == status)
    if priority:
        query = query.filter(Case.priority == priority)
    if category:
        query = query.filter(Case.case_category == category)
    
    cases = query.order_by(desc(Case.created_at)).offset(skip).limit(limit).all()
    
    return [
        CaseListItem(
            case_uuid=str(case.case_uuid),
            user_uuid=str(case.user_uuid),
            professional_uuid=str(case.professional_uuid) if case.professional_uuid else None,
            title=case.title,
            description=case.description,
            case_category=case.case_category,
            priority=case.priority,
            case_status=case.case_status,
            budget_cny=case.budget_cny,
            created_at=case.created_at.isoformat(),
            updated_at=case.updated_at.isoformat(),
            accepted_at=case.accepted_at.isoformat() if case.accepted_at else None,
            completed_at=case.completed_at.isoformat() if case.completed_at else None
        )
        for case in cases
    ]


# ==================== Professional Verification Management ====================

class VerificationRequestItem(BaseModel):
    """Schema for verification request in list"""
    request_uuid: str
    user_uuid: str
    username: Optional[str]
    full_name: str
    license_number: str
    law_firm_name: Optional[str]
    specialty_areas: Optional[List[str]]
    years_of_experience: Optional[int]
    status: str
    document_count: int
    created_at: str
    reviewed_at: Optional[str]


class VerificationRequestDetail(BaseModel):
    """Schema for detailed verification request"""
    request_uuid: str
    user_uuid: str
    username: Optional[str]
    phone: Optional[str]
    full_name: str
    license_number: str
    law_firm_name: Optional[str]
    specialty_areas: Optional[List[str]]
    years_of_experience: Optional[int]
    education_background: Optional[str]
    bio: Optional[str]
    consultation_fee_cny: Optional[float]
    hourly_rate_cny: Optional[float]
    city_name: Optional[str]
    province_name: Optional[str]
    status: str
    admin_notes: Optional[str]
    reviewed_by_uuid: Optional[str]
    reviewed_at: Optional[str]
    documents: List[dict]
    created_at: str
    updated_at: str


class VerificationApproval(BaseModel):
    """Schema for verification approval/rejection"""
    status: str  # 'approved' or 'rejected'
    admin_notes: Optional[str] = None


@router.get("/verifications", response_model=List[VerificationRequestItem])
async def get_verification_requests(
    status_filter: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    request: Request = None,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get all professional verification requests (Admin only)
    Filter by status: pending, approved, rejected, revoked
    """
    query = db.query(ProfessionalVerification)
    
    if status_filter:
        query = query.filter(ProfessionalVerification.status == status_filter)
    
    verifications = query.order_by(desc(ProfessionalVerification.created_at)).offset(skip).limit(limit).all()
    
    result = []
    for verif in verifications:
        # Get user info
        user = db.query(User).filter(User.user_uuid == verif.user_uuid).first()
        
        # Count documents
        doc_count = db.query(Document).filter(
            Document.verification_id == verif.request_uuid,
            Document.document_type == 'verification_doc'
        ).count()
        
        result.append(VerificationRequestItem(
            request_uuid=str(verif.request_uuid),
            user_uuid=str(verif.user_uuid),
            username=user.username if user else None,
            full_name=verif.full_name,
            license_number=verif.license_number,
            law_firm_name=verif.law_firm_name,
            specialty_areas=verif.specialty_areas,
            years_of_experience=verif.years_of_experience,
            status=verif.status,
            document_count=doc_count,
            created_at=verif.created_at.isoformat() if verif.created_at else None,
            reviewed_at=verif.reviewed_at.isoformat() if verif.reviewed_at else None
        ))
    
    return result


@router.get("/verifications/stats")
async def get_verification_stats(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get verification request statistics
    """
    total_requests = db.query(ProfessionalVerification).count()
    pending_requests = db.query(ProfessionalVerification).filter(
        ProfessionalVerification.status == 'pending'
    ).count()
    approved_requests = db.query(ProfessionalVerification).filter(
        ProfessionalVerification.status == 'approved'
    ).count()
    rejected_requests = db.query(ProfessionalVerification).filter(
        ProfessionalVerification.status == 'rejected'
    ).count()
    
    return {
        "total": total_requests,
        "pending": pending_requests,
        "approved": approved_requests,
        "rejected": rejected_requests
    }


@router.get("/verifications/{request_uuid}", response_model=VerificationRequestDetail)
async def get_verification_detail(
    request_uuid: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get detailed verification request information (Admin only)
    """
    verification = db.query(ProfessionalVerification).filter(
        ProfessionalVerification.request_uuid == uuid_lib.UUID(request_uuid)
    ).first()
    
    if not verification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="验证请求不存在"
        )
    
    # Get user info
    user = db.query(User).filter(User.user_uuid == verification.user_uuid).first()
    
    # Get documents
    documents = db.query(Document).filter(
        Document.verification_id == verification.request_uuid,
        Document.document_type == 'verification_doc'
    ).all()
    
    doc_list = [
        {
            "document_id": str(doc.document_id),
            "file_name": doc.file_name,
            "file_path": doc.file_path,
            "file_size": doc.file_size,
            "mime_type": doc.mime_type,
            "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None
        }
        for doc in documents
    ]
    
    return VerificationRequestDetail(
        request_uuid=str(verification.request_uuid),
        user_uuid=str(verification.user_uuid),
        username=user.username if user else None,
        phone=user.phone if user else None,
        full_name=verification.full_name,
        license_number=verification.license_number,
        law_firm_name=verification.law_firm_name,
        specialty_areas=verification.specialty_areas,
        years_of_experience=verification.years_of_experience,
        education_background=verification.education_background,
        bio=verification.bio,
        consultation_fee_cny=float(verification.consultation_fee_cny) if verification.consultation_fee_cny else None,
        hourly_rate_cny=float(verification.hourly_rate_cny) if verification.hourly_rate_cny else None,
        city_name=verification.city_name,
        province_name=verification.province_name,
        status=verification.status,
        admin_notes=verification.admin_notes,
        reviewed_by_uuid=str(verification.reviewed_by_uuid) if verification.reviewed_by_uuid else None,
        reviewed_at=verification.reviewed_at.isoformat() if verification.reviewed_at else None,
        documents=doc_list,
        created_at=verification.created_at.isoformat() if verification.created_at else None,
        updated_at=verification.updated_at.isoformat() if verification.updated_at else None
    )


@router.get("/verifications/documents/{document_id}")
async def get_verification_document(
    document_id: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Download/view a verification document file (Admin only)
    """
    # Get document from database
    document = db.query(Document).filter(
        Document.document_id == uuid_lib.UUID(document_id),
        Document.document_type == 'verification_doc'
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文档不存在"
        )
    
    # Check if file exists
    if not os.path.exists(document.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件不存在于服务器"
        )
    
    # Read file content
    try:
        with open(document.file_path, 'rb') as f:
            file_content = f.read()
        
        # Log file info
        print(f"📄 Serving document: {document.file_name}")
        print(f"   File path: {document.file_path}")
        print(f"   File size: {len(file_content)} bytes")
        print(f"   Mime type: {document.mime_type}")
        
        # Return file with inline disposition so it displays in browser
        return Response(
            content=file_content,
            media_type=document.mime_type or 'application/octet-stream',
            headers={
                'Content-Disposition': f'inline; filename="{document.file_name}"',
                'Cache-Control': 'no-cache',
                'Content-Length': str(len(file_content))
            }
        )
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"无法读取文件: {str(e)}"
        )


@router.post("/verifications/{request_uuid}/approve")
async def approve_verification(
    request_uuid: str,
    approval: VerificationApproval,
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Approve a professional verification request
    Creates Professional record automatically
    """
    verification = db.query(ProfessionalVerification).filter(
        ProfessionalVerification.request_uuid == uuid_lib.UUID(request_uuid)
    ).first()
    
    if not verification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="验证请求不存在"
        )
    
    if verification.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"该请求已经被{verification.status}，无法再次处理"
        )
    
    # Validate status
    if approval.status not in ["approved", "rejected"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="状态必须是 'approved' 或 'rejected'"
        )
    
    # Update verification status
    verification.status = approval.status
    verification.admin_notes = approval.admin_notes
    verification.reviewed_by_uuid = current_user.user_uuid
    verification.reviewed_at = datetime.utcnow()
    
    # If approved, create or update Professional record
    if approval.status == "approved":
        existing_prof = db.query(Professional).filter(
            Professional.user_uuid == verification.user_uuid
        ).first()
        
        if not existing_prof:
            # Create new Professional record
            professional = Professional(
                professional_uuid=uuid_lib.uuid4(),
                user_uuid=verification.user_uuid,
                license_number=verification.license_number,
                law_firm_name=verification.law_firm_name,
                specialty_areas=verification.specialty_areas,
                years_of_experience=verification.years_of_experience,
                education_background=verification.education_background,
                bio=verification.bio,
                hourly_rate_cny=verification.hourly_rate_cny,
                consultation_fee_cny=verification.consultation_fee_cny,
                is_verified=True,
                verified_at=datetime.utcnow(),
                verified_by_admin_uuid=current_user.user_uuid,
                account_status='active'
            )
            db.add(professional)
        else:
            # Update existing record
            existing_prof.license_number = verification.license_number
            existing_prof.law_firm_name = verification.law_firm_name
            existing_prof.specialty_areas = verification.specialty_areas
            existing_prof.years_of_experience = verification.years_of_experience
            existing_prof.education_background = verification.education_background
            existing_prof.bio = verification.bio
            existing_prof.hourly_rate_cny = verification.hourly_rate_cny
            existing_prof.consultation_fee_cny = verification.consultation_fee_cny
            existing_prof.is_verified = True
            existing_prof.verified_at = datetime.utcnow()
            existing_prof.verified_by_admin_uuid = current_user.user_uuid
            existing_prof.account_status = 'active'
    
    db.commit()
    
    # Log admin action
    await log_admin_action(
        db=db,
        admin_uuid=str(current_user.user_uuid),
        action_type=f"verification_{approval.status}",
        request=request,
        target_table="professional_verifications",
        target_uuid=request_uuid,
        details={
            "license_number": verification.license_number,
            "full_name": verification.full_name,
            "status": approval.status,
            "admin_notes": approval.admin_notes
        }
    )
    
    return {
        "message": f"验证请求已{approval.status}",
        "request_uuid": str(verification.request_uuid),
        "status": verification.status,
        "reviewed_at": verification.reviewed_at.isoformat() if verification.reviewed_at else None
    }


@router.post("/verifications/{request_uuid}/reject")
async def reject_verification(
    request_uuid: str,
    approval: VerificationApproval,
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Reject a professional verification request
    This is a convenience endpoint that calls approve with status='rejected'
    """
    approval.status = "rejected"
    return await approve_verification(request_uuid, approval, request, current_user, db)


@router.delete("/verifications/{request_uuid}")
async def delete_verification_request(
    request_uuid: str,
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Delete a verification request and associated documents
    """
    verification = db.query(ProfessionalVerification).filter(
        ProfessionalVerification.request_uuid == uuid_lib.UUID(request_uuid)
    ).first()
    
    if not verification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="验证请求不存在"
        )
    
    # Delete associated documents from filesystem
    documents = db.query(Document).filter(
        Document.verification_id == verification.request_uuid,
        Document.document_type == 'verification_doc'
    ).all()
    
    import os
    for doc in documents:
        if os.path.exists(doc.file_path):
            try:
                os.remove(doc.file_path)
            except Exception as e:
                print(f"Failed to delete file {doc.file_path}: {e}")
    
    # Log action before deletion
    await log_admin_action(
        db=db,
        admin_uuid=str(current_user.user_uuid),
        action_type="verification_deleted",
        request=request,
        target_table="professional_verifications",
        target_uuid=request_uuid,
        details={
            "license_number": verification.license_number,
            "full_name": verification.full_name
        }
    )
    
    # Delete verification (cascade will delete documents from DB)
    db.delete(verification)
    db.commit()
    
    return {"message": "验证请求已删除"}
