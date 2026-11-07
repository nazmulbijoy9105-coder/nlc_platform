"""
tests/conftest.py — Pytest Fixtures
NEUM LEX COUNSEL

Provides fixtures for:
  - Database: async test engine, async session, RLS bypass
  - Auth: JWT tokens for every role (super_admin, admin_staff, legal_staff, client)
  - Factory functions: companies, users, AGMs, audits, compliance flags
  - Rule engine: pre-initialised engine + clean CompanyProfile builder
  - HTTP client: FastAPI TestClient + authenticated async client
  - Mocks: Celery tasks (eager), AI provider, AWS S3, SES

Test database strategy:
  - Uses separate database: nlc_test (must exist before running tests)
  - DATABASE_URL_TEST env var, else local nlc_test (never derived from DATABASE_URL)
  - Each test gets a transaction that is rolled back — no cleanup needed
  - Alembic migrations run once per session (not per test)

Usage:
  pytest tests/                            # All tests
  pytest tests/unit/test_rule_engine.py    # Unit tests only
  pytest tests/ -k "test_agm"              # Filter by name
  pytest tests/ -v --tb=short              # Verbose with short tracebacks
  pytest tests/ --co -q                    # List tests without running
"""

from __future__ import annotations

import asyncio
import os
import sys
import uuid
from datetime import date, timedelta
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

# Ensure app is importable (adjust sys.path if tests run outside Docker)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Force test environment before any app imports
os.environ.setdefault("TESTING", "true")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("LOG_LEVEL", "WARNING")

# ---------------------------------------------------------------------------
# Test database URL
# ---------------------------------------------------------------------------

def _get_test_db_url() -> str:
    """Test DB URL. Never derived from DATABASE_URL (it may be production)."""
    return os.getenv(
        "DATABASE_URL_TEST",
        "postgresql+asyncpg://nlc_user:nlc_password@localhost:5432/nlc_test",
    )


TEST_DATABASE_URL = _get_test_db_url()

from sqlalchemy.engine import make_url as _make_url

assert _make_url(TEST_DATABASE_URL).host in ("localhost", "127.0.0.1"), \
    "tests must run against a local database"
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ.setdefault("JWT_SECRET_KEY", "ci-only-" + "x" * 40)


# ---------------------------------------------------------------------------
# Event loop (session-scoped for async fixtures)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def event_loop():
    """Session-scoped event loop — required for session-scoped async fixtures."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ---------------------------------------------------------------------------
# Database engine (session-scoped — created once)
# ---------------------------------------------------------------------------




@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """
    Async engine pointing at nlc_test database.
    NullPool ensures no connection leaks between tests.
    """
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=NullPool,
    )

    # Run migrations on test DB
    try:
        async with engine.begin() as conn:
            # Quick connectivity check
            await conn.execute(text("SELECT 1"))
    except Exception as e:
        pytest.skip(f"Test database not reachable: {e}. Run: make migrate (test DB)")

    # Build/upgrade schema from migrations (idempotent: no-op when already at head).
    # Subprocess avoids event-loop clashes with the async alembic/env.py.
    import subprocess
    import sys
    from pathlib import Path

    db_name = _make_url(TEST_DATABASE_URL).database or ""
    assert db_name.endswith("_test"), f"refusing to migrate non-test DB: {db_name!r}"
    proc = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=Path(__file__).resolve().parent.parent,
        env={**os.environ, "DATABASE_URL": TEST_DATABASE_URL},
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if proc.returncode != 0:
        pytest.fail(f"alembic upgrade head failed:\n{proc.stdout}\n{proc.stderr}", pytrace=False)

    yield engine
    await engine.dispose()


# ---------------------------------------------------------------------------
# Database session (function-scoped — transaction rolled back after each test)
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def db(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Async DB session wrapped in a transaction.
    Transaction is rolled back after each test — no cleanup needed.
    Ordinary service tests use the test owner; RLS-specific tests explicitly
    switch to nlc_app_role and a signed principal.
    """
    async with test_engine.connect() as conn:
        await conn.begin()
        session = AsyncSession(bind=conn, expire_on_commit=False)

        yield session

        await session.close()
        await conn.rollback()


