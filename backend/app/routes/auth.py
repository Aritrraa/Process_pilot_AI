from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete as sql_delete
from datetime import timedelta

from ..database import get_db
from ..models import User, Department, UserSetting, Task, Document
from ..schemas import UserCreate, UserLogin, Token, UserResponse, DepartmentResponse, DepartmentCreate
from ..auth import get_password_hash, verify_password, create_access_token, get_current_user
from ..config import settings
from ..rate_limiter import rate_limit

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(rate_limit(limit=100, window=3600))])
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    # Check if user already exists
    result = await db.execute(select(User).filter(User.email == user_in.email))
    existing = result.scalars().first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Security: Block self-registration as Admin
    if user_in.role == "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin accounts cannot be self-registered. Contact your administrator."
        )
        
    # Verify department if provided
    if user_in.department_id:
        dept_result = await db.execute(select(Department).filter(Department.id == user_in.department_id))
        dept = dept_result.scalars().first()
        if not dept:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Department not found"
            )
            
    # Create user
    hashed_password = get_password_hash(user_in.password)
    user = User(
        email=user_in.email,
        hashed_password=hashed_password,
        full_name=user_in.full_name,
        role=user_in.role,
        department_id=user_in.department_id,
        manager_id=user_in.manager_id
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    # Auto-initialize empty user setting
    setting = UserSetting(user_id=user.id, gemini_api_key="", system_prompt="")
    db.add(setting)
    await db.commit()
    
    return user

@router.post("/login", response_model=Token,
             dependencies=[Depends(rate_limit(limit=200, window=3600))])
async def login(user_in: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).filter(User.email == user_in.email))
    user = result.scalars().first()
    if not user or not verify_password(user_in.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password"
        )
        
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.id}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.get("/departments", response_model=list[DepartmentResponse])
async def list_departments(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Department))
    return result.scalars().all()

@router.post("/departments", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED)
async def create_department(
    dept_in: DepartmentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new department (Admin only)."""
    if current_user.role != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can create departments"
        )
    result = await db.execute(select(Department).filter(Department.name == dept_in.name))
    existing = result.scalars().first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Department name already exists"
        )
    dept = Department(name=dept_in.name, description=dept_in.description)
    db.add(dept)
    await db.commit()
    await db.refresh(dept)
    return dept

@router.get("/users", response_model=list[UserResponse])
async def list_all_users(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all users (Admin only)"""
    if current_user.role != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can list all users"
        )
    result = await db.execute(select(User))
    return result.scalars().all()

@router.get("/managers", response_model=list[UserResponse])
async def list_managers(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all managers in the system (authenticated users only)."""
    result = await db.execute(select(User).filter(User.role == "Manager"))
    return result.scalars().all()

@router.get("/team", response_model=list[UserResponse])
async def list_team(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List assignable users for the current user based on role."""
    if current_user.role == "Admin":
        result = await db.execute(select(User))
        return result.scalars().all()
    elif current_user.role == "Manager":
        result = await db.execute(
            select(User).filter(
                (User.manager_id == current_user.id) | (User.id == current_user.id)
            )
        )
        return result.scalars().all()
    return [current_user]

from pydantic import BaseModel
from typing import Optional

class EmployeeTransferRequest(BaseModel):
    manager_id: Optional[int] = None

class SelectManagerRequest(BaseModel):
    manager_id: int

class RoleChangeRequest(BaseModel):
    new_role: str
    new_manager_id: Optional[int] = None

@router.patch("/employees/{employee_id}/transfer", response_model=UserResponse)
async def transfer_employee(
    employee_id: int,
    payload: EmployeeTransferRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role not in ("Manager", "Admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only managers and admins can transfer employees"
        )
        
    result = await db.execute(select(User).filter(User.id == employee_id))
    employee = result.scalars().first()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found"
        )
        
    # If Manager, check that the employee reports to them
    if current_user.role == "Manager" and employee.manager_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only transfer or release employees from your own team"
        )
        
    employee.manager_id = payload.manager_id
    
    # Auto-align department if manager_id is specified
    if payload.manager_id:
        mgr_result = await db.execute(select(User).filter(User.id == payload.manager_id))
        new_mgr = mgr_result.scalars().first()
        if new_mgr:
            employee.department_id = new_mgr.department_id
    else:
        # If released, set department_id to None to prompt full re-assignment
        employee.department_id = None
        
    await db.commit()
    await db.refresh(employee)
    return employee

