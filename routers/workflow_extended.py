"""
Additional LangGraph Workflow Endpoints
=======================================

Adds summary validation and template selection endpoints.
Uses the same graph instance as workflow.py
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import uuid
import traceback

from sqlalchemy.orm import Session
from langgraph.types import Command

from database import get_db
from models.user import User
from models.questionnaire import QuestionnaireSession
from utils.auth import get_current_user

router = APIRouter(prefix="/api/workflow", tags=["workflow-extended"])


# ==================== Share graph with workflow.py ====================

def get_graph():
    """Get the graph from workflow.py (shared instance)"""
    from routers.workflow import get_graph as _get_graph
    return _get_graph()


# ==================== Request Schemas ====================

class ValidateSummaryRequest(BaseModel):
    session_id: str
    approved: bool
    feedback: Optional[str] = None


class SelectTemplatesRequest(BaseModel):
    session_id: str
    selected_templates: List[str]


# ==================== Endpoints ====================

@router.post("/questionnaire/validate-summary")
async def validate_summary(
    request: ValidateSummaryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Validate/approve the AI-generated summary"""
    session = db.query(QuestionnaireSession).filter(
        QuestionnaireSession.session_id == uuid.UUID(request.session_id),
        QuestionnaireSession.user_uuid == current_user.user_uuid
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    config = {"configurable": {"thread_id": request.session_id}}

    try:
        graph = get_graph()

        print(f"[validate-summary] approved={request.approved}, feedback={request.feedback}")

        result = await graph.ainvoke(
            Command(resume={"approved": request.approved, "feedback": request.feedback}),
            config=config
        )

        print(f"[validate-summary] result status: {result.get('status')}")

        # Check for interrupt first
        interrupt_info = result.get("__interrupt__", [])

        if interrupt_info:
            interrupt_value = interrupt_info[0].value if hasattr(interrupt_info[0], 'value') else interrupt_info[0]
            interrupt_type = interrupt_value.get("type", "unknown")

            print(f"[validate-summary] interrupt type: {interrupt_type}")

            if interrupt_type == "question":
                return {
                    "success": True,
                    "session_id": request.session_id,
                    "status": "awaiting_input",
                    "next_part": True,
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

        # No interrupt - check status
        status = result.get("status", "in_progress")

        if status in ["completed", "documents_ready"]:
            # Update session
            session.status = "completed"
            session.completed_at = datetime.utcnow()
            session.is_finalized = True
            db.commit()

            return {
                "success": True,
                "session_id": request.session_id,
                "status": "completed",
                "completed": True,
                "summaries": result.get("summaries", {}),
                "generated_documents": result.get("generated_documents", []),
                "submission_id": result.get("submission_id")
            }

        return {
            "success": True,
            "session_id": request.session_id,
            "status": status,
            "completed": False
        }

    except Exception as e:
        print(f"[validate-summary] ERROR: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to validate summary: {str(e)}")


@router.post("/questionnaire/select-templates")
async def select_templates(
    request: SelectTemplatesRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Select document templates to generate"""
    session = db.query(QuestionnaireSession).filter(
        QuestionnaireSession.session_id == uuid.UUID(request.session_id),
        QuestionnaireSession.user_uuid == current_user.user_uuid
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    config = {"configurable": {"thread_id": request.session_id}}

    try:
        graph = get_graph()

        # Handle empty or skip
        selected = request.selected_templates
        if not selected or selected == ["skip"]:
            selected = []

        print(f"[select-templates] selected: {selected}")

        result = await graph.ainvoke(
            Command(resume=selected),
            config=config
        )

        print(f"[select-templates] result status: {result.get('status')}")

        # Check for interrupt
        interrupt_info = result.get("__interrupt__", [])

        if interrupt_info:
            interrupt_value = interrupt_info[0].value if hasattr(interrupt_info[0], 'value') else interrupt_info[0]
            return {
                "success": True,
                "session_id": request.session_id,
                **interrupt_value
            }

        # Completed
        status = result.get("status", "in_progress")

        if status in ["completed", "documents_ready"]:
            session.status = "completed"
            session.completed_at = datetime.utcnow()
            session.is_finalized = True
            db.commit()

            return {
                "success": True,
                "session_id": request.session_id,
                "status": "completed",
                "completed": True,
                "summaries": result.get("summaries", {}),
                "generated_documents": result.get("generated_documents", []),
                "submission_id": result.get("submission_id")
            }

        return {
            "success": True,
            "session_id": request.session_id,
            "status": status,
            "completed": False
        }

    except Exception as e:
        print(f"[select-templates] ERROR: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to select templates: {str(e)}")