"""
Questionnaire models for legal assistant system
Updated to match schema_combined.sql with current_stage, is_finalized, expires_at
"""
from sqlalchemy import Column, String, Integer, DateTime, Text, Boolean, ForeignKey, JSON, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import uuid

from database import Base


class QuestionnaireSession(Base):
    """Questionnaire session tracking - 增强版支持Redis同步"""
    __tablename__ = "questionnaire_sessions"
    
    session_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_uuid = Column(UUID(as_uuid=True), ForeignKey("users.user_uuid", ondelete="CASCADE"), nullable=False, index=True)
    case_uuid = Column(UUID(as_uuid=True), ForeignKey("cases.case_uuid", ondelete="CASCADE"), nullable=True, index=True)
    questionnaire_type = Column(String(50), nullable=False)  # divorce, property, criminal, traffic_accident, etc.
    status = Column(String(20), default="in_progress", index=True)  # in_progress, completed, abandoned, expired
    
    # 新增字段 - 支持多阶段问卷
    current_stage = Column(String(50), nullable=True)  # 当前问卷阶段，如 "section_1", "section_2"
    is_finalized = Column(Boolean, default=False)  # TRUE表示已提交/创建案件，FALSE表示仍在进行中
    
    # Timestamps
    started_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    completed_at = Column(TIMESTAMP, nullable=True)
    expires_at = Column(TIMESTAMP, nullable=True)  # 会话过期时间，默认7天后
    last_activity_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    
    # Session data
    current_step = Column(Integer, default=0)
    total_steps = Column(Integer, nullable=True)
    session_data = Column(JSONB, default=dict)  # Store progress and answers
    
    # Relationships
    user = relationship("User", back_populates="questionnaire_sessions")
    case = relationship("Case", back_populates="questionnaire_sessions")
    submissions = relationship("QuestionnaireSubmission", back_populates="session", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<QuestionnaireSession {self.session_id} - {self.questionnaire_type}>"


class QuestionnaireSubmission(Base):
    """Completed questionnaire submissions"""
    __tablename__ = "questionnaire_submissions"
    
    submission_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("questionnaire_sessions.session_id", ondelete="CASCADE"), nullable=False)
    user_uuid = Column(UUID(as_uuid=True), ForeignKey("users.user_uuid", ondelete="CASCADE"), nullable=False, index=True)
    case_uuid = Column(UUID(as_uuid=True), ForeignKey("cases.case_uuid", ondelete="CASCADE"), nullable=True, index=True)
    
    # Questionnaire details
    questionnaire_type = Column(String(50), nullable=False)
    title = Column(String(200), nullable=True)
    description = Column(Text, nullable=True)
    
    # Submission data
    responses = Column(JSONB, nullable=False)  # All question-answer pairs
    meta_data = Column(JSONB, default=dict)  # Additional metadata
    
    # AI Analysis (if processed)
    ai_analyzed = Column(Boolean, default=False)
    ai_analysis = Column(JSONB, nullable=True)  # AI-generated insights
    recommended_actions = Column(JSONB, nullable=True)  # Suggested next steps
    
    # Processing status
    processing_status = Column(String(20), default="pending", index=True)  # pending, processing, completed, failed
    n8n_workflow_id = Column(String(100), nullable=True)  # Track n8n workflow execution
    
    # Timestamps
    submitted_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    processed_at = Column(TIMESTAMP, nullable=True)
    
    # Relationships
    session = relationship("QuestionnaireSession", back_populates="submissions")
    user = relationship("User", back_populates="questionnaire_submissions")
    case = relationship("Case", back_populates="questionnaire_submissions")
    
    def __repr__(self):
        return f"<QuestionnaireSubmission {self.submission_id} - {self.questionnaire_type}>"
