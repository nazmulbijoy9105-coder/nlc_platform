import os
from typing import List, Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "NLC Platform"
    app_version: str = "1.0.0"
    is_production: bool = True
    environment: str = "production"
    
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "production")
    PORT: int = int(os.getenv("PORT", "8000"))

    # CRITICAL: Live URLs
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "https://nlc-frontend.vercel.app")
    BACKEND_URL: str = os.getenv("BACKEND_URL", "https://nlc-platform.onrender.com")

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    @property
    def ASYNC_DATABASE_URL(self) -> str:
        url = self.DATABASE_URL
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+asyncpg://", 1)
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url

    @property
    def SYNC_DATABASE_URL(self) -> str:
        url = self.DATABASE_URL
        if "+asyncpg" in url:
            return url.replace("+asyncpg", "", 1)
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql://", 1)
        return url

    # JWT
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Admin
    ADMIN_EMAIL: str = os.getenv("ADMIN_EMAIL", "")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "")
    ADMIN_FIRST_NAME: str = os.getenv("ADMIN_FIRST_NAME", "System")
    ADMIN_LAST_NAME: str = os.getenv("ADMIN_LAST_NAME", "Admin")

    # Redis
    # FIX 1: Use lowercase 'redis_url' to match main.py
    aws_s3_bucket: str = ""
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "ap-southeast-1"
    # FIX 2: Read from 'CELERY_BROKER_URL' to match Render Dashboard
    redis_url: str = os.getenv("CELERY_BROKER_URL", "")
    CELERY_BROKER_URL: str = ""
    CELERY_RESULT_BACKEND: str = ""

    # Uploads & AI
    UPLOAD_DIR: str = "/tmp/uploads"
    MAX_UPLOAD_SIZE_MB: int = 25
    ai_provider: str = os.getenv("AI_PROVIDER", "groq")
    ai_key: str = os.getenv("AI_KEY", os.getenv("GROQ_API_KEY", ""))

    # FIX 3: Read allowed_origins from Environment Variable
    # This allows you to control it via Render Dashboard
    @property
    def allowed_origins(self) -> List[str]:
        origins_str = os.getenv("ALLOWED_ORIGINS", "https://nlc-frontend.vercel.app")
        return [o.strip() for o in origins_str.split(",") if o.strip()]


    # Rule engine
    rule_engine_version: str = "1.0.0"
    max_login_attempts: int = 5
    lockout_minutes: int = 30
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"

from functools import lru_cache


@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
