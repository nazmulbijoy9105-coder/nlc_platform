"""NEUM LEX COUNSEL — Core Module"""
from app.core.config import Settings, get_settings
from app.core.security import (
    hash_password, verify_password,
    encrypt_totp_secret, decrypt_totp_secret,
    generate_totp_secret, verify_totp_code,
    create_access_token, create_temp_token,
    create_refresh_token, decode_token,
)
from app.core.dependencies import (
    get_db, get_admin_db,
    verify_access_token, get_current_user,
    require_roles, require_revenue_access,
    require_company_access,
    get_pagination, get_request_id,
    TokenData, PaginationParams,
    DBSession, AdminDB, CurrentToken, CurrentUser,
    Pagination, RequestID, AppSettings,
    AdminAccess, SuperAdmin, StaffAccess, RevenueAccess,
)

__all__ = [
    "Settings", "get_settings",
    "hash_password", "verify_password",
    "encrypt_totp_secret", "decrypt_totp_secret",
    "generate_totp_secret", "verify_totp_code",
    "create_access_token", "create_temp_token",
    "create_refresh_token", "decode_token",
    "get_db", "get_admin_db",
    "verify_access_token", "get_current_user",
    "require_roles", "require_revenue_access",
    "require_company_access",
    "get_pagination", "get_request_id",
    "TokenData", "PaginationParams",
    "DBSession", "AdminDB", "CurrentToken", "CurrentUser",
    "Pagination", "RequestID", "AppSettings",
    "AdminAccess", "SuperAdmin", "StaffAccess", "RevenueAccess",
]
