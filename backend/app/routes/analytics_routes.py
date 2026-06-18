from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User
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
