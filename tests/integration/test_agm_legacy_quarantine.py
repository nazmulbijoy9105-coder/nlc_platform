"""Integration proof for the one-time AGM legacy-default quarantine migration."""
from datetime import datetime, timezone
import importlib.util
from pathlib import Path
import uuid

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import text

from app.models.filings import AGM


@pytest.mark.asyncio
async def test_0055_preserves_legacy_defaults_and_quarantines_unverified_values(
    db, db_company, db_user
):
    now = datetime.now(timezone.utc)
    unverified_id = uuid.uuid4()
    verified_id = uuid.uuid4()

    unverified = AGM(
        id=unverified_id,
        company_id=db_company.id,
        financial_year=2025,
        quorum_required=2,
        quorum_met=True,
        auditor_reappointed=True,
    )
    verified = AGM(
        id=verified_id,
        company_id=db_company.id,
        financial_year=2026,
        members_present=1,
        members_present_verified=True,
        members_present_evidence_ref="AGM-MINUTES-VERIFIED",
        members_present_verified_at=now,
        members_present_verified_by=db_user.id,
        quorum_required=3,
        quorum_required_verified=True,
        quorum_evidence_ref="AOA-QUORUM-VERIFIED",
        quorum_verified_at=now,
        quorum_verified_by=db_user.id,
        quorum_met=False,
        auditor_reappointed=False,
        auditor_reappointment_verified=True,
        auditor_reappointment_evidence_ref="AGM-MINUTES-AUDITOR-VERIFIED",
        auditor_reappointment_verified_at=now,
        auditor_reappointment_verified_by=db_user.id,
    )
    db.add_all([unverified, verified])
    await db.flush()

    # The migration has already run in the integration database. Re-execute
    # its idempotent upgrade body against controlled rows to prove the actual
    # SQL preserves legacy values and leaves provenance-backed values intact.
    await db.execute(text("RESET ROLE"))
    migration_path = (
        Path(__file__).resolve().parents[2]
        / "alembic"
        / "versions"
        / "0055_quarantine_unverified_agm_defaults.py"
    )
    spec = importlib.util.spec_from_file_location("nlc_migration_0055", migration_path)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    async_connection = await db.connection()

    def run_upgrade(sync_connection):
        context = MigrationContext.configure(sync_connection)
        with Operations.context(context):
            migration.upgrade()

    await async_connection.run_sync(run_upgrade)
    await db.refresh(unverified)
    await db.refresh(verified)

    assert unverified.quorum_required is None
    assert unverified.quorum_met is None
    assert unverified.auditor_reappointed is None

    assert verified.quorum_required == 3
    assert verified.quorum_met is False
    assert verified.auditor_reappointed is False

    legacy = await db.execute(
        text(
            "SELECT quorum_required_legacy, quorum_met_legacy, "
            "auditor_reappointed_legacy FROM agms WHERE id = :agm_id"
        ),
        {"agm_id": unverified_id},
    )
    assert legacy.one() == (2, True, True)
