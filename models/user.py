"""
User and system models for legal assistant platform
Updated to match schema_combined.sql
"""
from sqlalchemy import Column, String, Boolean, DateTime, Text, CheckConstraint, TIMESTAMP, Integer, Date, DECIMAL, ARRAY, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, INET, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from database import Base


class User(Base):
    __tablename__ = "users"

    user_uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), unique=True, nullable=True, index=True)
    phone = Column(String(20), unique=True, nullable=True, index=True)
    wechat_openid = Column(String(100), unique=True, nullable=True)
    wechat_unionid = Column(String(100), unique=True, nullable=True)
    password_hash = Column(Text, nullable=True)
    role = Column(String(20), nullable=False, default="user")
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    last_login_at = Column(TIMESTAMP, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    # Relationships
    questionnaire_sessions = relationship(
        "QuestionnaireSession",
        back_populates="user",
        foreign_keys="QuestionnaireSession.user_uuid"
    )
    questionnaire_submissions = relationship(
        "QuestionnaireSubmission", 
        back_populates="user",
        foreign_keys="QuestionnaireSubmission.user_uuid"  
    )

    __table_args__ = (
        CheckConstraint("role IN ('user', 'professional', 'admin')", name="check_role"),
    )


class UserProfile(Base):
    __tablename__ = "user_profiles"

    profile_uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_uuid = Column(UUID(as_uuid=True), ForeignKey("users.user_uuid", ondelete="CASCADE"), unique=True, nullable=False)
    full_name = Column(String(100), nullable=True)
    nickname = Column(String(50), nullable=True)
    avatar_url = Column(Text, nullable=True)
    gender = Column(String(10), nullable=True)
    description = Column(Text, nullable=True)
    id_card_number = Column(String(18), nullable=True)
    address_line = Column(Text, nullable=True)
    city_name = Column(String(50), nullable=True)
    province_name = Column(String(50), nullable=True)
    postal_code = Column(String(10), nullable=True)
    date_of_birth = Column(Date, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())


class UserSession(Base):
    __tablename__ = "user_sessions"

    session_uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_uuid = Column(UUID(as_uuid=True), ForeignKey("users.user_uuid", ondelete="CASCADE"), nullable=False, index=True)
    access_token_jti = Column(String(100), unique=True, nullable=False, index=True)
    refresh_token_jti = Column(String(100), unique=True, nullable=True)
    device_info = Column(JSONB, nullable=True)
    ip_address = Column(INET, nullable=True)
    user_agent = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    expires_at = Column(TIMESTAMP, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
    last_activity_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    token_uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_uuid = Column(UUID(as_uuid=True), ForeignKey("users.user_uuid", ondelete="CASCADE"), nullable=False)
    session_uuid = Column(UUID(as_uuid=True), ForeignKey("user_sessions.session_uuid", ondelete="SET NULL"), nullable=True)
    token_hash = Column(String(255), unique=True, nullable=False)
    is_revoked = Column(Boolean, default=False)
    revoked_at = Column(TIMESTAMP, nullable=True)
    revoked_reason = Column(String(100), nullable=True)
    expires_at = Column(TIMESTAMP, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())


class Professional(Base):
    __tablename__ = "professionals"

    professional_uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_uuid = Column(UUID(as_uuid=True), ForeignKey("users.user_uuid", ondelete="CASCADE"), unique=True, nullable=False)
    license_number = Column(String(50), unique=True, nullable=False)
    law_firm_name = Column(String(200), nullable=True)
    specialty_areas = Column(ARRAY(Text), nullable=True)
    years_of_experience = Column(Integer, nullable=True)
    education_background = Column(Text, nullable=True)
    bio = Column(Text, nullable=True)
    hourly_rate_cny = Column(DECIMAL(10, 2), nullable=True)
    consultation_fee_cny = Column(DECIMAL(10, 2), nullable=True)
    
    # Admin-managed fields
    average_rating = Column(DECIMAL(3, 2), default=5.0)
    total_cases_handled = Column(Integer, default=0)
    success_rate = Column(DECIMAL(5, 2), nullable=True)
    account_status = Column(String(20), default='active')
    is_verified = Column(Boolean, default=False)
    verified_at = Column(TIMESTAMP, nullable=True)
    verified_by_admin_uuid = Column(UUID(as_uuid=True), nullable=True)
    
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())


class ProfessionalVerification(Base):
    """律师认证申请表"""
    __tablename__ = "professional_verifications"

    request_uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_uuid = Column(UUID(as_uuid=True), ForeignKey("users.user_uuid", ondelete="CASCADE"), nullable=False, index=True)
    
    # Form fields
    full_name = Column(String(100), nullable=False)
    license_number = Column(String(50), nullable=False)
    law_firm_name = Column(String(200), nullable=True)
    specialty_areas = Column(ARRAY(Text), nullable=True)
    years_of_experience = Column(Integer, nullable=True)
    education_background = Column(Text, nullable=True)
    bio = Column(Text, nullable=True)
    consultation_fee_cny = Column(DECIMAL(10, 2), nullable=True)
    hourly_rate_cny = Column(DECIMAL(10, 2), nullable=True)
    city_name = Column(String(50), nullable=True)
    province_name = Column(String(50), nullable=True)
    
    # Status
    status = Column(String(20), default='pending', index=True)
    reviewed_by_uuid = Column(UUID(as_uuid=True), ForeignKey("users.user_uuid"), nullable=True)
    reviewed_at = Column(TIMESTAMP, nullable=True)
    admin_notes = Column(Text, nullable=True)
    status_history = Column(JSONB, default=list)
    
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'approved', 'rejected', 'revoked')", name="check_verif_status"),
    )


