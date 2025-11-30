from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime
import uuid


# ==========================================
# Authentication Schemas
# ==========================================
class UserRegister(BaseModel):
    username: Optional[str] = Field(None, min_length=5, max_length=50, description="Username must be 5-50 characters")
    phone: Optional[str] = Field(None, max_length=20, description="Phone number (optional)")
    password: str = Field(..., min_length=8, max_length=100, description="Password must be at least 8 characters with uppercase")
    sms_code: Optional[str] = Field(None, min_length=6, max_length=6)
    role: str = Field(default="user", pattern="^(user|professional)$")
    device_info: Optional[dict] = None

    @validator('username')
    def validate_username(cls, v):
        if v is not None and len(v) < 5:
            raise ValueError('Username must be at least 5 characters')
        return v

    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not any(char.isupper() for char in v):
            raise ValueError('Password must contain at least one uppercase letter')
        # Recommended but not required
        has_digit = any(char.isdigit() for char in v)
        has_lower = any(char.islower() for char in v)
        return v


class UserLogin(BaseModel):
    username: Optional[str] = None
    phone: Optional[str] = None
    password: str
    device_info: Optional[dict] = None


class PhoneLogin(BaseModel):
    phone: str = Field(..., pattern=r"^1[3-9]\d{9}$")
    sms_code: str = Field(..., min_length=6, max_length=6)
    device_info: Optional[dict] = None


class WeChatLogin(BaseModel):
    code: str  # WeChat authorization code
    device_info: Optional[dict] = None


class SMSCodeRequest(BaseModel):
    phone: str = Field(..., pattern=r"^1[3-9]\d{9}$")
    purpose: str = Field(..., pattern="^(login|register|reset_password)$")


class TokenRefresh(BaseModel):
    refresh_token: str


class PasswordReset(BaseModel):
    phone: str = Field(..., pattern=r"^1[3-9]\d{9}$")
    sms_code: str = Field(..., min_length=6, max_length=6)
    new_password: str = Field(..., min_length=8, max_length=100)


class PasswordChange(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=8, max_length=100)


# ==========================================
# Response Schemas
# ==========================================
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    user_uuid: uuid.UUID
    username: Optional[str]
    phone: Optional[str]
    role: str
    is_active: bool
    is_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    user: UserResponse
    token: Token


class MessageResponse(BaseModel):
    message: str
    success: bool = True


# ==========================================
# Profile Schemas
# ==========================================
class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = Field(None, max_length=100)
    nickname: Optional[str] = Field(None, max_length=50)
    avatar_url: Optional[str] = None
    gender: Optional[str] = Field(None, pattern="^(male|female|other)$")
    description: Optional[str] = None
    address_line: Optional[str] = None
    city_name: Optional[str] = None
    province_name: Optional[str] = None
    postal_code: Optional[str] = None
    date_of_birth: Optional[str] = None  # Format: YYYY-MM-DD


class UserProfileResponse(BaseModel):
    profile_uuid: uuid.UUID
    user_uuid: uuid.UUID
    full_name: Optional[str]
    nickname: Optional[str]
    avatar_url: Optional[str]
    gender: Optional[str]
    description: Optional[str]
    city_name: Optional[str]
    province_name: Optional[str]

    class Config:
        from_attributes = True