# ---------------------------------------------------------------------------
# Security helpers (tokens)
# ---------------------------------------------------------------------------

def _role_user_id(role: str) -> uuid.UUID:
    """Stable per-role user id so api_client can seed a matching DB user."""
    return uuid.uuid5(uuid.NAMESPACE_DNS, f"nlc-test-user-{role}")


def _make_token(role: str, user_id: str | None = None, company_ids: list[str] | None = None) -> str:
    """Generate a real JWT token for testing (uses actual security module)."""
    from app.core.security import create_access_token
    uid = user_id or str(_role_user_id(role))
    email = f"test_{role.lower()}@nlctest.com"
    companies = company_ids or []
    return create_access_token({
        "sub": uid,
        "user_id": uid,
        "email": email,
        "role": role,
        "company_ids": companies,
    })


@pytest.fixture(scope="session")
def super_admin_token() -> str:
    return _make_token("SUPER_ADMIN")


@pytest.fixture(scope="session")
def admin_token() -> str:
    return _make_token("ADMIN_STAFF")


@pytest.fixture(scope="session")
def legal_token() -> str:
    return _make_token("LEGAL_STAFF")


@pytest.fixture(scope="session")
def client_token(sample_company_id) -> str:
    return _make_token("CLIENT_DIRECTOR", company_ids=[sample_company_id])


@pytest.fixture(scope="session")
def client_view_token(sample_company_id) -> str:
    return _make_token("CLIENT_VIEW_ONLY", company_ids=[sample_company_id])


@pytest.fixture(scope="session")
def sample_company_id() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Auth headers helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def super_admin_headers(super_admin_token) -> dict[str, str]:
    return {"Authorization": f"Bearer {super_admin_token}"}


@pytest.fixture
def admin_headers(admin_token) -> dict[str, str]:
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def legal_headers(legal_token) -> dict[str, str]:
    return {"Authorization": f"Bearer {legal_token}"}


@pytest.fixture
def client_headers(client_token) -> dict[str, str]:
    return {"Authorization": f"Bearer {client_token}"}


# ---------------------------------------------------------------------------
# HTTP Client (FastAPI TestClient)
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def api_client(db) -> AsyncGenerator[AsyncClient, None]:
    """
    Async HTTP client wired to FastAPI app.
    DB session is overridden to use test transaction.
    Celery tasks are mocked to run eagerly (no worker needed).
    """
    from app.core.dependencies import get_db, get_db_for_user
    from app.main import create_app
    from app.models.database import get_db as auth_get_db
    from app.models.enums import UserRole
    from app.models.user import User

    # Seed one DB user per role so role tokens resolve in get_current_user.
    for _role in UserRole:
        _uid = _role_user_id(_role.value)
        if await db.get(User, _uid) is None:
            db.add(User(
                id=_uid,
                email=f"seed_{_role.value.lower()}@nlctest.com",
                full_name=f"Seed {_role.value}",
                password_hash="!seeded-no-login",
                role=_role,
                is_active=True,
                totp_enabled=False,
            ))
    await db.flush()

    app = create_app()

    # Override all DB dependency objects used by the API with the test transaction.
    async def _override_db():
        yield db

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_db_for_user] = _override_db
    app.dependency_overrides[auth_get_db] = _override_db

    # Patch Celery tasks to be no-ops
    with patch("app.worker.tasks.evaluate_company_compliance.apply_async", return_value=MagicMock(id="test-task")), \
         patch("app.worker.tasks.generate_ai_document_async.apply_async", return_value=MagicMock(id="test-task")), \
         patch("app.worker.tasks.render_pdf.apply_async", return_value=MagicMock(id="test-task")):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client


# ---------------------------------------------------------------------------
# Rule Engine
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def rule_engine():
    """
    Initialised NLCRuleEngine instance.
    Session-scoped — engine is stateless (flags reset per evaluate() call).
    """
    try:
        from C_rule_engine import NLCRuleEngine  # adjust import path as needed
    except ModuleNotFoundError:
        from app.rule_engine.engine import NLCRuleEngine
    return NLCRuleEngine()


