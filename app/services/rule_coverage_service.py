"""Company-scoped live rule coverage collection."""
from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.models.compliance import ComplianceEvaluationRun
from app.models.database import AsyncSessionLocal, set_catalog_context
from app.models.rules import LegalRule
from canonical_architecture.live_coverage import build_live_rule_coverage_report
from canonical_architecture.statutory_rules import STATUTORY_RULE_REGISTRY


async def collect_company_rule_coverage(
    db: AsyncSession,
    company_id: UUID,
) -> dict[str, Any] | None:
    """Collect current catalogue state and latest immutable run snapshot for one tenant."""
    company_result = await db.execute(
        select(Company.id).where(Company.id == company_id)
    )
    if company_result.scalar_one_or_none() is None:
        return None

    # Legal rules are a shared reference catalogue. Read them through the
    # dedicated CATALOG RLS context, not a broad ADMIN or tenant bypass.
    async with AsyncSessionLocal() as catalogue_db:
        await set_catalog_context(catalogue_db)
        rule_result = await catalogue_db.execute(
            select(
                LegalRule.rule_id,
                LegalRule.is_active,
                LegalRule.verification_status,
            ).order_by(LegalRule.rule_id)
        )
        database_rule_rows = [
            {
                "rule_id": row.rule_id,
                "is_active": bool(row.is_active),
                "verification_status": str(
                    getattr(row.verification_status, "value", row.verification_status)
                    or "UNKNOWN"
                ),
            }
            for row in rule_result.all()
        ]
        await catalogue_db.rollback()

    run_result = await db.execute(
        select(ComplianceEvaluationRun)
        .where(ComplianceEvaluationRun.company_id == company_id)
        .order_by(
            ComplianceEvaluationRun.calculated_at.desc(),
            ComplianceEvaluationRun.id.desc(),
        )
        .limit(1)
    )
    latest_run = run_result.scalar_one_or_none()

    engine_path = Path(__file__).resolve().parents[1] / "rule_engine" / "engine.py"
    engine_source = engine_path.read_text(encoding="utf-8")
    snapshot = (
        latest_run.rule_outcomes_snapshot
        if latest_run is not None
        and str(latest_run.evaluation_status).upper() in {"COMPLETED", "NOT_RELEASED"}
        and isinstance(latest_run.rule_outcomes_snapshot, list)
        else None
    )
    report = build_live_rule_coverage_report(
        engine_source=engine_source,
        registry=STATUTORY_RULE_REGISTRY,
        database_rule_rows=database_rule_rows,
        run_snapshot=snapshot,
    )
    return {
        "company_id": str(company_id),
        "evaluation_run_id": str(latest_run.id) if latest_run else None,
        "evaluation_status": latest_run.evaluation_status if latest_run else None,
        "evaluation_calculated_at": (
            latest_run.calculated_at.isoformat() if latest_run else None
        ),
        "report": report,
    }
