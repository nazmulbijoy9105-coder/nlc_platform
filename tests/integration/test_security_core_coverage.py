"""Integration-scope regression tests for authentication and tenant security primitives.

These tests deliberately exercise behavior rather than importing modules for coverage.
They run in the integration coverage command but do not require database fixtures.
"""
from __future__ import annotations

import time

import pytest

pytestmark = [pytest.mark.integration]


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, tuple[int | None, str]] = {}

    def setex(self, key: str, ttl: int, value: str) -> None:
        self.values[key] = (ttl, value)

    def set(self, key: str, value: str, *, ex: int | None = None, nx: bool = False):
        if nx and key in self.values:
            return False
        self.values[key] = (ex, value)
        return True

    def exists(self, key: str) -> int:
        return int(key in self.values)


class TestSecurityPrimitives:
    def test_password_policy_checks_each_required_character_class(self):
        from app.core.security import validate_password_strength

        cases = [
            ("short1!", "at least 8"),
            ("lowercase1!", "uppercase"),
            ("Uppercase!", "digit"),
            ("Uppercase1", "special"),
        ]
        for password, expected_message in cases:
            valid, message = validate_password_strength(password)
            assert valid is False
            assert expected_message in message

        assert validate_password_strength("CorrectHorse7!")[0] is True

    def test_password_hash_verifies_only_matching_password(self):
        from app.core.security import hash_password, verify_password

        encoded = hash_password("Nlc-Secure-Password-7!")
        assert encoded != "Nlc-Secure-Password-7!"
        assert verify_password("Nlc-Secure-Password-7!", encoded) is True
        assert verify_password("Nlc-Wrong-Password-8!", encoded) is False

    def test_password_hash_respects_bcrypt_72_byte_limit(self):
        from app.core.security import hash_password, verify_password

        prefix = "A" * 72
        encoded = hash_password(prefix + "first suffix")
        assert verify_password(prefix + "different suffix", encoded) is True

    def test_access_refresh_and_temp_tokens_enforce_token_type(self):
        from app.core.security import (
            create_access_token,
            create_refresh_token,
            create_temp_token,
            decode_token,
        )

        access = create_access_token({"sub": "user-1"})
        refresh = create_refresh_token({"sub": "user-1"})
        temporary = create_temp_token({"sub": "user-1"})

        assert decode_token(access, expected_type="access")["type"] == "access"
        assert decode_token(access, expected_type="refresh") is None
        assert decode_token(refresh, expected_type="refresh")["type"] == "refresh"
        assert decode_token(temporary, expected_type="temp")["type"] == "temp"

    def test_expired_token_is_rejected(self):
        from datetime import timedelta

        from app.core.security import create_access_token, decode_token

        token = create_access_token({"sub": "user-1"}, expires_delta=timedelta(seconds=-1))
        assert decode_token(token) is None

    def test_totp_secret_is_encrypted_and_round_trips(self, monkeypatch):
        from cryptography.fernet import Fernet

        import app.core.security as security

        key = Fernet.generate_key().decode()
        monkeypatch.setenv("TOTP_ENCRYPTION_KEY", key)
        monkeypatch.setattr(security, "_fernet_instance", None)
        secret = "JBSWY3DPEHPK3PXP"

        encrypted = security.encrypt_totp_secret(secret)
        assert encrypted != secret
        assert security.decrypt_totp_secret(encrypted) == secret
        with pytest.raises(Exception):
            security.decrypt_totp_secret("not-a-valid-fernet-token")
        monkeypatch.setattr(security, "_fernet_instance", None)


