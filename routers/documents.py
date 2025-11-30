"""
Document Management Router
==========================

API endpoints for:
- Document templates management
- Document autofill/generation
- OCR processing with result parsing
- Document upload and storage

Integrates with:
- DocumentTemplate, Document, DocumentData models
- DocumentFillerService
- OCR Parser
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path
import uuid
import shutil
import json
import os
import httpx
import base64

from database import get_db
from models.user import User, Document, DocumentData, DocumentTemplate, Case
from models.questionnaire import QuestionnaireSession
from utils.auth import get_current_user
from config import settings

from pydantic import BaseModel, Field


# ============================================================================
# Pydantic Schemas
# ============================================================================

class TemplateCreate(BaseModel):
    """Create a new template"""
    template_name: str = Field(..., description="模板名称")
    template_code: str = Field(..., description="模板编号（唯一）")
    required_fields: Dict[str, Any] = Field(default_factory=dict, description="必填字段定义")


class TemplateResponse(BaseModel):
    template_id: str
    template_name: str
    template_code: str
    template_url: str
    required_fields: Dict[str, Any]
    
    class Config:
        from_attributes = True


class FillTemplateRequest(BaseModel):
    """Request to fill a template"""
    template_id: Optional[str] = None
    template_code: Optional[str] = None
    session_id: Optional[str] = Field(None, description="问卷会话ID（自动获取数据）")
    case_uuid: Optional[str] = Field(None, description="案件UUID")
    data: Optional[Dict[str, Any]] = Field(None, description="直接提供的填充数据")
    apply_fangsong: bool = True


class FillTemplateResponse(BaseModel):
    success: bool
    document_id: Optional[str] = None
    download_url: Optional[str] = None
    filled_fields: int = 0
    error: Optional[str] = None


class OCRRequest(BaseModel):
    """Request for OCR processing"""
    image_base64: Optional[str] = None
    document_type: str = "auto"  # auto, id_card, driver_license, vehicle_registration, insurance
    session_id: Optional[str] = None  # 关联到问卷会话


class OCRResponse(BaseModel):
    success: bool
    document_type: str = "unknown"
    parsed_data: Dict[str, Any] = {}
    questionnaire_format: Dict[str, Any] = {}
    confidence: float = 0.0
    document_id: Optional[str] = None
    error: Optional[str] = None


class DocumentUploadResponse(BaseModel):
    success: bool
    document_id: str
    file_name: str
    file_path: str
    document_type: str


# ============================================================================
# Router
# ============================================================================

router = APIRouter(prefix="/api/documents", tags=["documents"])


# ============================================================================
# Helper Functions
# ============================================================================

def get_templates_dir() -> Path:
    """Get the templates directory path"""
    templates_dir = Path(settings.BASE_DIR if hasattr(settings, 'BASE_DIR') else '.') / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)
    return templates_dir


def get_uploads_dir() -> Path:
    """Get the uploads directory path"""
    uploads_dir = Path(settings.BASE_DIR if hasattr(settings, 'BASE_DIR') else '.') / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    return uploads_dir


def get_generated_dir() -> Path:
    """Get the generated documents directory path"""
    gen_dir = get_uploads_dir() / "generated_documents"
    gen_dir.mkdir(parents=True, exist_ok=True)
    return gen_dir


async def call_ocr_service(image_base64: str, language: str = "ch") -> Dict[str, Any]:
    """Call the PaddleOCR service"""
    ocr_url = getattr(settings, 'PADDLEOCR_URL', 'http://localhost:8765/ocr')
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                ocr_url,
                json={"image_base64": image_base64, "language": language},
                timeout=60.0
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            return {"success": False, "error": f"OCR service error: {e.response.status_code}"}
        except httpx.TimeoutException:
            return {"success": False, "error": "OCR service timeout"}
        except Exception as e:
            return {"success": False, "error": str(e)}


# ============================================================================
# Template Management Endpoints
# ============================================================================

@router.get("/templates", response_model=List[TemplateResponse])
async def list_templates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all available document templates"""
    templates = db.query(DocumentTemplate).all()
    return [
        TemplateResponse(
            template_id=str(t.template_id),
            template_name=t.template_name,
            template_code=t.template_code,
            template_url=t.template_url,
            required_fields=t.required_fields or {}
        )
        for t in templates
    ]


