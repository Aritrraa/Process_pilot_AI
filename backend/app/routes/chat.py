from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

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
    Main endpoint for the AI Copilot.
    Orchestrates multi-agent pipeline: Search → Incident → SOP → Memory → CEO synthesis.
    """
    result = ceo_agent.process_query(current_user, query.message, db, scope=query.scope)
    return result
