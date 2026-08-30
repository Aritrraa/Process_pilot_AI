from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional

from ..database import get_db
from ..models import User, AIFailure
from ..schemas import ChatQuery
from ..auth import get_current_user
from ..agents import process_query, process_query_stream

router = APIRouter(prefix="/chat", tags=["AI Chat"])


class FeedbackPayload(BaseModel):
    query: str
    response: str
    feedback_type: str  # 'thumbs_up' or 'thumbs_down'
    notes: Optional[str] = None


@router.post("/")
async def chat_with_ai(
    query: ChatQuery,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Main endpoint for the AI Copilot using Server-Sent Events (SSE).
    """
    if getattr(query, 'stream', True):  # Default to streaming
        return StreamingResponse(
            process_query_stream(current_user, query.query, db, scope=query.scope),
            media_type="text/event-stream",
            headers={
                "X-Accel-Buffering": "no",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )
    return await process_query(current_user, query.query, db, scope=query.scope)


@router.post("/feedback")
async def submit_feedback(
    payload: FeedbackPayload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Human-in-the-Loop (HITL) endpoint.
    Logs thumbs up/down feedback on AI responses for weekly review.
    Only thumbs_down entries are persisted to the ai_failures table.
    """
    if payload.feedback_type == "thumbs_down":
        failure = AIFailure(
            user_id=current_user.id,
            query=payload.query,
            response=payload.response,
            feedback_type=payload.feedback_type,
            notes=payload.notes,
        )
        db.add(failure)
        await db.commit()
        return {"status": "logged", "message": "Feedback recorded. Thank you — this helps us improve!"}

    # thumbs_up — acknowledge but don't store
    return {"status": "ok", "message": "Great! Glad the response was helpful."}
