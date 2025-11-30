from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_
from typing import List, Optional
from datetime import datetime
import uuid
import os
import shutil

from database import get_db
from models.user import Case, Document, User, Professional
from schemas.case import (
    CaseCreate, CaseUpdate, CaseResponse, CaseListResponse,
    CaseDocumentUpload, CaseDocumentResponse, CaseStatusUpdate
)
from utils.auth import get_current_user as get_user_object, require_role

router = APIRouter(prefix="/api/cases", tags=["Cases"])

# Directory for uploaded documents
UPLOAD_DIR = "/home/claude/uploads/case_documents"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# Helper function to convert User to dict
def get_current_user(user: User = Depends(get_user_object)) -> dict:
    """Wrapper to convert User object to dict"""
    return {
        "user_uuid": str(user.user_uuid),
        "username": user.username,
        "role": user.role,
        "is_active": user.is_active,
        "is_verified": user.is_verified
    }


# ==================== User Endpoints (Create & Manage Own Cases) ====================

@router.post("/", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
async def create_case(
    case_data: CaseCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new case (regular users only)
    """
    # Create new case
    new_case = Case(
        case_uuid=uuid.uuid4(),
        user_uuid=uuid.UUID(current_user["user_uuid"]),
        title=case_data.title,
        description=case_data.description,
        case_category=case_data.case_category,
        priority=case_data.priority,
        budget_cny=case_data.budget_cny,
        case_status='pending'
    )
    
    db.add(new_case)
    db.commit()
    db.refresh(new_case)
    
    # Get creator username
    creator = db.query(User).filter(User.user_uuid == new_case.user_uuid).first()
    
    response = CaseResponse.from_orm(new_case)
    response.creator_username = creator.username if creator else None
    response.document_count = 0
    
    return response


@router.get("/my-cases", response_model=CaseListResponse)
async def get_my_cases(
    skip: int = 0,
    limit: int = 50,
    status_filter: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all cases created by current user
    """
    query = db.query(Case).filter(Case.user_uuid == uuid.UUID(current_user["user_uuid"]))
    
    if status_filter:
        query = query.filter(Case.case_status == status_filter)
    
    total = query.count()
    cases = query.order_by(Case.created_at.desc()).offset(skip).limit(limit).all()
    
    # Enrich with additional info
    case_responses = []
    for case in cases:
        # Get professional info if assigned
        professional_name = None
        if case.professional_uuid:
            prof = db.query(User).filter(User.user_uuid == case.professional_uuid).first()
            professional_name = prof.username if prof else None
        
        # Count documents
        doc_count = db.query(func.count(Document.document_id)).filter(
            Document.case_uuid == case.case_uuid, Document.document_type == 'upload_evidence'
        ).scalar()
        
        response = CaseResponse.from_orm(case)
        response.creator_username = current_user["username"]
        response.professional_name = professional_name
        response.document_count = doc_count
        case_responses.append(response)
    
    return CaseListResponse(
        cases=case_responses,
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/{case_uuid}", response_model=CaseResponse)
async def get_case_detail(
    case_uuid: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get case details. Users can only see their own cases or cases they're assigned to.
    """
    case = db.query(Case).filter(Case.case_uuid == case_uuid).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    user_uuid = uuid.UUID(current_user["user_uuid"])
    
    # Check permissions
    if current_user["role"] == "admin":
        pass  # Admin can see all
    elif current_user["role"] == "professional":
        # Professionals can see pending cases or their assigned cases
        if case.case_status == "pending" or case.professional_uuid == user_uuid:
            pass
        else:
            raise HTTPException(status_code=403, detail="Access denied")
    elif current_user["role"] == "user":
        # Users can only see their own cases
        if case.user_uuid != user_uuid:
            raise HTTPException(status_code=403, detail="Access denied")
    
    # Get creator info
    creator = db.query(User).filter(User.user_uuid == case.user_uuid).first()
    
    # Get professional info if assigned
    professional_name = None
    if case.professional_uuid:
        prof = db.query(User).filter(User.user_uuid == case.professional_uuid).first()
        professional_name = prof.username if prof else None
    
    # Count documents
    doc_count = db.query(func.count(Document.document_id)).filter(
        Document.case_uuid == case.case_uuid, Document.document_type == 'upload_evidence'
    ).scalar()
    
    response = CaseResponse.from_orm(case)
    response.creator_username = creator.username if creator else None
    response.professional_name = professional_name
    response.document_count = doc_count
    
    return response


@router.put("/{case_uuid}", response_model=CaseResponse)
async def update_case(
    case_uuid: uuid.UUID,
    case_data: CaseUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update case (only by creator)
    """
    case = db.query(Case).filter(Case.case_uuid == case_uuid).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Only case creator can update
    if case.user_uuid != uuid.UUID(current_user["user_uuid"]):
        raise HTTPException(status_code=403, detail="Only case creator can update")
    
    # Can only update if case is still pending
    if case.case_status != 'pending':
        raise HTTPException(status_code=400, detail="Cannot update case that is already assigned")
    
    # Update fields
    update_data = case_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(case, field, value)
    
    case.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(case)
    
    response = CaseResponse.from_orm(case)
    response.creator_username = current_user["username"]
    response.document_count = db.query(func.count(Document.document_id)).filter(
        Document.case_uuid == case.case_uuid, Document.document_type == 'upload_evidence'
    ).scalar()
    
    return response


@router.delete("/{case_uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_case(
    case_uuid: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete case (only by creator, only if pending)
    """
    case = db.query(Case).filter(Case.case_uuid == case_uuid).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Only case creator can delete
    if case.user_uuid != uuid.UUID(current_user["user_uuid"]):
        raise HTTPException(status_code=403, detail="Only case creator can delete")
    
    # Can only delete if still pending
    if case.case_status != 'pending':
        raise HTTPException(status_code=400, detail="Cannot delete case that is already assigned")
    
    # Delete associated documents
    documents = db.query(Document).filter(Document.case_uuid == case_uuid, Document.document_type == 'upload_evidence').all()
    for doc in documents:
        # Delete physical file if exists
        if os.path.exists(doc.document_url):
            os.remove(doc.document_url)
        db.delete(doc)
    
    db.delete(case)
    db.commit()
    
    return None


# ==================== Document Management ====================

@router.post("/{case_uuid}/documents", response_model=CaseDocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_case_document(
    case_uuid: uuid.UUID,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload document for a case
    """
    case = db.query(Case).filter(Case.case_uuid == case_uuid).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Check permissions
    user_uuid = uuid.UUID(current_user["user_uuid"])
    if case.user_uuid != user_uuid and case.professional_uuid != user_uuid and current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Create directory for this case
    case_dir = os.path.join(UPLOAD_DIR, str(case_uuid))
    os.makedirs(case_dir, exist_ok=True)
    
    # Save file
    file_uuid = str(uuid.uuid4())
    file_extension = os.path.splitext(file.filename)[1]
    file_path = os.path.join(case_dir, f"{file_uuid}{file_extension}")
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Get file size
    file_size = os.path.getsize(file_path)
    
    # Create document record (new unified Document model)
    document = Document(
        document_id=uuid.uuid4(),
        user_uuid=user_uuid,
        case_uuid=case_uuid,
        document_type='upload_evidence',  # Type for case documents
        file_name=file.filename,
        file_path=file_path,
        file_size=file_size,
        mime_type=file.content_type
    )
    
    db.add(document)
    db.commit()
    db.refresh(document)
    
    response = CaseDocumentResponse.from_orm(document)
    response.uploader_username = current_user["username"]
    
    return response


@router.get("/{case_uuid}/documents", response_model=List[CaseDocumentResponse])
async def get_case_documents(
    case_uuid: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all documents for a case
    """
    case = db.query(Case).filter(Case.case_uuid == case_uuid).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Check permissions
    user_uuid = uuid.UUID(current_user["user_uuid"])
    if current_user["role"] == "admin":
        pass
    elif current_user["role"] == "professional":
        if case.case_status == "pending" or case.professional_uuid == user_uuid:
            pass
        else:
            raise HTTPException(status_code=403, detail="Access denied")
    elif case.user_uuid != user_uuid:
        raise HTTPException(status_code=403, detail="Access denied")
    
    documents = db.query(Document).filter(Document.case_uuid == case_uuid, Document.document_type == 'upload_evidence').all()
    
    # Enrich with uploader info
    doc_responses = []
    for doc in documents:
        uploader = db.query(User).filter(User.user_uuid == doc.uploaded_by_uuid).first()
        response = CaseDocumentResponse.from_orm(doc)
        response.uploader_username = uploader.username if uploader else None
        doc_responses.append(response)
    
    return doc_responses


@router.delete("/{case_uuid}/documents/{document_uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_case_document(
    case_uuid: uuid.UUID,
    document_uuid: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a case document
    """
    document = db.query(Document).filter(
        Document.document_id == document_uuid,
        Document.case_uuid == case_uuid
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    case = db.query(Case).filter(Case.case_uuid == case_uuid).first()
    
    # Only uploader or case creator can delete
    user_uuid = uuid.UUID(current_user["user_uuid"])
    if document.uploaded_by_uuid != user_uuid and case.user_uuid != user_uuid and current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Delete physical file
    if os.path.exists(document.document_url):
        os.remove(document.document_url)
    
    db.delete(document)
    db.commit()
    
    return None


# ==================== Professional Endpoints ====================

@router.get("/pool/available", response_model=CaseListResponse)
async def get_available_cases(
    skip: int = 0,
    limit: int = 50,
    category: Optional[str] = None,
    priority: Optional[str] = None,
    current_user: dict = Depends(require_role("professional")),
    db: Session = Depends(get_db)
):
    """
    Get all pending cases available for professionals to accept
    """
    query = db.query(Case).filter(Case.case_status == 'pending')
    
    if category:
        query = query.filter(Case.case_category == category)
    
    if priority:
        query = query.filter(Case.priority == priority)
    
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
    
    return CaseListResponse(
        cases=case_responses,
        total=total,
        skip=skip,
        limit=limit
    )


@router.post("/{case_uuid}/accept", response_model=CaseResponse)
async def accept_case(
    case_uuid: uuid.UUID,
    current_user: dict = Depends(require_role("professional")),
    db: Session = Depends(get_db)
):
    """
    Professional accepts a case
    """
    case = db.query(Case).filter(Case.case_uuid == case_uuid).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Check if case is still pending
    if case.case_status != 'pending':
        raise HTTPException(status_code=400, detail="Case is no longer available")
    
    # Check if professional is verified
    professional = db.query(Professional).filter(
        Professional.user_uuid == uuid.UUID(current_user["user_uuid"])
    ).first()
    
    if not professional or not professional.is_verified:
        raise HTTPException(
            status_code=403, 
            detail="Only verified professionals can accept cases"
        )
    
    # Assign case to professional
    case.professional_uuid = uuid.UUID(current_user["user_uuid"])
    case.case_status = 'accepted'
    case.accepted_at = datetime.utcnow()
    case.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(case)
    
    # Get creator info
    creator = db.query(User).filter(User.user_uuid == case.user_uuid).first()
    doc_count = db.query(func.count(Document.document_id)).filter(
        Document.case_uuid == case.case_uuid, Document.document_type == 'upload_evidence'
    ).scalar()
    
    response = CaseResponse.from_orm(case)
    response.creator_username = creator.username if creator else None
    response.professional_name = current_user["username"]
    response.document_count = doc_count
    
    return response


@router.get("/professional/my-cases", response_model=CaseListResponse)
async def get_professional_cases(
    skip: int = 0,
    limit: int = 50,
    status_filter: Optional[str] = None,
    current_user: dict = Depends(require_role("professional")),
    db: Session = Depends(get_db)
):
    """
    Get all cases assigned to current professional
    """
    query = db.query(Case).filter(
        Case.professional_uuid == uuid.UUID(current_user["user_uuid"])
    )
    
    if status_filter:
        query = query.filter(Case.case_status == status_filter)
    
    total = query.count()
    cases = query.order_by(Case.accepted_at.desc()).offset(skip).limit(limit).all()
    
    # Enrich with additional info
    case_responses = []
    for case in cases:
        creator = db.query(User).filter(User.user_uuid == case.user_uuid).first()
        doc_count = db.query(func.count(Document.document_id)).filter(
            Document.case_uuid == case.case_uuid, Document.document_type == 'upload_evidence'
        ).scalar()
        
        response = CaseResponse.from_orm(case)
        response.creator_username = creator.username if creator else None
        response.professional_name = current_user["username"]
        response.document_count = doc_count
        case_responses.append(response)
    
    return CaseListResponse(
        cases=case_responses,
        total=total,
        skip=skip,
        limit=limit
    )


@router.put("/{case_uuid}/status", response_model=CaseResponse)
async def update_case_status(
    case_uuid: uuid.UUID,
    status_data: CaseStatusUpdate,
    current_user: dict = Depends(require_role("professional")),
    db: Session = Depends(get_db)
):
    """
    Professional updates case status
    """
    case = db.query(Case).filter(Case.case_uuid == case_uuid).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Only assigned professional can update status
    if case.professional_uuid != uuid.UUID(current_user["user_uuid"]):
        raise HTTPException(status_code=403, detail="Only assigned professional can update status")
    
    old_status = case.case_status
    case.case_status = status_data.status
    case.updated_at = datetime.utcnow()
    
    if status_data.status == 'completed' and old_status != 'completed':
        case.completed_at = datetime.utcnow()
        
        # Update professional statistics
        professional = db.query(Professional).filter(
            Professional.user_uuid == case.professional_uuid
        ).first()
        if professional:
            professional.total_cases_handled += 1
    
    db.commit()
    db.refresh(case)
    
    creator = db.query(User).filter(User.user_uuid == case.user_uuid).first()
    doc_count = db.query(func.count(Document.document_id)).filter(
        Document.case_uuid == case.case_uuid, Document.document_type == 'upload_evidence'
    ).scalar()
    
    response = CaseResponse.from_orm(case)
    response.creator_username = creator.username if creator else None
    response.professional_name = current_user["username"]
    response.document_count = doc_count
    
    return response


# ==================== Admin Endpoints ====================

@router.get("/admin/all", response_model=CaseListResponse)
async def admin_get_all_cases(
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[str] = None,
    current_user: dict = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    """
    Admin: Get all cases in the system
    """
    query = db.query(Case)
    
    if status_filter:
        query = query.filter(Case.case_status == status_filter)
    
    total = query.count()
    cases = query.order_by(Case.created_at.desc()).offset(skip).limit(limit).all()
    
    # Enrich with additional info
    case_responses = []
    for case in cases:
        creator = db.query(User).filter(User.user_uuid == case.user_uuid).first()
        professional_name = None
        if case.professional_uuid:
            prof = db.query(User).filter(User.user_uuid == case.professional_uuid).first()
            professional_name = prof.username if prof else None
        
        doc_count = db.query(func.count(Document.document_id)).filter(
            Document.case_uuid == case.case_uuid, Document.document_type == 'upload_evidence'
        ).scalar()
        
        response = CaseResponse.from_orm(case)
        response.creator_username = creator.username if creator else None
        response.professional_name = professional_name
        response.document_count = doc_count
        case_responses.append(response)
    
    return CaseListResponse(
        cases=case_responses,
        total=total,
        skip=skip,
        limit=limit
    )


@router.delete("/admin/{case_uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_case(
    case_uuid: uuid.UUID,
    current_user: dict = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    """
    Admin: Delete any case
    """
    case = db.query(Case).filter(Case.case_uuid == case_uuid).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Delete associated documents
    documents = db.query(Document).filter(Document.case_uuid == case_uuid, Document.document_type == 'upload_evidence').all()
    for doc in documents:
        if os.path.exists(doc.document_url):
            os.remove(doc.document_url)
        db.delete(doc)
    
    db.delete(case)
    db.commit()
    
    return None
