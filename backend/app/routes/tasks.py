from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models import User, Task
from ..schemas import TaskCreate, TaskUpdate, TaskResponse
from ..auth import get_current_user

router = APIRouter(prefix="/tasks", tags=["Tasks"])

@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    task_in: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    assigned_to = task_in.assigned_to if task_in.assigned_to is not None else current_user.id
    
    # Check if assignee exists
    assignee = db.query(User).filter(User.id == assigned_to).first()
    if not assignee:
        raise HTTPException(status_code=404, detail="Assignee user not found")
        
    # Check permissions: Managers can only assign to themselves or their subordinates.
    if current_user.role == "Manager":
        if assigned_to != current_user.id and assignee.manager_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Managers can only assign tasks to their team members"
            )
    elif current_user.role == "Employee":
        if assigned_to != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Employees can only assign tasks to themselves"
            )

    task_manager_id = assignee.manager_id if assignee.role == "Employee" else assignee.id
    task = Task(
        title=task_in.title,
        description=task_in.description,
        assigned_to=assigned_to,
        manager_id=task_manager_id,
        document_id=task_in.document_id,
        meeting_id=task_in.meeting_id,
        status="Pending"
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    
    assignee_name = assignee.full_name or assignee.email
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "status": task.status,
        "assigned_to": task.assigned_to,
        "assignee_name": assignee_name,
        "manager_id": task.manager_id,
        "document_id": task.document_id,
        "meeting_id": task.meeting_id,
        "created_at": task.created_at
    }

@router.get("/", response_model=List[TaskResponse])
def list_tasks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role == "Admin":
        tasks = db.query(Task).all()
    elif current_user.role == "Manager":
        # Managers see their own tasks + tasks of their subordinates matching their manager ID context
        subordinate_ids = [u.id for u in db.query(User).filter(User.manager_id == current_user.id).all()]
        tasks = db.query(Task).filter(
            (Task.assigned_to == current_user.id) | 
            ((Task.assigned_to.in_(subordinate_ids)) & (Task.manager_id == current_user.id))
        ).all()
    else:
        # Employees see tasks assigned to them under their active manager context (or public/none)
        tasks = db.query(Task).filter(
            (Task.assigned_to == current_user.id) & 
            ((Task.manager_id == current_user.manager_id) | (Task.manager_id == None))
        ).all()

    # Pre-fetch users for assignee_name mapping to avoid N+1 queries
    users_dict = {u.id: (u.full_name or u.email) for u in db.query(User).all()}
    
    res = []
    for t in tasks:
        res.append({
            "id": t.id,
            "title": t.title,
            "description": t.description,
            "status": t.status,
            "assigned_to": t.assigned_to,
            "assignee_name": users_dict.get(t.assigned_to) if t.assigned_to else None,
            "manager_id": t.manager_id,
            "document_id": t.document_id,
            "meeting_id": t.meeting_id,
            "created_at": t.created_at
        })
    return res

from ..abac import verify_task_access

@router.patch("/{task_id}", response_model=TaskResponse)
def update_task_status(
    task_update: TaskUpdate,
    task: Task = Depends(verify_task_access("update")),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if task_update.status is not None:
        task.status = task_update.status
        
    if task_update.assigned_to is not None:
        # Verify the target user exists
        new_assignee = db.query(User).filter(User.id == task_update.assigned_to).first()
        if not new_assignee:
            raise HTTPException(status_code=404, detail="New assignee user not found")
            
        # Role-based assignment validation
        if current_user.role == "Manager":
            if task_update.assigned_to != current_user.id and new_assignee.manager_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Managers can only assign tasks to their team members"
                )
        elif current_user.role == "Employee":
            if task_update.assigned_to != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Employees can only assign tasks to themselves"
                )
        # Reset status to Pending (To Do) when assignee changes, unless a specific status was also provided
        if task_update.status is None and task.assigned_to != task_update.assigned_to:
            task.status = "Pending"
        task.assigned_to = task_update.assigned_to
        task.manager_id = new_assignee.manager_id if new_assignee.role == "Employee" else new_assignee.id

    db.commit()
    db.refresh(task)
    
    assignee = db.query(User).filter(User.id == task.assigned_to).first() if task.assigned_to else None
    assignee_name = (assignee.full_name or assignee.email) if assignee else None
    
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "status": task.status,
        "assigned_to": task.assigned_to,
        "assignee_name": assignee_name,
        "manager_id": task.manager_id,
        "document_id": task.document_id,
        "meeting_id": task.meeting_id,
        "created_at": task.created_at
    }

@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task: Task = Depends(verify_task_access("delete")),
    db: Session = Depends(get_db)
):
    db.delete(task)
    db.commit()
    return
