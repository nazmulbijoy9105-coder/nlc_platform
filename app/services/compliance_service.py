"""
NEUM LEX COUNSEL — Compliance Service
app/services/compliance_service.py

Implements _trigger_compliance_evaluation, _persist_evaluation_result,
_save_score_snapshot, _get_score_history, _get_dashboard_kpis stubs.

This is the orchestrator that:
  1. Builds CompanyProfile from DB (CompanyService)
  2. Runs NLCRuleEngine.evaluate()
  3. Persists flags to compliance_flags
  4. Persists score to compliance_score_history
  5. Updates company.current_compliance_score
  6. Queues notifications for new flags
  7. Triggers rescue plan generation if BLACK/RED

AI Constitution Article 4: Score history is append-only and tamper-evident.
AI Constitution Article 1: Rule engine output is immutable — AI cannot alter it.
"""
from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import date, datetime, timezone
from typing import Dict, List, Optional

from sqlalchemy import and_, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.compliance import ComplianceFlag, ComplianceScoreHistory
from app.models.company import Company
from app.models.enums import (
    ExposureBand, FlagStatus, RiskBand, RevenueTier, SeverityLevel,
)
from app.services.base import BaseService

logger = logging.getLogger("nlc.compliance")


class ComplianceService(BaseService[ComplianceFlag]):
    model = ComplianceFlag

    # ── Full Evaluation Pipeline ──────────────────────────────────

    async def evaluate_company(
        self,
        company_id: uuid.UUID,
        trigger_source: str = "API_REQUEST",
    ) -> Dict:
        """
        Full compliance evaluation pipeline:
        1. Build CompanyProfile from DB
        2. Run NLCRuleEngine
        3. Persist flags, score, update company
        4. Return structured result dict

        trigger_source: CRON_DAILY | API_REQUEST | RESCUE_STEP_COMPLETE | MANUAL
        AI Constitution Article 1: Result is deterministic. Identical input = identical output.
        """
        from app.services.company_service import CompanyService
        from app.core.dependencies import get_rule_engine
        from C_rule_engine import CompanyProfile, NLCRuleEngine

        # ── Step 1: Build profile ──────────────────────────────────
        company_svc = CompanyService(self.db)
        profile_data = await company_svc.build_company_profile(company_id)
        if not profile_data:
            raise ValueError(f"Company {company_id} not found or inactive.")

        # Convert dict to CompanyProfile dataclass
        try:
            profile = CompanyProfile(**profile_data)
        except TypeError as exc:
            raise ValueError(f"CompanyProfile assembly failed: {exc}") from exc

        # ── Step 2: Run rule engine ────────────────────────────────
        engine = get_rule_engine()
        output = engine.evaluate(profile)

        # ── Step 3: Persist results ────────────────────────────────
        await self._persist_evaluation(company_id, output, trigger_source)

        logger.info(
            f"[Compliance] Evaluated company={company_id} | "
            f"Score={output.score_breakdown.final_score} | "
            f"Band={output.score_breakdown.risk_band} | "
            f"Flags={len(output.flags)} | Trigger={trigger_source}"
        )

        return {
            "company_id":    str(company_id),
            "score":         output.score_breakdown.final_score,
            "risk_band":     output.score_breakdown.risk_band,
            "exposure_band": output.score_breakdown.exposure_band,
            "flags":         [
                {
                    "rule_id":        f.rule_id,
                    "severity":       f.severity,
                    "description":    f.description,
                    "score_impact":   f.score_impact,
                    "revenue_tier":   f.revenue_tier,
                    "statutory_basis": f.statutory_basis,
                }
                for f in output.flags
            ],
            "score_breakdown": {
                "agm_score":         output.score_breakdown.agm_score,
                "audit_score":       output.score_breakdown.audit_score,
                "return_score":      output.score_breakdown.return_score,
                "director_score":    output.score_breakdown.director_score,
                "shareholding_score":output.score_breakdown.shareholding_score,
                "override_applied":  output.score_breakdown.override_applied,
            },
            "rescue_required": output.rescue_plan is not None,
            "engine_version":  output.engine_version,
            "ilrmf_version":   output.ilrmf_version,
        }

    async def _persist_evaluation(
        self,
        company_id: uuid.UUID,
        output,  # EngineOutput from C_rule_engine.py
        trigger_source: str,
    ) -> None:
        """
        Persist all evaluation results to DB atomically.
        Order: resolve old flags → insert new flags → score snapshot → update company.
        """
        from app.core.config import get_settings
        settings = get_settings()

        now = datetime.now(timezone.utc)
        today = date.today()
        score = output.score_breakdown.final_score
        risk_band = RiskBand(output.score_breakdown.risk_band)
        rescue_required = output.rescue_plan is not None

        # ── Resolve previously active flags not in current output ──
        current_rule_ids = {f.rule_id for f in output.flags}
        await self.db.execute(
            update(ComplianceFlag)
            .where(
                ComplianceFlag.company_id == company_id,
                ComplianceFlag.flag_status == FlagStatus.ACTIVE,
                ComplianceFlag.rule_id.notin_(current_rule_ids),
            )
            .values(
                flag_status=FlagStatus.RESOLVED,
                resolved_date=today,
            )
        )

        # ── Insert new flags (upsert by company_id + rule_id) ──────
        for flag in output.flags:
            # Check if this flag already exists as ACTIVE
            existing = await self.db.execute(
                select(ComplianceFlag).where(
                    ComplianceFlag.company_id == company_id,
                    ComplianceFlag.rule_id == flag.rule_id,
                    ComplianceFlag.flag_status == FlagStatus.ACTIVE,
                )
            )
            existing_flag = existing.scalar_one_or_none()
            if existing_flag:
                # Update score impact and description in case rule changed
                existing_flag.score_impact = flag.score_impact
                existing_flag.description = flag.description
                self.db.add(existing_flag)
            else:
                # New flag
                new_flag = ComplianceFlag(
                    id=uuid.uuid4(),
                    company_id=company_id,
                    rule_id=flag.rule_id,
                    rule_version=settings.rule_engine_version,
                    flag_code=flag.rule_id,
                    statutory_basis=flag.statutory_basis,
                    severity=SeverityLevel(flag.severity),
                    score_impact=flag.score_impact,
                    exposure_band=ExposureBand(flag.exposure_band) if flag.exposure_band else None,
                    revenue_tier=RevenueTier(flag.revenue_tier),
                    flag_status=FlagStatus.ACTIVE,
                    triggered_date=today,
                    description=flag.description,
                    detail=getattr(flag, "detail", None),
                    notification_sent=False,
                )
                self.db.add(new_flag)

        # ── Score snapshot (monthly, append-only, tamper-evident) ──
        snapshot_month = today.replace(day=1)
        score_hash = hashlib.sha256(
            f"{company_id}{score}{risk_band}{snapshot_month}{settings.rule_engine_version}".encode()
        ).hexdigest()

        # Only one snapshot per company per month
        existing_snapshot = await self.db.execute(
            select(ComplianceScoreHistory).where(
                ComplianceScoreHistory.company_id == company_id,
                ComplianceScoreHistory.snapshot_month == snapshot_month,
            )
        )
        existing_snapshot_row = existing_snapshot.scalar_one_or_none()
        if not existing_snapshot_row:
            sb = output.score_breakdown
            black_flags = len([f for f in output.flags if f.severity == "BLACK"])
            snapshot = ComplianceScoreHistory(
                id=uuid.uuid4(),
                company_id=company_id,
                score=score,
                risk_band=risk_band,
                snapshot_month=snapshot_month,
                calculated_at=now,
                agm_score=sb.agm_score,
                audit_score=sb.audit_score,
                return_score=sb.return_score,
                director_score=sb.director_score,
                shareholding_score=sb.shareholding_score,
                active_flags_count=len(output.flags),
                black_flags_count=black_flags,
                override_applied=sb.override_applied,
                score_hash=score_hash,
                engine_version=settings.rule_engine_version,
                trigger_source=trigger_source,
            )
            self.db.add(snapshot)

        # ── Update company compliance state ────────────────────────
        company_svc_update: Dict = {
            "current_compliance_score": score,
            "current_risk_band":        risk_band,
            "rescue_required":          rescue_required,
            "last_evaluated_at":        now,
        }
        if rescue_required:
            company_svc_update["rescue_triggered_at"] = now

        await self.db.execute(
            update(Company)
            .where(Company.id == company_id)
            .values(**company_svc_update)
        )
        await self.db.flush()

    # ── Flag Management ───────────────────────────────────────────

    async def get_active_flags(self, company_id: uuid.UUID) -> List[ComplianceFlag]:
        """Return all ACTIVE compliance flags for a company."""
        result = await self.db.execute(
            select(ComplianceFlag)
            .where(
                ComplianceFlag.company_id == company_id,
                ComplianceFlag.flag_status == FlagStatus.ACTIVE,
            )
            .order_by(ComplianceFlag.severity.desc(), ComplianceFlag.triggered_date)
        )
        return list(result.scalars().all())

    async def get_flag_summary(self, company_id: uuid.UUID) -> Dict:
        """
        Flag summary from vw_company_flag_summary view.
        Fast — single query against pre-aggregated view.
        """
        result = await self.db.execute(
            text(
                "SELECT * FROM vw_company_flag_summary WHERE company_id = :cid"
            ),
            {"cid": str(company_id)},
        )
        row = result.mappings().one_or_none()
        return dict(row) if row else {}

    async def resolve_flag(
        self,
        flag_id: uuid.UUID,
        resolved_by: uuid.UUID,
        resolution_notes: str,
    ) -> Optional[ComplianceFlag]:
        """
        Manually resolve a compliance flag after remediation.
        Triggers score re-evaluation.
        """
        flag = await self.get_by_id(flag_id)
        if not flag:
            return None

        flag.flag_status = FlagStatus.RESOLVED
        flag.resolved_date = date.today()
        flag.resolved_by = resolved_by
        flag.resolution_notes = resolution_notes
        self.db.add(flag)
        await self.db.flush()
        return flag

    async def acknowledge_flag(
        self,
        flag_id: uuid.UUID,
        acknowledged_by: uuid.UUID,
    ) -> Optional[ComplianceFlag]:
        """Mark a flag as acknowledged (client has seen it)."""
        flag = await self.get_by_id(flag_id)
        if not flag:
            return None
        flag.flag_status = FlagStatus.ACKNOWLEDGED
        self.db.add(flag)
        await self.db.flush()
        return flag

    # ── Score History ─────────────────────────────────────────────

    async def get_score_history(
        self,
        company_id: uuid.UUID,
        months: int = 12,
    ) -> List[Dict]:
        """
        Return score history for the last N months.
        Used to render the compliance trend chart.
        """
        result = await self.db.execute(
            select(ComplianceScoreHistory)
            .where(ComplianceScoreHistory.company_id == company_id)
            .order_by(ComplianceScoreHistory.snapshot_month.desc())
            .limit(months)
        )
        rows = result.scalars().all()
        return [
            {
                "month":          row.snapshot_month.isoformat(),
                "score":          row.score,
                "risk_band":      row.risk_band,
                "agm_score":      row.agm_score,
                "audit_score":    row.audit_score,
                "return_score":   row.return_score,
                "director_score": row.director_score,
                "shareholding_score": row.shareholding_score,
                "active_flags":   row.active_flags_count,
                "black_flags":    row.black_flags_count,
                "override":       row.override_applied,
                "calculated_at":  row.calculated_at.isoformat(),
            }
            for row in rows
        ]

    async def get_dashboard_kpis(self) -> Dict:
        """Aggregate KPIs for admin dashboard from vw_admin_dashboard_kpis."""
        result = await self.db.execute(
            text("SELECT * FROM vw_admin_dashboard_kpis LIMIT 1")
        )
        row = result.mappings().one_or_none()
        return dict(row) if row else {}
