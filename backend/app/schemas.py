from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field


# Auth Schemas
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)
    full_name: str | None = None
    role: Literal["Employee", "Manager", "Admin", "Director", "Contractor"] | None = "Employee"
    department_id: int | None = None
    manager_id: int | None = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: str | None = None
    role: str
    department_id: int | None = None
    manager_id: int | None = None
    created_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

class TokenData(BaseModel):
    email: str | None = None
    user_id: int | None = None

# Settings
class UserSettingsUpdate(BaseModel):
    gemini_api_key: str | None = None
    groq_api_key: str | None = None
    openai_api_key: str | None = None
    llm_provider: Literal["simulation", "gemini", "groq", "openai"] | None = "simulation"
    system_prompt: str | None = None

class UserSettingsResponse(BaseModel):
    id: int
    user_id: int
    gemini_api_key_set: bool = False
    groq_api_key_set: bool = False
    openai_api_key_set: bool = False
    llm_provider: str | None = "simulation"
    system_prompt: str | None = None
    updated_at: datetime

    class Config:
        from_attributes = True

    @classmethod
    def from_settings(cls, setting):
        """Create a response from a UserSetting model, masking API keys."""
        return cls(
            id=setting.id,
            user_id=setting.user_id,
            gemini_api_key_set=bool(setting.gemini_api_key and setting.gemini_api_key.strip()),
            groq_api_key_set=bool(setting.groq_api_key and setting.groq_api_key.strip()),
            openai_api_key_set=bool(setting.openai_api_key and setting.openai_api_key.strip()),
            llm_provider=setting.llm_provider,
            system_prompt=setting.system_prompt,
            updated_at=setting.updated_at,
        )

# Department Schemas
class DepartmentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None

class DepartmentResponse(BaseModel):
    id: int
    name: str
    description: str | None = None

    class Config:
        from_attributes = True

# Document Schemas
class DocumentResponse(BaseModel):
    id: int
    title: str
    file_path: str
    file_type: str
    department_id: int | None = None
    uploaded_by: int
    ingestion_status: str
    created_at: datetime

    class Config:
        from_attributes = True

class DocumentChunkResponse(BaseModel):
    id: int
    document_id: int
    content: str
    chunk_index: int
    metadata_json: dict[str, Any] | None = None

    class Config:
        from_attributes = True

# Meeting Schemas
class MeetingCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    transcript: str | None = ""
    meeting_link: str | None = None

class MeetingResponse(BaseModel):
    id: int
    title: str
    transcript: str
    meeting_link: str | None = None
    summary: str | None = None
    uploaded_by: int
    created_at: datetime

    class Config:
        from_attributes = True

# Task Schemas
class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = None
    assigned_to: int | None = None
    document_id: int | None = None
    meeting_id: int | None = None

class TaskUpdate(BaseModel):
    title: str | None = None  # Data flywheel: track if manager edits AI-generated title
    status: Literal["Pending", "In_Progress", "Completed"] | None = None
    assigned_to: int | None = None

class TaskResponse(BaseModel):
    id: int
    title: str
    description: str | None = None
    status: str
    assigned_to: int | None = None
    assignee_name: str | None = None
    manager_id: int | None = None
    document_id: int | None = None
    meeting_id: int | None = None
    created_at: datetime

    class Config:
        from_attributes = True

# Agent Log Schemas
class AgentLogResponse(BaseModel):
    id: int
    user_id: int
    query: str
    response: str
    agent_steps: list[dict[str, Any]] | None = None
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
    query: str = Field(..., min_length=1, max_length=10000)
    scope: list[str] | None = None
    stream: bool = True

# Pagination
class PaginatedResponse(BaseModel):
    items: list[Any]
    total: int
    page: int
    page_size: int
    pages: int
