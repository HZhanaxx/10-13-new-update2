from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import date
from typing import Optional

from database import get_db
from models.user import User, UserProfile
from utils.auth import get_current_user
from pydantic import BaseModel

router = APIRouter(prefix="/api/profile", tags=["User Profile"])


class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    nickname: Optional[str] = None
    avatar_url: Optional[str] = None
    gender: Optional[str] = None
    description: Optional[str] = None
    address_line: Optional[str] = None
    city_name: Optional[str] = None
    province_name: Optional[str] = None
    postal_code: Optional[str] = None
    date_of_birth: Optional[date] = None

    class Config:
        json_schema_extra = {
            "example": {
                "full_name": "张三",
                "nickname": "小张",
                "gender": "male",
                "description": "这是我的个人简介",
                "city_name": "北京",
                "province_name": "北京市"
            }
        }


class ProfileResponse(BaseModel):
    profile_uuid: str
    user_uuid: str
    full_name: Optional[str]
    nickname: Optional[str]
    avatar_url: Optional[str]
    gender: Optional[str]
    description: Optional[str]
    address_line: Optional[str]
    city_name: Optional[str]
    province_name: Optional[str]
    postal_code: Optional[str]
    date_of_birth: Optional[date]
    
    # Add user info
    username: Optional[str]
    phone: Optional[str]
    role: str
    is_verified: bool
    created_at: str

    class Config:
        from_attributes = True


@router.get("/me", response_model=ProfileResponse)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's profile information
    """
    # Get user profile
    profile = db.query(UserProfile).filter(
        UserProfile.user_uuid == current_user.user_uuid
    ).first()
    
    if not profile:
        # Create profile if it doesn't exist
        profile = UserProfile(user_uuid=current_user.user_uuid)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    
    # Combine user and profile data
    return ProfileResponse(
        profile_uuid=str(profile.profile_uuid),
        user_uuid=str(profile.user_uuid),
        full_name=profile.full_name,
        nickname=profile.nickname,
        avatar_url=profile.avatar_url,
        gender=profile.gender,
        description=profile.description,
        address_line=profile.address_line,
        city_name=profile.city_name,
        province_name=profile.province_name,
        postal_code=profile.postal_code,
        date_of_birth=profile.date_of_birth,
        username=current_user.username,
        phone=current_user.phone,
        role=current_user.role,
        is_verified=current_user.is_verified,
        created_at=current_user.created_at.isoformat()
    )


@router.put("/me", response_model=ProfileResponse)
async def update_my_profile(
    profile_data: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update current user's profile information
    """
    # Get user profile
    profile = db.query(UserProfile).filter(
        UserProfile.user_uuid == current_user.user_uuid
    ).first()
    
    if not profile:
        # Create profile if it doesn't exist
        profile = UserProfile(user_uuid=current_user.user_uuid)
        db.add(profile)
    
    # Update only provided fields
    update_data = profile_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)
    
    db.commit()
    db.refresh(profile)
    
    # Return updated profile
    return ProfileResponse(
        profile_uuid=str(profile.profile_uuid),
        user_uuid=str(profile.user_uuid),
        full_name=profile.full_name,
        nickname=profile.nickname,
        avatar_url=profile.avatar_url,
        gender=profile.gender,
        description=profile.description,
        address_line=profile.address_line,
        city_name=profile.city_name,
        province_name=profile.province_name,
        postal_code=profile.postal_code,
        date_of_birth=profile.date_of_birth,
        username=current_user.username,
        phone=current_user.phone,
        role=current_user.role,
        is_verified=current_user.is_verified,
        created_at=current_user.created_at.isoformat()
    )


@router.delete("/avatar")
async def delete_avatar(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete user's avatar
    """
    profile = db.query(UserProfile).filter(
        UserProfile.user_uuid == current_user.user_uuid
    ).first()
    
    if profile:
        profile.avatar_url = None
        db.commit()
    
    return {"message": "头像已删除"}
