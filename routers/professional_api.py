from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List
from decimal import Decimal
from pydantic import BaseModel
from datetime import datetime
import uuid

from database import get_db
from models.user import User, Professional, UserProfile, Case, Document, ProfessionalVerification
from utils.auth import get_current_user
from utils.verification_middleware import require_verified_professional, get_professional_status  # NEW
from schemas.case import CaseResponse, CaseListResponse

router = APIRouter(prefix="/api/professional", tags=["Professional"])


class ProfessionalProfileUpdate(BaseModel):
    # Professional-specific fields (editable)
    license_number: Optional[str] = None
    law_firm_name: Optional[str] = None
    specialty_areas: Optional[List[str]] = None
    years_of_experience: Optional[int] = None
    education_background: Optional[str] = None
    bio: Optional[str] = None
    hourly_rate_cny: Optional[Decimal] = None
    consultation_fee_cny: Optional[Decimal] = None
    
    # User profile fields (editable)
    full_name: Optional[str] = None
    phone: Optional[str] = None
    city_name: Optional[str] = None
    province_name: Optional[str] = None
    address_line: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "license_number": "LAW-2024-001",
                "law_firm_name": "北京律师事务所",
                "specialty_areas": ["民事诉讼", "公司法", "知识产权"],
                "years_of_experience": 10,
                "education_background": "北京大学法学院 法学硕士",
                "bio": "专注于企业法律服务10年...",
                "hourly_rate_cny": 800.00,
                "consultation_fee_cny": 500.00,
                "full_name": "张律师",
                "city_name": "北京",
                "province_name": "北京市"
            }
        }


class ProfessionalProfileResponse(BaseModel):
    # User info
    user_uuid: str
    username: Optional[str]
    phone: Optional[str]
    is_verified: bool
    
    # Profile info
    full_name: Optional[str]
    city_name: Optional[str]
    province_name: Optional[str]
    address_line: Optional[str]
    
    # Professional info (editable)
    professional_uuid: Optional[str]
    license_number: Optional[str]
    law_firm_name: Optional[str]
    specialty_areas: Optional[List[str]]
    years_of_experience: Optional[int]
    education_background: Optional[str]
    bio: Optional[str]
    hourly_rate_cny: Optional[Decimal]
    consultation_fee_cny: Optional[Decimal]
    
    # Professional info (read-only, admin-managed)
    average_rating: Optional[Decimal]
    total_cases_handled: Optional[int]
    success_rate: Optional[Decimal]
    account_status: Optional[str]
    is_professional_verified: Optional[bool]
    verified_at: Optional[str]
    
    created_at: str
    
    class Config:
        from_attributes = True


def require_professional(current_user: User = Depends(get_current_user)):
    """Dependency to ensure user is professional"""
    if current_user.role != 'professional':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要专业人士权限"
        )
    return current_user


# NEW: Verification status endpoint
@router.get("/verification-status")
async def check_verification_status(
    professional_status: dict = Depends(get_professional_status)
):
    """
    Check professional verification status
    Returns verification state without blocking access
    """
    return professional_status


# NEW: Professional statistics endpoint
@router.get("/stats")
async def get_professional_stats(
    current_user: User = Depends(require_professional),
    db: Session = Depends(get_db)
):
    """
    Get professional statistics
    Returns zeros if not verified - dashboard accessible to all professionals
    """
    # Get professional record
    professional = db.query(Professional).filter(
        Professional.user_uuid == current_user.user_uuid
    ).first()
    
    # If no professional record or not verified, return zeros
    if not professional or not professional.is_verified:
        return {
            "total_cases": 0,
            "pending_cases": 0,
            "in_progress_cases": 0,
            "completed_cases": 0,
            "total_earnings": 0.0,
            "average_rating": 0.0,
            "success_rate": 0.0,
            "is_verified": False
        }
    
    # Count cases by status
    total_cases = db.query(func.count(Case.case_uuid)).filter(
        Case.professional_uuid == current_user.user_uuid
    ).scalar()
    
    pending_cases = db.query(func.count(Case.case_uuid)).filter(
        Case.professional_uuid == current_user.user_uuid,
        Case.case_status == 'pending'
    ).scalar()
    
    in_progress_cases = db.query(func.count(Case.case_uuid)).filter(
        Case.professional_uuid == current_user.user_uuid,
        Case.case_status == 'in_progress'
    ).scalar()
    
    completed_cases = db.query(func.count(Case.case_uuid)).filter(
        Case.professional_uuid == current_user.user_uuid,
        Case.case_status == 'completed'
    ).scalar()
    
    # Calculate total earnings (sum of completed case budgets)
    total_earnings = db.query(func.sum(Case.budget_cny)).filter(
        Case.professional_uuid == current_user.user_uuid,
        Case.case_status == 'completed'
    ).scalar() or 0
    
    return {
        "total_cases": total_cases,
        "pending_cases": pending_cases,
        "in_progress_cases": in_progress_cases,
        "completed_cases": completed_cases,
        "total_earnings": float(total_earnings),
        "average_rating": float(professional.average_rating) if professional.average_rating else 0,
        "success_rate": float(professional.success_rate) if professional.success_rate else 0,
        "is_verified": True
    }