# ---------------------------------------------------------------------------
# CompanyProfile builder (test factory)
# ---------------------------------------------------------------------------

@pytest.fixture
def build_profile():
    """
    Factory fixture: returns a function to build CompanyProfile instances.
    All fields have sensible defaults for a fully-compliant company.
    Override specific fields in each test to trigger rules.

    Usage:
        profile = build_profile(agm_held_this_cycle=False)  # triggers AGM default
    """
    try:
        from C_rule_engine import CompanyProfile, DirectorChange, ShareTransfer
    except ModuleNotFoundError:
        from app.rule_engine.engine import CompanyProfile

    def _build(**overrides) -> CompanyProfile:
        today = date.today()
        defaults = {
            "company_id": str(uuid.uuid4()),
            "company_name": "Test Company Ltd",
            "company_type": "PRIVATE_LIMITED",
            # Incorporated 3 years ago — old enough for all deadlines
            "incorporation_date": today - timedelta(days=365 * 3),
            "financial_year_end": date(today.year - 1, 12, 31),
            # AGM — fully compliant
            "agm_count": 3,
            "agm_history_verified": True,
            "agm_history_evidence_ref": "AGM-HISTORY-TEST",
            "agm_history_verified_at": today,
            "agm_history_verified_by": "reviewer-001",
            "last_agm_date": today - timedelta(days=60),
            "agm_held_this_cycle": True,
            "agm_attendance_verified": True,
            "agm_attendance_evidence_ref": "AGM-MINUTES-TEST",
            "agm_quorum_required": 2,
            "agm_quorum_basis_verified": True,
            "agm_quorum_evidence_ref": "AOA-QUORUM-TEST",
            "agm_scheduled_date": None,
            "notice_sent_date": today - timedelta(days=84),  # 21+ days before AGM
            "members_present_at_agm": 3,
            "auditor_reappointed_at_agm": True,
            "auditor_reappointment_verified": True,
            "auditor_reappointment_evidence_ref": "AGM-AUDITOR-TEST",
            "accounts_adopted_at_agm": True,
            # Audit — fully compliant
            "audit_complete": True,
            "last_audit_signed_date": today - timedelta(days=90),
            "audit_in_progress": False,
            # Annual return — fully compliant
            "last_return_filed_year": today.year - 1,
            "unfiled_returns_count": 0,
            "annual_return_filed": True,
            "annual_return_content_complete": True,
            "annual_return_filed_date": today - timedelta(days=30),
            # Directors — no changes pending
            "director_changes": [],
            # Shareholders — no changes
            "shareholder_change_date": None,
            "form_xv_filed": True,
            # Transfers — none
            "share_transfers": [],
            # Office — no change
            "registered_office_change_date": None,
            "form_vi_filed": True,
            # Corporate structure
            "aoa_transfer_restriction": True,
            "has_foreign_shareholder": False,
            "is_dormant": False,
            "is_fdi_registered": False,
            # Registers & certificates
            "maintained_registers": ["members", "directors", "charges", "transfers", "debentures", "minutes_agm", "minutes_board"],
            "agm_minutes_prepared": True,
            "tax_return_filed_for_current_fy": True,
            "advance_tax_q1_paid": True,
            "advance_tax_q2_paid": True,
            "advance_tax_q3_paid": True,
            "advance_tax_q4_paid": True,
            "vat_annual_return_filed_for_fy": True,
            "tin_number": "TIN-TEST-001",
            "trade_license_expiry": today + timedelta(days=200),
            "last_tax_return_filed_year": today.year - 1,
            "last_allotment_date": None,
            # Capital
            "capital_increase_date": None,
            "capital_increase_resolution": True,
            "first_auditor_appointed": True,
            "first_auditor_appointment_date": today - timedelta(days=365 * 3) + timedelta(days=15),
            "first_auditor_appointment_verified": True,
            "first_auditor_appointment_evidence_ref": "FIRST-AUDITOR-APPOINTMENT-TEST",
            "first_auditor_appointment_verified_at": today,
            "first_auditor_appointment_verified_by": "reviewer-001",
            "tin_obtained": True,
            "vat_registered": True,
            "trade_license_obtained": True,
            "form_iii_filed": True,
            "form_iv_filed": True,
            "moa_aoa_filed": True,
            "share_certificates_issued": True,
            "minimum_directors_met": True,
            "paid_up_ge_authorized": True,
            "register_of_directors_interests": True,
            "register_of_contracts": True,
            "worker_compensation_filed": True,
            "bsec_quarterly_report_filed": True,
            "cg_certificate_obtained": True,
            "board_independent_director": True,
            "audit_committee_established": True,
            "current_director_count": 3,
            "factory_license_obtained": True,
            # New fields (Section 95/96/89/181/183/190/93/104/110/222/150)
            "last_board_meeting_date": date.today() - timedelta(days=30),
            "board_meeting_notice_given": True,
            "board_minutes_prepared": True,
            "financial_statements_presented": True,
            "financial_statements_filed": True,
            "books_of_account_kept": True,
            "director_consent_filed": True,
            "director_office_of_profit": False,
            "member_count": 5,
            "business_commencement_declaration_filed": True,
        }
        defaults.update(overrides)
        # Keep fixture appointment evidence consistent with any overridden
        # registration date unless a test explicitly supplies its own date.
        if "first_auditor_appointment_date" not in overrides:
            if defaults.get("first_auditor_appointed") is True and defaults.get("incorporation_date"):
                defaults["first_auditor_appointment_date"] = (
                    defaults["incorporation_date"] + timedelta(days=15)
                )
            else:
                defaults["first_auditor_appointment_date"] = None
        return CompanyProfile(**defaults)

    return _build