@router.patch("/select-manager", response_model=UserResponse)
async def select_manager(
    payload: SelectManagerRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role != "Employee":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only standard employees can select a manager"
        )
        
    if current_user.manager_id is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already have an assigned manager"
        )
        
    mgr_result = await db.execute(select(User).filter(User.id == payload.manager_id, User.role == "Manager"))
    manager = mgr_result.scalars().first()
    if not manager:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Selected manager not found"
        )
        
    current_user.manager_id = manager.id
    current_user.department_id = manager.department_id
    
    await db.commit()
    await db.refresh(current_user)
    return current_user


class UserDeleteRequest(BaseModel):
    successor_id: Optional[int] = None

@router.patch("/users/{user_id}/role", response_model=UserResponse)
async def change_user_role(
    user_id: int,
    payload: RoleChangeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role != "Admin":
        raise HTTPException(status_code=403, detail="Only admins can change roles")
        
    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    valid_roles = ["Admin", "Director", "Manager", "Employee", "Contractor"]
    if payload.new_role not in valid_roles:
        raise HTTPException(status_code=400, detail="Invalid role")

    old_role = user.role
    user.role = payload.new_role

    # If promoting to Director or Admin, they don't have a manager
    if payload.new_role in ["Admin", "Director"]:
        user.manager_id = None
        
    # If Manager/Employee/Contractor, they need a manager_id (except top level managers occasionally)
    elif payload.new_manager_id is not None:
        mgr_result = await db.execute(select(User).filter(User.id == payload.new_manager_id))
        new_mgr = mgr_result.scalars().first()
        if not new_mgr:
            raise HTTPException(status_code=404, detail="New manager not found")
        user.manager_id = new_mgr.id
        user.department_id = new_mgr.department_id

    # If demoting a Manager/Director, we must re-assign their direct reports and assigned tasks
    if old_role in ["Manager", "Director"] and payload.new_role in ["Employee", "Contractor"]:
        if not payload.new_manager_id:
            raise HTTPException(status_code=400, detail="Must provide new_manager_id to inherit subordinates when demoting a manager.")
        
        # Re-assign subordinates
        await db.execute(
            update(User).where(User.manager_id == user.id).values(manager_id=payload.new_manager_id)
        )
        # Re-assign tasks where this person was the manager
        await db.execute(
            update(Task).where(Task.manager_id == user.id).values(manager_id=payload.new_manager_id)
        )

    await db.commit()
    await db.refresh(user)
    return user



@router.delete("/users/{user_id}", status_code=status.HTTP_200_OK)
async def delete_user(
    user_id: int,
    payload: UserDeleteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # 1. Access Control: Only Admin can delete accounts
    if current_user.role != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can delete user accounts"
        )

    # 2. Find user to delete
    result = await db.execute(select(User).filter(User.id == user_id))
    user_to_delete = result.scalars().first()
    if not user_to_delete:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User account not found"
        )

    # 3. Prevent self-deletion of the active admin session
    if user_to_delete.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own admin account"
        )

    # Shared helper: reassign all documents owned by user_to_delete → Admin
    # Append original owner name in parentheses so history is preserved.
    async def _reassign_documents_to_admin(user: User):
        # Find the first Admin user (excluding the one being deleted)
        admin_result = await db.execute(
            select(User).filter(User.role == "Admin", User.id != user.id)
        )
        admin_user = admin_result.scalars().first()
        if not admin_user:
            # If no other admin found, just soft-clear the FK to None (allowed by schema)
            await db.execute(
                update(Document).where(Document.uploaded_by == user.id).values(uploaded_by=None)
            )
            return
        # Reassign ownership and annotate title with original owner name
        docs_result = await db.execute(select(Document).filter(Document.uploaded_by == user.id))
        docs = docs_result.scalars().all()
        for doc in docs:
            original_name = user.full_name or user.email
            # Only append the tag once (idempotent)
            if f"(originally by {original_name})" not in (doc.title or ""):
                doc.title = f"{doc.title} (originally by {original_name})"
            doc.uploaded_by = admin_user.id
        await db.flush()

    # 4. Handle Employee / Contractor Deletion
    if user_to_delete.role in ("Employee", "Contractor"):
        manager_id = user_to_delete.manager_id
        # Reassign documents → Admin with ownership breadcrumb in title
        await _reassign_documents_to_admin(user_to_delete)
        if manager_id:
            # Reassign ALL their tasks to their team manager
            await db.execute(
                update(Task).where(Task.assigned_to == user_to_delete.id).values(
                    assigned_to=manager_id, manager_id=manager_id
                )
            )
        else:
            # No manager – NULL out (DB-level SET NULL handles this safely)
            await db.execute(
                update(Task).where(Task.assigned_to == user_to_delete.id).values(assigned_to=None)
            )

        await db.execute(sql_delete(UserSetting).where(UserSetting.user_id == user_to_delete.id))
        await db.delete(user_to_delete)
        await db.commit()
        return {"detail": "Account deleted. Tasks transferred to the team manager."}

    # 5. Handle Manager / Director Deletion
    elif user_to_delete.role in ("Manager", "Director"):
        if not payload.successor_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Successor manager/employee ID is required to delete a manager"
            )
        # Reassign documents → Admin with ownership breadcrumb in title
        await _reassign_documents_to_admin(user_to_delete)

        succ_result = await db.execute(select(User).filter(User.id == payload.successor_id))
        successor = succ_result.scalars().first()
        if not successor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Successor not found"
            )

        if successor.id == user_to_delete.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Successor cannot be the manager being deleted"
            )

        if successor.role == "Manager":
            await db.execute(
                update(Task).where(Task.assigned_to == user_to_delete.id).values(
                    assigned_to=successor.id, manager_id=successor.id
                )
            )
            reports_result = await db.execute(select(User).filter(User.manager_id == user_to_delete.id))
            reports = reports_result.scalars().all()
            for report in reports:
                report.manager_id = successor.id
                report.department_id = successor.department_id
                await db.execute(
                    update(Task).where(Task.assigned_to == report.id).values(manager_id=successor.id)
                )

        elif successor.role == "Employee":
            previous_manager_id = successor.manager_id
            successor.role = "Manager"
            successor.manager_id = None
            successor.department_id = user_to_delete.department_id

            if previous_manager_id:
                await db.execute(
                    update(Task).where(Task.assigned_to == successor.id).values(
                        assigned_to=previous_manager_id, manager_id=previous_manager_id
                    )
                )
            else:
                await db.execute(
                    update(Task).where(Task.assigned_to == successor.id).values(assigned_to=None)
                )

            await db.execute(
                update(Task).where(Task.assigned_to == user_to_delete.id).values(
                    assigned_to=successor.id, manager_id=successor.id
                )
            )

            reports_result = await db.execute(select(User).filter(User.manager_id == user_to_delete.id))
            reports = reports_result.scalars().all()
            for report in reports:
                report.manager_id = successor.id
                report.department_id = successor.department_id
                await db.execute(
                    update(Task).where(Task.assigned_to == report.id).values(manager_id=successor.id)
                )

        await db.execute(sql_delete(UserSetting).where(UserSetting.user_id == user_to_delete.id))
        await db.delete(user_to_delete)
        await db.commit()
        return {"detail": "Manager account deleted and tasks/reports successfully transferred."}

    # 6. Handle Admin Deletion (non-self)
    else:
        # Reassign documents → another Admin with ownership breadcrumb
        await _reassign_documents_to_admin(user_to_delete)
        # Reassign tasks to current_user (the admin performing the deletion)
        await db.execute(
            update(Task).where(Task.assigned_to == user_to_delete.id).values(
                assigned_to=current_user.id, manager_id=current_user.id
            )
        )
        await db.execute(sql_delete(UserSetting).where(UserSetting.user_id == user_to_delete.id))
        await db.delete(user_to_delete)
        await db.commit()
        return {"detail": "Admin account deleted. Documents and tasks reassigned."}


