import os
import logging
from typing import Optional, Any, List
from pydantic import field_validator
from pydantic_settings import BaseSettings

logger = logging.getLogger("processpilot.config")

class Settings(BaseSettings):
    # App Settings
    PROJECT_NAME: str = "ProcessPilot AI"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"  # development, production

    # CORS Origins configuration
    BACKEND_CORS_ORIGINS: Any = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Any) -> Any:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    @field_validator("ENVIRONMENT", mode="before")
    @classmethod
    def detect_environment(cls, v: Any) -> str:
        """Auto-detect production if DATABASE_URL contains postgresql."""
        db_url = os.getenv("DATABASE_URL", "")
        if "postgresql" in db_url or "postgres" in db_url:
            return "production"
        return v or "development"
    
    # Auth Security
    SECRET_KEY: str = "dev_secret_key_processpilot_ai_9876543210"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # Database
    DATABASE_URL: str = "sqlite:///./processpilot.db"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Vector Database Settings
    VECTOR_DB_TYPE: str = "pgvector"  # pgvector, pinecone, qdrant, chroma
    CHROMA_PERSIST_DIR: str = "./chroma_db"
    
    # Pinecone Managed Credentials
    PINECONE_API_KEY: Optional[str] = None
    PINECONE_ENV: Optional[str] = None
    PINECONE_INDEX: str = "processpilot"
    
    # Qdrant Managed Credentials
    QDRANT_URL: Optional[str] = None
    QDRANT_API_KEY: Optional[str] = None
    
    # Upload Settings
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 10
    ALLOWED_FILE_TYPES: List[str] = ["pdf", "docx", "doc", "txt", "csv", "md", "xlsx", "xls"]

    # Supabase Storage — for persistent file storage on Render
    # Set these env vars to enable Supabase Storage bucket uploads.
    # Without them, files fall back to local disk (ephemeral on Render).
    SUPABASE_URL: Optional[str] = None
    SUPABASE_KEY: Optional[str] = None
    SUPABASE_STORAGE_BUCKET: str = "documents"

    class Config:
        case_sensitive = True
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()

# Production safety check — fail fast if SECRET_KEY is default in production
if settings.ENVIRONMENT == "production" and settings.SECRET_KEY == "dev_secret_key_processpilot_ai_9876543210":
    raise RuntimeError(
        "CRITICAL: SECRET_KEY must be set via environment variable in production! "
        "Set SECRET_KEY to a random 32+ character string."
    )

# Ensure uploads directory exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
