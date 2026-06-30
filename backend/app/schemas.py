from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime

# Auth Schemas
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: Optional[str] = None
    role: Optional[Literal["Employee", "Manager"]] = "Employee"
    department_id: Optional[int] = None
    manager_id: Optional[int] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: Optional[str] = None
    role: str
    department_id: Optional[int] = None
    manager_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

class TokenData(BaseModel):
    email: Optional[str] = None
    user_id: Optional[int] = None

# Settings
class UserSettingsUpdate(BaseModel):
    gemini_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    llm_provider: Optional[Literal["simulation", "gemini", "groq", "openai"]] = "simulation"
    system_prompt: Optional[str] = None

class UserSettingsResponse(BaseModel):
    id: int
    user_id: int
    gemini_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    llm_provider: Optional[str] = "simulation"
    system_prompt: Optional[str] = None
    updated_at: datetime

    class Config:
        from_attributes = True

# Department Schemas
class DepartmentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None

class DepartmentResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None

    class Config:
        from_attributes = True

# Document Schemas
class DocumentResponse(BaseModel):
    id: int
    title: str
    file_path: str
    file_type: str
    department_id: Optional[int] = None
    uploaded_by: int
    created_at: datetime

    class Config:
        from_attributes = True

class DocumentChunkResponse(BaseModel):
    id: int
    document_id: int
    content: str
    chunk_index: int
    metadata_json: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True

# Meeting Schemas
class MeetingCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    transcript: Optional[str] = ""
    meeting_link: Optional[str] = None

class MeetingResponse(BaseModel):
    id: int
    title: str
    transcript: str
    meeting_link: Optional[str] = None
    summary: Optional[str] = None
    uploaded_by: int
    created_at: datetime

    class Config:
        from_attributes = True

# Task Schemas
class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    assigned_to: Optional[int] = None
    document_id: Optional[int] = None
    meeting_id: Optional[int] = None

class TaskUpdate(BaseModel):
    status: Optional[Literal["Pending", "In_Progress", "Completed"]] = None
    assigned_to: Optional[int] = None

class TaskResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    status: str
    assigned_to: Optional[int] = None
    assignee_name: Optional[str] = None
    manager_id: Optional[int] = None
    document_id: Optional[int] = None
    meeting_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True

# Agent Log Schemas
class AgentLogResponse(BaseModel):
    id: int
    user_id: int
    query: str
    response: str
    agent_steps: Optional[List[Dict[str, Any]]] = None
    timestamp: datetime

    class Config:
        from_attributes = True

# Memory Schemas
class MemoryCreate(BaseModel):
    key: str
    value: str

class MemoryResponse(BaseModel):
    id: int
    user_id: int
    key: str
    value: str
    updated_at: datetime

    class Config:
        from_attributes = True

# Query Schemas
class ChatQuery(BaseModel):
    message: str = Field(..., min_length=1, max_length=10000)
    scope: Optional[List[str]] = None
    stream: bool = True

# Pagination
class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    page_size: int
    pages: int
