from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
import json
import asyncio
import logging

logger = logging.getLogger("processpilot.tasks")

from .ws import manager

from ..database import get_db
from ..models import User, Task, AIFailure
from ..schemas import TaskCreate, TaskUpdate, TaskResponse
from ..auth import get_current_user

router = APIRouter(prefix="/tasks", tags=["Tasks"])

@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_in: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    assigned_to = task_in.assigned_to if task_in.assigned_to is not None else current_user.id
    
    # Check if assignee exists
    result = await db.execute(select(User).filter(User.id == assigned_to))
    assignee = result.scalars().first()
    if not assignee:
        raise HTTPException(status_code=404, detail="Assignee user not found")
        
    # Check permissions: Managers can only assign to themselves or their subordinates.
    if current_user.role in ("Manager", "Director"):
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
    assignee_name = assignee.full_name or assignee.email if assignee else None

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
    await db.commit()
    await db.refresh(task)
    
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
async def list_tasks(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role == "Admin":
        result = await db.execute(select(Task).offset(skip).limit(limit))
        tasks = result.scalars().all()
    elif current_user.role in ("Manager", "Director"):
        sub_result = await db.execute(select(User).filter(User.manager_id == current_user.id))
        subordinate_ids = [u.id for u in sub_result.scalars().all()]
        result = await db.execute(
            select(Task).filter(
                (Task.assigned_to == current_user.id) |
                ((Task.assigned_to.in_(subordinate_ids)) & (Task.manager_id == current_user.id))
            ).offset(skip).limit(limit)
        )
        tasks = result.scalars().all()
    else:
        result = await db.execute(
            select(Task).filter(
                (Task.assigned_to == current_user.id) &
                ((Task.manager_id == current_user.manager_id) | (Task.manager_id == None))
            ).offset(skip).limit(limit)
        )
        tasks = result.scalars().all()

    # Pre-fetch users for assignee_name mapping to avoid N+1 queries
    users_result = await db.execute(select(User))
    users_dict = {u.id: (u.full_name or u.email) for u in users_result.scalars().all()}
    
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

@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task: Task = Depends(verify_task_access("read"))
):
    """Get a specific task by ID."""
    return task

@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task_status(
    task_update: TaskUpdate,
    task: Task = Depends(verify_task_access("update")),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # ===== DATA FLYWHEEL: Implicit Feedback =====
    # If the user changes the title AND there was an AI-generated original,
    # log it as training signal — the manager implicitly told us the AI's title was wrong.
    if task_update.title is not None and task.ai_generated_title:
        if task_update.title.strip() != task.ai_generated_title.strip():
            try:
                flywheel_log = AIFailure(
                    user_id=current_user.id,
                    query=f"[Task Title Generation] Meeting-generated task",
                    response=task.ai_generated_title,
                    feedback_type="implicit_title_edit",
                    notes=f"Manager edited AI title to: '{task_update.title}'"
                )
                db.add(flywheel_log)
                logger.info(
                    f"[DataFlywheel] Title edit detected: "
                    f"'{task.ai_generated_title}' → '{task_update.title}'"
                )
            except Exception:
                pass  # Non-critical

    update_data = task_update.model_dump(exclude_unset=True)

    if "title" in update_data:
        task.title = update_data["title"]
        
    if "status" in update_data:
        task.status = update_data["status"]
        
    if "assigned_to" in update_data:
        new_assigned_to = update_data["assigned_to"]
        if new_assigned_to is not None:
            # Verify the target user exists
            result = await db.execute(select(User).filter(User.id == new_assigned_to))
            new_assignee = result.scalars().first()
            if not new_assignee:
                raise HTTPException(status_code=404, detail="New assignee user not found")
                
            # Role-based assignment validation
            if current_user.role in ("Manager", "Director"):
                if new_assigned_to != current_user.id and new_assignee.manager_id != current_user.id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Managers can only assign tasks to their team members"
                    )
            elif current_user.role == "Employee":
                if new_assigned_to != current_user.id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Employees can only assign tasks to themselves"
                    )
            # Reset status to Pending (To Do) when assignee changes, unless a specific status was also provided
            if "status" not in update_data and task.assigned_to != new_assigned_to:
                task.status = "Pending"
            task.assigned_to = new_assigned_to
            task.manager_id = new_assignee.manager_id if new_assignee.role == "Employee" else new_assignee.id
        else:
            # Explicitly unassigning
            task.assigned_to = None
            task.manager_id = None

    await db.commit()
    await db.refresh(task)
    
    if task.assigned_to:
        a_result = await db.execute(select(User).filter(User.id == task.assigned_to))
        assignee = a_result.scalars().first()
    else:
        assignee = None
    assignee_name = (assignee.full_name or assignee.email) if assignee else None

    # Broadcast notification to the manager and the assignee (if not the same)
    notification = json.dumps({
        "type": "task_update",
        "task_id": task.id,
        "title": task.title,
        "status": task.status,
        "message": f"Task '{task.title}' status updated to {task.status}"
    })
    
    # Run broadcast in background
    try:
        loop = asyncio.get_event_loop()
        if task.manager_id:
            loop.create_task(manager.send_personal_message(notification, task.manager_id))
        if task.assigned_to and task.assigned_to != task.manager_id:
            loop.create_task(manager.send_personal_message(notification, task.assigned_to))
    except Exception:
        pass
    
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
async def delete_task(
    task: Task = Depends(verify_task_access("delete")),
    db: AsyncSession = Depends(get_db)
):
    await db.delete(task)
    await db.commit()
    return
