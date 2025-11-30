# ============================================================================
# 问卷系统 API 路由
# 添加到 proj1/routers/ 目录
# ============================================================================

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timedelta
import uuid
import httpx

from database import get_db
from models.user import User
from models.questionnaire import QuestionnaireSession, QuestionnaireSubmission
from utils.auth import get_current_user
from pydantic import BaseModel, Field
from typing import Any
from config import settings


# ============================================================================
# Pydantic 模型
# ============================================================================

class QuestionnaireSessionCreate(BaseModel):
    """创建问卷会话"""
    template_type: int = Field(..., description="问卷模板类型（1=交通事故, 2=劳动纠纷, 3=合同纠纷等）")
    case_uuid: Optional[str] = Field(None, description="关联的案件UUID（可选）")
    metadata: Optional[dict] = Field(default_factory=dict, description="额外元数据")


class QuestionnaireSessionUpdate(BaseModel):
    """更新问卷答案"""
    answer_key: str = Field(..., description="答案键名")
    answer_value: Any = Field(..., description="答案值")
    current_step: Optional[int] = Field(None, description="当前步骤")
    metadata: Optional[dict] = Field(None, description="额外元数据")


class QuestionnaireSessionComplete(BaseModel):
    """完成问卷提交"""
    session_id: str = Field(..., description="会话ID")
    final_answers: Optional[dict] = Field(None, description="最终答案（可选，用于覆盖）")
    metadata: Optional[dict] = Field(default_factory=dict, description="额外元数据")


class QuestionnaireSessionResponse(BaseModel):
    """问卷会话响应"""
    session_id: str
    user_id: int
    case_uuid: Optional[str]
    template_type: int
    status: str
    current_step: int
    answers: dict
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]
    expires_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class QuestionnaireSubmissionResponse(BaseModel):
    """问卷提交响应"""
    submission_id: str
    session_id: str
    user_id: int
    case_uuid: Optional[str]
    template_type: int
    answers: dict
    status: str
    completed_at: datetime
    
    class Config:
        from_attributes = True


# ============================================================================
# 路由
# ============================================================================

router = APIRouter(
    prefix="/api/questionnaire",
    tags=["questionnaire"]
)


@router.post("/sessions/start", response_model=QuestionnaireSessionResponse)
async def start_questionnaire_session(
    data: QuestionnaireSessionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    开始新的问卷会话
    
    - 用户可以为现有案件创建问卷，也可以独立创建问卷
    - 会话有效期默认为24小时
    """
    # 如果指定了 case_uuid，验证案件是否属于当前用户
    if data.case_uuid:
        from models.user import Case
        case = db.query(Case).filter(
            Case.case_uuid == data.case_uuid,
            Case.user_id == current_user.id
        ).first()
        
        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="案件不存在或无权访问"
            )
    
    # 生成唯一的 session_id
    session_id = str(uuid.uuid4())
    
    # 创建会话
    session = QuestionnaireSession(
        session_id=session_id,
        user_id=current_user.id,
        case_uuid=data.case_uuid,
        template_type=data.template_type,
        status='in_progress',
        current_step=1,
        answers={},
        metadata=data.metadata or {},
        expires_at=datetime.now() + timedelta(hours=24)
    )
    
    db.add(session)
    db.commit()
    db.refresh(session)
    
    return session


@router.post("/sessions/{session_id}/update", response_model=QuestionnaireSessionResponse)
async def update_questionnaire_answer(
    session_id: str,
    data: QuestionnaireSessionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    更新问卷会话的答案
    
    - 每次提交一个答案
    - 支持更新当前步骤
    - 支持添加元数据
    """
    # 查询会话
    session = db.query(QuestionnaireSession).filter(
        QuestionnaireSession.session_id == session_id,
        QuestionnaireSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="问卷会话不存在"
        )
    
    if session.status == 'completed':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="问卷已完成，无法修改"
        )
    
    if session.expires_at and session.expires_at < datetime.now():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="问卷会话已过期"
        )
    
    # 更新答案
    if session.answers is None:
        session.answers = {}
    
    session.answers[data.answer_key] = data.answer_value
    
    # 更新步骤
    if data.current_step is not None:
        session.current_step = data.current_step
    
    # 更新元数据
    if data.metadata:
        if session.metadata is None:
            session.metadata = {}
        session.metadata.update(data.metadata)
    
    session.updated_at = datetime.now()
    
    db.commit()
    db.refresh(session)
    
    return session


