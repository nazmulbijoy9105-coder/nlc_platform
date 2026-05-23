from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.models.database import get_db

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

class LoginBody(BaseModel):
    email: EmailStr
    password: str

class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict

class RefreshRequest(BaseModel):
    refresh_token: str

class RefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    is_active: bool

async def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return payload

@router.post("/login", response_model=LoginResponse)
async def login(body: LoginBody, db=Depends(get_db)):
    from sqlalchemy import select

    from app.models.user import User

    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")

    token_data = {"sub": str(user.id), "email": user.email, "role": user.role}

    if user.totp_enabled:
        from app.core.security import create_temp_token
        temp = create_temp_token({"sub": str(user.id), "email": user.email, "role": user.role})
        from fastapi.responses import JSONResponse as _JSONResponse
        return _JSONResponse(content={"requires_2fa": True, "temp_token": temp})

    return LoginResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
        user={"id": user.id, "email": user.email, "full_name": user.full_name, "role": user.role}
    )

@router.post("/refresh", response_model=RefreshResponse)
async def refresh(body: RefreshRequest):
    payload = decode_token(body.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    token_data = {"sub": payload["sub"], "email": payload["email"], "role": payload["role"]}
    return RefreshResponse(access_token=create_access_token(token_data))

@router.get("/me", response_model=UserResponse)
async def me(current_user=Depends(get_current_user), db=Depends(get_db)):
    from sqlalchemy import select

    from app.models.user import User

    result = await db.execute(select(User).where(User.id == int(current_user["sub"])))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(id=str(user.id), email=user.email, full_name=user.full_name, role=user.role, is_active=user.is_active)

class Verify2FARequest(BaseModel):
    temp_token: str
    totp_code: str

@router.post("/verify-2fa")
async def verify_2fa(body: Verify2FARequest, db=Depends(get_db)):
    from sqlalchemy import select

    from app.core.security import decrypt_totp_secret, verify_totp_code
    from app.models.user import User

    payload = decode_token(body.temp_token)
    if not payload or payload.get("type") != "temp":
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    result = await db.execute(select(User).where(User.id == int(payload["sub"])))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found")

    if not user.totp_enabled or not user.totp_secret_encrypted:
        raise HTTPException(status_code=400, detail="2FA not configured for this account")

    decrypted = decrypt_totp_secret(user.totp_secret_encrypted)
    if not verify_totp_code(decrypted, body.totp_code):
        raise HTTPException(status_code=401, detail="Invalid 2FA code")

    token_data = {"sub": str(user.id), "email": user.email, "role": user.role}

    if user.totp_enabled:
        from app.core.security import create_temp_token
        temp = create_temp_token({"sub": str(user.id), "email": user.email, "role": user.role})
        from fastapi.responses import JSONResponse as _JSONResponse
        return _JSONResponse(content={"requires_2fa": True, "temp_token": temp})

    return LoginResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
        user={"id": user.id, "email": user.email, "full_name": user.full_name, "role": user.role}
    )
