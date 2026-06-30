"""
Audit Trail System — logs all significant actions for compliance.
Free-tier compatible: stores in SQLite/PostgreSQL, no external services.
"""
import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session

logger = logging.getLogger("processpilot.audit")


def log_action(
    db: Session,
    user_id: int,
    action: str,
    resource_type: str = None,
    resource_id: int = None,
    details: str = None,
    ip_address: str = None
):
    """
    Log an action to the audit trail.
    
    Actions: login, register, upload, delete, chat, access_denied, 
             task_update, meeting_create, settings_update
    Resource types: document, task, meeting, user, settings
    """
    try:
        from .models import AuditLog
        entry = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address,
            created_at=datetime.now(timezone.utc)
        )
        db.add(entry)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to log audit action '{action}': {e}")
        try:
            db.rollback()
        except Exception:
            pass


def get_audit_log(db: Session, user_id: int = None, action: str = None, limit: int = 100):
    """Retrieve audit log entries with optional filters."""
    from .models import AuditLog
    query = db.query(AuditLog)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if action:
        query = query.filter(AuditLog.action == action)
    return query.order_by(AuditLog.created_at.desc()).limit(limit).all()
