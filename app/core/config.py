from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    PROJECT_NAME: str = "NLC Platform"
    app_version: str = "1.0.0"
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
    REDIS_URL: str = os.getenv("REDIS_URL", "")
    CELERY_BROKER_URL: str = REDIS_URL
    CELERY_RESULT_BACKEND: str = REDIS_URL

    # Uploads & AI
    UPLOAD_DIR: str = "/tmp/uploads"
    MAX_UPLOAD_SIZE_MB: int = 25
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")

    class Config:
        env_file = ".env"
        case_sensitive = True

from functools import lru_cache

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
