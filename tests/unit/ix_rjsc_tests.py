#!/usr/bin/env python3
"""
Fix two bugs found by the test run:
1. rjsc_forms.py mark_form_filed — change form_id: str → form_id: uuid.UUID
   (prevents 500 errors on invalid UUID input)
2. tests/unit/test_rjsc_forms_idor.py — add registration_number to db_company fixture
   (fixes NOT NULL constraint violation)
"""
import re
from pathlib import Path

# ── 1. Patch app/api/rjsc_forms.py — form_id: str → form_id: uuid.UUID ────

p = Path("app/api/rjsc_forms.py")
src = p.read_text(encoding="utf-8")

# Find mark_form_filed signature and change form_id: str → form_id: uuid.UUID
old_sig = '''async def mark_form_filed(
    form_id: str,
    body: MarkFiledRequest,'''

new_sig = '''async def mark_form_filed(
    form_id: uuid.UUID,
    body: MarkFiledRequest,'''

if old_sig in src:
    src = src.replace(old_sig, new_sig, 1)
    # Ensure uuid is imported
    if "import uuid" not in src and "from uuid" not in src:
        src = "import uuid\n" + src
    p.write_text(src, encoding="utf-8")
    print("[OK] rjsc_forms.py: form_id: str → form_id: uuid.UUID")
else:
    print("[SKIP] rjsc_forms.py: signature not found (already patched?)")

# ── 2. Patch tests/unit/test_rjsc_forms_idor.py — add registration_number ──

p = Path("tests/unit/test_rjsc_forms_idor.py")
if not p.exists():
    print("[SKIP] tests/unit/test_rjsc_forms_idor.py not found")
else:
    src = p.read_text(encoding="utf-8")

    # Fix db_company fixture
    old_company = '''    company = Company(
        id=str(uuid.uuid4()),
        company_name=f"Test Co {uuid.uuid4().hex[:6]}",
        company_type="PRIVATE_LIMITED",
        incorporation_date=date(2020, 1, 1),
    )'''

    new_company = '''    company = Company(
        id=str(uuid.uuid4()),
        registration_number=f"REG-{uuid.uuid4().hex[:8].upper()}",
        company_name=f"Test Co {uuid.uuid4().hex[:6]}",
        company_type="PRIVATE_LIMITED",
        incorporation_date=date(2020, 1, 1),
    )'''

    if old_company in src:
        src = src.replace(old_company, new_company, 1)
        print("[OK] tests: added registration_number to db_company fixture")

    # Fix db_other_company fixture (same issue)
    old_other = '''    company = Company(
        id=str(uuid.uuid4()),
        company_name=f"Other Co {uuid.uuid4().hex[:6]}",
        company_type="PRIVATE_LIMITED",
        incorporation_date=date(2020, 1, 1),
    )'''

    new_other = '''    company = Company(
        id=str(uuid.uuid4()),
        registration_number=f"REG-{uuid.uuid4().hex[:8].upper()}",
        company_name=f"Other Co {uuid.uuid4().hex[:6]}",
        company_type="PRIVATE_LIMITED",
        incorporation_date=date(2020, 1, 1),
    )'''

    if old_other in src:
        src = src.replace(old_other, new_other, 1)
        print("[OK] tests: added registration_number to db_other_company fixture")

    # Update test_422 — now expects 422 (with form_id: uuid.UUID, FastAPI validates)
    old_422 = '''    @pytest.mark.asyncio
    async def test_422_for_invalid_form_id_format(self, api_client, admin_headers):
        """PATCH with a non-UUID string → 422 (path param validation)."""
        resp = await api_client.patch(
            "/api/v1/rjsc-forms/not-a-uuid/filed",
            json={"filed_date": "2024-12-01"},
            headers=admin_headers,
        )
        assert resp.status_code == 422, (
            f"Expected 422 for invalid UUID, got {resp.status_code}: {resp.text}"
        )'''

    new_422 = '''    @pytest.mark.asyncio
    async def test_422_for_invalid_form_id_format(self, api_client, admin_headers):
        """PATCH with a non-UUID string → 422 (FastAPI validates path param type).

        This requires form_id: uuid.UUID in the endpoint signature.
        With form_id: str, invalid UUIDs would cause a 500 error (DBAPIError).
        """
        resp = await api_client.patch(
            "/api/v1/rjsc-forms/not-a-uuid/filed",
            json={"filed_date": "2024-12-01"},
            headers=admin_headers,
        )
        assert resp.status_code == 422, (
            f"Expected 422 for invalid UUID, got {resp.status_code}: {resp.text}"
        )'''

    if old_422 in src:
        src = src.replace(old_422, new_422, 1)
        print("[OK] tests: updated test_422 docstring")

    p.write_text(src, encoding="utf-8")

print("\n[DONE] Both fixes applied. Run: pytest tests/unit/test_rjsc_forms_idor.py -v")
print("Expected: 7 passed, 1 xfailed (IDOR test)")