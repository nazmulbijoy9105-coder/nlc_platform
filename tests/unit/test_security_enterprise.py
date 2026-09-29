"""Enterprise security tests."""

class TestPasswordPolicy:
    def test_short_password_rejected(self):
        from app.core.security import validate_password_strength
        ok, msg = validate_password_strength("Ab1!")
        assert not ok
        assert "8" in msg

    def test_strong_password_accepted(self):
        from app.core.security import validate_password_strength
        ok, msg = validate_password_strength("Str0ng!Pass")
        assert ok

class TestSecurityHeaders:
    def test_security_headers_configured(self):
        with open("app/main.py", encoding="utf-8") as f:
            content = f.read()
        assert "X-Content-Type-Options" in content or "nosniff" in content

class TestNoHardcodedSecrets:
    def test_no_hardcoded_admin_password(self):
        for fname in ["app/api/auth.py", "app/api/admin.py"]:
            with open(fname, encoding="utf-8") as f:
                content = f.read()
            assert "NLC@Admin2026" not in content, f"Hardcoded password in {fname}"
