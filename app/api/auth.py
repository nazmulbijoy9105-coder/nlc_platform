from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr
from typing import Optional

from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from app.core.config import settings
# Import from your actual database location
from app.models.database import get_db

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

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
    id: int
    email: str
    first_name: str
    last_name: str
    role: str
    is_active: bool

async def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return payload

@router.post("/login", response_model=LoginResponse)
async def login(request: Request, db=Depends(get_db)):
    from sqlalchemy import select
    from app.models.user import User

    form = await request.form()
    email = form.get("username", "")
    password = form.get("password", "")

    if not email or not password:
        raise HTTPException(status_code=422, detail="Email and password required")

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")

    token_data = {"sub": str(user.id), "email": user.email, "role": user.role}
    return LoginResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
        user={"id": user.id, "email": user.email, "first_name": user.first_name, "last_name": user.last_name, "role": user.role}
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
    return UserResponse(id=user.id, email=user.email, first_name=user.first_name, last_name=user.last_name, role=user.role, is_active=user.is_active)
