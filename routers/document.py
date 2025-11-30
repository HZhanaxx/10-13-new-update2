"""
Document Router - Template Management & Auto-Fill API
======================================================

API endpoints for:
- Document template management (CRUD operations)
- Auto-fill documents from questionnaire data
- OCR result parsing and integration
- Document generation and storage

Integrates with:
- DocumentTemplate model (stores template metadata in DB)
- Document model (stores generated documents)
- DocumentData model (stores OCR results & fill data)
- DocumentFillerService (handles actual filling)
- OCRResultParser (parses OCR JSON)
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path
import uuid
import os
import shutil
import json

from pydantic import BaseModel, Field

from database import get_db
from models.user import User, Document, DocumentData, DocumentTemplate, Case
from models.questionnaire import QuestionnaireSession, QuestionnaireSubmission
from utils.auth import get_current_user
from services.document_filler import DocumentFillerService, get_filler_service, transform_json
from services.ocr_parser import (
    OCRResultParser, 
    get_parser, 
    parse_ocr_result, 
    parse_and_map_to_questionnaire,
    DocumentType,
    OCRParseResult
)


router = APIRouter(prefix="/api/documents", tags=["documents"])


# ============================================================================
# Configuration
# ============================================================================

TEMPLATES_DIR = Path("templates")
UPLOADS_DIR = Path("uploads")
GENERATED_DIR = UPLOADS_DIR / "generated_documents"

# Ensure directories exist
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
GENERATED_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================================
# Pydantic Models
# ============================================================================

class TemplateCreate(BaseModel):
    """Request to create a new template"""
    template_name: str = Field(..., description="模板名称")
    template_code: str = Field(..., description="模板编号 (唯一)")
    category: str = Field(default="general", description="模板分类")
    description: Optional[str] = Field(None, description="模板描述")
    required_fields: Dict[str, Any] = Field(default_factory=dict, description="所需字段定义")


class TemplateUpdate(BaseModel):
    """Request to update a template"""
    template_name: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    required_fields: Optional[Dict[str, Any]] = None


class TemplateResponse(BaseModel):
    """Template response"""
    template_id: str
    template_name: str
    template_code: str
    template_url: str
    category: Optional[str] = None
    required_fields: Dict[str, Any]
    
    class Config:
        from_attributes = True


class AutoFillRequest(BaseModel):
    """Request to auto-fill a template"""
    template_code: str = Field(..., description="模板编号")
    data: Dict[str, Any] = Field(..., description="填充数据")
    session_id: Optional[str] = Field(None, description="关联的问卷会话ID")
    case_uuid: Optional[str] = Field(None, description="关联的案件UUID")
    apply_fangsong: bool = Field(default=True, description="是否应用仿宋字体")
    output_filename: Optional[str] = Field(None, description="输出文件名 (可选)")


class AutoFillFromSessionRequest(BaseModel):
    """Request to auto-fill from questionnaire session"""
    template_code: str = Field(..., description="模板编号")
    session_id: str = Field(..., description="问卷会话ID")
    include_ocr_data: bool = Field(default=True, description="是否包含OCR数据")
    apply_fangsong: bool = Field(default=True, description="是否应用仿宋字体")


class AutoFillResponse(BaseModel):
    """Response from auto-fill operation"""
    success: bool
    document_id: Optional[str] = None
    output_filename: Optional[str] = None
    download_url: Optional[str] = None
    filled_fields: int = 0
    error: Optional[str] = None


class OCRParseRequest(BaseModel):
    """Request to parse OCR result"""
    ocr_result: Dict[str, Any] = Field(..., description="OCR JSON结果")
    document_type: Optional[str] = Field(None, description="文档类型 (可选)")


class OCRParseResponse(BaseModel):
    """Response from OCR parsing"""
    success: bool
    document_type: str
    extracted_fields: Dict[str, Any]
    confidence: float
    raw_text: Optional[str] = None
    warnings: List[str] = []
    errors: List[str] = []


# ============================================================================
# Template Management Endpoints
# ============================================================================

@router.get("/templates", response_model=List[TemplateResponse])
async def list_templates(
    category: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all available document templates.
    """
    query = db.query(DocumentTemplate)
    
    # Filter by category if provided (using JSON field)
    if category:
        query = query.filter(DocumentTemplate.required_fields["category"].astext == category)
    
    templates = query.all()
    
    return [
        TemplateResponse(
            template_id=str(t.template_id),
            template_name=t.template_name,
            template_code=t.template_code,
            template_url=t.template_url,
            category=t.required_fields.get("category") if t.required_fields else None,
            required_fields=t.required_fields or {}
        )
        for t in templates
    ]


