
from datetime import datetime, timedelta, timezone
from typing import Optional
import bcrypt
from jose import JWTError, jwt
from app.core.config import settings

def hash_password(password: str) -> str:
    # bcrypt limit is 72 bytes
    pwd = password[:72].encode()
    return bcrypt.hashpw(pwd, bcrypt.gensalt()).decode()

def verify_password(plain: str, hashed: str) -> bool:
    pwd = plain[:72].encode()
    return bcrypt.checkpw(pwd, hashed.encode())

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

def decode_token(token: str, expected_type: str | None = None) -> dict | None:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        if expected_type is not None and payload.get("type") != expected_type:
            return None
        return payload
    except JWTError:
        return None

# TOTP & Temp Token Functions
import base64
import os

def create_temp_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire, "type": "temp"})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def generate_totp_secret() -> str:
    return base64.b32encode(os.urandom(20)).decode("utf-8")

def encrypt_totp_secret(secret: str) -> str:
    return base64.b64encode(secret.encode()).decode()

def decrypt_totp_secret(encrypted: str) -> str:
    return base64.b64decode(encrypted.encode()).decode()

def verify_totp_code(secret: str, code: str) -> bool:
    try:
        import pyotp
        totp = pyotp.TOTP(secret)
        return totp.verify(code, valid_window=1)
    except ImportError:
        return False

def get_totp_provisioning_uri(secret: str, email: str, issuer_name: str = "NLC Platform") -> str:
    try:
        import pyotp
        return pyotp.totp.TOTP(secret).provisioning_uri(name=email, issuer_name=issuer_name)
    except ImportError:
        return ""