@pytest.fixture
def compliant_profile(build_profile):
    """A perfectly compliant company profile — engine should produce 0 flags."""
    return build_profile()


@pytest.fixture
def black_band_profile(build_profile):
    """A maximally non-compliant profile — should trigger BLACK band."""
    today = date.today()
    return build_profile(
        incorporation_date=today - timedelta(days=365 * 5),
        agm_held_this_cycle=False,
        agm_count=0,
        last_agm_date=None,
        audit_complete=False,
        first_auditor_appointed=False,
        first_auditor_appointment_date=None,
        unfiled_returns_count=3,
        annual_return_filed=False,
        agm_held_without_audit=True,
    )


# ---------------------------------------------------------------------------
# DirectorChange and ShareTransfer factory helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def make_director_change():
    """Factory for DirectorChange test objects."""
    try:
        from C_rule_engine import DirectorChange
    except ModuleNotFoundError:
        from app.rule_engine.engine import DirectorChange

    def _make(
        event_type: str = "appointment",
        days_ago: int = 400,
        form_filed: bool | None = False,
        form_filed_days_ago: int | None = None,
        form_filed_verified: bool = True,
        form_filed_evidence_ref: str | None = "evidence://test/form-xii",
        consent_filed: bool | None = None,
        consent_filed_days_ago: int | None = None,
        consent_verified: bool = False,
        consent_evidence_ref: str | None = None,
    ) -> DirectorChange:
        today = date.today()
        filed_date = today - timedelta(days=form_filed_days_ago) if form_filed and form_filed_days_ago else None
        consent_date = today - timedelta(days=consent_filed_days_ago) if consent_filed and consent_filed_days_ago else None
        return DirectorChange(
            director_id=str(uuid.uuid4()),
            event_type=event_type,
            event_date=today - timedelta(days=days_ago),
            form_filed=form_filed,
            form_filed_date=filed_date,
            form_filed_verified=form_filed_verified,
            form_filed_evidence_ref=form_filed_evidence_ref,
            consent_filed=consent_filed,
            consent_filed_date=consent_date,
            consent_verified=consent_verified,
            consent_evidence_ref=consent_evidence_ref,
        )

    return _make


