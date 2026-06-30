from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import json

from ..database import get_db
from ..models import User
from ..schemas import ChatQuery
from ..auth import get_current_user
from ..agents import ceo_agent

router = APIRouter(prefix="/chat", tags=["AI Chat"])

@router.post("/")
def chat_with_ai(
    query: ChatQuery,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Main endpoint for the AI Copilot using Server-Sent Events (SSE).
    """
    if getattr(query, 'stream', True):  # Default to streaming
        return StreamingResponse(
            ceo_agent.process_query_stream(current_user, query.message, db, scope=query.scope),
            media_type="text/event-stream"
        )
    return ceo_agent.process_query(current_user, query.message, db, scope=query.scope)