# NEW: My cases endpoint (no verification required)
@router.get("/my-cases")
async def get_my_cases(
    current_user: User = Depends(require_professional),
    db: Session = Depends(get_db)
):
    """
    Get cases assigned to this professional
    Returns empty array if not verified - dashboard accessible to all professionals
    """
    # Get professional record
    professional = db.query(Professional).filter(
        Professional.user_uuid == current_user.user_uuid
    ).first()
    
    # If no professional record or not verified, return empty
    if not professional or not professional.is_verified:
        return {"cases": [], "total": 0, "is_verified": False}
    
    cases = db.query(Case).filter(
        Case.professional_uuid == current_user.user_uuid
    ).order_by(Case.created_at.desc()).all()
    
    # Get document counts
    result = []
    for case in cases:
        doc_count = db.query(func.count(Document.document_id)).filter(
            Document.case_uuid == case.case_uuid, 
            Document.document_type == 'upload_evidence'
        ).scalar()
        
        case_dict = {
            "case_uuid": str(case.case_uuid),
            "title": case.title,
            "description": case.description,
            "case_category": case.case_category,
            "priority": case.priority,
            "case_status": case.case_status,
            "budget_cny": float(case.budget_cny) if case.budget_cny else None,
            "document_count": doc_count,
            "created_at": case.created_at.isoformat() if case.created_at else None,
            "accepted_at": case.accepted_at.isoformat() if case.accepted_at else None,
            "completed_at": case.completed_at.isoformat() if case.completed_at else None
        }
        result.append(case_dict)
    
    return {"cases": result, "total": len(result), "is_verified": True}


@router.get("/me", response_model=ProfessionalProfileResponse)
async def get_professional_profile(
    current_user: User = Depends(require_professional),
    db: Session = Depends(get_db)
):
    """
    Get current professional's complete profile
    """
    # Get user profile
    profile = db.query(UserProfile).filter(
        UserProfile.user_uuid == current_user.user_uuid
    ).first()
    
    if not profile:
        profile = UserProfile(user_uuid=current_user.user_uuid)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    
    # Get professional profile
    professional = db.query(Professional).filter(
        Professional.user_uuid == current_user.user_uuid
    ).first()
    
    # Build response
    return ProfessionalProfileResponse(
        user_uuid=str(current_user.user_uuid),
        username=current_user.username,
        phone=current_user.phone,
        is_verified=current_user.is_verified,
        full_name=profile.full_name,
        city_name=profile.city_name,
        province_name=profile.province_name,
        address_line=profile.address_line,
        professional_uuid=str(professional.professional_uuid) if professional else None,
        license_number=professional.license_number if professional else None,
        law_firm_name=professional.law_firm_name if professional else None,
        specialty_areas=professional.specialty_areas if professional else None,
        years_of_experience=professional.years_of_experience if professional else None,
        education_background=professional.education_background if professional else None,
        bio=professional.bio if professional else None,
        hourly_rate_cny=professional.hourly_rate_cny if professional else None,
        consultation_fee_cny=professional.consultation_fee_cny if professional else None,
        average_rating=professional.average_rating if professional else None,
        total_cases_handled=professional.total_cases_handled if professional else None,
        success_rate=professional.success_rate if professional else None,
        account_status=professional.account_status if professional else None,
        is_professional_verified=professional.is_verified if professional else False,
        verified_at=professional.verified_at.isoformat() if professional and professional.verified_at else None,
        created_at=current_user.created_at.isoformat()
    )


