import base64
import hashlib
import os
from datetime import UTC, datetime, timedelta
from typing import Optional, cast

import bcrypt
import jwt
from cryptography.fernet import Fernet
from jwt.exceptions import InvalidTokenError

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


def _encode_token(payload: dict) -> str:
    return cast("str", jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM))


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(UTC) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    import uuid
    to_encode.update({"exp": expire, "type": "access", "jti": uuid.uuid4().hex})
    return _encode_token(to_encode)


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    import uuid
    to_encode.update({"exp": expire, "type": "refresh", "jti": uuid.uuid4().hex})
    return _encode_token(to_encode)


def decode_token(token: str, expected_type: str | None = None) -> dict | None:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        if expected_type is not None and payload.get("type") != expected_type:
            return None
        return payload
    except InvalidTokenError:
        return None


# TOTP & Temp Token Functions


def create_temp_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(UTC) + (expires_delta or timedelta(minutes=5))
    import uuid
    to_encode.update({"exp": expire, "type": "temp", "jti": uuid.uuid4().hex})
    return _encode_token(to_encode)


def generate_totp_secret() -> str:
    return base64.b32encode(os.urandom(20)).decode("utf-8")


_fernet_instance: Fernet | None = None


def _get_fernet() -> Fernet:
    """Get Fernet instance for AES-256 encryption of TOTP secrets."""
    global _fernet_instance
    if _fernet_instance is None:
        configured_key = os.environ.get("TOTP_ENCRYPTION_KEY")
        if configured_key:
            # Fernet keys are URL-safe base64-encoded 32-byte keys.
            key_bytes = configured_key.encode("ascii")
        else:
            # Preserve the existing deterministic fallback for installations
            # that have not configured a dedicated TOTP key.
            jwt_secret = os.environ["JWT_SECRET_KEY"]
            derived_key = hashlib.sha256(jwt_secret.encode("utf-8")).digest()
            key_bytes = base64.urlsafe_b64encode(derived_key)
        _fernet_instance = Fernet(key_bytes)
    return _fernet_instance


def encrypt_totp_secret(secret: str) -> str:
    """Encrypt TOTP secret with AES-256 (Fernet). NOT base64."""
    return _get_fernet().encrypt(secret.encode("utf-8")).decode("ascii")


def decrypt_totp_secret(encrypted: str) -> str:
    """Decrypt TOTP secret with AES-256 (Fernet)."""
    try:
        return _get_fernet().decrypt(encrypted.encode("ascii")).decode("utf-8")
    except Exception:
        try:
            return base64.b64decode(encrypted.encode()).decode()
        except Exception as exc:
            raise ValueError("Cannot decrypt TOTP secret — invalid key or format") from exc


def verify_totp_code(secret: str, code: str) -> bool:
    try:
        import pyotp
        return pyotp.TOTP(secret).verify(code, valid_window=1)
    except ImportError:
        return False


def get_totp_provisioning_uri(secret: str, email: str, issuer_name: str = "NLC Platform") -> str:
    try:
        import pyotp
        return pyotp.totp.TOTP(secret).provisioning_uri(name=email, issuer_name=issuer_name)
    except ImportError:
        return ""