@router.get("/templates/{template_code}", response_model=TemplateResponse)
async def get_template(
    template_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific template by code"""
    template = db.query(DocumentTemplate).filter(
        DocumentTemplate.template_code == template_code
    ).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return TemplateResponse(
        template_id=str(template.template_id),
        template_name=template.template_name,
        template_code=template.template_code,
        template_url=template.template_url,
        required_fields=template.required_fields or {}
    )


@router.post("/templates", response_model=TemplateResponse)
async def create_template(
    template_name: str = Form(...),
    template_code: str = Form(...),
    required_fields: str = Form("{}"),  # JSON string
    template_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload and create a new document template (admin only)"""
    # Check if admin
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Check if code already exists
    existing = db.query(DocumentTemplate).filter(
        DocumentTemplate.template_code == template_code
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Template code already exists")
    
    # Save template file
    templates_dir = get_templates_dir()
    file_ext = Path(template_file.filename).suffix
    file_path = templates_dir / f"{template_code}{file_ext}"
    
    with open(file_path, "wb") as f:
        content = await template_file.read()
        f.write(content)
    
    # Parse required fields JSON
    try:
        fields = json.loads(required_fields)
    except json.JSONDecodeError:
        fields = {}
    
    # Create database record
    template = DocumentTemplate(
        template_id=uuid.uuid4(),
        template_name=template_name,
        template_code=template_code,
        template_url=str(file_path),
        required_fields=fields
    )
    
    db.add(template)
    db.commit()
    db.refresh(template)
    
    return TemplateResponse(
        template_id=str(template.template_id),
        template_name=template.template_name,
        template_code=template.template_code,
        template_url=template.template_url,
        required_fields=template.required_fields or {}
    )


@router.delete("/templates/{template_code}")
async def delete_template(
    template_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a template (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    template = db.query(DocumentTemplate).filter(
        DocumentTemplate.template_code == template_code
    ).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Delete file if exists
    if os.path.exists(template.template_url):
        os.remove(template.template_url)
    
    db.delete(template)
    db.commit()
    
    return {"success": True, "message": f"Template {template_code} deleted"}


# ============================================================================
# Document Generation (AutoFill) Endpoints
# ============================================================================

@router.post("/fill", response_model=FillTemplateResponse)
async def fill_template(
    request: FillTemplateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Fill a document template with data.
    
    Data sources (in priority order):
    1. Direct data provided in request
    2. Questionnaire session answers
    3. Case information
    """
    from services.document_filler import get_filler_service, transform_questionnaire_to_filler_data
    
    # Find template
    template = None
    if request.template_id:
        template = db.query(DocumentTemplate).filter(
            DocumentTemplate.template_id == uuid.UUID(request.template_id)
        ).first()
    elif request.template_code:
        template = db.query(DocumentTemplate).filter(
            DocumentTemplate.template_code == request.template_code
        ).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Gather data
    fill_data = request.data or {}
    
    # Get questionnaire session data if provided
    autofill_data = {}
    if request.session_id:
        session = db.query(QuestionnaireSession).filter(
            QuestionnaireSession.session_id == uuid.UUID(request.session_id),
            QuestionnaireSession.user_uuid == current_user.user_uuid
        ).first()
        
        if session and session.session_data:
            # Get answers from session_data
            answers = session.session_data.get("answers", {})
            fill_data.update(transform_questionnaire_to_filler_data(answers))
            
            # Get autofill data (from OCR)
            autofill_data = session.session_data.get("autofill_data", {})
    
    # Get case info if provided
    if request.case_uuid:
        case = db.query(Case).filter(
            Case.case_uuid == uuid.UUID(request.case_uuid),
            Case.user_uuid == current_user.user_uuid
        ).first()
        
        if case:
            fill_data.setdefault("CaseTitle", case.title)
            fill_data.setdefault("CaseCategory", case.case_category)
            fill_data.setdefault("CaseDescription", case.description)
    
    # Fill template
    filler = get_filler_service(
        templates_dir=str(get_templates_dir()),
        output_dir=str(get_generated_dir())
    )
    
    result = filler.fill_from_questionnaire(
        template_code=template.template_code,
        questionnaire_answers=fill_data,
        autofill_data=autofill_data,
        apply_fangsong=request.apply_fangsong
    )
    
    if not result.success:
        return FillTemplateResponse(
            success=False,
            error=result.error
        )
    
    # Save document record to database
    doc = Document(
        document_id=uuid.uuid4(),
        user_uuid=current_user.user_uuid,
        case_uuid=uuid.UUID(request.case_uuid) if request.case_uuid else None,
        session_id=uuid.UUID(request.session_id) if request.session_id else None,
        document_type="generated",
        file_name=result.output_filename,
        file_path=result.output_path,
        file_size=os.path.getsize(result.output_path) if result.output_path else None,
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        description=f"Generated from template: {template.template_name}"
    )
    
    db.add(doc)
    
    # Save fill data to document_data
    doc_data = DocumentData(
        data_id=uuid.uuid4(),
        document_id=doc.document_id,
        data_type="form_data",
        data_content={
            "template_code": template.template_code,
            "fill_data": fill_data,
            "autofill_data": autofill_data,
            "filled_at": datetime.utcnow().isoformat()
        }
    )
    
    db.add(doc_data)
    db.commit()
    
    return FillTemplateResponse(
        success=True,
        document_id=str(doc.document_id),
        download_url=f"/api/documents/download/{doc.document_id}",
        filled_fields=result.filled_fields
    )


@router.get("/download/{document_id}")
async def download_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Download a generated document"""
    doc = db.query(Document).filter(
        Document.document_id == uuid.UUID(document_id),
        Document.user_uuid == current_user.user_uuid
    ).first()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if not os.path.exists(doc.file_path):
        raise HTTPException(status_code=404, detail="Document file not found")
    
    return FileResponse(
        doc.file_path,
        filename=doc.file_name,
        media_type=doc.mime_type
    )


# ============================================================================
# OCR Endpoints
# ============================================================================

@router.post("/ocr", response_model=OCRResponse)
async def process_ocr(
    request: OCRRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Process an image with OCR and parse the results.
    
    Returns structured data that can be used for questionnaire autofill.
    """
    from services.ocr_parser import parse_document
    
    if not request.image_base64:
        raise HTTPException(status_code=400, detail="image_base64 is required")
    
    # Call OCR service
    ocr_result = await call_ocr_service(request.image_base64)
    
    if not ocr_result.get("success"):
        return OCRResponse(
            success=False,
            error=ocr_result.get("error", "OCR processing failed")
        )
    
    # Parse OCR result
    parsed = parse_document(ocr_result, request.document_type)
    
    # Save OCR result to database if session provided
    doc_id = None
    if request.session_id:
        session = db.query(QuestionnaireSession).filter(
            QuestionnaireSession.session_id == uuid.UUID(request.session_id),
            QuestionnaireSession.user_uuid == current_user.user_uuid
        ).first()
        
        if session:
            # Create document record
            doc = Document(
                document_id=uuid.uuid4(),
                user_uuid=current_user.user_uuid,
                session_id=session.session_id,
                document_type="ocr_result",
                file_name=f"ocr_{parsed.get('document_type')}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json",
                file_path="",  # No file stored
                mime_type="application/json",
                description=f"OCR result: {parsed.get('document_type')}"
            )
            db.add(doc)
            
            # Store OCR data
            ocr_data = DocumentData(
                data_id=uuid.uuid4(),
                document_id=doc.document_id,
                data_type="ocr_result",
                data_content={
                    "raw_ocr": ocr_result,
                    "parsed": parsed,
                    "processed_at": datetime.utcnow().isoformat()
                }
            )
            db.add(ocr_data)
            
            # Update session with autofill data
            if session.session_data is None:
                session.session_data = {}
            
            session.session_data["autofill_data"] = parsed.get("questionnaire_format", {})
            session.session_data["last_ocr_type"] = parsed.get("document_type")
            
            # Mark session_data as modified
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(session, "session_data")
            
            db.commit()
            doc_id = str(doc.document_id)
    
    return OCRResponse(
        success=True,
        document_type=parsed.get("document_type", "unknown"),
        parsed_data=parsed.get("parsed_data", {}),
        questionnaire_format=parsed.get("questionnaire_format", {}),
        confidence=parsed.get("confidence", 0.0),
        document_id=doc_id
    )


@router.post("/ocr/upload")
async def upload_and_ocr(
    file: UploadFile = File(...),
    document_type: str = Form("auto"),
    session_id: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload a file and process with OCR"""
    from services.ocr_parser import parse_document
    
    # Read and encode file
    content = await file.read()
    image_base64 = base64.b64encode(content).decode()
    
    # Save uploaded file
    uploads_dir = get_uploads_dir() / "ocr_uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    
    file_id = str(uuid.uuid4())
    file_ext = Path(file.filename).suffix
    file_path = uploads_dir / f"{file_id}{file_ext}"
    
    with open(file_path, "wb") as f:
        f.write(content)
    
    # Call OCR
    ocr_result = await call_ocr_service(image_base64)
    
    if not ocr_result.get("success"):
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": ocr_result.get("error")}
        )
    
    # Parse result
    parsed = parse_document(ocr_result, document_type)
    
    # Save to database
    doc = Document(
        document_id=uuid.uuid4(),
        user_uuid=current_user.user_uuid,
        session_id=uuid.UUID(session_id) if session_id else None,
        document_type="ocr_result",
        file_name=file.filename,
        file_path=str(file_path),
        file_size=len(content),
        mime_type=file.content_type,
        description=f"OCR upload: {parsed.get('document_type')}"
    )
    db.add(doc)
    
    # Store OCR data
    ocr_data = DocumentData(
        data_id=uuid.uuid4(),
        document_id=doc.document_id,
        data_type="ocr_result",
        data_content={
            "raw_ocr": ocr_result,
            "parsed": parsed,
            "processed_at": datetime.utcnow().isoformat()
        }
    )
    db.add(ocr_data)
    
    # Update session autofill data if session provided
    if session_id:
        session = db.query(QuestionnaireSession).filter(
            QuestionnaireSession.session_id == uuid.UUID(session_id),
            QuestionnaireSession.user_uuid == current_user.user_uuid
        ).first()
        
        if session:
            if session.session_data is None:
                session.session_data = {}
            session.session_data["autofill_data"] = parsed.get("questionnaire_format", {})
            
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(session, "session_data")
    
    db.commit()
    
    return {
        "success": True,
        "document_id": str(doc.document_id),
        "document_type": parsed.get("document_type"),
        "parsed_data": parsed.get("parsed_data", {}),
        "questionnaire_format": parsed.get("questionnaire_format", {}),
        "confidence": parsed.get("confidence", 0.0)
    }


# ============================================================================
# Document Upload Endpoints
# ============================================================================

@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    document_type: str = Form("upload_evidence"),
    case_uuid: Optional[str] = Form(None),
    session_id: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload a document (evidence, attachment, etc.)"""
    # Determine upload directory
    if document_type == "upload_evidence":
        upload_dir = get_uploads_dir() / "evidence"
    elif document_type == "questionnaire_attachment":
        upload_dir = get_uploads_dir() / "questionnaire_attachments"
    else:
        upload_dir = get_uploads_dir() / "general"
    
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename
    file_id = str(uuid.uuid4())
    file_ext = Path(file.filename).suffix
    file_path = upload_dir / f"{file_id}{file_ext}"
    
    # Save file
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    
    # Create database record
    doc = Document(
        document_id=uuid.uuid4(),
        user_uuid=current_user.user_uuid,
        case_uuid=uuid.UUID(case_uuid) if case_uuid else None,
        session_id=uuid.UUID(session_id) if session_id else None,
        document_type=document_type,
        file_name=file.filename,
        file_path=str(file_path),
        file_size=len(content),
        mime_type=file.content_type,
        description=description
    )
    
    db.add(doc)
    db.commit()
    db.refresh(doc)
    
    return DocumentUploadResponse(
        success=True,
        document_id=str(doc.document_id),
        file_name=doc.file_name,
        file_path=doc.file_path,
        document_type=doc.document_type
    )


@router.get("/list")
async def list_documents(
    document_type: Optional[str] = None,
    case_uuid: Optional[str] = None,
    session_id: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List user's documents with optional filters"""
    query = db.query(Document).filter(Document.user_uuid == current_user.user_uuid)
    
    if document_type:
        query = query.filter(Document.document_type == document_type)
    
    if case_uuid:
        query = query.filter(Document.case_uuid == uuid.UUID(case_uuid))
    
    if session_id:
        query = query.filter(Document.session_id == uuid.UUID(session_id))
    
    docs = query.order_by(Document.uploaded_at.desc()).limit(limit).all()
    
    return [
        {
            "document_id": str(d.document_id),
            "document_type": d.document_type,
            "file_name": d.file_name,
            "file_size": d.file_size,
            "mime_type": d.mime_type,
            "description": d.description,
            "uploaded_at": d.uploaded_at.isoformat() if d.uploaded_at else None,
            "case_uuid": str(d.case_uuid) if d.case_uuid else None,
            "session_id": str(d.session_id) if d.session_id else None
        }
        for d in docs
    ]


@router.get("/{document_id}")
async def get_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get document details including associated data"""
    doc = db.query(Document).filter(
        Document.document_id == uuid.UUID(document_id),
        Document.user_uuid == current_user.user_uuid
    ).first()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Get associated data
    data_records = db.query(DocumentData).filter(
        DocumentData.document_id == doc.document_id
    ).all()
    
    return {
        "document_id": str(doc.document_id),
        "document_type": doc.document_type,
        "file_name": doc.file_name,
        "file_path": doc.file_path,
        "file_size": doc.file_size,
        "mime_type": doc.mime_type,
        "description": doc.description,
        "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
        "case_uuid": str(doc.case_uuid) if doc.case_uuid else None,
        "session_id": str(doc.session_id) if doc.session_id else None,
        "data": [
            {
                "data_id": str(d.data_id),
                "data_type": d.data_type,
                "data_content": d.data_content,
                "created_at": d.created_at.isoformat() if d.created_at else None
            }
            for d in data_records
        ]
    }


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a document"""
    doc = db.query(Document).filter(
        Document.document_id == uuid.UUID(document_id),
        Document.user_uuid == current_user.user_uuid
    ).first()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Delete file if exists
    if doc.file_path and os.path.exists(doc.file_path):
        os.remove(doc.file_path)
    
    # Delete associated data (cascade should handle this, but be explicit)
    db.query(DocumentData).filter(DocumentData.document_id == doc.document_id).delete()
    
    db.delete(doc)
    db.commit()
    
    return {"success": True, "message": "Document deleted"}
