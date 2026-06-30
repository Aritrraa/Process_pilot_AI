from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import timedelta

from ..database import get_db
from ..models import User, Department, UserSetting
from ..schemas import UserCreate, UserLogin, Token, UserResponse, DepartmentResponse, DepartmentCreate
from ..auth import get_password_hash, verify_password, create_access_token, get_current_user
from ..config import settings
from ..rate_limiter import rate_limit

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(rate_limit(limit=3, window=3600))])
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    # Check if user already exists
    existing = db.query(User).filter(User.email == user_in.email).first()
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
        dept = db.query(Department).filter(Department.id == user_in.department_id).first()
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
    db.commit()
    db.refresh(user)
    
    # Auto-initialize empty user setting
    setting = UserSetting(user_id=user.id, gemini_api_key="", system_prompt="")
    db.add(setting)
    db.commit()
    
    return user

@router.post("/login", response_model=Token,
             dependencies=[Depends(rate_limit(limit=5, window=60))])
def login(user_in: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == user_in.email).first()
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
def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.get("/departments", response_model=list[DepartmentResponse])
def list_departments(db: Session = Depends(get_db)):
    return db.query(Department).all()

@router.post("/departments", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED)
def create_department(dept_in: DepartmentCreate, db: Session = Depends(get_db)):
    existing = db.query(Department).filter(Department.name == dept_in.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Department name already exists"
        )
    dept = Department(name=dept_in.name, description=dept_in.description)
    db.add(dept)
    db.commit()
    db.refresh(dept)
    return dept

@router.get("/managers", response_model=list[UserResponse])
def list_managers(db: Session = Depends(get_db)):
    """List all managers in the system (for signup assignment)."""
    return db.query(User).filter(User.role == "Manager").all()

