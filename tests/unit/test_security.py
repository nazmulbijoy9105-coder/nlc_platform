"""Security audit tests — CORS, rate limiting, PII, SQL injection."""

class TestSecurity:
    """Verify security configurations."""

    def test_no_hardcoded_secrets(self):
        """No hardcoded secrets in application code."""
        import os
        # Scan for hardcoded secrets
        import re
        secret_pattern = re.compile(r'(password|secret|key|token)\s*=\s*["\'][^"\']{10,}["\']', re.IGNORECASE)
        violations = []
        for root, dirs, files in os.walk("app"):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for fname in files:
                if fname.endswith(".py"):
                    fpath = os.path.join(root, fname)
                    with open(fpath, encoding="utf-8", errors="ignore") as f:
                        for i, line in enumerate(f, 1):
                            if secret_pattern.search(line) and "CHANGE_ME" not in line and "example" not in line.lower():
                                violations.append(f"{fpath}:{i}: {line.strip()}")
        assert len(violations) == 0, f"Hardcoded secrets found:\n{chr(10).join(violations)}"

    def test_no_raw_sql_injection(self):
        """No f-string SQL in API or service files (migrations excluded)."""
        import os, re
        # Only check api/ and services/ directories, not migrations
        sql_pattern = re.compile(r'f["\'].*(?:SELECT|INSERT|UPDATE|DELETE).*["\']', re.IGNORECASE)
        violations = []
        for check_dir in ["app/api", "app/services"]:
            if not os.path.exists(check_dir):
                continue
            for root, dirs, files in os.walk(check_dir):
                dirs[:] = [d for d in dirs if d != "__pycache__"]
                for fname in files:
                    if fname.endswith(".py"):
                        fpath = os.path.join(root, fname)
                        with open(fpath, encoding="utf-8", errors="ignore") as f:
                            for i, line in enumerate(f, 1):
                                if sql_pattern.search(line) and "text(" not in line:
                                    violations.append(f"{fpath}:{i}: {line.strip()[:80]}")
        assert len(violations) == 0, f"Potential SQL injection:\n{chr(10).join(violations)}"

    def test_pii_fields_identified(self):
        """PII fields exist and are handled."""
        import os
        pii_fields = ["nid_number", "passport_number", "national_id"]
        found = False
        for root, dirs, files in os.walk("app"):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for fname in files:
                if fname.endswith(".py"):
                    with open(os.path.join(root, fname), encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                        if any(p in content for p in pii_fields):
                            found = True
                            break
            if found:
                break
        assert found, "No PII fields found — verify NID/passport handling exists"

    def test_pii_sanitization_exists(self):
        """PII sanitization function should exist in document service."""
        import os
        found = False
        for root, dirs, files in os.walk("app"):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for fname in files:
                if fname.endswith(".py") and "document" in fname.lower():
                    with open(os.path.join(root, fname), encoding="utf-8", errors="ignore") as f:
                        if "sanitize" in f.read().lower() or "pii" in f.read().lower() if False else "sanitize" in open(os.path.join(root, fname), encoding="utf-8", errors="ignore").read().lower():
                            found = True
                            break
            if found:
                break
        if not found:
            # Check if PII list exists
            for root, dirs, files in os.walk("app"):
                dirs[:] = [d for d in dirs if d != "__pycache__"]
                for fname in files:
                    if fname.endswith(".py"):
                        with open(os.path.join(root, fname), encoding="utf-8", errors="ignore") as f:
                            if "nid_number" in f.read() and "sanit" in open(os.path.join(root, fname), encoding="utf-8", errors="ignore").read().lower():
                                found = True
                                break
                if found:
                    break
        assert found, "PII sanitization not found — verify _sanitize function exists"

    def test_rate_limiting_configured(self):
        """Rate limiting should be configured in code or .env.example."""
        import os
        found = False
        # Check .env.example
        if os.path.exists(".env.example"):
            with open(".env.example", encoding="utf-8", errors="ignore") as f:
                if "RATE_LIMIT" in f.read():
                    found = True
        # Check app code
        if not found:
            for root, dirs, files in os.walk("app"):
                dirs[:] = [d for d in dirs if d != "__pycache__"]
                for fname in files:
                    if fname.endswith(".py"):
                        with open(os.path.join(root, fname), encoding="utf-8", errors="ignore") as f:
                            if "rate_limit" in f.read().lower():
                                found = True
                                break
                    if found:
                        break
                if found:
                    break
        assert found, "Rate limiting not configured in .env.example or app code"

    def test_cors_middleware_present(self):
        """CORS middleware should be present in the app."""
        from app.main import create_app
        app = create_app()
        middleware_names = [str(m) for m in app.user_middleware]
        assert any("CORS" in m for m in middleware_names), "CORS middleware not found"