@router.put("/me", response_model=ProfessionalProfileResponse)
async def update_professional_profile(
    profile_data: ProfessionalProfileUpdate,
    current_user: User = Depends(require_professional),
    db: Session = Depends(get_db)
):
    """
    Update current professional's profile
    Excludes admin-managed fields (rating, cases, success_rate, etc.)
    """
    # Update user profile fields
    profile = db.query(UserProfile).filter(
        UserProfile.user_uuid == current_user.user_uuid
    ).first()
    
    if not profile:
        profile = UserProfile(user_uuid=current_user.user_uuid)
        db.add(profile)
    
    if profile_data.full_name is not None:
        profile.full_name = profile_data.full_name
    if profile_data.city_name is not None:
        profile.city_name = profile_data.city_name
    if profile_data.province_name is not None:
        profile.province_name = profile_data.province_name
    if profile_data.address_line is not None:
        profile.address_line = profile_data.address_line
    
    # Get or create professional profile
    professional = db.query(Professional).filter(
        Professional.user_uuid == current_user.user_uuid
    ).first()
    
    if not professional:
        # Create new professional profile
        if not profile_data.license_number:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="首次创建专业资料需要提供执业证号"
            )
        
        professional = Professional(
            user_uuid=current_user.user_uuid,
            license_number=profile_data.license_number
        )
        db.add(professional)
    
    # Update professional fields (only editable ones)
    if profile_data.license_number is not None:
        # Check if license number is already used by another professional
        existing = db.query(Professional).filter(
            Professional.license_number == profile_data.license_number,
            Professional.user_uuid != current_user.user_uuid
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="该执业证号已被使用"
            )
        professional.license_number = profile_data.license_number
    
    if profile_data.law_firm_name is not None:
        professional.law_firm_name = profile_data.law_firm_name
    if profile_data.specialty_areas is not None:
        professional.specialty_areas = profile_data.specialty_areas
    if profile_data.years_of_experience is not None:
        professional.years_of_experience = profile_data.years_of_experience
    if profile_data.education_background is not None:
        professional.education_background = profile_data.education_background
    if profile_data.bio is not None:
        professional.bio = profile_data.bio
    if profile_data.hourly_rate_cny is not None:
        professional.hourly_rate_cny = profile_data.hourly_rate_cny
    if profile_data.consultation_fee_cny is not None:
        professional.consultation_fee_cny = profile_data.consultation_fee_cny
    
    db.commit()
    db.refresh(professional)
    db.refresh(profile)
    
    # Return updated profile
    return ProfessionalProfileResponse(
        user_uuid=str(current_user.user_uuid),
        username=current_user.username,
        phone=current_user.phone,
        is_verified=current_user.is_verified,
        full_name=profile.full_name,
        city_name=profile.city_name,
        province_name=profile.province_name,
        address_line=profile.address_line,
        professional_uuid=str(professional.professional_uuid),
        license_number=professional.license_number,
        law_firm_name=professional.law_firm_name,
        specialty_areas=professional.specialty_areas,
        years_of_experience=professional.years_of_experience,
        education_background=professional.education_background,
        bio=professional.bio,
        hourly_rate_cny=professional.hourly_rate_cny,
        consultation_fee_cny=professional.consultation_fee_cny,
        average_rating=professional.average_rating,
        total_cases_handled=professional.total_cases_handled,
        success_rate=professional.success_rate,
        account_status=professional.account_status,
        is_professional_verified=professional.is_verified,
        verified_at=professional.verified_at.isoformat() if professional.verified_at else None,
        created_at=current_user.created_at.isoformat()
    )


@router.get("/public/{user_uuid}", response_model=ProfessionalProfileResponse)
async def get_professional_public_profile(
    user_uuid: str,
    db: Session = Depends(get_db)
):
    """
    Get public professional profile (for matching/search)
    Anyone can view this
    """
    user = db.query(User).filter(
        User.user_uuid == user_uuid,
        User.role == 'professional'
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="专业人士不存在"
        )
    
    profile = db.query(UserProfile).filter(
        UserProfile.user_uuid == user.user_uuid
    ).first()
    
    professional = db.query(Professional).filter(
        Professional.user_uuid == user.user_uuid
    ).first()
    
    if not professional:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="专业资料不存在"
        )
    
    return ProfessionalProfileResponse(
        user_uuid=str(user.user_uuid),
        username=user.username,
        phone=None,  # Hide phone in public profile
        is_verified=user.is_verified,
        full_name=profile.full_name if profile else None,
        city_name=profile.city_name if profile else None,
        province_name=profile.province_name if profile else None,
        address_line=None,  # Hide detailed address in public profile
        professional_uuid=str(professional.professional_uuid),
        license_number=professional.license_number,
        law_firm_name=professional.law_firm_name,
        specialty_areas=professional.specialty_areas,
        years_of_experience=professional.years_of_experience,
        education_background=professional.education_background,
        bio=professional.bio,
        hourly_rate_cny=professional.hourly_rate_cny,
        consultation_fee_cny=professional.consultation_fee_cny,
        average_rating=professional.average_rating,
        total_cases_handled=professional.total_cases_handled,
        success_rate=professional.success_rate,
        account_status=professional.account_status,
        is_professional_verified=professional.is_verified,
        verified_at=professional.verified_at.isoformat() if professional.verified_at else None,
        created_at=user.created_at.isoformat()
    )


