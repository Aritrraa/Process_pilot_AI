from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import timedelta

from ..database import get_db
from ..models import User, Department, UserSetting
from ..schemas import UserCreate, UserLogin, Token, UserResponse, DepartmentResponse, DepartmentCreate
from ..auth import get_password_hash, verify_password, create_access_token, get_current_user
from ..config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    # Check if user already exists
    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
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

@router.post("/login", response_model=Token)
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
