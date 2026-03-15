from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUser, RequireAdmin
from app.core.schemas import create_data_response
from app.models import User
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: str = "CLIENT_VIEW_ONLY"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    totp_code: str | None = None


class RefreshRequest(BaseModel):
    refresh_token: str


class TOTPSetupResponse(BaseModel):
    secret: str
    qr_code: str


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    is_totp_enabled: bool


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    try:
        user = await AuthService.register_user(
            db=db,
            email=request.email,
            password=request.password,
            full_name=request.full_name,
            role=request.role,
        )
        return create_data_response(
            data=UserResponse.model_validate(user),
            message="User registered successfully",
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/login")
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    user = await AuthService.authenticate_user(db, request.email, request.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if user.is_totp_enabled and not request.totp_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="TOTP code required",
        )

    if user.is_totp_enabled:
        if not await AuthService.verify_totp_login(db, user, request.totp_code):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid TOTP code",
            )

    tokens = await AuthService.create_session(db, user)

    return create_data_response(
        data={
            "user": UserResponse.model_validate(user),
            **tokens,
        },
        message="Login successful",
    )


@router.post("/refresh")
async def refresh_token(request: RefreshRequest):
    from app.core.security import decode_token

    try:
        payload = decode_token(request.refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )

        from app.core.security import create_access_token

        access_token = create_access_token(payload.get("sub"))
        return create_data_response(
            data={"access_token": access_token, "token_type": "bearer"},
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )


@router.post("/logout")
async def logout(current_user: CurrentUser):
    return create_data_response(message="Logged out successfully")


@router.post("/totp/setup")
async def setup_totp(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    secret, qr_code = await AuthService.setup_totp(db, current_user)

    import base64

    qr_code_b64 = base64.b64encode(qr_code).decode()

    return create_data_response(
        data=TOTPSetupResponse(secret=secret, qr_code=qr_code_b64),
        message="TOTP setup initiated",
    )


class VerifyTOTPRequest(BaseModel):
    code: str


@router.post("/totp/verify")
async def verify_totp(
    request: VerifyTOTPRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    success = await AuthService.verify_totp_and_enable(db, current_user, request.code)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid TOTP code",
        )

    return create_data_response(message="TOTP enabled successfully")


@router.post("/totp/disable")
async def disable_totp(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    await AuthService.disable_totp(db, current_user)
    return create_data_response(message="TOTP disabled successfully")


@router.get("/me")
async def get_me(current_user: CurrentUser):
    return create_data_response(data=UserResponse.model_validate(current_user))