@router.get("/available-cases")
async def get_available_cases(
    skip: int = 0,
    limit: int = 50,
    category: Optional[str] = None,
    professional: Professional = Depends(require_verified_professional),
    db: Session = Depends(get_db)
):
    """
    Get all open/pending cases available for professionals to accept
    REQUIRES: Verified professional - blocks access if not verified
    """
    # Query pending cases for verified professionals
    query = db.query(Case).filter(Case.case_status == 'pending')
    
    if category:
        query = query.filter(Case.case_category == category)
    
    total = query.count()
    cases = query.order_by(Case.created_at.desc()).offset(skip).limit(limit).all()
    
    # Enrich with additional info
    case_responses = []
    for case in cases:
        creator = db.query(User).filter(User.user_uuid == case.user_uuid).first()
        doc_count = db.query(func.count(Document.document_id)).filter(
            Document.case_uuid == case.case_uuid, Document.document_type == 'upload_evidence'
        ).scalar()
        
        response = CaseResponse.from_orm(case)
        response.creator_username = creator.username if creator else None
        response.document_count = doc_count
        case_responses.append(response)
    
    return {
        "cases": [case.dict() for case in case_responses],
        "total": total
    }


@router.post("/cases/{case_uuid}/accept", response_model=CaseResponse)
async def accept_case(
    case_uuid: str,
    professional: Professional = Depends(require_verified_professional),
    db: Session = Depends(get_db)
):
    """
    Professional accepts a case from the pool
    REQUIRES: Verified professional - blocks if not verified
    """
    # Get the case
    try:
        case_uuid_obj = uuid.UUID(case_uuid)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的案件ID"
        )
    
    case = db.query(Case).filter(Case.case_uuid == case_uuid_obj).first()
    if not case:
        raise HTTPException(status_code=404, detail="案件不存在")
    
    # Check if case is still pending
    if case.case_status != 'pending':
        raise HTTPException(status_code=400, detail="该案件已被接受或已关闭")
    
    # Assign case to professional
    case.professional_uuid = professional.user_uuid
    case.case_status = 'accepted'
    case.accepted_at = datetime.utcnow()
    case.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(case)
    
    # Get creator info
    creator = db.query(User).filter(User.user_uuid == case.user_uuid).first()
    current_user = db.query(User).filter(User.user_uuid == professional.user_uuid).first()
    doc_count = db.query(func.count(Document.document_id)).filter(
        Document.case_uuid == case.case_uuid, Document.document_type == 'upload_evidence'
    ).scalar()
    
    response = CaseResponse.from_orm(case)
    response.creator_username = creator.username if creator else None
    response.professional_name = current_user.username if current_user else None
    response.document_count = doc_count
    
    return response


@router.get("/profile")
async def get_professional_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get professional profile information
    """
    if current_user.role != 'professional':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅专业人员可访问"
        )
    
    # Get professional record
    professional = db.query(Professional).filter(
        Professional.user_uuid == current_user.user_uuid
    ).first()
    
    if not professional:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到专业资料"
        )
    
    # Get full_name, city_name, province_name from UserProfile
    from models.user import UserProfile
    user_profile = db.query(UserProfile).filter(
        UserProfile.user_uuid == current_user.user_uuid
    ).first()
    
    # Get additional info from most recent approved verification request
    verification = db.query(ProfessionalVerification).filter(
        ProfessionalVerification.user_uuid == current_user.user_uuid,
        ProfessionalVerification.status == 'approved'
    ).order_by(ProfessionalVerification.created_at.desc()).first()
    
    # Parse specialty areas if it's a string
    specialty_areas = professional.specialty_areas
    if isinstance(specialty_areas, str):
        try:
            import json
            specialty_areas = json.loads(specialty_areas)
        except:
            specialty_areas = []
    elif specialty_areas is None:
        specialty_areas = []
    
    # Get full_name from multiple sources (priority: verification > user_profile > username)
    full_name = None
    if verification and verification.full_name:
        full_name = verification.full_name
    elif user_profile and user_profile.full_name:
        full_name = user_profile.full_name
    else:
        full_name = current_user.username
    
    # Get location from verification
    city_name = verification.city_name if verification else (user_profile.city_name if user_profile else None)
    province_name = verification.province_name if verification else (user_profile.province_name if user_profile else None)
    
    return {
        "professional_uuid": str(professional.professional_uuid),
        "user_uuid": str(professional.user_uuid),
        "full_name": full_name,
        "license_number": professional.license_number,
        "law_firm_name": professional.law_firm_name,
        "specialty_areas": specialty_areas,
        "years_of_experience": professional.years_of_experience,
        "education_background": professional.education_background,
        "bio": professional.bio,
        "consultation_fee_cny": float(professional.consultation_fee_cny) if professional.consultation_fee_cny else 0,
        "hourly_rate_cny": float(professional.hourly_rate_cny) if professional.hourly_rate_cny else 0,
        "city_name": city_name,
        "province_name": province_name,
        "is_verified": professional.is_verified,
        "verified_at": professional.verified_at.isoformat() if professional.verified_at else None,
        "account_status": professional.account_status
    }