# ── Circular Reporting Detection ───────────────────────────────────────────────
async def _is_subordinate(db: AsyncSession, user_id: int, potential_ancestor_id: int) -> bool:
    """
    Returns True if user_id is already in the downstream reporting tree of
    potential_ancestor_id. Used to prevent circular manager assignments.
    """
    visited = set()
    queue = [user_id]
    while queue:
        current = queue.pop()
        if current in visited:
            continue
        visited.add(current)
        result = await db.execute(select(User).filter(User.manager_id == current))
        subordinates = result.scalars().all()
        for sub in subordinates:
            if sub.id == potential_ancestor_id:
                return True
            queue.append(sub.id)
    return False


class SwapPositionRequest(BaseModel):
    manager_id: int   # The Manager being demoted to Employee
    employee_id: int  # The Employee being promoted to Manager


@router.post("/users/swap-positions")
async def swap_positions(
    payload: SwapPositionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Atomically swap a Manager and an Employee's positions:
    - Manager → Employee (inherits the employee's IC tasks)
    - Employee → Manager (inherits the manager's team, oversight tasks, department)
    All operations occur in a single SQL transaction.
    """
    if current_user.role != "Admin":
        raise HTTPException(status_code=403, detail="Only admins can swap positions")

    # 1. Fetch both users
    mgr_result = await db.execute(select(User).filter(User.id == payload.manager_id))
    manager = mgr_result.scalars().first()
    emp_result = await db.execute(select(User).filter(User.id == payload.employee_id))
    employee = emp_result.scalars().first()

    if not manager or not employee:
        raise HTTPException(status_code=404, detail="One or both users not found")

    if manager.role not in ("Manager", "Director"):
        raise HTTPException(status_code=400, detail=f"User {manager.id} must be a Manager or Director to swap")

    if employee.role not in ("Employee", "Contractor"):
        raise HTTPException(status_code=400, detail=f"User {employee.id} must be an Employee or Contractor to swap")

    if manager.id == employee.id:
        raise HTTPException(status_code=400, detail="Cannot swap a user with themselves")

    # 2. Circular reporting check: ensure employee is not already managing the manager
    if await _is_subordinate(db, manager.id, employee.id):
        raise HTTPException(
            status_code=400,
            detail="Circular reporting detected. The employee is already in the manager's downstream tree."
        )

    # 3. Save original values before swapping
    old_mgr_dept = manager.department_id
    old_emp_dept = employee.department_id
    old_emp_manager_id = employee.manager_id

    # 4. Promote employee → Manager
    employee.role = manager.role           # Inherits Director or Manager title
    employee.department_id = old_mgr_dept  # Inherits the manager's department
    employee.manager_id = None             # Top-level in their new department

    # 5. Demote manager → Employee
    manager.role = "Employee"
    manager.department_id = old_emp_dept   # Inherits the employee's old department
    manager.manager_id = employee.id       # Now reports to the newly promoted manager

    # 6. Flush to DB so IDs are stable for subsequent UPDATE statements
    await db.flush()

    # 7. Transfer direct reports from old manager → new manager (employee)
    await db.execute(
        update(User)
        .where(User.manager_id == manager.id, User.id != employee.id)
        .values(manager_id=employee.id, department_id=old_mgr_dept)
    )

    # 8. Transfer task OVERSIGHT: tasks managed by old manager → new manager
    await db.execute(
        update(Task).where(Task.manager_id == manager.id).values(manager_id=employee.id)
    )

    # 9. Transfer ASSIGNED tasks: old manager's IC tasks → new employee (old manager)
    #    and old employee's IC tasks → old manager (now employee)
    # Step A: temp sentinel to avoid overlapping update collisions
    TEMP_SENTINEL = -99999
    await db.execute(
        update(Task).where(Task.assigned_to == manager.id).values(assigned_to=TEMP_SENTINEL)
    )
    # Step B: give employee's tasks to manager
    await db.execute(
        update(Task).where(Task.assigned_to == employee.id).values(assigned_to=manager.id)
    )
    # Step C: give manager's tasks (sentinel) to employee
    await db.execute(
        update(Task).where(Task.assigned_to == TEMP_SENTINEL).values(assigned_to=employee.id)
    )

    await db.commit()
    await db.refresh(manager)
    await db.refresh(employee)

    return {
        "detail": "Position swap completed successfully.",
        "new_manager": {
            "id": employee.id,
            "name": employee.full_name,
            "role": employee.role,
            "department_id": employee.department_id
        },
        "new_employee": {
            "id": manager.id,
            "name": manager.full_name,
            "role": manager.role,
            "department_id": manager.department_id
        }
    }