@router.get("/team", response_model=list[UserResponse])
def list_team(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List assignable users for the current user based on role."""
    if current_user.role == "Admin":
        return db.query(User).all()
    elif current_user.role == "Manager":
        return db.query(User).filter(
            (User.manager_id == current_user.id) | (User.id == current_user.id)
        ).all()
    return [current_user]

from pydantic import BaseModel
from typing import Optional

class EmployeeTransferRequest(BaseModel):
    manager_id: Optional[int] = None

class SelectManagerRequest(BaseModel):
    manager_id: int

@router.patch("/employees/{employee_id}/transfer", response_model=UserResponse)
def transfer_employee(
    employee_id: int,
    payload: EmployeeTransferRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role not in ("Manager", "Admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only managers and admins can transfer employees"
        )
        
    employee = db.query(User).filter(User.id == employee_id).first()
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
        new_mgr = db.query(User).filter(User.id == payload.manager_id).first()
        if new_mgr:
            employee.department_id = new_mgr.department_id
    else:
        # If released, set department_id to None to prompt full re-assignment
        employee.department_id = None
        
    db.commit()
    db.refresh(employee)
    return employee

@router.patch("/select-manager", response_model=UserResponse)
def select_manager(
    payload: SelectManagerRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
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
        
    manager = db.query(User).filter(User.id == payload.manager_id, User.role == "Manager").first()
    if not manager:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Selected manager not found"
        )
        
    current_user.manager_id = manager.id
    current_user.department_id = manager.department_id
    
    db.commit()
    db.refresh(current_user)
    return current_user


class UserDeleteRequest(BaseModel):
    successor_id: Optional[int] = None


@router.delete("/users/{user_id}", status_code=status.HTTP_200_OK)
def delete_user(
    user_id: int,
    payload: UserDeleteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from ..models import Task

    # 1. Access Control: Only Admin can delete accounts
    if current_user.role != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can delete user accounts"
        )

    # 2. Find user to delete
    user_to_delete = db.query(User).filter(User.id == user_id).first()
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

    # 4. Handle Employee Deletion
    if user_to_delete.role == "Employee":
        manager_id = user_to_delete.manager_id
        if manager_id:
            # Reassign all employee's tasks to their present manager
            db.query(Task).filter(Task.assigned_to == user_to_delete.id).update(
                {Task.assigned_to: manager_id, Task.manager_id: manager_id},
                synchronize_session=False
            )
        else:
            # No manager: unassign tasks
            db.query(Task).filter(Task.assigned_to == user_to_delete.id).update(
                {Task.assigned_to: None},
                synchronize_session=False
            )
        
        # Clean settings and delete user
        db.query(UserSetting).filter(UserSetting.user_id == user_to_delete.id).delete()
        db.delete(user_to_delete)
        db.commit()
        return {"detail": "Employee account deleted and tasks transferred to manager."}

    # 5. Handle Manager Deletion
    elif user_to_delete.role == "Manager":
        if not payload.successor_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Successor manager/employee ID is required to delete a manager"
            )

        successor = db.query(User).filter(User.id == payload.successor_id).first()
        if not successor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Successor not found"
            )

        # Successor cannot be the deleted manager themselves
        if successor.id == user_to_delete.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Successor cannot be the manager being deleted"
            )

        # Case A: Successor is an existing Manager
        if successor.role == "Manager":
            # Successor inherits deleted manager's tasks
            db.query(Task).filter(Task.assigned_to == user_to_delete.id).update(
                {Task.assigned_to: successor.id, Task.manager_id: successor.id},
                synchronize_session=False
            )
            
            # Successor inherits deleted manager's reports (team members)
            reports = db.query(User).filter(User.manager_id == user_to_delete.id).all()
            for report in reports:
                report.manager_id = successor.id
                # Align department to successor's department
                report.department_id = successor.department_id
                # Update report tasks' manager_id to successor so successor can view/manage them
                db.query(Task).filter(Task.assigned_to == report.id).update(
                    {Task.manager_id: successor.id},
                    synchronize_session=False
                )

        # Case B: Successor is an Employee
        elif successor.role == "Employee":
            previous_manager_id = successor.manager_id

            # Promote employee to Manager
            successor.role = "Manager"
            successor.manager_id = None
            # Move successor to the deleted manager's department (takes over team department)
            successor.department_id = user_to_delete.department_id

            # Successor's current employee tasks are passed to their previous manager
            if previous_manager_id:
                db.query(Task).filter(Task.assigned_to == successor.id).update(
                    {Task.assigned_to: previous_manager_id, Task.manager_id: previous_manager_id},
                    synchronize_session=False
                )
            else:
                db.query(Task).filter(Task.assigned_to == successor.id).update(
                    {Task.assigned_to: None},
                    synchronize_session=False
                )

            # Successor inherits deleted manager's tasks
            db.query(Task).filter(Task.assigned_to == user_to_delete.id).update(
                {Task.assigned_to: successor.id, Task.manager_id: successor.id},
                synchronize_session=False
            )

            # Successor inherits deleted manager's reports (team members)
            reports = db.query(User).filter(User.manager_id == user_to_delete.id).all()
            for report in reports:
                report.manager_id = successor.id
                report.department_id = successor.department_id
                # Update report tasks' manager_id to successor so successor can view/manage them
                db.query(Task).filter(Task.assigned_to == report.id).update(
                    {Task.manager_id: successor.id},
                    synchronize_session=False
                )

        # Clean settings and delete user
        db.query(UserSetting).filter(UserSetting.user_id == user_to_delete.id).delete()
        db.delete(user_to_delete)
        db.commit()
        return {"detail": "Manager account deleted and tasks/reports successfully transferred."}

    # 6. Handle Admin Deletion (non-self)
    else:
        # Clean settings and delete user
        db.query(UserSetting).filter(UserSetting.user_id == user_to_delete.id).delete()
        db.delete(user_to_delete)
        db.commit()
        return {"detail": "Admin account deleted."}