@pytest.fixture
def make_share_transfer():
    """Factory for ShareTransfer test objects."""
    try:
        from C_rule_engine import ShareTransfer
    except ModuleNotFoundError:
        from app.rule_engine.engine import ShareTransfer

    def _make(
        days_ago: int = 30,
        instrument_recorded: bool | None = None,
        stamp_duty_paid: bool | None = None,
        stamp_duty_applicability_verified: bool = False,
        board_approval: bool | None = None,
        share_register_updated: bool | None = None,
        aoa_restriction_apply: bool | None = None,
        board_approval_obtained: bool | None = None,
        stamp_duty_amount: float | None = None,
        form_117_filed: bool | None = None,
        transfer_registered: bool | None = None,
        registration_refused: bool | None = None,
        refusal_notice_sent: bool | None = None,
        instrument_lodged_date: date | None = None,
        articles_clause_evidence_ref: str | None = None,
        refusal_decision_evidence_ref: str | None = None,
        transfer_registration_evidence_ref: str | None = None,
    ) -> ShareTransfer:
        return ShareTransfer(
            transfer_id=str(uuid.uuid4()),
            transfer_date=date.today() - timedelta(days=days_ago),
            instrument_recorded=instrument_recorded,
            stamp_duty_paid=stamp_duty_paid,
            stamp_duty_applicability_verified=stamp_duty_applicability_verified,
            stamp_duty_amount=stamp_duty_amount,
            board_approval=board_approval,
            share_register_updated=share_register_updated,
            aoa_restriction_apply=aoa_restriction_apply,
            board_approval_obtained=board_approval_obtained,
            form_117_filed=form_117_filed,
            transfer_registered=transfer_registered,
            registration_refused=registration_refused,
            refusal_notice_sent=refusal_notice_sent,
            instrument_lodged_date=instrument_lodged_date,
            articles_clause_evidence_ref=articles_clause_evidence_ref,
            refusal_decision_evidence_ref=refusal_decision_evidence_ref,
            transfer_registration_evidence_ref=transfer_registration_evidence_ref,
        )

    return _make


# ---------------------------------------------------------------------------
# DB Model factories (for integration tests)
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def db_company(db: AsyncSession) -> Company:
    """Create a Company row in the test DB."""
    from app.models.company import Company
    from app.models.enums import CompanyStatus, RiskBand

    today = date.today()
    company = Company(
        id=uuid.uuid4(),
        company_name="Test Company Ltd",
        registration_number=f"C-TEST-{uuid.uuid4().hex[:8].upper()}",
        incorporation_date=today - timedelta(days=365 * 2),
        registered_address="123 Test Street, Dhaka, Bangladesh",
        company_type="PRIVATE_LIMITED",
        member_count=5,
        financial_year_end=date(2025, 12, 31),
        current_compliance_score=85,
        current_risk_band=RiskBand.GREEN,
        company_status=CompanyStatus.ACTIVE,
        is_active=True,
        is_dormant=False,
        is_fdi_registered=False,
    )
    db.add(company)
    await db.flush()
    return company


@pytest_asyncio.fixture
async def legal_staff_company_scope(api_client, db: AsyncSession, db_company: Company) -> Company:
    """Assign the persisted LEGAL_STAFF test identity to this company explicitly."""
    db_company.assigned_staff_id = _role_user_id("LEGAL_STAFF")
    await db.flush()
    return db_company


@pytest_asyncio.fixture
async def db_user(db: AsyncSession) -> User:
    """Create a User row in the test DB."""
    from app.core.security import hash_password
    from app.models.enums import UserRole
    from app.models.user import User

    user = User(
        id=uuid.uuid4(),
        email=f"test_{uuid.uuid4().hex[:6]}@nlctest.com",
        full_name="Test User",
        password_hash=hash_password("TestPassword123!"),
        role=UserRole.ADMIN_STAFF,
        is_active=True,
        totp_enabled=False,
    )
    db.add(user)
    await db.flush()
    return user


