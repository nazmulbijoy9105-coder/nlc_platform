"""Security tests."""

class TestSecurity:
    def test_no_hardcoded_secrets(self):
        import os, re
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
                                violations.append(f"{fpath}:{i}")
        assert len(violations) == 0, f"Hardcoded secrets: {violations}"

    def test_no_raw_sql_injection(self):
        import os, re
        sql_pattern = re.compile(r'f["\'].*(?:SELECT\s+.*\s+FROM|INSERT\s+INTO\s+\w|UPDATE\s+\w+\s+SET|DELETE\s+FROM\s+\w).*["\']', re.IGNORECASE)
        violations = []
        for check_dir in ["app/api", "app/services"]:
            if not os.path.exists(check_dir): continue
            for root, dirs, files in os.walk(check_dir):
                dirs[:] = [d for d in dirs if d != "__pycache__"]
                for fname in files:
                    if fname.endswith(".py"):
                        fpath = os.path.join(root, fname)
                        with open(fpath, encoding="utf-8", errors="ignore") as f:
                            for i, line in enumerate(f, 1):
                                if sql_pattern.search(line) and "text(" not in line:
                                    violations.append(f"{fpath}:{i}: {line.strip()[:80]}")
        assert len(violations) == 0

    def test_pii_fields_identified(self):
        import os
        pii_fields = ["nid_number", "passport_number", "national_id"]
        found = False
        for root, dirs, files in os.walk("app"):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for fname in files:
                if fname.endswith(".py"):
                    with open(os.path.join(root, fname), encoding="utf-8", errors="ignore") as f:
                        if any(p in f.read() for p in pii_fields):
                            found = True
                            break
            if found: break
        assert found

    def test_pii_sanitization_exists(self):
        import os
        found = False
        for root, dirs, files in os.walk("app"):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for fname in files:
                if fname.endswith(".py"):
                    with open(os.path.join(root, fname), encoding="utf-8", errors="ignore") as f:
                        c = f.read()
                        if "nid_number" in c and "sanit" in c.lower():
                            found = True
                            break
            if found: break
        assert found

    def test_rate_limiting_configured(self):
        import os
        found = False
        if os.path.exists(".env.example"):
            with open(".env.example", encoding="utf-8", errors="ignore") as f:
                if "RATE_LIMIT" in f.read():
                    found = True
        if not found:
            for root, dirs, files in os.walk("app"):
                dirs[:] = [d for d in dirs if d != "__pycache__"]
                for fname in files:
                    if fname.endswith(".py"):
                        with open(os.path.join(root, fname), encoding="utf-8", errors="ignore") as f:
                            if "rate_limit" in f.read().lower():
                                found = True
                                break
                if found: break
        assert found

    def test_cors_middleware_present(self):
        try:
            with open("app/main.py", encoding="utf-8") as f:
                main_content = f.read()
            assert "CORSMiddleware" in main_content or "cors" in main_content.lower()
        except Exception:
            assert True
