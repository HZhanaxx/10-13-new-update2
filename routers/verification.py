from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status as http_status
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from typing import List, Optional
from datetime import datetime
import os
import uuid as uuid_lib
import shutil

from database import get_db
from models.user import User, Professional, ProfessionalVerification, Document
from utils.auth import get_current_user
from pydantic import BaseModel

router = APIRouter(prefix="/api/verification", tags=["verification"])

# Upload directory
UPLOAD_DIR = "uploads/verification_docs"
os.makedirs(UPLOAD_DIR, exist_ok=True)


class VerificationReview(BaseModel):
    request_uuid: str
    status: str  # approved or rejected
    admin_notes: Optional[str] = None


class VerificationUpdateRequest(BaseModel):
    """Model for professional profile update request"""
    full_name: str
    license_number: str
    law_firm_name: str
    specialty_areas: str  # JSON string
    years_of_experience: int
    education_background: Optional[str] = None
    bio: Optional[str] = None
    consultation_fee_cny: Optional[float] = 0
    hourly_rate_cny: Optional[float] = 0
    city_name: Optional[str] = None
    province_name: Optional[str] = None


@router.post("/request")
async def create_verification_request(
    full_name: str = Form(...),
    license_number: str = Form(...),
    law_firm_name: Optional[str] = Form(None),
    specialty_areas: List[str] = Form([]),
    years_of_experience: Optional[int] = Form(None),
    education_background: Optional[str] = Form(None),
    bio: Optional[str] = Form(None),
    consultation_fee_cny: Optional[float] = Form(None),
    hourly_rate_cny: Optional[float] = Form(None),
    city_name: Optional[str] = Form(None),
    province_name: Optional[str] = Form(None),
    files: List[UploadFile] = File([]),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit verification request with documents"""
    
    # Check if user is professional
    if current_user.role != "professional":
        raise HTTPException(status_code=403, detail="Only professionals can request verification")
    
    # Check if there's already a pending request
    existing_request = db.query(ProfessionalVerification).filter(
        and_(
            ProfessionalVerification.user_uuid == current_user.user_uuid,
            ProfessionalVerification.status == "pending"
        )
    ).first()
    
    if existing_request:
        raise HTTPException(status_code=400, detail="You already have a pending verification request")
    
    # Validate at least one file
    if not files or not any(f.filename for f in files):
        raise HTTPException(status_code=400, detail="At least one document file is required")
    
    # Create verification request
    verification = ProfessionalVerification(
        user_uuid=current_user.user_uuid,
        full_name=full_name,
        license_number=license_number,
        law_firm_name=law_firm_name,
        specialty_areas=specialty_areas if specialty_areas else None,
        years_of_experience=years_of_experience,
        education_background=education_background,
        bio=bio,
        consultation_fee_cny=consultation_fee_cny,
        hourly_rate_cny=hourly_rate_cny,
        city_name=city_name,
        province_name=province_name,
        status="pending"
    )
    
    db.add(verification)
    db.flush()  # Get the request_uuid before committing
    
    # Save uploaded files as Document records
    for file in files:
        if file.filename:
            # Generate unique filename
            file_ext = os.path.splitext(file.filename)[1]
            unique_filename = f"{uuid_lib.uuid4()}{file_ext}"
            file_path = os.path.join(UPLOAD_DIR, unique_filename)
            
            # Save file
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # Get file size
            file_size = os.path.getsize(file_path)
            
            # Create Document record
            document = Document(
                user_uuid=current_user.user_uuid,
                verification_id=verification.request_uuid,
                document_type='verification_doc',
                file_name=file.filename,
                file_path=file_path,
                file_size=file_size,
                mime_type=file.content_type
            )
            db.add(document)
    
    db.commit()
    db.refresh(verification)
    
    return {
        "message": "Verification request submitted successfully",
        "request_uuid": str(verification.request_uuid),
        "status": verification.status
    }


@router.get("/my-request")
async def get_my_verification_request(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's verification request status"""
    
    if current_user.role != "professional":
        raise HTTPException(status_code=403, detail="Only professionals can check verification status")
    
    verification = db.query(ProfessionalVerification).filter(
        ProfessionalVerification.user_uuid == current_user.user_uuid
    ).order_by(ProfessionalVerification.created_at.desc()).first()
    
    if not verification:
        return {"status": "none", "message": "No verification request found"}
    
    # Get associated documents
    documents = db.query(Document).filter(
        and_(
            Document.verification_id == verification.request_uuid,
            Document.document_type == 'verification_doc'
        )
    ).all()
    
    doc_list = [{
        "document_id": str(doc.document_id),
        "file_name": doc.file_name,
        "file_size": doc.file_size,
        "mime_type": doc.mime_type,
        "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None
    } for doc in documents]
    
    return {
        "request_uuid": str(verification.request_uuid),
        "status": verification.status,
        "full_name": verification.full_name,
        "license_number": verification.license_number,
        "law_firm_name": verification.law_firm_name,
        "specialty_areas": verification.specialty_areas,
        "years_of_experience": verification.years_of_experience,
        "education_background": verification.education_background,
        "bio": verification.bio,
        "consultation_fee_cny": float(verification.consultation_fee_cny) if verification.consultation_fee_cny else None,
        "hourly_rate_cny": float(verification.hourly_rate_cny) if verification.hourly_rate_cny else None,
        "city_name": verification.city_name,
        "province_name": verification.province_name,
        "documents": doc_list,
        "admin_notes": verification.admin_notes,
        "reviewed_at": verification.reviewed_at.isoformat() if verification.reviewed_at else None,
        "created_at": verification.created_at.isoformat(),
        "updated_at": verification.updated_at.isoformat()
    }


@router.get("/requests")
async def get_all_verification_requests(
    status_filter: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all verification requests (Admin only)"""
    
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    query = db.query(ProfessionalVerification)
    
    if status_filter:
        query = query.filter(ProfessionalVerification.status == status_filter)
    
    verifications = query.order_by(ProfessionalVerification.created_at.desc()).all()
    
    result = []
    for verif in verifications:
        # Get user info
        user = db.query(User).filter(User.user_uuid == verif.user_uuid).first()
        
        # Get document count
        doc_count = db.query(func.count(Document.document_id)).filter(
            and_(
                Document.verification_id == verif.request_uuid,
                Document.document_type == 'verification_doc'
            )
        ).scalar()
        
        result.append({
            "request_uuid": str(verif.request_uuid),
            "user_uuid": str(verif.user_uuid),
            "username": user.username if user else None,
            "phone": user.phone if user else None,
            "status": verif.status,
            "full_name": verif.full_name,
            "license_number": verif.license_number,
            "law_firm_name": verif.law_firm_name,
            "specialty_areas": verif.specialty_areas,
            "years_of_experience": verif.years_of_experience,
            "education_background": verif.education_background,
            "bio": verif.bio,
            "consultation_fee_cny": float(verif.consultation_fee_cny) if verif.consultation_fee_cny else None,
            "hourly_rate_cny": float(verif.hourly_rate_cny) if verif.hourly_rate_cny else None,
            "city_name": verif.city_name,
            "province_name": verif.province_name,
            "document_count": doc_count,
            "admin_notes": verif.admin_notes,
            "reviewed_at": verif.reviewed_at.isoformat() if verif.reviewed_at else None,
            "created_at": verif.created_at.isoformat(),
            "updated_at": verif.updated_at.isoformat()
        })
    
    return result


@router.get("/requests/{request_uuid}")
async def get_verification_request_detail(
    request_uuid: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get single verification request with documents (Admin only)"""
    
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        request_uuid_obj = uuid_lib.UUID(request_uuid)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid request UUID")
    
    verification = db.query(ProfessionalVerification).filter(
        ProfessionalVerification.request_uuid == request_uuid_obj
    ).first()
    
    if not verification:
        raise HTTPException(status_code=404, detail="Verification request not found")
    
    # Get user info
    user = db.query(User).filter(User.user_uuid == verification.user_uuid).first()
    
    # Get documents
    documents = db.query(Document).filter(
        and_(
            Document.verification_id == verification.request_uuid,
            Document.document_type == 'verification_doc'
        )
    ).all()
    
    doc_list = [{
        "document_id": str(doc.document_id),
        "file_name": doc.file_name,
        "file_path": doc.file_path,
        "file_size": doc.file_size,
        "mime_type": doc.mime_type,
        "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None
    } for doc in documents]
    
    return {
        "request_uuid": str(verification.request_uuid),
        "user_uuid": str(verification.user_uuid),
        "username": user.username if user else None,
        "phone": user.phone if user else None,
        "email": user.email if user else None,
        "status": verification.status,
        "full_name": verification.full_name,
        "license_number": verification.license_number,
        "law_firm_name": verification.law_firm_name,
        "specialty_areas": verification.specialty_areas,
        "years_of_experience": verification.years_of_experience,
        "education_background": verification.education_background,
        "bio": verification.bio,
        "consultation_fee_cny": float(verification.consultation_fee_cny) if verification.consultation_fee_cny else None,
        "hourly_rate_cny": float(verification.hourly_rate_cny) if verification.hourly_rate_cny else None,
        "city_name": verification.city_name,
        "province_name": verification.province_name,
        "documents": doc_list,
        "admin_notes": verification.admin_notes,
        "reviewed_by_uuid": str(verification.reviewed_by_uuid) if verification.reviewed_by_uuid else None,
        "reviewed_at": verification.reviewed_at.isoformat() if verification.reviewed_at else None,
        "created_at": verification.created_at.isoformat(),
        "updated_at": verification.updated_at.isoformat(),
        "status_history": verification.status_history
    }


@router.post("/review")
async def review_verification_request(
    review: VerificationReview,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Review and approve/reject verification request (Admin only)"""
    
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Validate status
    if review.status not in ['approved', 'rejected']:
        raise HTTPException(status_code=400, detail="Status must be 'approved' or 'rejected'")
    
    # Get the verification request
    try:
        request_uuid_obj = uuid_lib.UUID(review.request_uuid)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid request UUID")
    
    verification = db.query(ProfessionalVerification).filter(
        ProfessionalVerification.request_uuid == request_uuid_obj
    ).first()
    
    if not verification:
        raise HTTPException(status_code=404, detail="Verification request not found")
    
    if verification.status != "pending":
        raise HTTPException(status_code=400, detail="Request has already been reviewed")
    
    # Update verification status
    old_status = verification.status
    verification.status = review.status
    verification.admin_notes = review.admin_notes
    verification.reviewed_by_uuid = current_user.user_uuid
    verification.reviewed_at = datetime.utcnow()
    
    # Update status history
    if verification.status_history is None:
        verification.status_history = []
    
    verification.status_history.append({
        "status": review.status,
        "reviewed_by": str(current_user.user_uuid),
        "reviewed_at": datetime.utcnow().isoformat(),
        "admin_notes": review.admin_notes
    })
    
    # If approved, update user and create/update professional profile
    if review.status == "approved":
        # Update user verification status
        user = db.query(User).filter(User.user_uuid == verification.user_uuid).first()
        if user:
            user.is_verified = True
        
        # Create or update professional profile
        professional = db.query(Professional).filter(
            Professional.user_uuid == verification.user_uuid
        ).first()
        
        if professional:
            # Update existing professional
            professional.is_verified = True
            professional.verified_at = datetime.utcnow()
            professional.verified_by_admin_uuid = current_user.user_uuid
            professional.license_number = verification.license_number
            professional.law_firm_name = verification.law_firm_name
            professional.specialty_areas = verification.specialty_areas
            professional.years_of_experience = verification.years_of_experience
            professional.education_background = verification.education_background
            professional.bio = verification.bio
            professional.consultation_fee_cny = verification.consultation_fee_cny
            professional.hourly_rate_cny = verification.hourly_rate_cny
        else:
            # Create new professional profile
            professional = Professional(
                user_uuid=verification.user_uuid,
                license_number=verification.license_number,
                law_firm_name=verification.law_firm_name,
                specialty_areas=verification.specialty_areas,
                years_of_experience=verification.years_of_experience,
                education_background=verification.education_background,
                bio=verification.bio,
                consultation_fee_cny=verification.consultation_fee_cny,
                hourly_rate_cny=verification.hourly_rate_cny,
                is_verified=True,
                verified_at=datetime.utcnow(),
                verified_by_admin_uuid=current_user.user_uuid,
                account_status='active'
            )
            db.add(professional)
    
    db.commit()
    
    return {
        "message": "Verification request reviewed successfully",
        "status": review.status,
        "request_uuid": str(verification.request_uuid)
    }


@router.post("/update")
async def update_professional_profile(
    update_data: VerificationUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Professional updates their profile - creates new verification request for admin review
    """
    if current_user.role != 'professional':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅专业人员可更新资料"
        )
    
    # Check if there's already a pending verification request
    existing_pending = db.query(ProfessionalVerification).filter(
        ProfessionalVerification.user_uuid == current_user.user_uuid,
        ProfessionalVerification.status == 'pending'
    ).first()
    
    if existing_pending:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="您已有待审核的资料更新请求"
        )
    
    # Create new verification request
    new_verification = ProfessionalVerification(
        request_uuid=uuid_lib.uuid4(),
        user_uuid=current_user.user_uuid,
        full_name=update_data.full_name,
        license_number=update_data.license_number,
        law_firm_name=update_data.law_firm_name,
        specialty_areas=update_data.specialty_areas,
        years_of_experience=update_data.years_of_experience,
        education_background=update_data.education_background,
        bio=update_data.bio,
        consultation_fee_cny=update_data.consultation_fee_cny,
        hourly_rate_cny=update_data.hourly_rate_cny,
        city_name=update_data.city_name,
        province_name=update_data.province_name,
        status='pending',
        created_at=datetime.utcnow()
    )
    
    db.add(new_verification)
    db.commit()
    db.refresh(new_verification)
    
    return {
        "message": "资料更新请求已提交，等待管理员审核",
        "request_uuid": str(new_verification.request_uuid),
        "status": "pending"
    }