@pytest_asyncio.fixture
async def db_client_user(db: AsyncSession, db_company: Company) -> User:
    """Create a real client identity with membership in exactly db_company."""
    from app.core.security import hash_password
    from app.models.company import CompanyUserAccess
    from app.models.enums import UserRole
    from app.models.user import User

    user = User(
        id=uuid.uuid4(),
        email=f"client_{uuid.uuid4().hex[:8]}@nlctest.com",
        full_name="Tenant A Client",
        password_hash=hash_password("TestPassword123!"),
        role=UserRole.CLIENT_DIRECTOR,
        is_active=True,
        totp_enabled=False,
    )
    db.add(user)
    await db.flush()
    db.add(CompanyUserAccess(
        user_id=user.id,
        company_id=db_company.id,
        can_edit=True,
        can_view_financials=True,
        is_active=True,
    ))
    await db.flush()
    return user


@pytest_asyncio.fixture
async def db_other_company(db: AsyncSession) -> Company:
    """Create a second real tenant with no membership for db_client_user."""
    from app.models.company import Company
    from app.models.enums import CompanyStatus, RiskBand

    today = date.today()
    company = Company(
        id=uuid.uuid4(),
        company_name="Other Tenant Ltd",
        registration_number=f"C-OTHER-{uuid.uuid4().hex[:8].upper()}",
        incorporation_date=today - timedelta(days=365 * 2),
        registered_address="456 Other Street, Dhaka, Bangladesh",
        company_type="PRIVATE_LIMITED",
        financial_year_end=date(2025, 12, 31),
        current_compliance_score=70,
        current_risk_band=RiskBand.YELLOW,
        company_status=CompanyStatus.ACTIVE,
        is_active=True,
        is_dormant=False,
        is_fdi_registered=False,
    )
    db.add(company)
    await db.flush()
    return company


@pytest_asyncio.fixture
async def db_super_admin(db: AsyncSession) -> User:
    """Create a Super Admin user in the test DB."""
    from app.core.security import hash_password
    from app.models.enums import UserRole
    from app.models.user import User

    user = User(
        id=uuid.uuid4(),
        email=f"superadmin_{uuid.uuid4().hex[:6]}@nlctest.com",
        full_name="Super Admin",
        password_hash=hash_password("SuperSecret123!"),
        role=UserRole.SUPER_ADMIN,
        is_active=True,
        totp_enabled=False,
    )
    db.add(user)
    await db.flush()
    return user


# ---------------------------------------------------------------------------
# Celery mock (eager execution in tests)
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def mock_celery_tasks(monkeypatch):
    """
    Auto-used fixture: all Celery task.apply_async() calls become no-ops.
    Prevents tests from needing a running worker.
    Tests that need to verify task dispatch can assert on mock calls.
    """
    mock_result = MagicMock()
    mock_result.id = "mock-task-id-" + uuid.uuid4().hex[:8]

    with patch("celery.app.task.Task.apply_async", return_value=mock_result) as mock_apply:
        yield mock_apply


# ---------------------------------------------------------------------------
# AI Provider mock
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_ai_provider():
    """Mock the AI provider API call — returns deterministic response."""
    sample_output = """
DRAFT AGM MINUTES

Company: Test Company Ltd
Registration Number: C-TEST-001
Meeting Date: 1 January 2024

IMPORTANT LEGAL NOTICE — NEUM LEX COUNSEL
This document has been prepared by NLC using AI-assisted drafting tools...
[Draft minutes content]
"""
    with patch("app.services.document_service._call_ai_provider", new_callable=AsyncMock) as mock:
        mock.return_value = sample_output
        yield mock


# ---------------------------------------------------------------------------
# S3 mock
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_s3():
    """Mock all S3 operations — prevents actual AWS calls in tests."""
    with patch("app.services.document_service._upload_to_s3", new_callable=AsyncMock) as mock_upload, \
         patch("app.services.document_service._presign_s3_url", new_callable=AsyncMock) as mock_presign:
        mock_upload.return_value = "documents/test/mock-doc.pdf"
        mock_presign.return_value = "https://s3.amazonaws.com/mock-presigned-url?expires=3600"
        yield {"upload": mock_upload, "presign": mock_presign}


# ---------------------------------------------------------------------------
# Helpers used in multiple test files
# ---------------------------------------------------------------------------

