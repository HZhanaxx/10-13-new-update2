from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
import uuid


class CaseCreate(BaseModel):
    title: str = Field(..., min_length=5, max_length=200, description="Case title")
    description: str = Field(..., min_length=10, description="Detailed case description")
    case_category: Optional[str] = Field(None, description="Case category (民事/刑事/商事)")
    priority: str = Field(default='medium', description="Priority: low, medium, high, urgent")
    budget_cny: Optional[Decimal] = Field(None, ge=0.01, le=999999999.99, description="Client's budget in CNY (0.01-999999999.99)")
    
    @validator('priority')
    def validate_priority(cls, v):
        allowed = ['low', 'medium', 'high', 'urgent']
        if v not in allowed:
            raise ValueError(f'Priority must be one of {allowed}')
        return v


class CaseUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=5, max_length=200)
    description: Optional[str] = Field(None, min_length=10)
    case_category: Optional[str] = None
    priority: Optional[str] = None
    budget_cny: Optional[Decimal] = Field(None, ge=0.01, le=999999999.99, description="Client's budget in CNY (0.01-999999999.99)")
    
    @validator('priority')
    def validate_priority(cls, v):
        if v is not None:
            allowed = ['low', 'medium', 'high', 'urgent']
            if v not in allowed:
                raise ValueError(f'Priority must be one of {allowed}')
        return v


class CaseResponse(BaseModel):
    case_uuid: uuid.UUID
    user_uuid: uuid.UUID
    professional_uuid: Optional[uuid.UUID]
    
    title: str
    description: str
    case_category: Optional[str]
    priority: str
    case_status: str
    budget_cny: Optional[Decimal]
    
    created_at: datetime
    updated_at: datetime
    accepted_at: Optional[datetime]
    completed_at: Optional[datetime]
    
    # Additional info from joins
    creator_username: Optional[str] = None
    professional_name: Optional[str] = None
    document_count: Optional[int] = 0
    
    class Config:
        from_attributes = True


class CaseDocumentUpload(BaseModel):
    file_name: str = Field(..., min_length=1, max_length=255)
    file_path: str = Field(..., description="File path or URL")
    mime_type: Optional[str] = None
    file_size: Optional[int] = Field(None, ge=0)


class CaseDocumentResponse(BaseModel):
    document_id: uuid.UUID
    case_uuid: uuid.UUID
    user_uuid: uuid.UUID
    file_name: str
    file_path: str
    mime_type: Optional[str]
    file_size: Optional[int]
    uploaded_at: datetime
    
    # Additional info
    uploader_username: Optional[str] = None
    
    class Config:
        from_attributes = True


class CaseListResponse(BaseModel):
    cases: List[CaseResponse]
    total: int
    skip: int
    limit: int


class CaseStatusUpdate(BaseModel):
    status: str = Field(..., description="New status")
    
    @validator('status')
    def validate_status(cls, v):
        allowed = ['pending', 'accepted', 'in_progress', 'completed', 'cancelled']
        if v not in allowed:
            raise ValueError(f'Status must be one of {allowed}')
        return v