@router.get("/templates/{template_code}", response_model=TemplateResponse)
async def get_template(
    template_code: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific template by code.
    """
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
        category=template.required_fields.get("category") if template.required_fields else None,
        required_fields=template.required_fields or {}
    )


@router.post("/templates", response_model=TemplateResponse)
async def create_template(
    template_file: UploadFile = File(...),
    template_name: str = Form(...),
    template_code: str = Form(...),
    category: str = Form(default="general"),
    description: str = Form(default=""),
    required_fields_json: str = Form(default="{}"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload and create a new document template.
    Only admins can create templates.
    """
    # Check admin permission
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can create templates")
    
    # Check if template code already exists
    existing = db.query(DocumentTemplate).filter(
        DocumentTemplate.template_code == template_code
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail=f"Template code '{template_code}' already exists")
    
    # Parse required_fields JSON
    try:
        required_fields = json.loads(required_fields_json)
    except json.JSONDecodeError:
        required_fields = {}
    
    # Add metadata to required_fields
    required_fields["category"] = category
    required_fields["description"] = description
    
    # Save template file
    file_ext = Path(template_file.filename).suffix
    if file_ext.lower() != ".docx":
        raise HTTPException(status_code=400, detail="Only .docx files are allowed")
    
    file_path = TEMPLATES_DIR / f"{template_code}{file_ext}"
    
    try:
        with open(file_path, "wb") as f:
            content = await template_file.read()
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save template file: {str(e)}")
    
    # Create database record
    template = DocumentTemplate(
        template_id=uuid.uuid4(),
        template_name=template_name,
        template_code=template_code,
        template_url=str(file_path),
        required_fields=required_fields
    )
    
    db.add(template)
    db.commit()
    db.refresh(template)
    
    return TemplateResponse(
        template_id=str(template.template_id),
        template_name=template.template_name,
        template_code=template.template_code,
        template_url=template.template_url,
        category=category,
        required_fields=required_fields
    )


@router.put("/templates/{template_code}", response_model=TemplateResponse)
async def update_template(
    template_code: str,
    update_data: TemplateUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update template metadata.
    Only admins can update templates.
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can update templates")
    
    template = db.query(DocumentTemplate).filter(
        DocumentTemplate.template_code == template_code
    ).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Update fields
    if update_data.template_name:
        template.template_name = update_data.template_name
    
    if update_data.required_fields:
        template.required_fields = update_data.required_fields
    elif update_data.category or update_data.description:
        # Update individual metadata fields
        rf = template.required_fields or {}
        if update_data.category:
            rf["category"] = update_data.category
        if update_data.description:
            rf["description"] = update_data.description
        template.required_fields = rf
    
    db.commit()
    db.refresh(template)
    
    return TemplateResponse(
        template_id=str(template.template_id),
        template_name=template.template_name,
        template_code=template.template_code,
        template_url=template.template_url,
        category=template.required_fields.get("category") if template.required_fields else None,
        required_fields=template.required_fields or {}
    )


@router.delete("/templates/{template_code}")
async def delete_template(
    template_code: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a template.
    Only admins can delete templates.
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can delete templates")
    
    template = db.query(DocumentTemplate).filter(
        DocumentTemplate.template_code == template_code
    ).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Delete file
    if template.template_url and os.path.exists(template.template_url):
        try:
            os.remove(template.template_url)
        except Exception:
            pass  # File might not exist
    
    db.delete(template)
    db.commit()
    
    return {"success": True, "message": f"Template '{template_code}' deleted"}


# ============================================================================
# Auto-Fill Endpoints
# ============================================================================

@router.post("/autofill", response_model=AutoFillResponse)
async def autofill_template(
    request: AutoFillRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Auto-fill a document template with provided data.
    
    The data should contain field values that match the template placeholders.
    Common placeholders: {{OriClientName}}, {{AccidentDate}}, {CourtName}, etc.
    """
    # Find template
    template = db.query(DocumentTemplate).filter(
        DocumentTemplate.template_code == request.template_code
    ).first()
    
    if not template:
        return AutoFillResponse(
            success=False,
            error=f"Template not found: {request.template_code}"
        )
    
    # Get filler service
    filler = get_filler_service(
        templates_dir=str(TEMPLATES_DIR),
        output_dir=str(GENERATED_DIR)
    )
    
    # Fill the template
    result = filler.fill_directly(
        template_path=template.template_url,
        data=request.data,
        apply_fangsong=request.apply_fangsong
    )
    
    if not result.success:
        return AutoFillResponse(
            success=False,
            error=result.error
        )
    
    # Store document record in database
    document = Document(
        document_id=uuid.uuid4(),
        user_uuid=current_user.user_uuid,
        case_uuid=uuid.UUID(request.case_uuid) if request.case_uuid else None,
        session_id=uuid.UUID(request.session_id) if request.session_id else None,
        document_type="generated",
        file_name=result.output_filename,
        file_path=result.output_path,
        file_size=os.path.getsize(result.output_path) if result.output_path else None,
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        description=f"Auto-filled from template: {request.template_code}",
        tags=["auto-filled", request.template_code]
    )
    
    db.add(document)
    
    # Store fill data
    doc_data = DocumentData(
        data_id=uuid.uuid4(),
        document_id=document.document_id,
        data_type="form_data",
        data_content={
            "template_code": request.template_code,
            "fill_data": request.data,
            "filled_at": datetime.utcnow().isoformat()
        }
    )
    
    db.add(doc_data)
    db.commit()
    
    return AutoFillResponse(
        success=True,
        document_id=str(document.document_id),
        output_filename=result.output_filename,
        download_url=f"/api/documents/download/{document.document_id}",
        filled_fields=result.filled_fields
    )


@router.post("/autofill-from-session", response_model=AutoFillResponse)
async def autofill_from_session(
    request: AutoFillFromSessionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Auto-fill a document template using data from a questionnaire session.
    
    This endpoint:
    1. Retrieves answers from the questionnaire session
    2. Optionally includes OCR data from uploaded documents
    3. Transforms the data to match template placeholders
    4. Fills and generates the document
    """
    # Find questionnaire session
    session = db.query(QuestionnaireSession).filter(
        QuestionnaireSession.session_id == uuid.UUID(request.session_id),
        QuestionnaireSession.user_uuid == current_user.user_uuid
    ).first()
    
    if not session:
        return AutoFillResponse(
            success=False,
            error="Questionnaire session not found"
        )
    
    # Find template
    template = db.query(DocumentTemplate).filter(
        DocumentTemplate.template_code == request.template_code
    ).first()
    
    if not template:
        return AutoFillResponse(
            success=False,
            error=f"Template not found: {request.template_code}"
        )
    
    # Get session data
    session_data = session.session_data or {}
    answers = session_data.get("answers", {})
    
    # Get OCR data if requested
    ocr_data = {}
    if request.include_ocr_data:
        # Find documents with OCR data for this session
        ocr_docs = db.query(DocumentData).join(Document).filter(
            Document.session_id == session.session_id,
            DocumentData.data_type == "ocr_result"
        ).all()
        
        for doc_data in ocr_docs:
            if doc_data.data_content:
                # Parse OCR result
                parsed = parse_ocr_result(doc_data.data_content)
                ocr_data.update(parsed)
    
    # Merge answers with OCR data (OCR data takes priority for matching fields)
    merged_data = {}
    
    # First add questionnaire answers
    for q_id, answer in answers.items():
        if isinstance(answer, dict):
            value = answer.get("value", answer.get("text", ""))
        else:
            value = answer
        merged_data[q_id] = value
    
    # Then add OCR data (overwrites questionnaire if same field)
    merged_data.update(ocr_data)
    
    # Use the filler service
    filler = get_filler_service(
        templates_dir=str(TEMPLATES_DIR),
        output_dir=str(GENERATED_DIR)
    )
    
    result = filler.fill_from_questionnaire(
        template_code=request.template_code,
        questionnaire_answers=merged_data,
        autofill_data=ocr_data,
        apply_fangsong=request.apply_fangsong
    )
    
    if not result.success:
        return AutoFillResponse(
            success=False,
            error=result.error
        )
    
    # Store document record
    document = Document(
        document_id=uuid.uuid4(),
        user_uuid=current_user.user_uuid,
        case_uuid=session.case_uuid,
        session_id=session.session_id,
        document_type="generated",
        file_name=result.output_filename,
        file_path=result.output_path,
        file_size=os.path.getsize(result.output_path) if result.output_path else None,
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        description=f"Auto-filled from questionnaire session",
        tags=["auto-filled", "questionnaire", request.template_code]
    )
    
    db.add(document)
    db.commit()
    
    return AutoFillResponse(
        success=True,
        document_id=str(document.document_id),
        output_filename=result.output_filename,
        download_url=f"/api/documents/download/{document.document_id}",
        filled_fields=result.filled_fields
    )


# ============================================================================
# OCR Parsing Endpoints
# ============================================================================

@router.post("/parse-ocr", response_model=OCRParseResponse)
async def parse_ocr_endpoint(
    request: OCRParseRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Parse OCR result and extract essential fields.
    
    Supported document types:
    - id_card: 身份证
    - driver_license: 驾驶证
    - insurance_policy: 保险单
    - accident_report: 交通事故认定书
    - general: 通用文档
    
    If document_type is not provided, it will be auto-detected.
    """
    parser = get_parser()
    
    doc_type = None
    if request.document_type:
        try:
            doc_type = DocumentType(request.document_type)
        except ValueError:
            pass
    
    result = parser.parse(request.ocr_result, doc_type)
    
    return OCRParseResponse(
        success=result.success,
        document_type=result.document_type.value,
        extracted_fields=result.extracted_fields,
        confidence=result.confidence,
        raw_text=result.raw_text,
        warnings=result.warnings,
        errors=result.errors
    )


@router.post("/parse-ocr-for-questionnaire")
async def parse_ocr_for_questionnaire(
    request: OCRParseRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Parse OCR result and map to questionnaire field format.
    
    Returns fields in the format that can be used to pre-fill questionnaire answers.
    """
    mapped_fields = parse_and_map_to_questionnaire(
        request.ocr_result,
        request.document_type
    )
    
    return {
        "success": len(mapped_fields) > 0,
        "questionnaire_fields": mapped_fields,
        "field_count": len(mapped_fields)
    }


# ============================================================================
# Document Download & Management
# ============================================================================

@router.get("/download/{document_id}")
async def download_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Download a generated document.
    """
    document = db.query(Document).filter(
        Document.document_id == uuid.UUID(document_id),
        Document.user_uuid == current_user.user_uuid
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if not document.file_path or not os.path.exists(document.file_path):
        raise HTTPException(status_code=404, detail="Document file not found")
    
    return FileResponse(
        path=document.file_path,
        filename=document.file_name,
        media_type=document.mime_type or "application/octet-stream"
    )


@router.get("/my-documents")
async def list_my_documents(
    document_type: Optional[str] = None,
    case_uuid: Optional[str] = None,
    session_id: Optional[str] = None,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List documents belonging to the current user.
    """
    query = db.query(Document).filter(
        Document.user_uuid == current_user.user_uuid
    )
    
    if document_type:
        query = query.filter(Document.document_type == document_type)
    
    if case_uuid:
        query = query.filter(Document.case_uuid == uuid.UUID(case_uuid))
    
    if session_id:
        query = query.filter(Document.session_id == uuid.UUID(session_id))
    
    documents = query.order_by(Document.uploaded_at.desc()).limit(limit).all()
    
    return [
        {
            "document_id": str(doc.document_id),
            "file_name": doc.file_name,
            "document_type": doc.document_type,
            "description": doc.description,
            "tags": doc.tags,
            "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
            "download_url": f"/api/documents/download/{doc.document_id}"
        }
        for doc in documents
    ]


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a document.
    """
    document = db.query(Document).filter(
        Document.document_id == uuid.UUID(document_id),
        Document.user_uuid == current_user.user_uuid
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Delete file
    if document.file_path and os.path.exists(document.file_path):
        try:
            os.remove(document.file_path)
        except Exception:
            pass
    
    # Delete associated data
    db.query(DocumentData).filter(
        DocumentData.document_id == document.document_id
    ).delete()
    
    db.delete(document)
    db.commit()
    
    return {"success": True, "message": "Document deleted"}


# ============================================================================
# Bulk Template Import
# ============================================================================

@router.post("/templates/bulk-import")
async def bulk_import_templates(
    templates_zip: UploadFile = File(...),
    category: str = Form(default="民事诉讼"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Bulk import templates from a ZIP file.
    
    The ZIP should contain .docx files. File names will be used to generate
    template codes (e.g., "001_异议书.docx" -> code "001", name "异议书").
    
    Only admins can import templates.
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can import templates")
    
    import zipfile
    import tempfile
    
    # Save uploaded ZIP
    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp_zip:
        content = await templates_zip.read()
        tmp_zip.write(content)
        tmp_path = tmp_zip.name
    
    imported = []
    errors = []
    
    try:
        with zipfile.ZipFile(tmp_path, 'r') as zip_ref:
            for filename in zip_ref.namelist():
                if not filename.endswith('.docx'):
                    continue
                
                if filename.startswith('__MACOSX') or filename.startswith('.'):
                    continue
                
                try:
                    # Parse filename
                    base_name = Path(filename).stem
                    
                    # Handle encoded Chinese filenames
                    # Pattern: "001_名称" or just "名称"
                    parts = base_name.split('_', 1)
                    if len(parts) == 2 and parts[0].isdigit():
                        template_code = parts[0]
                        template_name = parts[1]
                    else:
                        template_code = base_name[:3] if len(base_name) >= 3 else base_name
                        template_name = base_name
                    
                    # Check if already exists
                    existing = db.query(DocumentTemplate).filter(
                        DocumentTemplate.template_code == template_code
                    ).first()
                    
                    if existing:
                        errors.append(f"Template code '{template_code}' already exists, skipped: {filename}")
                        continue
                    
                    # Extract file
                    file_path = TEMPLATES_DIR / f"{template_code}.docx"
                    with zip_ref.open(filename) as source:
                        with open(file_path, 'wb') as target:
                            target.write(source.read())
                    
                    # Create database record
                    template = DocumentTemplate(
                        template_id=uuid.uuid4(),
                        template_name=template_name,
                        template_code=template_code,
                        template_url=str(file_path),
                        required_fields={
                            "category": category,
                            "original_filename": filename,
                            "imported_at": datetime.utcnow().isoformat()
                        }
                    )
                    
                    db.add(template)
                    imported.append({
                        "code": template_code,
                        "name": template_name,
                        "file": filename
                    })
                    
                except Exception as e:
                    errors.append(f"Failed to import {filename}: {str(e)}")
        
        db.commit()
        
    finally:
        # Clean up temp file
        os.unlink(tmp_path)
    
    return {
        "success": True,
        "imported_count": len(imported),
        "imported": imported,
        "errors": errors
    }
