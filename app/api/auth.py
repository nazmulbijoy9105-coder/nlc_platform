import datetime
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from sqlalchemy import select

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    decrypt_totp_secret,
    hash_password,
    verify_password,
    verify_totp_code,
)
from app.models.database import get_db
from app.models.user import User

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


class LoginBody(BaseModel):
    email: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict


class RefreshRequest(BaseModel):
    refresh_token: str


class Verify2FARequest(BaseModel):
    temp_token: str
    totp_code: str


class RefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """MATCHES frontend types/index.ts User interface EXACTLY."""
    id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    requires_2fa: bool  # ← frontend field name (was missing)


async def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return payload


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginBody, db=Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account deactivated")

    # Return user dict with requires_2fa
    user_dict = {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "role": str(user.role),
        "is_active": user.is_active,
        "requires_2fa": getattr(user, "requires_2fa", False),  # ← FIX
    }

    access_token = create_access_token({"sub": str(user.id), "user_id": str(user.id), "email": user.email, "role": str(user.role), "type": "access"})
    refresh_token = create_refresh_token({"sub": str(user.id), "user_id": str(user.id), "email": user.email, "role": str(user.role), "type": "refresh"})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": user_dict,
    }


@router.get("/me", response_model=UserResponse)
async def me(current_user: dict = Depends(get_current_user), db=Depends(get_db)):
    result = await db.execute(select(User).where(User.id == current_user["sub"]))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role=str(user.role),
        is_active=user.is_active,
        requires_2fa=getattr(user, "requires_2fa", False),  # ← FIX
    )



@router.post("/verify-2fa", response_model=LoginResponse)
async def verify_2fa(body: Verify2FARequest, db=Depends(get_db)):
    """Verify TOTP code and issue full tokens."""
    payload = decode_token(body.temp_token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    result = await db.execute(select(User).where(User.id == payload["sub"]))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    totp_secret = getattr(user, "totp_secret", None)
    if not totp_secret:
        raise HTTPException(status_code=400, detail="2FA not configured for this user")
    decrypted = decrypt_totp_secret(totp_secret)
    if not verify_totp_code(decrypted, body.totp_code):
        raise HTTPException(status_code=401, detail="Invalid 2FA code")
    user_dict = {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "role": str(user.role),
        "is_active": user.is_active,
        "requires_2fa": True,
    }
    access_token = create_access_token({"sub": str(user.id), "user_id": str(user.id), "email": user.email, "role": str(user.role), "type": "access"})
    refresh_token = create_refresh_token({"sub": str(user.id), "user_id": str(user.id), "email": user.email, "role": str(user.role), "type": "refresh"})
    return LoginResponse(access_token=access_token, refresh_token=refresh_token, token_type="bearer", user=user_dict)


@router.post("/refresh", response_model=RefreshResponse)
async def refresh_token(body: RefreshRequest, db=Depends(get_db)):
    """Exchange a valid refresh token for a new access token."""
    payload = decode_token(body.refresh_token, expected_type="refresh")
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    result = await db.execute(select(User).where(User.id == payload["sub"]))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or deactivated")
    new_access = create_access_token({"sub": str(user.id), "user_id": str(user.id), "email": user.email, "role": str(user.role), "type": "access"})
    return RefreshResponse(access_token=new_access, token_type="bearer")


@router.post("/logout")
async def logout():
    """Logout endpoint. Token blacklisting can be added later."""
    return {"status": "ok"}

@router.post("/setup-admin", include_in_schema=False)
async def setup_admin(db=Depends(get_db)):
    """One-time admin setup. Delete after use."""
    existing = await db.execute(select(User).where(User.email == "admin@neumlexcounsel.com"))
    if existing.scalar_one_or_none():
        return {"status": "already exists"}
    user = User(id=uuid.uuid4(), email="admin@neumlexcounsel.com",
        password_hash=hash_password("NLC@Admin2026!"), full_name="NLC Super Admin",
        role="SUPER_ADMIN", is_active=True, requires_2fa=False,
        created_at=datetime.datetime.utcnow(), updated_at=datetime.datetime.utcnow())
    db.add(user)
    await db.commit()
    return {"status": "created", "email": "admin@neumlexcounsel.com"}
