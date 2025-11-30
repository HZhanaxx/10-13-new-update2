"""
LangGraph Workflow Router - Replaces n8n_integration.py
========================================================

FastAPI endpoints for the questionnaire workflow using LangGraph v1.0.
No n8n dependency, everything runs in-process.
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, Any, Dict
from datetime import datetime, timedelta
import uuid
import json
import traceback

from sqlalchemy.orm import Session
from langgraph.types import Command

from database import get_db
from models.user import User, Case
from models.questionnaire import QuestionnaireSession, QuestionnaireSubmission
from utils.auth import get_current_user
from utils.redis_client import redis_client


router = APIRouter(prefix="/api/workflow", tags=["workflow"])


# ==================== Lazy Graph Initialization ====================
# Initialize graph lazily to avoid startup errors

_graph = None
_checkpointer = None


def get_graph():
    """Get or create the questionnaire graph (lazy initialization)"""
    global _graph, _checkpointer

    if _graph is None:
        try:
            from graphs.questionnaire import create_questionnaire_graph, get_question_count
            from graphs.checkpointer import get_checkpointer

            print("Initializing LangGraph questionnaire workflow...")
            _checkpointer = get_checkpointer("memory")  # Use memory for reliability
            _graph = create_questionnaire_graph(_checkpointer)
            print("✅ LangGraph questionnaire graph initialized")
        except Exception as e:
            print(f"❌ Failed to initialize graph: {e}")
            traceback.print_exc()
            raise

    return _graph


def get_question_count_safe():
    """Safely get question count"""
    try:
        from graphs.questionnaire import get_question_count
        return get_question_count()
    except:
        return 20  # Default fallback


# ==================== Request/Response Schemas ====================

class StartRequest(BaseModel):
    template_type: int = Field(default=1, description="问卷模板类型 (1=交通事故)")
    case_uuid: Optional[str] = Field(default=None, description="关联的案件UUID")


class AnswerRequest(BaseModel):
    session_id: str = Field(..., description="会话ID")
    question_id: str = Field(..., description="问题ID")
    answer: Any = Field(..., description="答案")
    file: Optional[dict] = Field(default=None, description="上传文件信息")


class RegenerateSummaryRequest(BaseModel):
    session_id: str
    part_number: int


class CreateCaseFromQuestionnaireRequest(BaseModel):
    session_id: str = Field(..., description="会话ID")
    title: Optional[str] = Field(None, description="案件标题")
    priority: str = Field(default="medium", description="优先级")


# ==================== Helper Functions ====================

def get_questionnaire_type_name(template_type: int) -> str:
    types = {1: "traffic_accident", 2: "labor_dispute", 3: "contract_dispute"}
    return types.get(template_type, "general")


async def store_session_in_db(
    db: Session,
    session_id: str,
    user_uuid: str,
    template_type: int,
    case_uuid: Optional[str] = None
) -> QuestionnaireSession:
    """Store questionnaire session in database"""
    session = QuestionnaireSession(
        session_id=uuid.UUID(session_id),
        user_uuid=uuid.UUID(user_uuid),
        case_uuid=uuid.UUID(case_uuid) if case_uuid else None,
        questionnaire_type=get_questionnaire_type_name(template_type),
        status="in_progress",
        current_step=0,
        total_steps=get_question_count_safe(),
        session_data={},
        expires_at=datetime.utcnow() + timedelta(hours=24)
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


async def update_session_status(
    db: Session,
    session_id: str,
    status: str,
    current_step: Optional[int] = None,
    session_data: Optional[dict] = None
):
    """Update questionnaire session status"""
    session = db.query(QuestionnaireSession).filter(
        QuestionnaireSession.session_id == uuid.UUID(session_id)
    ).first()

    if session:
        session.status = status
        if current_step is not None:
            session.current_step = current_step
        if session_data:
            session.session_data = session_data
        session.last_activity_at = datetime.utcnow()

        if status == "completed":
            session.completed_at = datetime.utcnow()
            session.is_finalized = True

        db.commit()


async def create_case_from_questionnaire(
    db: Session,
    user_uuid: str,
    session_id: str,
    answers: dict,
    summaries: dict,
    title: Optional[str] = None,
    priority: str = "medium"
) -> Case:
    """Create a case from completed questionnaire data"""
    if not title:
        accident_type = answers.get("q2", {}).get("value", "交通事故")
        title = f"{accident_type}案件 - {datetime.now().strftime('%Y%m%d')}"

    description_parts = []
    for part_key, summary_data in summaries.items():
        if isinstance(summary_data, dict) and "content" in summary_data:
            description_parts.append(summary_data["content"])
        elif isinstance(summary_data, str):
            description_parts.append(summary_data)

    description = "\n\n".join(description_parts) if description_parts else "通过智能问卷创建的案件"

    new_case = Case(
        case_uuid=uuid.uuid4(),
        user_uuid=uuid.UUID(user_uuid),
        title=title,
        description=description,
        case_category="交通事故",
        priority=priority,
        case_status="pending"
    )

    db.add(new_case)
    db.commit()
    db.refresh(new_case)

    # Update questionnaire session
    session = db.query(QuestionnaireSession).filter(
        QuestionnaireSession.session_id == uuid.UUID(session_id)
    ).first()

    if session:
        session.case_uuid = new_case.case_uuid
        session.is_finalized = True
        db.commit()

    return new_case


async def create_submission_record(
    db: Session,
    user_uuid: str,
    session_id: str,
    answers: dict,
    summaries: dict,
    case_uuid: Optional[str] = None
) -> QuestionnaireSubmission:
    """Create a questionnaire submission record"""
    submission = QuestionnaireSubmission(
        submission_id=uuid.uuid4(),
        session_id=uuid.UUID(session_id),
        user_uuid=uuid.UUID(user_uuid),
        case_uuid=uuid.UUID(case_uuid) if case_uuid else None,
        questionnaire_type="traffic_accident",
        title="交通事故法律咨询问卷",
        responses=answers,
        meta_data={
            "summaries": summaries,
            "completed_at": datetime.utcnow().isoformat()
        },
        processing_status="completed"
    )

    db.add(submission)
    db.commit()
    db.refresh(submission)

    return submission


# ==================== Endpoints ====================

@router.post("/questionnaire/start")
async def start_questionnaire(
    request: StartRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Start a new questionnaire session"""
    session_id = str(uuid.uuid4())
    user_uuid = str(current_user.user_uuid)

    try:
        # Store session in database first
        await store_session_in_db(
            db, session_id, user_uuid,
            request.template_type, request.case_uuid
        )
    except Exception as e:
        print(f"Failed to store session in DB: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    # Config with thread_id for checkpointer
    config = {"configurable": {"thread_id": session_id}}

    # Initial state
    initial_state = {
        "session_id": session_id,
        "user_id": user_uuid,
        "template_type": request.template_type,
        "current_part": 1,
        "current_question_index": 0,
        "total_questions": get_question_count_safe(),
        "answered_count": 0,
        "answers": {},
        "summaries": {},
        "uploaded_files": [],
        "evidence_list": [],
        "status": "in_progress",
        "needs_summary": False,
        "current_question": None,
        "part_info": None,
        "progress": None,
        "pending_answer": None,
        "pending_ocr_file": None,
        "ocr_result": None,
        "autofill_data": None,
        "submission_id": None,
        "final_document": None,
        "should_create_case": False,
        "created_case_uuid": None
    }

    try:
        # Get the graph (lazy initialization)
        graph = get_graph()

        # Invoke the graph - will run until first interrupt()
        result = await graph.ainvoke(initial_state, config=config)

        # Extract interrupt payload (the question data)
        interrupt_info = result.get("__interrupt__", [])

        if interrupt_info:
            # Graph paused at interrupt - extract question
            interrupt_value = interrupt_info[0].value if hasattr(interrupt_info[0], 'value') else interrupt_info[0]

            return {
                "success": True,
                "session_id": session_id,
                "status": "awaiting_input",
                **interrupt_value
            }
        else:
            # Graph completed without interrupt (shouldn't happen for questionnaire)
            return {
                "success": True,
                "session_id": session_id,
                "status": result.get("status", "unknown"),
                "message": "Questionnaire started"
            }

    except Exception as e:
        print(f"❌ Failed to start questionnaire: {e}")
        traceback.print_exc()

        # Cleanup on failure
        try:
            db.query(QuestionnaireSession).filter(
                QuestionnaireSession.session_id == uuid.UUID(session_id)
            ).delete()
            db.commit()
        except:
            pass

        raise HTTPException(status_code=500, detail=f"Failed to start questionnaire: {str(e)}")


@router.post("/questionnaire/answer")
async def submit_answer(
    request: AnswerRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit an answer to the current question"""
    # Verify session ownership
    session = db.query(QuestionnaireSession).filter(
        QuestionnaireSession.session_id == uuid.UUID(request.session_id),
        QuestionnaireSession.user_uuid == current_user.user_uuid
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status == "completed":
        raise HTTPException(status_code=400, detail="Questionnaire already completed")

    config = {"configurable": {"thread_id": request.session_id}}

    # Prepare answer data for Command(resume=...)
    answer_data = {
        "question_id": request.question_id,
        "answer": request.answer,
        "file": request.file
    }

    try:
        graph = get_graph()

        # Resume the graph with the answer
        result = await graph.ainvoke(
            Command(resume=answer_data),
            config=config
        )

        # Check for interrupt (next question or summary review)
        interrupt_info = result.get("__interrupt__", [])

        if interrupt_info:
            interrupt_value = interrupt_info[0].value if hasattr(interrupt_info[0], 'value') else interrupt_info[0]
            interrupt_type = interrupt_value.get("type", "question")

            if interrupt_type == "question":
                return {
                    "success": True,
                    "session_id": request.session_id,
                    "status": "awaiting_input",
                    **interrupt_value
                }
            elif interrupt_type == "summary_validation":
                return {
                    "success": True,
                    "session_id": request.session_id,
                    "status": "awaiting_summary_validation",
                    "show_summary": True,
                    **interrupt_value
                }
            elif interrupt_type == "template_selection":
                return {
                    "success": True,
                    "session_id": request.session_id,
                    "status": "awaiting_template_selection",
                    "show_template_selection": True,
                    **interrupt_value
                }
            else:
                return {
                    "success": True,
                    "session_id": request.session_id,
                    **interrupt_value
                }

        # Graph completed
        status = result.get("status")
        if status in ["completed", "documents_ready"]:
            await update_session_status(db, request.session_id, "completed")

            submission = await create_submission_record(
                db=db,
                user_uuid=str(current_user.user_uuid),
                session_id=request.session_id,
                answers=result.get("answers", {}),
                summaries=result.get("summaries", {}),
                case_uuid=str(result.get("created_case_uuid")) if result.get("created_case_uuid") else None
            )

            return {
                "success": True,
                "session_id": request.session_id,
                "status": "completed",
                "completed": True,
                "submission_id": str(submission.submission_id),
                "summaries": result.get("summaries", {}),
                "generated_documents": result.get("generated_documents", []),
                "case_uuid": str(result.get("created_case_uuid")) if result.get("created_case_uuid") else None
            }

        return {
            "success": True,
            "session_id": request.session_id,
            "status": status or "in_progress"
        }

    except Exception as e:
        print(f"❌ Failed to submit answer: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to submit answer: {str(e)}")


@router.post("/questionnaire/regenerate-summary")
async def regenerate_summary(
    request: RegenerateSummaryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Regenerate a part summary"""
    session = db.query(QuestionnaireSession).filter(
        QuestionnaireSession.session_id == uuid.UUID(request.session_id),
        QuestionnaireSession.user_uuid == current_user.user_uuid
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    config = {"configurable": {"thread_id": request.session_id}}

    try:
        graph = get_graph()
        state = await graph.aget_state(config)

        if not state or not state.values:
            raise HTTPException(status_code=404, detail="Session state not found")

        summaries = state.values.get("summaries", {})
        part_key = f"part{request.part_number}"

        return {
            "success": True,
            "session_id": request.session_id,
            "part_number": request.part_number,
            "summary": summaries.get(part_key, {})
        }

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to regenerate summary: {str(e)}")


@router.get("/questionnaire/sessions/incomplete")
async def get_incomplete_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all incomplete questionnaire sessions for the current user"""
    sessions = db.query(QuestionnaireSession).filter(
        QuestionnaireSession.user_uuid == current_user.user_uuid,
        QuestionnaireSession.status == "in_progress",
        QuestionnaireSession.is_finalized == False
    ).order_by(QuestionnaireSession.last_activity_at.desc()).all()

    result = []
    for session in sessions:
        session_data = {
            "session_id": str(session.session_id),
            "questionnaire_type": session.questionnaire_type,
            "status": session.status,
            "current_step": session.current_step,
            "total_steps": session.total_steps,
            "started_at": session.started_at.isoformat() if session.started_at else None,
            "last_activity_at": session.last_activity_at.isoformat() if session.last_activity_at else None,
            "expires_at": session.expires_at.isoformat() if session.expires_at else None,
            "progress_percentage": round((session.current_step / session.total_steps * 100) if session.total_steps else 0),
        }

        # Try to get more info from LangGraph state
        try:
            config = {"configurable": {"thread_id": str(session.session_id)}}
            graph = get_graph()
            state = await graph.aget_state(config)

            if state and state.values:
                current_state = state.values
                session_data.update({
                    "current_part": current_state.get("current_part"),
                    "answered_count": current_state.get("answered_count", 0),
                    "progress": current_state.get("progress"),
                    "part_info": current_state.get("part_info"),
                })
        except Exception as e:
            print(f"Could not get LangGraph state for session {session.session_id}: {e}")

        result.append(session_data)

    return {"sessions": result, "count": len(result)}


@router.get("/questionnaire/session/{session_id}/resume")
async def resume_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Resume an incomplete questionnaire session - returns current question"""
    session = db.query(QuestionnaireSession).filter(
        QuestionnaireSession.session_id == uuid.UUID(session_id),
        QuestionnaireSession.user_uuid == current_user.user_uuid
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status == "completed":
        raise HTTPException(status_code=400, detail="Session already completed")

    if session.is_finalized:
        raise HTTPException(status_code=400, detail="Session already finalized")

    config = {"configurable": {"thread_id": session_id}}

    try:
        graph = get_graph()
        state = await graph.aget_state(config)

        if not state or not state.values:
            raise HTTPException(status_code=404, detail="Session state not found in LangGraph. Session may have expired.")

        current_state = state.values

        # Check if there's a pending interrupt (current question)
        if state.next:
            # There's a pending interrupt - extract question data from state
            interrupt_value = current_state.get("current_question")
            progress = current_state.get("progress")
            part_info = current_state.get("part_info")

            if interrupt_value:
                # Update last activity
                session.last_activity_at = datetime.utcnow()
                db.commit()

                return {
                    "success": True,
                    "session_id": session_id,
                    "status": "awaiting_input",
                    "question": interrupt_value,
                    "progress": progress,
                    "part_info": part_info,
                    "answered_count": current_state.get("answered_count", 0),
                    "answers": current_state.get("answers", {}),
                }

        # No pending interrupt - session might be in a weird state
        return {
            "success": True,
            "session_id": session_id,
            "status": current_state.get("status", "unknown"),
            "current_part": current_state.get("current_part"),
            "answered_count": current_state.get("answered_count", 0),
            "message": "Session found but no pending question. May need to restart."
        }

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to resume session: {str(e)}")


@router.get("/questionnaire/session/{session_id}")
async def get_session_status(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the current status of a questionnaire session"""
    session = db.query(QuestionnaireSession).filter(
        QuestionnaireSession.session_id == uuid.UUID(session_id),
        QuestionnaireSession.user_uuid == current_user.user_uuid
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    config = {"configurable": {"thread_id": session_id}}

    try:
        graph = get_graph()
        state = await graph.aget_state(config)

        if not state or not state.values:
            return {
                "session_id": session_id,
                "status": session.status,
                "current_step": session.current_step,
                "total_steps": session.total_steps,
                "questionnaire_type": session.questionnaire_type,
                "created_at": session.started_at.isoformat() if session.started_at else None
            }

        current_state = state.values

        return {
            "session_id": session_id,
            "status": current_state.get("status"),
            "current_part": current_state.get("current_part"),
            "progress": current_state.get("progress"),
            "answered_count": current_state.get("answered_count"),
            "summaries": list(current_state.get("summaries", {}).keys()),
            "has_autofill_data": bool(current_state.get("autofill_data"))
        }

    except Exception as e:
        return {
            "session_id": session_id,
            "status": session.status,
            "current_step": session.current_step,
            "error": str(e)
        }


@router.delete("/questionnaire/session/{session_id}")
async def delete_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a questionnaire session"""
    session = db.query(QuestionnaireSession).filter(
        QuestionnaireSession.session_id == uuid.UUID(session_id),
        QuestionnaireSession.user_uuid == current_user.user_uuid
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status == "completed" and session.is_finalized:
        raise HTTPException(status_code=400, detail="Cannot delete finalized session")

    db.delete(session)
    db.commit()

    return {"success": True, "message": f"Session {session_id} deleted"}


class GoBackRequest(BaseModel):
    session_id: str = Field(..., description="会话ID")
    target_question_id: Optional[str] = Field(default=None, description="目标问题ID (可选，默认回到上一个)")


@router.post("/questionnaire/go-back")
async def go_back_to_previous(
    request: GoBackRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Go back to a previous question in the questionnaire.
    This manipulates the LangGraph state to rewind to a previous question.
    """
    session = db.query(QuestionnaireSession).filter(
        QuestionnaireSession.session_id == uuid.UUID(request.session_id),
        QuestionnaireSession.user_uuid == current_user.user_uuid
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status == "completed":
        raise HTTPException(status_code=400, detail="Cannot go back in completed questionnaire")

    config = {"configurable": {"thread_id": request.session_id}}

    try:
        graph = get_graph()
        state = await graph.aget_state(config)

        if not state or not state.values:
            raise HTTPException(status_code=404, detail="Session state not found")

        current_state = state.values
        answers = current_state.get("answers", {})
        current_question_index = current_state.get("current_question_index", 0)

        if current_question_index <= 0 and not request.target_question_id:
            raise HTTPException(status_code=400, detail="Already at the first question")

        # Calculate target index
        if request.target_question_id:
            # Find the index of the target question
            from graphs.questionnaire.data import get_all_questions
            all_questions = get_all_questions()
            target_index = None
            for i, q in enumerate(all_questions):
                if q.get("id") == request.target_question_id:
                    target_index = i
                    break
            if target_index is None:
                raise HTTPException(status_code=400, detail=f"Question {request.target_question_id} not found")
            if target_index >= current_question_index:
                raise HTTPException(status_code=400, detail="Cannot go forward with go-back")
        else:
            # Go back one question
            target_index = current_question_index - 1

        # Get the target question
        from graphs.questionnaire.data import get_all_questions, get_part_for_question_index
        all_questions = get_all_questions()
        target_question = all_questions[target_index]
        target_part = get_part_for_question_index(target_index)

        # Remove answers for questions after target
        questions_to_remove = []
        for i in range(target_index, len(all_questions)):
            q_id = all_questions[i].get("id")
            if q_id in answers:
                questions_to_remove.append(q_id)

        new_answers = {k: v for k, v in answers.items() if k not in questions_to_remove}

        # Update the state
        updated_state = {
            **current_state,
            "current_question_index": target_index,
            "current_part": target_part,
            "answered_count": target_index,
            "answers": new_answers,
            "current_question": target_question,
            "progress": {
                "current": target_index + 1,
                "total": len(all_questions),
                "percentage": round((target_index / len(all_questions)) * 100)
            },
            "part_info": {
                "current": target_part,
                "name": f"第{target_part}部分"
            }
        }

        # Update the graph state
        await graph.aupdate_state(config, updated_state)

        # Update database
        session.current_step = target_index
        session.last_activity_at = datetime.utcnow()
        db.commit()

        # Get previous answer if it exists
        previous_answer = answers.get(target_question.get("id"))

        return {
            "success": True,
            "session_id": request.session_id,
            "status": "awaiting_input",
            "question": target_question,
            "previous_answer": previous_answer,
            "progress": updated_state["progress"],
            "part_info": updated_state["part_info"],
            "can_go_back": target_index > 0
        }

    except HTTPException:
        raise
    except ImportError as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Module import error: {str(e)}")
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to go back: {str(e)}")


@router.post("/questionnaire/create-case")
async def create_case_from_session(
    request: CreateCaseFromQuestionnaireRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Manually create a case from a completed questionnaire session"""
    session = db.query(QuestionnaireSession).filter(
        QuestionnaireSession.session_id == uuid.UUID(request.session_id),
        QuestionnaireSession.user_uuid == current_user.user_uuid
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.case_uuid:
        raise HTTPException(status_code=400, detail="Case already created for this session")

    config = {"configurable": {"thread_id": request.session_id}}

    try:
        graph = get_graph()
        state = await graph.aget_state(config)

        if not state or not state.values:
            raise HTTPException(status_code=404, detail="Session state not found")

        current_state = state.values
        answers = current_state.get("answers", {})
        summaries = current_state.get("summaries", {})

        new_case = await create_case_from_questionnaire(
            db=db,
            user_uuid=str(current_user.user_uuid),
            session_id=request.session_id,
            answers=answers,
            summaries=summaries,
            title=request.title,
            priority=request.priority
        )

        return {
            "success": True,
            "case_uuid": str(new_case.case_uuid),
            "case_title": new_case.title,
            "message": "Case created successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to create case: {str(e)}")


@router.get("/health")
async def health_check():
    """Health check endpoint for the workflow service"""
    try:
        graph = get_graph()
        return {
            "status": "healthy",
            "service": "langgraph-workflow",
            "graph": "initialized" if graph else "not initialized"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


# ==================== Finalization Endpoint ====================

class FinalizeQuestionnaireRequest(BaseModel):
    session_id: str = Field(..., description="会话ID")
    create_case: bool = Field(default=False, description="是否创建案件到案件池")
    case_title: Optional[str] = Field(None, description="案件标题")
    case_priority: str = Field(default="medium", description="案件优先级")
    selected_templates: Optional[list] = Field(default=None, description="选择的文档模板编号列表")


@router.post("/questionnaire/finalize")
async def finalize_questionnaire(
    request: FinalizeQuestionnaireRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Finalize a questionnaire session:
    1. Store all answers to PostgreSQL
    2. Optionally create a case in the case pool
    3. Generate selected document templates
    4. Mark session as finalized
    """
    session = db.query(QuestionnaireSession).filter(
        QuestionnaireSession.session_id == uuid.UUID(request.session_id),
        QuestionnaireSession.user_uuid == current_user.user_uuid
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.is_finalized:
        raise HTTPException(status_code=400, detail="Session already finalized")

    config = {"configurable": {"thread_id": request.session_id}}

    try:
        graph = get_graph()
        state = await graph.aget_state(config)

        if not state or not state.values:
            raise HTTPException(status_code=404, detail="Session state not found")

        current_state = state.values
        answers = current_state.get("answers", {})
        summaries = current_state.get("summaries", {})
        should_create_case = current_state.get("should_create_case", False)
        
        # Store answers in session_data
        session.session_data = {
            "answers": answers,
            "summaries": summaries,
            "should_create_case": should_create_case,
            "finalized_at": datetime.utcnow().isoformat()
        }
        session.status = "completed"
        session.completed_at = datetime.utcnow()
        session.is_finalized = True
        
        # Create submission record
        submission = QuestionnaireSubmission(
            submission_id=uuid.uuid4(),
            session_id=session.session_id,
            user_uuid=current_user.user_uuid,
            questionnaire_type=session.questionnaire_type,
            title="交通事故法律咨询问卷",
            responses=answers,
            meta_data={
                "summaries": summaries,
                "should_create_case": should_create_case,
                "completed_at": datetime.utcnow().isoformat()
            },
            processing_status="completed"
        )
        db.add(submission)
        
        result = {
            "success": True,
            "session_id": request.session_id,
            "submission_id": str(submission.submission_id),
            "answers_saved": True,
            "answers_count": len(answers),
            "summaries": summaries
        }
        
        # Create case if requested or if user selected "需要律师"
        case_created = None
        if request.create_case or should_create_case:
            try:
                new_case = await create_case_from_questionnaire(
                    db=db,
                    user_uuid=str(current_user.user_uuid),
                    session_id=request.session_id,
                    answers=answers,
                    summaries=summaries,
                    title=request.case_title,
                    priority=request.case_priority
                )
                case_created = {
                    "case_uuid": str(new_case.case_uuid),
                    "title": new_case.title,
                    "status": new_case.case_status
                }
                result["case"] = case_created
                submission.case_uuid = new_case.case_uuid
            except Exception as e:
                result["case_error"] = str(e)
        
        # Generate documents if templates selected
        generated_docs = []
        if request.selected_templates:
            try:
                from services.document_filler import get_filler_service
                filler = get_filler_service()
                autofill_data = current_state.get("autofill_data", {})
                
                for template_code in request.selected_templates:
                    try:
                        doc_result = await filler.fill_from_questionnaire(
                            template_code=template_code,
                            questionnaire_answers=answers,
                            autofill_data=autofill_data,
                            session_id=request.session_id,
                            user_id=str(current_user.user_uuid)
                        )
                        if doc_result.get("success"):
                            generated_docs.append({
                                "template_code": template_code,
                                "document_id": doc_result.get("document_id"),
                                "filename": doc_result.get("output_filename"),
                                "download_url": doc_result.get("download_url"),
                                "success": True
                            })
                        else:
                            generated_docs.append({
                                "template_code": template_code,
                                "error": doc_result.get("error", "生成失败"),
                                "success": False
                            })
                    except Exception as doc_err:
                        generated_docs.append({
                            "template_code": template_code,
                            "error": str(doc_err),
                            "success": False
                        })
                        
                result["generated_documents"] = generated_docs
            except ImportError:
                result["documents_error"] = "Document filler service not available"
        
        db.commit()
        
        return result

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to finalize: {str(e)}")


@router.get("/questionnaire/session/{session_id}/completion-data")
async def get_completion_data(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all data needed for the completion page:
    - Answers and summaries
    - Whether case should be created
    - Recommended templates
    - Evidence list
    """
    session = db.query(QuestionnaireSession).filter(
        QuestionnaireSession.session_id == uuid.UUID(session_id),
        QuestionnaireSession.user_uuid == current_user.user_uuid
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    config = {"configurable": {"thread_id": session_id}}

    try:
        graph = get_graph()
        state = await graph.aget_state(config)

        if not state or not state.values:
            # Try to get from session_data if LangGraph state is lost
            if session.session_data:
                return {
                    "success": True,
                    "session_id": session_id,
                    "status": session.status,
                    "is_finalized": session.is_finalized,
                    "answers": session.session_data.get("answers", {}),
                    "summaries": session.session_data.get("summaries", {}),
                    "should_create_case": session.session_data.get("should_create_case", False),
                    "case_uuid": str(session.case_uuid) if session.case_uuid else None,
                    "recommended_templates": [],
                    "evidence_list": []
                }
            raise HTTPException(status_code=404, detail="Session state not found")

        current_state = state.values
        answers = current_state.get("answers", {})
        summaries = current_state.get("summaries", {})
        should_create_case = current_state.get("should_create_case", False)
        evidence_list = current_state.get("evidence_list", [])
        uploaded_files = current_state.get("uploaded_files", [])
        
        # Get recommended templates
        try:
            from graphs.questionnaire.data import get_recommended_templates
            recommended_templates = get_recommended_templates(answers)
        except Exception:
            recommended_templates = [
                {"code": "035", "name": "民事起诉状", "description": "标准民事起诉状模板"},
                {"code": "008", "name": "授权委托书", "description": "律师授权委托书"},
            ]
        
        return {
            "success": True,
            "session_id": session_id,
            "status": current_state.get("status", session.status),
            "is_finalized": session.is_finalized,
            "answers": answers,
            "summaries": summaries,
            "should_create_case": should_create_case,
            "case_uuid": str(session.case_uuid) if session.case_uuid else None,
            "recommended_templates": recommended_templates,
            "evidence_list": evidence_list,
            "uploaded_files": uploaded_files,
            "questionnaire_type": session.questionnaire_type,
            "started_at": session.started_at.isoformat() if session.started_at else None,
            "completed_at": session.completed_at.isoformat() if session.completed_at else None
        }

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to get completion data: {str(e)}")


# ==================== Document Generation Demo Endpoint ====================

class GenerateDocumentRequest(BaseModel):
    session_id: str = Field(..., description="会话ID")
    template_code: str = Field(default="035", description="模板编号")
    preview_only: bool = Field(default=False, description="仅预览，不保存")


@router.post("/questionnaire/generate-document")
async def generate_document_from_questionnaire(
    request: GenerateDocumentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate a document from questionnaire answers.
    This is the demo endpoint for document auto-filling.
    Uses all collected answers from the questionnaire to fill the template.
    """
    session = db.query(QuestionnaireSession).filter(
        QuestionnaireSession.session_id == uuid.UUID(request.session_id),
        QuestionnaireSession.user_uuid == current_user.user_uuid
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    config = {"configurable": {"thread_id": request.session_id}}

    try:
        graph = get_graph()
        state = await graph.aget_state(config)

        if not state or not state.values:
            raise HTTPException(status_code=404, detail="Session state not found")

        current_state = state.values
        answers = current_state.get("answers", {})
        autofill_data = current_state.get("autofill_data", {})

        # Extract actual values from answers (they might be wrapped in {value:..., answered_at:...})
        clean_answers = {}
        for q_id, ans in answers.items():
            if isinstance(ans, dict):
                value = ans.get("value", "")
                # If value is also a dict (form answers), merge it
                if isinstance(value, dict):
                    for field_name, field_value in value.items():
                        clean_answers[field_name] = field_value
                else:
                    clean_answers[q_id] = value
            else:
                clean_answers[q_id] = ans

        # Merge autofill data (OCR results)
        if autofill_data:
            for key, value in autofill_data.items():
                if value and key not in clean_answers:
                    clean_answers[key] = value

        # Generate the document
        try:
            from services.document_filler import get_filler_service
            filler = get_filler_service()

            result = await filler.fill_from_questionnaire(
                template_code=request.template_code,
                questionnaire_answers=clean_answers,
                autofill_data=autofill_data,
                session_id=request.session_id,
                user_id=str(current_user.user_uuid)
            )

            if result.get("success"):
                # Update session to record document generation
                if not request.preview_only:
                    generated_docs = current_state.get("generated_documents", [])
                    generated_docs.append({
                        "template_code": request.template_code,
                        "document_id": result.get("document_id"),
                        "filename": result.get("output_filename"),
                        "download_url": result.get("download_url"),
                        "generated_at": datetime.utcnow().isoformat()
                    })
                    
                    # Update state with generated document
                    await graph.aupdate_state(config, {
                        **current_state,
                        "generated_documents": generated_docs
                    })

                return {
                    "success": True,
                    "session_id": request.session_id,
                    "template_code": request.template_code,
                    "document_id": result.get("document_id"),
                    "filename": result.get("output_filename"),
                    "download_url": result.get("download_url"),
                    "filled_fields": result.get("filled_fields", 0),
                    "preview_only": request.preview_only,
                    "message": "文档生成成功！" if not request.preview_only else "预览文档已生成"
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error", "文档生成失败"),
                    "template_code": request.template_code
                }

        except ImportError as e:
            return {
                "success": False,
                "error": f"文档服务不可用: {str(e)}",
                "template_code": request.template_code
            }

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to generate document: {str(e)}")


# ==================== LLM Test Endpoint ====================

@router.get("/llm/test")
async def test_llm_backends():
    """
    Test which LLM backends are available.
    Useful for debugging and configuration verification.
    """
    try:
        from services.llm_service import test_llm_connection
        results = await test_llm_connection()
        
        # Determine overall status
        any_working = any(r.get("status") == "ok" for r in results.values())
        
        return {
            "success": True,
            "any_backend_available": any_working,
            "backends": results,
            "recommendation": "All backends working!" if any_working else "Please configure at least one LLM backend. Options: 1) Start Ollama locally, 2) Set DEEPSEEK_API_KEY, 3) Set SILICONFLOW_API_KEY, 4) Set OPENAI_API_KEY"
        }
    except Exception as e:
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e)
        }


# ==================== Legacy Compatibility Endpoints ====================

@router.post("/questionnaire/webhook/start")
async def legacy_start_questionnaire(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Legacy endpoint for compatibility with existing frontend"""
    try:
        data = await request.json()
        template_type = data.get("template_type", 1)
        start_request = StartRequest(template_type=template_type)
        return await start_questionnaire(start_request, current_user, db)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/questionnaire/webhook/answer")
async def legacy_submit_answer(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Legacy endpoint for compatibility with existing frontend"""
    try:
        data = await request.json()
        answer_request = AnswerRequest(
            session_id=data.get("session_id"),
            question_id=data.get("question_id"),
            answer=data.get("answer"),
            file=data.get("file")
        )
        return await submit_answer(answer_request, current_user, db)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/questionnaire/webhook/summary-regenerate")
async def legacy_regenerate_summary(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Legacy endpoint for compatibility"""
    try:
        data = await request.json()
        regen_request = RegenerateSummaryRequest(
            session_id=data.get("session_id"),
            part_number=data.get("part_number", 1)
        )
        return await regenerate_summary(regen_request, current_user, db)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ==================== File Upload Endpoint ====================

from fastapi import UploadFile, File, Form
from pathlib import Path
import base64
import os

# Upload directory
UPLOAD_DIR = Path("uploads/questionnaire_files")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/questionnaire/upload")
async def upload_questionnaire_file(
    file: UploadFile = File(...),
    session_id: str = Form(...),
    question_id: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload a file for a questionnaire question (e.g., ID card, evidence photo).
    Accepts multipart/form-data with direct file upload.
    """
    # Verify session ownership
    session = db.query(QuestionnaireSession).filter(
        QuestionnaireSession.session_id == uuid.UUID(session_id),
        QuestionnaireSession.user_uuid == current_user.user_uuid
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status == "completed":
        raise HTTPException(status_code=400, detail="Questionnaire already completed")

    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/jpg", "image/webp", "application/pdf"]
    content_type = file.content_type or "application/octet-stream"

    if content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Allowed: {', '.join(allowed_types)}"
        )

    # Generate unique filename
    file_ext = Path(file.filename).suffix if file.filename else ".bin"
    file_id = f"{session_id}_{question_id}_{uuid.uuid4().hex[:8]}"
    filename = f"{file_id}{file_ext}"

    # Create session directory
    session_dir = UPLOAD_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    file_path = session_dir / filename

    try:
        # Read and save file directly
        content = await file.read()

        with open(file_path, "wb") as f:
            f.write(content)

        print(f"[upload] Saved: {file_path} ({len(content)} bytes)")

        # Optional: Call OCR service if it's an image
        ocr_result = None
        if content_type.startswith("image/"):
            try:
                import httpx
                # Convert to base64 for OCR service
                base64_content = base64.b64encode(content).decode("utf-8")
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        "http://localhost:8765/ocr",
                        json={"image_base64": base64_content},
                        timeout=30.0
                    )
                    if response.status_code == 200:
                        ocr_result = response.json()
                        print(f"[upload] OCR done")
            except Exception as ocr_error:
                print(f"[upload] OCR unavailable: {ocr_error}")

        return {
            "success": True,
            "file_id": file_id,
            "filename": file.filename,
            "content_type": content_type,
            "size": len(content),
            "path": str(file_path),
            "ocr_result": ocr_result,
            "evidence_number": f"EV-{uuid.uuid4().hex[:8].upper()}"
        }

    except Exception as e:
        print(f"[upload] ERROR: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")


@router.get("/questionnaire/upload/{session_id}/{file_id}")
async def get_uploaded_file(
    session_id: str,
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get info about an uploaded file"""
    # Verify session ownership
    session = db.query(QuestionnaireSession).filter(
        QuestionnaireSession.session_id == uuid.UUID(session_id),
        QuestionnaireSession.user_uuid == current_user.user_uuid
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Find file
    session_dir = UPLOAD_DIR / session_id
    if not session_dir.exists():
        raise HTTPException(status_code=404, detail="No files found for this session")

    # Find file matching file_id
    for f in session_dir.iterdir():
        if f.name.startswith(file_id):
            return {
                "file_id": file_id,
                "filename": f.name,
                "size": f.stat().st_size,
                "path": str(f)
            }

    raise HTTPException(status_code=404, detail="File not found")


# Export for main.py imports
questionnaire_graph = None  # Will be set on first use via get_graph()
checkpointer = None