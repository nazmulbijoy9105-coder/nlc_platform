from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decrypt_data,
    encrypt_data,
    generate_totp_qr_code,
    generate_totp_secret,
    get_password_hash,
    get_totp_uri,
    verify_password,
    verify_totp,
)
from app.models import User, UserSession

settings = get_settings()


class AuthService:
    @staticmethod
    async def register_user(
        db: AsyncSession,
        email: str,
        password: str,
        full_name: str,
        role: str = "CLIENT_VIEW_ONLY",
    ) -> User:
        result = await db.execute(select(User).where(User.email == email))
        existing_user = result.scalar_one_or_none()

        if existing_user:
            raise ValueError("Email already registered")

        user = User(
            id=generate_uuid(),
            email=email,
            password_hash=get_password_hash(password),
            full_name=full_name,
            role=role,
            is_active=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    async def authenticate_user(db: AsyncSession, email: str, password: str) -> User | None:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user or not verify_password(password, user.password_hash):
            return None

        return user

    @staticmethod
    async def create_session(
        db: AsyncSession,
        user: User,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict[str, str]:
        access_token = create_access_token(user.id)
        refresh_token = create_refresh_token(user.id)

        session = UserSession(
            id=generate_uuid(),
            user_id=user.id,
            token=encrypt_data(access_token),
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
        )
        db.add(session)
        await db.commit()

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }

    @staticmethod
    async def setup_totp(db: AsyncSession, user: User) -> tuple[str, bytes]:
        secret = generate_totp_secret()
        uri = get_totp_uri(secret, user.email)

        user.totp_secret = secret
        await db.commit()

        qr_code = generate_totp_qr_code(uri)
        return secret, qr_code

    @staticmethod
    async def verify_totp_and_enable(db: AsyncSession, user: User, code: str) -> bool:
        if not user.totp_secret:
            return False

        if verify_totp(user.totp_secret, code):
            user.is_totp_enabled = True
            await db.commit()
            return True

        return False

    @staticmethod
    async def disable_totp(db: AsyncSession, user: User) -> bool:
        user.is_totp_enabled = False
        user.totp_secret = None
        await db.commit()
        return True

    @staticmethod
    async def verify_totp_login(db: AsyncSession, user: User, code: str) -> bool:
        if not user.is_totp_enabled or not user.totp_secret:
            return False

        return verify_totp(user.totp_secret, code)


def generate_uuid() -> str:
    import uuid

    return str(uuid.uuid4())
