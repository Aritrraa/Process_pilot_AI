from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models import User, AIFailure, AgentLog
from ..auth import get_current_user, check_role
from ..analytics import get_system_analytics

router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("/")
def get_analytics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns system-wide analytics for the dashboard.
    Available to all authenticated users (Admin gets full view).
    """
    return get_system_analytics(db, current_user)


@router.get("/ai-failures")
def get_ai_failures(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(check_role(["Admin", "Manager"])),
    db: Session = Depends(get_db)
):
    """
    Human-in-the-Loop (HITL) Review Dashboard.
    Returns all logged AI failures (thumbs-down + implicit title edits).
    Admin and Manager only.
    """
    failures = (
        db.query(AIFailure)
        .order_by(AIFailure.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [
        {
            "id": f.id,
            "user_id": f.user_id,
            "feedback_type": f.feedback_type,
            "query": f.query,
            "response": f.response[:300] + "..." if f.response and len(f.response) > 300 else f.response,
            "notes": f.notes,
            "created_at": f.created_at.isoformat() if f.created_at else None,
        }
        for f in failures
    ]


@router.get("/synthetic-export")
def export_synthetic_dataset(
    limit: int = 500,
    current_user: User = Depends(check_role(["Admin"])),
    db: Session = Depends(get_db)
):
    """
    Synthetic Fine-Tuning Dataset Export.
    Exports high-quality (non-failed) query-response pairs from AgentLog
    in JSONL-ready format for fine-tuning smaller open-source models.
    Admin only.
    """
    # Get all logged agent interactions that have both a query and response
    logs = (
        db.query(AgentLog)
        .filter(AgentLog.query.isnot(None), AgentLog.response.isnot(None))
        .filter(AgentLog.response != "")
        .order_by(AgentLog.timestamp.desc())
        .limit(limit)
        .all()
    )

    # Get IDs of failed queries so we can exclude them
    failed_queries = set(
        f.query for f in db.query(AIFailure).filter(AIFailure.feedback_type == "thumbs_down").all()
    )

    # Build the dataset — exclude thumbs-down queries
    dataset = []
    for log in logs:
        if log.query in failed_queries:
            continue
        dataset.append({
            "instruction": "You are ProcessPilot AI, an Enterprise Operations Copilot. Answer the user's question based on company context.",
            "input": log.query,
            "output": log.response,
            "metadata": {
                "user_id": log.user_id,
                "timestamp": log.timestamp.isoformat() if log.timestamp else None,
            }
        })

    return JSONResponse(content={
        "total_records": len(dataset),
        "format": "alpaca_instruction_tuning",
        "description": "High-quality query-response pairs for fine-tuning. Thumbs-down responses are excluded.",
        "dataset": dataset
    })

