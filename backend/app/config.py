import os
from typing import Optional, Any
from pydantic import field_validator
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # App Settings
    PROJECT_NAME: str = "ProcessPilot AI"
    API_V1_STR: str = "/api/v1"
    
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
    
    # Auth Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev_secret_key_processpilot_ai_9876543210")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./processpilot.db")
    
    # Vector Database Settings
    VECTOR_DB_TYPE: str = os.getenv("VECTOR_DB_TYPE", "chroma")  # chroma, pinecone, qdrant
    CHROMA_PERSIST_DIR: str = "./chroma_db"
    
    # Pinecone Managed Credentials
    PINECONE_API_KEY: Optional[str] = os.getenv("PINECONE_API_KEY", None)
    PINECONE_ENV: Optional[str] = os.getenv("PINECONE_ENV", None)
    PINECONE_INDEX: str = os.getenv("PINECONE_INDEX", "processpilot")
    
    # Qdrant Managed Credentials
    QDRANT_URL: Optional[str] = os.getenv("QDRANT_URL", None)
    QDRANT_API_KEY: Optional[str] = os.getenv("QDRANT_API_KEY", None)
    
    # Upload folder
    UPLOAD_DIR: str = "./uploads"

    class Config:
        case_sensitive = True

settings = Settings()

# Ensure uploads directory exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
