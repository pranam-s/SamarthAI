from pydantic_settings import BaseSettings
from typing import Optional, Dict, Any, List
import secrets


class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "AI-Powered Job Matching Platform"
    
    # Security
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 5 
    
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./job_matcher.db"
    
    # AI Service
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-pro"
    EMBEDDING_MODEL: str = "paraphrase-MiniLM-L6-v2"
    
    # File Storage
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10 MB
    
    class Config:
        env_file = ".env"


settings = Settings()