@router.post("/sessions/{session_id}/complete", response_model=QuestionnaireSubmissionResponse)
async def complete_questionnaire(
    session_id: str,
    data: QuestionnaireSessionComplete,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    完成问卷并创建提交记录
    
    - 标记会话为已完成
    - 创建正式的提交记录
    - 可选：触发AI分析
    """
    # 查询会话
    session = db.query(QuestionnaireSession).filter(
        QuestionnaireSession.session_id == session_id,
        QuestionnaireSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="问卷会话不存在"
        )
    
    if session.status == 'completed':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="问卷已完成"
        )
    
    # 使用 final_answers 或当前答案
    final_answers = data.final_answers if data.final_answers else session.answers
    
    # 生成唯一的 submission_id
    submission_id = f"SUB-{uuid.uuid4().hex[:12].upper()}"
    
    # 创建提交记录
    submission = QuestionnaireSubmission(
        submission_id=submission_id,
        user_id=current_user.id,
        session_id=session_id,
        case_uuid=session.case_uuid,
        template_type=session.template_type,
        answers=final_answers,
        status='pending',
        metadata=data.metadata or {},
        completed_at=datetime.now()
    )
    
    # 更新会话状态
    session.status = 'completed'
    session.completed_at = datetime.now()
    
    db.add(submission)
    db.commit()
    db.refresh(submission)
    
    # TODO: 触发 AI 分析或通知律师
    
    return submission


@router.get("/sessions", response_model=List[QuestionnaireSessionResponse])
async def get_my_questionnaire_sessions(
    status_filter: Optional[str] = None,
    template_type: Optional[int] = None,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取当前用户的问卷会话列表
    
    - 支持按状态筛选
    - 支持按模板类型筛选
    """
    query = db.query(QuestionnaireSession).filter(
        QuestionnaireSession.user_id == current_user.id
    )
    
    if status_filter:
        query = query.filter(QuestionnaireSession.status == status_filter)
    
    if template_type is not None:
        query = query.filter(QuestionnaireSession.template_type == template_type)
    
    sessions = query.order_by(QuestionnaireSession.created_at.desc()).limit(limit).all()
    
    return sessions


@router.get("/sessions/{session_id}", response_model=QuestionnaireSessionResponse)
async def get_questionnaire_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取特定问卷会话的详情
    """
    session = db.query(QuestionnaireSession).filter(
        QuestionnaireSession.session_id == session_id,
        QuestionnaireSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="问卷会话不存在"
        )
    
    return session


@router.get("/submissions", response_model=List[QuestionnaireSubmissionResponse])
async def get_my_submissions(
    status_filter: Optional[str] = None,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取当前用户的问卷提交记录
    """
    query = db.query(QuestionnaireSubmission).filter(
        QuestionnaireSubmission.user_id == current_user.id
    )
    
    if status_filter:
        query = query.filter(QuestionnaireSubmission.status == status_filter)
    
    submissions = query.order_by(QuestionnaireSubmission.created_at.desc()).limit(limit).all()
    
    return submissions


@router.get("/submissions/{submission_id}", response_model=QuestionnaireSubmissionResponse)
async def get_submission_detail(
    submission_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取特定提交的详情
    """
    submission = db.query(QuestionnaireSubmission).filter(
        QuestionnaireSubmission.submission_id == submission_id,
        QuestionnaireSubmission.user_id == current_user.id
    ).first()
    
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="提交记录不存在"
        )
    
    return submission


@router.delete("/sessions/{session_id}")
async def delete_questionnaire_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    删除问卷会话（仅限未完成的会话）
    """
    session = db.query(QuestionnaireSession).filter(
        QuestionnaireSession.session_id == session_id,
        QuestionnaireSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="问卷会话不存在"
        )
    
    if session.status == 'completed':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="已完成的问卷无法删除"
        )
    
    db.delete(session)
    db.commit()
    
    return {"message": "问卷会话已删除"}


# ============================================================================
# N8N State Machine Proxy
# ============================================================================

class N8NStateRequest(BaseModel):
    """Request model for n8n state machine proxy"""
    sessionId: str = Field(..., description="问卷会话ID")
    action: Optional[str] = Field(default='init', description="动作类型: init, next, jump")
    answer: Optional[str] = Field(None, description="用户答案")
    targetIndex: Optional[int] = Field(None, description="跳转目标步骤索引")


class N8NStateResponse(BaseModel):
    """Response model from n8n state machine"""
    text: str = Field(..., description="LLM生成的问题文本")
    step_index: int = Field(..., description="当前步骤索引")
    total_steps: int = Field(..., description="总步骤数")
    finished: bool = Field(..., description="是否完成")
    question_type: str = Field(..., description="问题类型")
    options: Optional[List[str]] = Field(default=[], description="选项列表")
    previous_answer: Optional[str] = Field(default="", description="之前的答案")


@router.post("/n8n-proxy", response_model=N8NStateResponse)
async def proxy_to_n8n_engine(
    request: N8NStateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    代理请求到n8n工作流引擎
    
    - 隐藏n8n webhook URL
    - 验证用户身份
    - 转发请求并返回结果
    """
    # Get n8n webhook URL from settings
    N8N_WEBHOOK_URL = settings.N8N_LEGAL_SESSION_WEBHOOK
    
    # Optional: Verify user owns this session
    session = db.query(QuestionnaireSession).filter(
        QuestionnaireSession.session_id == request.sessionId,
        QuestionnaireSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="问卷会话不存在或无权访问"
        )
    
    if session.status == 'completed' and request.action != 'init':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="问卷已完成"
        )
    
    # Prepare payload for n8n
    payload = {
        "sessionId": request.sessionId,
        "action": request.action,
        "answer": request.answer,
        "targetIndex": request.targetIndex,
        "userId": current_user.id,
        "userUuid": str(current_user.user_uuid)
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                N8N_WEBHOOK_URL,
                json=payload,
                timeout=60.0  # Give LLM time to generate response
            )
            response.raise_for_status()
            
            result = response.json()
            
            # Update session metadata if needed
            if result.get('finished'):
                session.status = 'completed'
                session.completed_at = datetime.now()
                db.commit()
            
            return result
            
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code, 
                detail=f"n8n引擎错误: {e.response.text}"
            )
        except httpx.TimeoutException:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="AI引擎响应超时，请重试"
            )
        except Exception as e:
            print(f"N8N Proxy Error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail="无法连接到法律AI引擎"
            )
