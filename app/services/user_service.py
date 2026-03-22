"""
NEUM LEX COUNSEL — User Service
app/services/user_service.py

Implements all _get_user_by_email, _get_user_by_id,
_get_user_company_ids, and _verify_password stubs from B_backend_api.py.

Handles:
  - User CRUD (Super Admin only for create/deactivate)
  - Login credential verification
  - 2FA setup and verification
  - Account lockout enforcement
  - Company access grant/revoke
  - JWT payload assembly
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import (
    encrypt_totp_secret, generate_totp_secret,
    get_totp_provisioning_uri, hash_password,
    verify_password, verify_totp_code,
)
from app.models.company import CompanyUserAccess
from app.models.enums import UserRole
from app.models.user import User
from app.services.base import BaseService


class UserService(BaseService[User]):
    model = User

    # ── Authentication ────────────────────────────────────────────

    async def get_by_email(self, email: str) -> Optional[User]:
        """
        Fetch user by email (case-insensitive).
        Returns None if not found or deactivated.
        """
        result = await self.db.execute(
            select(User).where(
                User.email == email.lower().strip(),
                User.is_active == True,
            )
        )
        return result.scalar_one_or_none()

    async def verify_credentials(
        self,
        email: str,
        password: str,
    ) -> Optional[User]:
        """
        Verify email + password. Returns User on success, None on failure.
        Increments failed_login_attempts on bad password.
        Does NOT handle lockout — call check_lockout() first.
        """
        user = await self.get_by_email(email)
        if user is None:
            # Timing attack mitigation: run hash even on miss
            from passlib.context import CryptContext
            CryptContext(schemes=["bcrypt"]).verify("dummy", "$2b$12$" + "x" * 53)
            return None

        if not verify_password(password, user.password_hash):
            await self.increment_failed_attempts(user)
            return None

        # Successful credential check — reset counter
        await self.reset_failed_attempts(user)
        return user

    async def check_lockout(self, user: User) -> bool:
        """
        Returns True if the account is currently locked out.
        Auto-clears expired lockouts.
        """
        if user.locked_until is None:
            return False
        now = datetime.now(timezone.utc)
        locked_until = user.locked_until
        if locked_until.tzinfo is None:
            locked_until = locked_until.replace(tzinfo=timezone.utc)
        if now < locked_until:
            return True
        # Lockout expired — clear it
        await self.reset_lockout(user)
        return False

    async def increment_failed_attempts(self, user: User) -> None:
        """
        Increment failed login attempts. Lock account if threshold reached.
        """
        from app.core.config import get_settings
        settings = get_settings()
        new_count = user.failed_login_attempts + 1
        updates: Dict = {"failed_login_attempts": new_count}
        if new_count >= settings.max_login_attempts:
            lockout_until = datetime.now(timezone.utc) + timedelta(
                minutes=settings.lockout_minutes
            )
            updates["locked_until"] = lockout_until
        await self.update_instance(user, **updates)

    async def reset_failed_attempts(self, user: User) -> None:
        """Reset failed login counter after successful authentication."""
        await self.update_instance(
            user,
            failed_login_attempts=0,
            locked_until=None,
        )

    async def reset_lockout(self, user: User) -> None:
        """Clear lockout state after expiry."""
        await self.update_instance(
            user,
            failed_login_attempts=0,
            locked_until=None,
        )

    async def record_login(self, user: User) -> None:
        """Update last_login_at timestamp."""
        await self.update_instance(user, last_login_at=datetime.now(timezone.utc))

    # ── 2FA Setup ─────────────────────────────────────────────────

    async def setup_totp(self, user: User) -> Dict[str, str]:
        """
        Generate a new TOTP secret for the user.
        Returns the secret and provisioning URI for QR code.
        Does NOT enable 2FA yet — call confirm_totp() after user scans.
        """
        secret = generate_totp_secret()
        encrypted = encrypt_totp_secret(secret)
        await self.update_instance(
            user,
            totp_secret_encrypted=encrypted,
            totp_enabled=False,  # Not yet confirmed
        )
        return {
            "secret": secret,
            "provisioning_uri": get_totp_provisioning_uri(secret, user.email),
            "qr_url": f"otpauth://totp/{user.email}?secret={secret}&issuer=NeumLexCounsel",
        }

    async def confirm_totp(self, user: User, code: str) -> bool:
        """
        Confirm TOTP setup by verifying the first code.
        Enables 2FA on success. Returns True if enabled.
        """
        if not user.totp_secret_encrypted:
            return False
        if verify_totp_code(user.totp_secret_encrypted, code):
            await self.update_instance(user, totp_enabled=True)
            return True
        return False

    async def verify_totp(self, user: User, code: str) -> bool:
        """
        Verify a TOTP code during login step 2.
        Returns True if valid.
        """
        if not user.totp_enabled or not user.totp_secret_encrypted:
            return False
        return verify_totp_code(user.totp_secret_encrypted, code)

    # ── Company Access ────────────────────────────────────────────

    async def get_company_ids(self, user_id: uuid.UUID) -> List[str]:
        """
        Return list of company UUID strings this user can access.
        Used to populate JWT company_ids claim.
        Admin users always get [] (they use RLS ADMIN context).
        """
        result = await self.db.execute(
            select(CompanyUserAccess.company_id).where(
                CompanyUserAccess.user_id == user_id,
                CompanyUserAccess.is_active == True,
            )
        )
        return [str(row[0]) for row in result.all()]

    async def grant_company_access(
        self,
        user_id: uuid.UUID,
        company_id: uuid.UUID,
        *,
        can_edit: bool = False,
        can_view_financials: bool = False,
        granted_by: uuid.UUID,
    ) -> CompanyUserAccess:
        """Grant a user access to a company."""
        # Check if already exists (re-activate if soft-deleted)
        result = await self.db.execute(
            select(CompanyUserAccess).where(
                CompanyUserAccess.user_id == user_id,
                CompanyUserAccess.company_id == company_id,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.is_active = True
            existing.can_edit = can_edit
            existing.can_view_financials = can_view_financials
            existing.granted_by = granted_by
            existing.granted_at = datetime.now(timezone.utc)
            self.db.add(existing)
            await self.db.flush()
            return existing

        access = CompanyUserAccess(
            id=uuid.uuid4(),
            user_id=user_id,
            company_id=company_id,
            can_edit=can_edit,
            can_view_financials=can_view_financials,
            granted_by=granted_by,
            granted_at=datetime.now(timezone.utc),
        )
        self.db.add(access)
        await self.db.flush()
        return access

    async def revoke_company_access(
        self,
        user_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> bool:
        """Revoke a user's access to a company."""
        result = await self.db.execute(
            update(CompanyUserAccess)
            .where(
                CompanyUserAccess.user_id == user_id,
                CompanyUserAccess.company_id == company_id,
            )
            .values(is_active=False)
        )
        return result.rowcount > 0

    # ── User Management ───────────────────────────────────────────

    async def create_user(
        self,
        email: str,
        full_name: str,
        role: UserRole,
        plain_password: str,
        *,
        phone: Optional[str] = None,
        designation: Optional[str] = None,
        created_by: uuid.UUID,
    ) -> User:
        """
        Create a new user. Only SUPER_ADMIN may call this.
        Password is hashed immediately — plain text never stored.
        """
        return await self.create(
            email=email.lower().strip(),
            full_name=full_name,
            role=role,
            password_hash=hash_password(plain_password),
            phone=phone,
            designation=designation,
            totp_enabled=False,
            failed_login_attempts=0,
        )

    async def change_password(
        self,
        user: User,
        new_plain_password: str,
    ) -> None:
        """Change user password. Invalidates active sessions (no token blacklist — use short expiry)."""
        await self.update_instance(
            user,
            password_hash=hash_password(new_plain_password),
        )

    async def get_all_active(self) -> List[User]:
        """List all active users. Admin only."""
        return await self.list_all(
            filters=[User.is_active == True],
            order_by=User.full_name,
        )

    async def build_jwt_payload(self, user: User) -> Dict:
        """
        Build the full JWT payload for an authenticated user.
        For admin roles, company_ids is empty (RLS handles access).
        For client roles, loads their assigned company IDs.
        """
        if user.role in (UserRole.SUPER_ADMIN, UserRole.ADMIN_STAFF, UserRole.LEGAL_STAFF):
            company_ids = []
        else:
            company_ids = await self.get_company_ids(user.id)
        return {
            "user_id":     str(user.id),
            "email":       user.email,
            "full_name":   user.full_name,
            "role":        user.role,
            "company_ids": company_ids,
        }