class Case(Base):
    __tablename__ = "cases"

    case_uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_uuid = Column(UUID(as_uuid=True), ForeignKey("users.user_uuid", ondelete="CASCADE"), nullable=False, index=True)
    professional_uuid = Column(UUID(as_uuid=True), ForeignKey("users.user_uuid"), nullable=True, index=True)
    
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    case_category = Column(String(50), nullable=True)
    priority = Column(String(20), default='medium')
    case_status = Column(String(20), default='pending', index=True)
    budget_cny = Column(DECIMAL(10, 2), nullable=True)
    
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    accepted_at = Column(TIMESTAMP, nullable=True)
    completed_at = Column(TIMESTAMP, nullable=True)

    # Relationships
    questionnaire_sessions = relationship("QuestionnaireSession", back_populates="case")
    questionnaire_submissions = relationship("QuestionnaireSubmission", back_populates="case")

    __table_args__ = (
        CheckConstraint("case_status IN ('pending', 'accepted', 'in_progress', 'completed', 'cancelled')", 
                       name="check_case_status"),
        CheckConstraint("priority IN ('low', 'medium', 'high', 'urgent')", 
                       name="check_priority"),
    )


class DocumentTemplate(Base):
    """文档模板 - 简化版，只存储4个字段"""
    __tablename__ = "document_templates"
    
    template_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    template_name = Column(String(200), nullable=False)        # 模板名称
    template_code = Column(String(50), unique=True, nullable=False)  # 模板编号
    template_url = Column(String(500), nullable=False)         # 模板文件路径/URL
    required_fields = Column(JSONB, nullable=False)            # 填写所需字段定义


class Document(Base):
    """统一文档表 - 替代 case_documents, generated_documents, ocr_results"""
    __tablename__ = "documents"
    
    document_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # 关联
    user_uuid = Column(UUID(as_uuid=True), ForeignKey("users.user_uuid", ondelete="CASCADE"), nullable=False, index=True)
    case_uuid = Column(UUID(as_uuid=True), ForeignKey("cases.case_uuid", ondelete="CASCADE"), nullable=True, index=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("questionnaire_sessions.session_id", ondelete="CASCADE"), nullable=True, index=True)
    verification_id = Column(UUID(as_uuid=True), ForeignKey("professional_verifications.request_uuid", ondelete="CASCADE"), nullable=True, index=True)
    
    # 文档信息
    document_type = Column(String(50), nullable=False, index=True)  # upload_evidence, generated, ocr_result, verification_doc
    file_name = Column(String(255), nullable=False)
    file_path = Column(Text, nullable=False)  # S3/Local 存储路径
    file_size = Column(Integer, nullable=True)
    mime_type = Column(String(100), nullable=True)
    
    # 元数据
    description = Column(Text, nullable=True)
    tags = Column(ARRAY(String), nullable=True)
    version = Column(Integer, default=1)
    
    # 时间戳
    uploaded_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        CheckConstraint(
            "document_type IN ('upload_evidence', 'generated', 'ocr_result', 'verification_doc', 'questionnaire_attachment')",
            name="check_document_type"
        ),
    )


class DocumentData(Base):
    """统一JSON数据表 - 存储OCR结果、生成文档的填充数据等"""
    __tablename__ = "document_data"
    
    data_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.document_id", ondelete="CASCADE"), nullable=False, index=True)
    
    data_type = Column(String(50), nullable=False, index=True)  # ocr_result, form_data, template_data
    data_content = Column(JSONB, nullable=False)  # 实际JSON数据
    
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        CheckConstraint(
            "data_type IN ('ocr_result', 'form_data', 'template_data', 'analysis_result')",
            name="check_data_type"
        ),
    )


class AdminLog(Base):
    __tablename__ = "admin_logs"

    log_uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    admin_user_uuid = Column(UUID(as_uuid=True), ForeignKey("users.user_uuid"), nullable=False, index=True)
    action_type = Column(String(100), nullable=False)
    target_table_name = Column(String(50), nullable=True)
    target_record_uuid = Column(UUID(as_uuid=True), nullable=True)
    action_details = Column(JSONB, nullable=True)
    ip_address = Column(INET, nullable=True)
    user_agent = Column(Text, nullable=True)
    performed_at = Column(TIMESTAMP, server_default=func.now())


# Note: SMSVerification is not in the new schema but keeping for backwards compatibility
class SMSVerification(Base):
    __tablename__ = "sms_verification"

    verification_uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone = Column(String(20), nullable=False, index=True)
    verification_code = Column(String(6), nullable=False)
    purpose = Column(String(20), nullable=False)
    is_used = Column(Boolean, default=False)
    attempt_count = Column(Integer, default=0)
    max_attempts = Column(Integer, default=5)
    ip_address = Column(INET, nullable=True)
    expires_at = Column(TIMESTAMP, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
    used_at = Column(TIMESTAMP, nullable=True)
