"""
NEUM LEX COUNSEL — ORM LAYER
user.py — User model
AI Constitution Article 2: Role-based access enforced at API layer.
Password hashed (bcrypt). TOTP secret encrypted at application layer.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base
from .enums import UserRole
from .mixins import FullMixin

if TYPE_CHECKING:
    from datetime import datetime

    from .company import CompanyUserAccess
    from .infrastructure import UserActivityLog


class User(FullMixin, Base):
    __tablename__ = "users"

    # ── Identity ──────────────────────────────────────────────────
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"), nullable=False, index=True
    )

    # ── Auth ──────────────────────────────────────────────────────
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    totp_secret_encrypted: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="AES-256 encrypted TOTP secret"
    )
    totp_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Profile ───────────────────────────────────────────────────
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    designation: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Relationships ─────────────────────────────────────────────
    company_access: Mapped[list[CompanyUserAccess]] = relationship(
        "CompanyUserAccess", back_populates="user", lazy="selectin"
    )
    activity_logs: Mapped[list[UserActivityLog]] = relationship(
        "UserActivityLog", back_populates="user", lazy="noload"
    )

    # ── Helpers ───────────────────────────────────────────────────
    @property
    def is_admin(self) -> bool:
        return self.role in (UserRole.SUPER_ADMIN, UserRole.ADMIN_STAFF)

    @property
    def is_super_admin(self) -> bool:
        return self.role == UserRole.SUPER_ADMIN

    @property
    def is_client(self) -> bool:
        return self.role in (UserRole.CLIENT_DIRECTOR, UserRole.CLIENT_VIEW_ONLY)

    def __repr__(self) -> str:
        return f"<User {self.email} [{self.role}]>"
