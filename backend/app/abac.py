from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from .database import get_db
from .models import User, Document, Task, Meeting
from .auth import get_current_user

def evaluate_policy(subject: User, resource_type: str, resource_obj: any, action: str, db: Session) -> bool:
    """
    Evaluates Attribute-Based Access Control (ABAC) policies.
    """
    # Admins bypass all policies
    if subject.role == "Admin":
        return True

    if resource_type == "document":
        doc = resource_obj
        if action == "create":
            return True
        elif action == "read":
            # Anyone in same department can read it
            return subject.department_id == doc.department_id
        elif action == "delete":
            # Employees can only delete their own documents
            if subject.role == "Employee":
                return doc.uploaded_by == subject.id
            # Managers can delete documents uploaded by their direct reports or by themselves
            if subject.role == "Manager":
                if doc.uploaded_by == subject.id:
                    return True
                uploader = db.query(User).filter(User.id == doc.uploaded_by).first()
                return uploader and uploader.manager_id == subject.id
            return False

    elif resource_type == "task":
        task = resource_obj
        if action in ("update", "change_status"):
            # Employees can update status of tasks assigned to them
            if task.assigned_to == subject.id:
                return True
            # Managers can update status/reassign tasks of their reports or themselves
            if subject.role == "Manager":
                if task.assigned_to == subject.id:
                    return True
                assignee = db.query(User).filter(User.id == task.assigned_to).first()
                return assignee and assignee.manager_id == subject.id
            return False
        elif action == "delete":
            # Only managers can delete tasks assigned to their reports/themselves
            if subject.role == "Manager":
                if task.assigned_to == subject.id:
                    return True
                assignee = db.query(User).filter(User.id == task.assigned_to).first()
                return assignee and assignee.manager_id == subject.id
            return False

    elif resource_type == "meeting":
        meeting = resource_obj
        if action == "read":
            # Employees can read meetings created by themselves, teammates, or their manager
            if meeting.uploaded_by == subject.id:
                return True
            creator = db.query(User).filter(User.id == meeting.uploaded_by).first()
            if not creator:
                return False
            if subject.role == "Employee":
                if creator.id == subject.manager_id:
                    return True
                if creator.manager_id == subject.manager_id and subject.manager_id is not None:
                    return True
            elif subject.role == "Manager":
                if creator.manager_id == subject.id:
                    return True
            return False

    return False

# FastAPI Dependency Factories
def verify_document_access(action: str):
    def dependency(document_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        if not evaluate_policy(subject=current_user, resource_type="document", resource_obj=doc, action=action, db=db):
            raise HTTPException(status_code=403, detail=f"Permission denied: cannot {action} this document")
        return doc
    return dependency

def verify_task_access(action: str):
    def dependency(task_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        if not evaluate_policy(subject=current_user, resource_type="task", resource_obj=task, action=action, db=db):
            raise HTTPException(status_code=403, detail=f"Permission denied: cannot {action} this task")
        return task
    return dependency

def verify_meeting_access(action: str):
    def dependency(meeting_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if not meeting:
            raise HTTPException(status_code=404, detail="Meeting not found")
        if not evaluate_policy(subject=current_user, resource_type="meeting", resource_obj=meeting, action=action, db=db):
            raise HTTPException(status_code=403, detail=f"Permission denied: cannot {action} this meeting")
        return meeting
    return dependency