def assert_flag_triggered(output, rule_id: str) -> None:
    """Assert that a specific rule ID was flagged in engine output."""
    flag_ids = [f.rule_id for f in output.flags]
    assert rule_id in flag_ids, (
        f"Expected rule '{rule_id}' to be flagged, but only got: {flag_ids}"
    )


def assert_flag_not_triggered(output, rule_id: str) -> None:
    """Assert that a specific rule ID was NOT flagged in engine output."""
    flag_ids = [f.rule_id for f in output.flags]
    assert rule_id not in flag_ids, (
        f"Rule '{rule_id}' was unexpectedly triggered. All flags: {flag_ids}"
    )


def assert_risk_band(output, expected_band: str) -> None:
    """Assert the computed risk band matches expected."""
    actual = output.score_breakdown.risk_band
    assert actual == expected_band, (
        f"Expected risk band '{expected_band}', got '{actual}'. "
        f"Score: {output.score_breakdown.final_score}"
    )


# Expose helpers as fixtures too (so tests can import from conftest)
@pytest.fixture
def assert_helpers():
    return {
        "flag_triggered": assert_flag_triggered,
        "flag_not_triggered": assert_flag_not_triggered,
        "risk_band": assert_risk_band,
    }


# ---------------------------------------------------------------------------
# RLS-aware fixtures (tenant isolation)
# ---------------------------------------------------------------------------

import os


# ---------------------------------------------------------------------------
# RLS-aware fixtures (tenant isolation)
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def db_for_user(test_engine, request):
    """
    DB session with REAL RLS context for a specific user.
    Does NOT set app.rls_bypass.
    """
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.models.database import set_admin_context, set_rls_context
    from app.models.enums import UserRole
    from app.models.user import User

    user_id = getattr(request, "param", None)
    if user_id is None:
        user_id = str(_role_user_id("CLIENT_DIRECTOR"))
    user_uuid = uuid.UUID(str(user_id))

    async with test_engine.connect() as conn:
        await conn.begin()
        session = AsyncSession(bind=conn, expire_on_commit=False)
        try:
            # Seed identities under the signed service principal, then switch
            # to the requested tenant actor. Never fall back to unsigned GUCs.
            await set_admin_context(session)
            for role in UserRole:
                role_user_id = _role_user_id(role.value)
                existing = await session.get(User, role_user_id)
                if existing is None:
                    session.add(User(
                        id=role_user_id,
                        email=f"seed_{role.value.lower()}@nlctest.com",
                        full_name=f"Seed {role.value}",
                        password_hash="!seeded-no-login",
                        role=role,
                        is_active=True,
                        totp_enabled=False,
                    ))
            if await session.get(User, user_uuid) is None:
                session.add(User(
                    id=user_uuid,
                    email=f"seed_custom_{user_uuid.hex[:10]}@nlctest.com",
                    full_name="Seed Custom Test User",
                    password_hash="!seeded-no-login",
                    role=UserRole.CLIENT_DIRECTOR,
                    is_active=True,
                    totp_enabled=False,
                ))
            await session.flush()
            await set_rls_context(session, str(user_uuid))
            yield session
        finally:
            await session.close()
            await conn.rollback()


@pytest_asyncio.fixture
async def api_client_as_user(db_for_user):
    """
    HTTP client whose get_db_for_user uses a real RLS session.
    Use this for tenant-isolation tests.
    """
    from httpx import ASGITransport, AsyncClient
    from unittest.mock import MagicMock, patch
    from app.core.dependencies import get_db, get_db_for_user
    from app.main import create_app
    from app.models.database import get_db as auth_get_db
    app = create_app()

    async def _override_user_db():
        yield db_for_user

    app.dependency_overrides[get_db_for_user] = _override_user_db
    app.dependency_overrides[get_db] = _override_user_db
    app.dependency_overrides[auth_get_db] = _override_user_db

    with patch("app.worker.tasks.evaluate_company_compliance.apply_async", return_value=MagicMock(id="test-task")), \
         patch("app.worker.tasks.generate_ai_document_async.apply_async", return_value=MagicMock(id="test-task")), \
         patch("app.worker.tasks.render_pdf.apply_async", return_value=MagicMock(id="test-task")):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client

    app.dependency_overrides.clear()

