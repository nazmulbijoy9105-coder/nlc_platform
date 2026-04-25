"""
NEUM LEX COUNSEL — Configuration Layer
app/core/config.py

Pydantic v2 BaseSettings — reads from environment and .env file.
Every value that differs between environments lives here.
Never hardcode secrets in source code.

Usage:
    from app.core.config import get_settings
    settings = get_settings()

    # In FastAPI dependencies:
    async def endpoint(settings: Settings = Depends(get_settings)):
        ...

Release Governance Protocol: Changing production environment variables
requires Super Admin approval and is logged as a system event.
"""
from __future__ import annotations

import json
from functools import lru_cache
from typing import List, Literal, Optional

from pydantic import (
    AnyHttpUrl, EmailStr, Field,
    PostgresDsn, RedisDsn, SecretStr,
    field_validator, model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    All platform configuration in one place.
    Values are loaded from environment variables (case-insensitive).
    Falls back to .env file if not set in environment.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",           # Ignore unknown env vars
    )

    # ═══════════════════════════════════════════════════════════════
    # ENVIRONMENT
    # ═══════════════════════════════════════════════════════════════
    environment: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Deployment environment. Affects logging, CORS, docs URL."
    )
    app_name: str = "NEUM LEX COUNSEL — RJSC Compliance Intelligence"
    app_version: str = "1.0.0"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO"
    )
    sql_echo: bool = Field(
        default=False,
        description="Log SQL statements. Never True in production."
    )
    testing: bool = Field(
        default=False,
        description="Testing mode — uses NullPool, skips external calls."
    )

    # ═══════════════════════════════════════════════════════════════
    # DATABASE
    # ═══════════════════════════════════════════════════════════════
    database_url: str = Field(
        description="Async database URL. postgresql+asyncpg://user:pass@host:5432/db",
        examples=["postgresql+asyncpg://nlc:secret@localhost:5432/nlc_db"]
    )
    database_url_sync: Optional[str] = Field(
        default=None,
        description="Sync URL for Alembic. postgresql://user:pass@host:5432/db"
    )
    db_pool_size: int = Field(default=20, ge=1, le=100)
    db_max_overflow: int = Field(default=40, ge=0, le=200)
    db_pool_recycle: int = Field(default=3600, description="Seconds before recycling connections")

    @model_validator(mode="after")
    def derive_sync_url(self) -> "Settings":
        """Auto-derive sync URL from async URL if not set."""
        if not self.database_url_sync and self.database_url:
            self.database_url_sync = (
                self.database_url
                .replace("postgresql+asyncpg://", "postgresql://")
                .replace("postgres+asyncpg://", "postgresql://")
            )
        return self

    # ═══════════════════════════════════════════════════════════════
    # SECURITY — JWT
    # ═══════════════════════════════════════════════════════════════
    jwt_secret_key: SecretStr = Field(
        description="256-bit secret key. Generate: openssl rand -hex 32"
    )
    jwt_algorithm: str = Field(default="HS256")
    jwt_access_token_expire_minutes: int = Field(
        default=480,
        description="Access token lifetime. Default 8 hours."
    )
    jwt_refresh_token_expire_days: int = Field(
        default=30,
        description="Refresh token lifetime. Default 30 days."
    )
    jwt_temp_token_expire_minutes: int = Field(
        default=5,
        description="Temp token lifetime for 2FA step. Default 5 minutes."
    )

    # ═══════════════════════════════════════════════════════════════
    # SECURITY — TOTP / 2FA
    # ═══════════════════════════════════════════════════════════════
    totp_issuer: str = Field(
        default="Neum Lex Counsel",
        description="TOTP issuer name shown in authenticator apps."
    )
    totp_encryption_key: SecretStr = Field(
        description="32-byte key for AES-256 encrypting TOTP secrets at rest. "
                    "Generate: python -c \"import secrets; print(secrets.token_hex(32))\""
    )

    # ═══════════════════════════════════════════════════════════════
    # SECURITY — RATE LIMITING + LOGIN
    # ═══════════════════════════════════════════════════════════════
    max_login_attempts: int = Field(
        default=5,
        description="Failed login attempts before account lockout."
    )
    lockout_minutes: int = Field(
        default=30,
        description="Account lockout duration after max failed attempts."
    )
    rate_limit_login: str = Field(
        default="10/minute",
        description="Rate limit for /auth/login endpoint."
    )
    rate_limit_api: str = Field(
        default="120/minute",
        description="Default API rate limit per IP."
    )
    super_admin_ip_whitelist: List[str] = Field(
        default=[],
        description="IP addresses allowed for Super Admin login. Empty = no restriction."
    )

    @field_validator("super_admin_ip_whitelist", mode="before")
    @classmethod
    def parse_ip_whitelist(cls, v):
        """Accept JSON string or list."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [ip.strip() for ip in v.split(",") if ip.strip()]
        return v or []

    # ═══════════════════════════════════════════════════════════════
    # CORS
    # ═══════════════════════════════════════════════════════════════

    @field_validator("allowed_origins", "allowed_hosts", mode="before")
    @classmethod
    def parse_list_str(cls, v):
        """Handle empty, comma-separated, or JSON array values for list[str] fields."""
        if isinstance(v, str):
            if not v.strip():
                return []
            try:
                import json
                result = json.loads(v)
                if isinstance(result, list):
                    return result
                return [str(result)]
            except (json.JSONDecodeError, ValueError):
                return [item.strip() for item in v.split(",") if item.strip()]
        return v

    allowed_origins: List[str] = Field(
        default=["http://localhost:3000"],
        description="Allowed CORS origins. Production: https://app.neumlexcounsel.com"
    )

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_origins(cls, v):
        """Accept JSON string, comma-separated string, or list."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [o.strip() for o in v.split(",") if o.strip()]
        return v or []

    allowed_hosts: List[str] = Field(
        default=["*"],
        description="TrustedHostMiddleware hosts. Production: [\"app.neumlexcounsel.com\"]"
    )

    @field_validator("allowed_hosts", mode="before")
    @classmethod
    def parse_hosts(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [h.strip() for h in v.split(",") if h.strip()]
        return v or ["*"]

    # ═══════════════════════════════════════════════════════════════
    # REDIS (Celery broker + session cache)
    # ═══════════════════════════════════════════════════════════════
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL. redis://:password@host:6379/0"
    )
    redis_max_connections: int = Field(default=20)
    celery_broker_url: Optional[str] = Field(
        default=None,
        description="Celery broker URL. Defaults to redis_url if not set."
    )
    celery_result_backend: Optional[str] = Field(
        default=None,
        description="Celery result backend. Defaults to redis_url if not set."
    )

    @model_validator(mode="after")
    def derive_celery_urls(self) -> "Settings":
        """Default Celery URLs to Redis if not explicitly set."""
        if not self.celery_broker_url:
            self.celery_broker_url = self.redis_url
        if not self.celery_result_backend:
            self.celery_result_backend = self.redis_url
        return self

    # ═══════════════════════════════════════════════════════════════
    # AWS
    # ═══════════════════════════════════════════════════════════════
    aws_access_key_id: Optional[SecretStr] = Field(
        default=None,
        description="IAM user with S3 + SES access only. Never root credentials."
    )
    aws_secret_access_key: Optional[SecretStr] = Field(default=None)
    aws_region: str = Field(
        default="ap-southeast-1",
        description="Primary AWS region. Singapore for Bangladesh latency."
    )

    # S3 — Document storage
    s3_bucket_name: str = Field(
        default="nlc-documents-development",
        description="Primary S3 bucket for compliance documents."
    )
    s3_backup_bucket: str = Field(
        default="nlc-backups-development",
        description="S3 bucket for database backups."
    )
    s3_presigned_url_expire_seconds: int = Field(
        default=900,
        description="Pre-signed URL expiry. Default 15 minutes."
    )
    s3_document_prefix: str = Field(
        default="documents/",
        description="S3 key prefix for documents."
    )

    # SES — Email
    ses_region: str = Field(
        default="ap-southeast-1",
        description="AWS SES region. May differ from primary region."
    )
    email_from: EmailStr = Field(
        default="noreply@neumlexcounsel.com",
        description="From address for all outbound emails."
    )
    email_reply_to: Optional[EmailStr] = Field(
        default=None,
        description="Reply-to address. Defaults to email_from."
    )

    # ═══════════════════════════════════════════════════════════════
    # AI PROVIDER (AI Constitution Article 3)
    # ═══════════════════════════════════════════════════════════════
    ai_provider: Literal["openai", "anthropic", "local_llm"] = Field(
        default="local_llm",
        description="AI provider for document drafting. "
                    "AI Constitution: provider must be sandboxed, never direct DB access."
    )
    openai_api_key: Optional[SecretStr] = Field(default=None)
    anthropic_api_key: Optional[SecretStr] = Field(default=None)
    local_llm_base_url: str = Field(
        default="http://ollama:11434",
        description="Ollama or local LLM base URL."
    )
    local_llm_model: str = Field(
        default="llama3",
        description="Local LLM model name."
    )
    ai_request_timeout_seconds: int = Field(
        default=60,
        description="Max seconds to wait for AI API response."
    )
    ai_max_retries: int = Field(
        default=3,
        description="Max retry attempts for AI API calls."
    )

    # ═══════════════════════════════════════════════════════════════
    # WHATSAPP (optional)
    # ═══════════════════════════════════════════════════════════════
    whatsapp_enabled: bool = Field(default=False)
    whatsapp_api_token: Optional[SecretStr] = Field(default=None)
    whatsapp_api_url: str = Field(
        default="https://graph.facebook.com/v18.0",
        description="WhatsApp Business API base URL."
    )
    whatsapp_phone_number_id: Optional[str] = Field(default=None)

    # ═══════════════════════════════════════════════════════════════
    # RULE ENGINE (AI Constitution Article 1)
    # ═══════════════════════════════════════════════════════════════
    rule_engine_version: str = Field(
        default="1.0",
        description="ILRMF version. Must match C_rule_engine.py RULE_ENGINE_VERSION."
    )
    ilrmf_version: str = Field(
        default="1.0",
        description="ILRMF rule set version. Immutable in production."
    )

    # ═══════════════════════════════════════════════════════════════
    # COMPLIANCE CRON
    # ═══════════════════════════════════════════════════════════════
    cron_daily_eval_time: str = Field(
        default="00:00",
        description="UTC time for daily compliance evaluation cron. HH:MM"
    )
    cron_deadline_warning_days: List[int] = Field(
        default=[30, 15, 7, 3, 1],
        description="Days ahead to send deadline warnings."
    )
    cron_score_snapshot_day: int = Field(
        default=1,
        description="Day of month for monthly score snapshot."
    )

    @field_validator("cron_deadline_warning_days", mode="before")
    @classmethod
    def parse_warning_days(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [int(d.strip()) for d in v.split(",") if d.strip()]
        return v

    # ═══════════════════════════════════════════════════════════════
    # DOCUMENT + PDF
    # ═══════════════════════════════════════════════════════════════
    pdf_font_path: str = Field(
        default="/app/static/fonts",
        description="Path to fonts for WeasyPrint PDF generation."
    )
    pdf_template_path: str = Field(
        default="/app/templates/pdf",
        description="Path to Jinja2 templates for PDF generation."
    )
    document_max_size_mb: int = Field(
        default=50,
        description="Maximum document upload size in MB."
    )

    # ═══════════════════════════════════════════════════════════════
    # PAGINATION
    # ═══════════════════════════════════════════════════════════════
    default_page_size: int = Field(default=25)
    max_page_size: int = Field(default=100)

    # ═══════════════════════════════════════════════════════════════
    # API DOCS (disabled in production)
    # ═══════════════════════════════════════════════════════════════
    @property
    def docs_url(self) -> Optional[str]:
        return "/docs" if self.environment == "development" else None

    @property
    def redoc_url(self) -> Optional[str]:
        return "/redoc" if self.environment == "development" else None

    @property
    def openapi_url(self) -> Optional[str]:
        return "/api/v1/openapi.json" if self.environment != "production" else None

    # ═══════════════════════════════════════════════════════════════
    # DERIVED PROPERTIES
    # ═══════════════════════════════════════════════════════════════
    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    @property
    def jwt_secret(self) -> str:
        """Unwrapped JWT secret for jose library."""
        return self.jwt_secret_key.get_secret_value()

    @property
    def totp_key(self) -> str:
        """Unwrapped TOTP encryption key."""
        return self.totp_encryption_key.get_secret_value()

    @property
    def aws_key_id(self) -> Optional[str]:
        return self.aws_access_key_id.get_secret_value() if self.aws_access_key_id else None

    @property
    def aws_secret(self) -> Optional[str]:
        return self.aws_secret_access_key.get_secret_value() if self.aws_secret_access_key else None

    @property
    def ai_key(self) -> Optional[str]:
        """Unwrapped AI API key for the active provider."""
        if self.ai_provider == "openai" and self.openai_api_key:
            return self.openai_api_key.get_secret_value()
        if self.ai_provider == "anthropic" and self.anthropic_api_key:
            return self.anthropic_api_key.get_secret_value()
        return None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Cached settings instance — loaded once at startup.
    Use Depends(get_settings) in FastAPI endpoints.
    In tests, override with: app.dependency_overrides[get_settings] = lambda: test_settings
    """
    return Settings()
