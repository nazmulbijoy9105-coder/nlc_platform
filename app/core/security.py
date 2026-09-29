
from datetime import UTC, datetime, timedelta
from typing import Optional

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings
if len(settings.JWT_SECRET_KEY) < 32:
    raise RuntimeError("JWT_SECRET_KEY missing or shorter than 32 chars; refusing to start")


def validate_password_strength(password: str) -> tuple[bool, str]:
    """Enterprise password policy: min 8, 1 upper, 1 digit, 1 special."""
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least 1 uppercase letter"
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least 1 digit"
    if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        return False, "Password must contain at least 1 special character (!@#$%^&*)"
    return True, "Password meets strength requirements"



def hash_password(password: str) -> str:
    # bcrypt limit is 72 bytes
    pwd = password[:72].encode()
    return bcrypt.hashpw(pwd, bcrypt.gensalt()).decode()

def verify_password(plain: str, hashed: str) -> bool:
    pwd = plain[:72].encode()
    return bcrypt.checkpw(pwd, hashed.encode())

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(UTC) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
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
from cryptography.fernet import Fernet
import os
import os


def create_temp_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(UTC) + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire, "type": "temp"})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def generate_totp_secret() -> str:
    return base64.b32encode(os.urandom(20)).decode("utf-8")

_fernet_instance = None

def _get_fernet():
    """Get Fernet instance for AES-256 encryption of TOTP secrets."""
    global _fernet_instance
    if _fernet_instance is None:
        key = os.environ.get("TOTP_ENCRYPTION_KEY", "")
        if not key:
            # Fallback: derive from JWT secret (not ideal, but better than base64)
            import hashlib
            jwt_secret = os.environ["JWT_SECRET_KEY"]
            key = hashlib.sha256(jwt_secret.encode()).digest()
            key = base64.urlsafe_b64encode(key)
        _fernet_instance = Fernet(key if isinstance(key, bytes) else key.encode())
    return _fernet_instance

def encrypt_totp_secret(secret: str) -> str:
    """Encrypt TOTP secret with AES-256 (Fernet). NOT base64."""
    return _get_fernet().encrypt(secret.encode()).decode()

def decrypt_totp_secret(encrypted: str) -> str:
    """Decrypt TOTP secret with AES-256 (Fernet)."""
    try:
        return _get_fernet().decrypt(encrypted.encode()).decode()
    except Exception:
        # Fallback: try old base64 format (for backward compat)
        try:
            return base64.b64decode(encrypted.encode()).decode()
        except Exception:
            raise ValueError("Cannot decrypt TOTP secret — invalid key or format")

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
