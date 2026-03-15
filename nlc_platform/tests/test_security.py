import pytest

from app.core.security import (
    generate_totp_secret,
    get_totp_uri,
    verify_totp,
    verify_password,
    get_password_hash,
)


class TestPasswordHashing:
    def test_password_hashing(self):
        password = "test_password_123"
        hashed = get_password_hash(password)

        assert hashed != password
        assert verify_password(password, hashed) is True
        assert verify_password("wrong_password", hashed) is False

    def test_different_hashes_for_same_password(self):
        password = "test_password"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)

        assert hash1 != hash2
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


class TestTOTP:
    def test_totp_generation(self):
        secret = generate_totp_secret()
        assert len(secret) > 0

        uri = get_totp_uri(secret, "test@example.com")
        assert "otpauth://totp/" in uri
        assert "test@example.com" in uri

    def test_totp_verification(self):
        import pyotp

        secret = generate_totp_secret()
        totp = pyotp.TOTP(secret)
        code = totp.now()

        assert verify_totp(secret, code) is True
        assert verify_totp(secret, "000000") is False


class TestTokenGeneration:
    def test_access_token_creation(self):
        from app.core.security import create_access_token

        token = create_access_token("user-123")
        assert token is not None
        assert len(token) > 0

    def test_refresh_token_creation(self):
        from app.core.security import create_refresh_token

        token = create_refresh_token("user-123")
        assert token is not None
        assert len(token) > 0

    def test_token_decode(self):
        from app.core.security import create_access_token, decode_token

        token = create_access_token("user-123")
        payload = decode_token(token)

        assert payload["sub"] == "user-123"
        assert payload["type"] == "access"

    def test_invalid_token_raises(self):
        from app.core.security import decode_token

        with pytest.raises(ValueError, match="Invalid token"):
            decode_token("invalid.token.here")