class TestTokenBlacklist:
    def test_revoke_and_check_revocation(self, monkeypatch):
        import app.core.token_blacklist as blacklist

        fake = FakeRedis()
        monkeypatch.setattr(blacklist, "_client", lambda: fake)
        assert blacklist.revoke("jti-1", time.time() + 300) is True
        assert blacklist.is_revoked("jti-1") is True
        assert blacklist.is_revoked("jti-2") is False

    def test_revoke_uses_fallback_ttl_when_expiry_missing(self, monkeypatch):
        import app.core.token_blacklist as blacklist

        fake = FakeRedis()
        monkeypatch.setattr(blacklist, "_client", lambda: fake)
        assert blacklist.revoke("jti-no-exp", None) is True
        assert fake.values["blacklist:jti-no-exp"] == (3600, "revoked")

    def test_test_environment_fails_open_for_read_only_revocation_check(self, monkeypatch):
        import app.core.token_blacklist as blacklist

        monkeypatch.setenv("ENVIRONMENT", "test")

        def unavailable():
            raise ConnectionError("redis unavailable")

        monkeypatch.setattr(blacklist, "_client", unavailable)
        assert blacklist.is_revoked("jti-test") is False

    def test_production_revocation_check_fails_closed(self, monkeypatch):
        from app.core.token_blacklist import BlacklistUnavailable
        import app.core.token_blacklist as blacklist

        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

        def unavailable():
            raise ConnectionError("redis unavailable")

        monkeypatch.setattr(blacklist, "_client", unavailable)
        with pytest.raises(BlacklistUnavailable):
            blacklist.is_revoked("jti-production", fail_closed=True)

    def test_refresh_and_temp_tokens_are_consumed_once(self, monkeypatch):
        import app.core.token_blacklist as blacklist

        fake = FakeRedis()
        monkeypatch.setattr(blacklist, "_client", lambda: fake)
        expiry = time.time() + 300

        assert blacklist.consume_refresh_token("refresh-1", expiry) is True
        assert blacklist.consume_refresh_token("refresh-1", expiry) is False
        assert blacklist.consume_temp_token("temp-1", expiry) is True
        assert blacklist.consume_temp_token("temp-1", expiry) is False

    @pytest.mark.parametrize(
        ("consumer", "jti", "expiry"),
        [
            ("consume_refresh_token", "", time.time() + 60),
            ("consume_temp_token", "missing-expiry", None),
        ],
    )
    def test_one_time_token_rejects_missing_identity_or_expiry(
        self, monkeypatch, consumer, jti, expiry
    ):
        import app.core.token_blacklist as blacklist

        fake = FakeRedis()
        monkeypatch.setattr(blacklist, "_client", lambda: fake)
        assert getattr(blacklist, consumer)(jti, expiry) is False
        assert fake.values == {}


class TestRescueAuditModelRegistration:
    def test_rescue_audit_log_is_registered_in_alembic_metadata(self):
        from app.models import Base, RescueAuditLog

        assert RescueAuditLog.__tablename__ == "rescue_audit_log"
        assert Base.metadata.tables["rescue_audit_log"] is RescueAuditLog.__table__
        rescue_plan_fk = next(iter(RescueAuditLog.__table__.c.rescue_plan_id.foreign_keys))
        assert rescue_plan_fk.ondelete == "CASCADE"



class TestAuthenticationDependency:
    @pytest.mark.asyncio
    async def test_valid_access_token_is_returned_when_not_revoked(self, monkeypatch):
        import app.core.token_blacklist as blacklist
        from app.api.auth import get_current_user
        from app.core.security import create_access_token

        monkeypatch.setattr(blacklist, "is_revoked", lambda _jti: False)
        token = create_access_token({"sub": "user-1"})
        payload = await get_current_user(token=token)
        assert payload["sub"] == "user-1"
        assert payload["type"] == "access"
        assert payload["jti"]

    @pytest.mark.asyncio
    async def test_invalid_access_token_is_rejected(self):
        from fastapi import HTTPException

        from app.api.auth import get_current_user

        with pytest.raises(HTTPException) as exc:
            await get_current_user(token="not.a.valid.jwt")
        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_access_token_without_jti_is_rejected(self):
        from datetime import UTC, datetime, timedelta

        from fastapi import HTTPException
        from jose import jwt

        from app.api.auth import get_current_user
        from app.core.config import settings

        token = jwt.encode(
            {
                "sub": "user-1",
                "type": "access",
                "exp": datetime.now(UTC) + timedelta(minutes=5),
            },
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )
        with pytest.raises(HTTPException) as exc:
            await get_current_user(token=token)
        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_revoked_access_token_is_rejected(self, monkeypatch):
        from fastapi import HTTPException

        import app.core.token_blacklist as blacklist
        from app.api.auth import get_current_user
        from app.core.security import create_access_token

        monkeypatch.setattr(blacklist, "is_revoked", lambda _jti: True)
        token = create_access_token({"sub": "user-1"})
        with pytest.raises(HTTPException) as exc:
            await get_current_user(token=token)
        assert exc.value.status_code == 401
        assert "revoked" in exc.value.detail

    @pytest.mark.asyncio
    async def test_blacklist_outage_returns_service_unavailable(self, monkeypatch):
        from fastapi import HTTPException

        import app.core.token_blacklist as blacklist
        from app.api.auth import get_current_user
        from app.core.security import create_access_token

        def unavailable(_jti):
            raise blacklist.BlacklistUnavailable("redis unavailable")

        monkeypatch.setattr(blacklist, "is_revoked", unavailable)
        token = create_access_token({"sub": "user-1"})
        with pytest.raises(HTTPException) as exc:
            await get_current_user(token=token)
        assert exc.value.status_code == 503
