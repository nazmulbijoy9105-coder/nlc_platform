from datetime import datetime, timedelta, timezone
from typing import Optional
from passlib.context import CryptContext
from jose import JWTError, jwt

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        return None

async def create_admin_user_if_missing():
    if not settings.ADMIN_EMAIL or not settings.ADMIN_PASSWORD:
        print("[WARN] ADMIN_EMAIL or ADMIN_PASSWORD not set")
        return
    if not settings.DATABASE_URL:
        print("[WARN] No DATABASE_URL")
        return

    try:
        # Import from your actual database.py location
        from app.models.database import async_session_factory
        from sqlalchemy import select, text

        async with async_session_factory() as session:
            try:
                await session.execute(text("SELECT 1 FROM users LIMIT 1"))
            except Exception:
                print("[WARN] Users table missing — run migrations")
                return

            from app.models.user import User
            result = await session.execute(select(User).where(User.email == settings.ADMIN_EMAIL))
            if result.scalar_one_or_none():
                print(f"[OK] Admin exists: {settings.ADMIN_EMAIL}")
                return

            admin = User(
                email=settings.ADMIN_EMAIL,
                password_hash=hash_password(settings.ADMIN_PASSWORD),
                first_name=settings.ADMIN_FIRST_NAME,
                last_name=settings.ADMIN_LAST_NAME,
                role="admin",
                is_active=True,
                is_verified=True,
            )
            session.add(admin)
            await session.commit()
            print(f"[OK] Admin created: {settings.ADMIN_EMAIL}")
    except Exception as e:
        print(f"[ERROR] Admin seed failed: {e}")
