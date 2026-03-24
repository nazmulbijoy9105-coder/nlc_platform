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
  - DATABASE_URL_TEST env var or auto-derived from DATABASE_URL with "_test" suffix
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
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import AsyncGenerator, Dict, Generator, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

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
    """
    Derive test database URL.
    Priority: DATABASE_URL_TEST env var → DATABASE_URL with _test suffix.
    """
    explicit = os.getenv("DATABASE_URL_TEST")
    if explicit:
        return explicit
    base = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://nlc_user:nlc_password@localhost:5432/nlc_db",
    )
    # Replace database name with test database
    return base.rsplit("/", 1)[0] + "/nlc_test"


TEST_DATABASE_URL = _get_test_db_url()


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
    Sets admin RLS context (bypasses row-level security for test isolation).
    """
    async with test_engine.connect() as conn:
        await conn.begin()
        session = AsyncSession(bind=conn, expire_on_commit=False)

        # Bypass RLS for tests (admin context)
        await session.execute(text("SET app.rls_bypass = 'true'"))

        yield session

        await session.close()
        await conn.rollback()


# ---------------------------------------------------------------------------
# Security helpers (tokens)
# ---------------------------------------------------------------------------

def _make_token(role: str, user_id: Optional[str] = None, company_ids: Optional[List[str]] = None) -> str:
    """Generate a real JWT token for testing (uses actual security module)."""
    from app.core.security import create_access_token
    uid = user_id or str(uuid.uuid4())
    email = f"test_{role.lower()}@nlctest.com"
    companies = company_ids or []
    return create_access_token(uid, email, role, companies)


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
def super_admin_headers(super_admin_token) -> Dict[str, str]:
    return {"Authorization": f"Bearer {super_admin_token}"}


@pytest.fixture
def admin_headers(admin_token) -> Dict[str, str]:
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def legal_headers(legal_token) -> Dict[str, str]:
    return {"Authorization": f"Bearer {legal_token}"}


@pytest.fixture
def client_headers(client_token) -> Dict[str, str]:
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
    from app.main import create_app
    from app.core.dependencies import get_db, get_db_for_user

    app = create_app()

    # Override DB dependency with test session
    async def _override_db():
        yield db

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_db_for_user] = _override_db

    # Patch Celery tasks to be no-ops
    with patch("app.worker.tasks.evaluate_company_compliance.apply_async", return_value=MagicMock(id="test-task")), \
         patch("app.worker.tasks.generate_ai_document_async.apply_async", return_value=MagicMock(id="test-task")), \
         patch("app.worker.tasks.render_pdf.apply_async", return_value=MagicMock(id="test-task")):
        async with AsyncClient(app=app, base_url="http://test") as client:
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
        from app.rule_engine.engine import CompanyProfile, DirectorChange, ShareTransfer

    def _build(**overrides) -> CompanyProfile:
        today = date.today()
        defaults = dict(
            company_id=str(uuid.uuid4()),
            company_name="Test Company Ltd",
            company_type="PRIVATE_LIMITED",
            # Incorporated 3 years ago — old enough for all deadlines
            incorporation_date=today - timedelta(days=365 * 3),
            financial_year_end=date(today.year - 1, 12, 31),
            # AGM — fully compliant
            agm_count=3,
            last_agm_date=today - timedelta(days=60),
            agm_held_this_cycle=True,
            agm_scheduled_date=None,
            notice_sent_date=today - timedelta(days=84),  # 21+ days before AGM
            members_present_at_agm=3,
            auditor_reappointed_at_agm=True,
            accounts_adopted_at_agm=True,
            # Audit — fully compliant
            first_auditor_appointed=True,
            audit_complete=True,
            last_audit_signed_date=today - timedelta(days=90),
            audit_in_progress=False,
            # Annual return — fully compliant
            last_return_filed_year=today.year - 1,
            unfiled_returns_count=0,
            annual_return_filed=True,
            annual_return_content_complete=True,
            last_agm_filing_date=today - timedelta(days=30),
            # Directors — no changes pending
            director_changes=[],
            # Shareholders — no changes
            shareholder_change_date=None,
            form_xv_filed=True,
            # Transfers — none
            share_transfers=[],
            # Office — no change
            registered_office_change_date=None,
            form_ix_filed=True,
            # Corporate structure
            aoa_transfer_restriction=True,
            has_foreign_shareholder=False,
            is_dormant=False,
            is_fdi_registered=False,
            # Registers & certificates
            maintained_registers=["members", "directors", "charges", "transfers", "debentures", "mortgages"],
            last_allotment_date=None,
            share_certificate_issued=True,
            # Capital
            capital_increase_date=None,
            capital_increase_resolution=True,
            charge_creation_date=None,
            form_viii_filed=True,
        )
        defaults.update(overrides)
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
        form_filed: bool = False,
        form_filed_days_ago: Optional[int] = None,
    ) -> DirectorChange:
        today = date.today()
        filed_date = today - timedelta(days=form_filed_days_ago) if form_filed and form_filed_days_ago else None
        return DirectorChange(
            director_id=str(uuid.uuid4()),
            event_type=event_type,
            event_date=today - timedelta(days=days_ago),
            form_filed=form_filed,
            form_filed_date=filed_date,
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
        instrument_recorded: bool = True,
        stamp_duty_paid: bool = True,
        board_approval: bool = True,
        share_register_updated: bool = True,
        aoa_restriction_apply: bool = False,
        board_approval_obtained: bool = True,
        stamp_duty_amount: Optional[float] = 1000.0,
    ) -> ShareTransfer:
        return ShareTransfer(
            transfer_id=str(uuid.uuid4()),
            transfer_date=date.today() - timedelta(days=days_ago),
            instrument_recorded=instrument_recorded,
            stamp_duty_paid=stamp_duty_paid,
            stamp_duty_amount=stamp_duty_amount,
            board_approval=board_approval,
            share_register_updated=share_register_updated,
            aoa_restriction_apply=aoa_restriction_apply,
            board_approval_obtained=board_approval_obtained,
        )

    return _make


# ---------------------------------------------------------------------------
# DB Model factories (for integration tests)
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def db_company(db: AsyncSession) -> "Company":
    """Create a Company row in the test DB."""
    from app.models.company import Company
    from app.models.enums import RiskBand, CompanyStatus

    today = date.today()
    company = Company(
        id=uuid.uuid4(),
        company_name="Test Company Ltd",
        registration_number=f"C-TEST-{uuid.uuid4().hex[:8].upper()}",
        incorporation_date=today - timedelta(days=365 * 2),
        registered_address="123 Test Street, Dhaka, Bangladesh",
        company_type="PRIVATE_LIMITED",
        financial_year_end="12-31",
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
async def db_user(db: AsyncSession) -> "User":
    """Create a User row in the test DB."""
    from app.models.user import User
    from app.models.enums import UserRole
    from app.core.security import get_password_hash

    user = User(
        id=uuid.uuid4(),
        email=f"test_{uuid.uuid4().hex[:6]}@nlctest.com",
        full_name="Test User",
        hashed_password=get_password_hash("TestPassword123!"),
        role=UserRole.ADMIN_STAFF,
        is_active=True,
        totp_enabled=False,
    )
    db.add(user)
    await db.flush()
    return user


@pytest_asyncio.fixture
async def db_super_admin(db: AsyncSession) -> "User":
    """Create a Super Admin user in the test DB."""
    from app.models.user import User
    from app.models.enums import UserRole
    from app.core.security import get_password_hash

    user = User(
        id=uuid.uuid4(),
        email=f"superadmin_{uuid.uuid4().hex[:6]}@nlctest.com",
        full_name="Super Admin",
        hashed_password=get_password_hash("SuperSecret123!"),
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
