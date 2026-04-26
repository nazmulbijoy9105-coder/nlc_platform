"""
NEUM LEX COUNSEL — Security Utilities
app/core/security.py

Password hashing (bcrypt), TOTP encryption (AES-256-GCM),
JWT creation/verification. All auth primitives live here.

AI Constitution Article 2: Auth state is immutable mid-session.
Lockout enforced in UserService, not here.
"""
from __future__ import annotations

import base64
import os
from datetime import UTC, datetime, timedelta
from typing import Any

import pyotp
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

# ── Password hashing ─────────────────────────────────────────────────
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """Hash a plain password with bcrypt. Returns the hashed string."""
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Compare plain password against bcrypt hash. Returns True if match."""
    return _pwd_context.verify(plain_password, hashed_password)


# ── TOTP encryption (AES-256-GCM) ────────────────────────────────────
def _get_aes_key() -> bytes:
    """
    Derive 32-byte AES key from TOTP_ENCRYPTION_KEY setting.
    Key must be exactly 64 hex chars (= 32 bytes).
    """
    key_hex = get_settings().totp_key
    if len(key_hex) == 64:
        return bytes.fromhex(key_hex)
    # Pad/truncate to 32 bytes for safety
    raw = key_hex.encode("utf-8")
    return (raw + b"\x00" * 32)[:32]


def encrypt_totp_secret(totp_secret: str) -> str:
    """
    Encrypt a TOTP secret with AES-256-GCM.
    Returns base64(nonce + ciphertext + tag) string for DB storage.
    AI Constitution: TOTP secrets never stored in plaintext.
    """
    key = _get_aes_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)  # 96-bit nonce
    plaintext = totp_secret.encode("utf-8")
    ciphertext_with_tag = aesgcm.encrypt(nonce, plaintext, None)
    # nonce (12) + ciphertext_with_tag stored together
    combined = nonce + ciphertext_with_tag
    return base64.b64encode(combined).decode("utf-8")


def decrypt_totp_secret(encrypted: str) -> str:
    """
    Decrypt an AES-256-GCM encrypted TOTP secret.
    Raises ValueError on decryption failure.
    """
    key = _get_aes_key()
    aesgcm = AESGCM(key)
    combined = base64.b64decode(encrypted.encode("utf-8"))
    nonce = combined[:12]
    ciphertext_with_tag = combined[12:]
    try:
        plaintext = aesgcm.decrypt(nonce, ciphertext_with_tag, None)
        return plaintext.decode("utf-8")
    except Exception as exc:
        raise ValueError("TOTP secret decryption failed — key mismatch or corrupted data") from exc


def generate_totp_secret() -> str:
    """Generate a new TOTP secret (base32 encoded, standard for authenticator apps)."""
    return pyotp.random_base32()


def verify_totp_code(encrypted_secret: str, code: str) -> bool:
    """
    Verify a 6-digit TOTP code against an encrypted TOTP secret.
    Allows a 30-second window (1 step before + 1 step after for clock drift).
    Returns True if valid, False otherwise.
    """
    try:
        secret = decrypt_totp_secret(encrypted_secret)
        totp = pyotp.TOTP(secret)
        return totp.verify(code, valid_window=1)
    except Exception:
        return False


def get_totp_provisioning_uri(secret: str, email: str) -> str:
    """Generate TOTP provisioning URI for QR code display."""
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(
        name=email,
        issuer_name=get_settings().totp_issuer,
    )


# ── JWT token creation ────────────────────────────────────────────────
def create_access_token(
    user_id: str | dict[str, Any],
    email: str | None = None,
    role: str | None = None,
    company_ids: list[str] | None = None,
) -> str:
    """
    Create a full access JWT (issued after successful 2FA).
    Supports both old payload-style calls `create_access_token(payload)` and
    new explicit args `create_access_token(user_id, email, role, company_ids)`.
    Contains: user_id, email, role, company_ids.
    Expires: jwt_access_token_expire_minutes (default 480 = 8 hours).
    """
    settings = get_settings()
    now = datetime.now(UTC)

    if isinstance(user_id, dict):
        payload_data = user_id
        uid = payload_data.get("user_id") or payload_data.get("sub")
        if not uid:
            raise ValueError("user_id or sub must be set in payload")
        email = payload_data.get("email")
        role = payload_data.get("role")
        company_ids = payload_data.get("company_ids", [])
    else:
        uid = user_id

    if not (email and role and company_ids is not None):
        raise ValueError("email, role, and company_ids must be provided")

    payload = {
        "sub":         uid,
        "user_id":     uid,
        "email":       email,
        "role":        role,
        "company_ids": company_ids,
        "type":        "access",
        "iat":         int(now.timestamp()),
        "exp":         int((now + timedelta(minutes=settings.jwt_access_token_expire_minutes)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_temp_token(user_id: str, email: str, role: str) -> str:
    """
    Create a short-lived temp JWT for the 2FA step.
    Does NOT contain company_ids — those are added after 2FA.
    Expires: jwt_temp_token_expire_minutes (default 5 minutes).
    """
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub":     user_id,
        "user_id": user_id,
        "email":   email,
        "role":    role,
        "type":    "temp_2fa",
        "iat":     int(now.timestamp()),
        "exp":     int((now + timedelta(minutes=settings.jwt_temp_token_expire_minutes)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(user_id: str) -> str:
    """
    Create a long-lived refresh token.
    Only contains user_id — all other claims fetched fresh on refresh.
    Expires: jwt_refresh_token_expire_days (default 30 days).
    """
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub":     user_id,
        "user_id": user_id,
        "type":    "refresh",
        "iat":     int(now.timestamp()),
        "exp":     int((now + timedelta(days=settings.jwt_refresh_token_expire_days)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_password_reset_token(user_id: str, email: str) -> str:
    """
    Create a short-lived password-reset JWT (15 minutes).
    Sent via email link; must be single-use (checked by consuming endpoint).
    """
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub":     user_id,
        "user_id": user_id,
        "email":   email,
        "type":    "password_reset",
        "iat":     int(now.timestamp()),
        "exp":     int((now + timedelta(minutes=15)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str, expected_type: str | None = None) -> dict[str, Any]:
    """
    Decode and validate a JWT token.
    Raises JWTError if invalid, expired, or wrong type.
    """
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError as exc:
        raise JWTError(f"Token validation failed: {exc}") from exc

    if expected_type and payload.get("type") != expected_type:
        raise JWTError(
            f"Wrong token type. Expected '{expected_type}', got '{payload.get('type')}'"
        )
    return payload
