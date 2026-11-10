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
import json
import logging
import uuid
from fastapi.encoders import jsonable_encoder
from dataclasses import fields as dataclass_fields
from datetime import UTC, date, datetime

from sqlalchemy import select, text, update

from app.models.company import Company
from app.models.compliance import ComplianceEvaluationRun, ComplianceFlag, ComplianceScoreHistory
from app.models.company_fact import CompanyFact
from app.models.enums import (
    ExposureBand,
    FlagStatus,
    RevenueTier,
    RiskBand,
    SeverityLevel,
)
from app.services.base import BaseService
from app.services.notification_service import NotificationService

logger = logging.getLogger("nlc.compliance")



def _company_profile_kwargs(profile_data: dict, profile_cls) -> dict:
    """Normalize CompanyService profile output to the active rule-engine dataclass."""
    accepted = {field.name for field in dataclass_fields(profile_cls)}
    aliases = {
        "last_agm_filing_date": "annual_return_filed_date",
        "form_ix_filed": "form_vi_filed",
        "share_certificate_issued": "share_certificates_issued",
        "charge_creation_date": None,
    }

    normalized = dict(profile_data)
    for old_key, new_key in aliases.items():
        if old_key in normalized and new_key and new_key not in normalized:
            normalized[new_key] = normalized[old_key]

    return {key: value for key, value in normalized.items() if key in accepted}


def _has_rescue_output(output) -> bool:
    """Whether the engine produced rescue steps (informational only).
    Do NOT use this to decide whether a company needs rescue — use
    _is_rescue_required instead."""
    rescue_plan = getattr(output, "rescue_plan", None)
    rescue_sequence = getattr(output, "rescue_sequence", None)
    return bool(rescue_plan or rescue_sequence)


def _applied_score_impacts(flags) -> list[dict]:
    """Reconcile nominal flag impacts with the verified-rule gate and caps.

    The returned value is aligned by index with the original flags list so
    repeated rule IDs cannot overwrite one another.
    """
    from app.rule_engine.engine import (
        AUTHORIZED_BLACK_OVERRIDE_RULE_IDS,
        CATEGORY_CAPS,
        PRODUCT_SCORING_RULE_IDS,
        RuleState,
        legal_score_is_released,
    )

    remaining = {name: cap[0] for name, cap in CATEGORY_CAPS.items()}
    results = []
    for flag in flags:
        state = getattr(flag, "state", None)
        active = not getattr(flag, "resolved", False) and getattr(flag, "conditional_applies", True)
        if not active:
            results.append({"applied": 0, "status": "INACTIVE"})
            continue
        confirmed_violation = (
            state in (RuleState.NON_COMPLIANT, RuleState.VERIFIED_ABSENT)
            and getattr(flag, "eval_state", "VIOLATION") == "VIOLATION"
        )
        if not confirmed_violation:
            results.append({"applied": 0, "status": "NOT_A_CONFIRMED_VIOLATION"})
            continue

        # The global release gate takes precedence over per-rule eligibility:
        # while release is closed, no rule has an applied score impact.
        if not legal_score_is_released():
            results.append({"applied": 0, "status": "LEGAL_SCORE_NOT_RELEASED"})
            continue
        if flag.rule_id not in PRODUCT_SCORING_RULE_IDS:
            results.append({"applied": 0, "status": "EXCLUDED_FROM_PRODUCT_SCORING"})
            continue

        severity_value = getattr(
            getattr(flag, "severity", None),
            "value",
            getattr(flag, "severity", None),
        )
        authorised_black_override = (
            flag.rule_id in PRODUCT_SCORING_RULE_IDS
            and flag.rule_id in AUTHORIZED_BLACK_OVERRIDE_RULE_IDS
            and getattr(flag, "is_black_override", False) is True
            and severity_value == "BLACK"
        )
        if authorised_black_override:
            results.append({"applied": 0, "status": "BLACK_OVERRIDE_APPLIED"})
            continue

        category = next(
            (name for name, (_, prefixes) in CATEGORY_CAPS.items()
             if flag.rule_id.startswith(prefixes)),
            None,
        )
        if category is None:
            results.append({"applied": 0, "status": "NO_SCORING_CATEGORY"})
            continue

        applied = min(max(0, int(flag.score_impact)), remaining[category])
        remaining[category] -= applied
        results.append({
            "applied": applied,
            "status": "APPLIED" if applied else "CATEGORY_CAP_REACHED",
        })
    return results


def _is_rescue_required(output) -> bool:
    """Whether the company NEEDS a rescue plan — based on flag presence,
    not on whether the engine happened to produce a sequence."""
    sb = output.score_breakdown
    return bool(
        sb.black_flag_count > 0
        or sb.red_flag_count > 0
        or sb.override_applied
    )


class ComplianceService(BaseService[ComplianceFlag]):
    model = ComplianceFlag

    # ── Full Evaluation Pipeline ──────────────────────────────────

    async def evaluate_company(
        self,
        company_id: uuid.UUID,
        trigger_source: str = "API_REQUEST",
        rule_engine=None,
    ) -> dict:
        """
        Full compliance evaluation pipeline:
        1. Build CompanyProfile from DB
        2. Run NLCRuleEngine
        3. Persist flags, score, update company
        4. Return structured result dict

        trigger_source: CRON_DAILY | API_REQUEST | RESCUE_STEP_COMPLETE | MANUAL
        AI Constitution Article 1: Result is deterministic. Identical input = identical output.
        """
        from app.core.dependencies import get_rule_engine
        from app.rule_engine import CompanyProfile
        from app.rule_engine.engine import (
            CATEGORY_CAPS,
            _COVERAGE_FIELDS,
            PRODUCT_SCORING_RULE_IDS,
            legal_score_is_released,
        )
        from app.services.company_service import CompanyService

        # ── Step 1: Build profile ──────────────────────────────────
        company_svc = CompanyService(self.db)
        profile_data = await company_svc.build_company_profile(company_id)
        if not profile_data:
            raise ValueError(f"Company {company_id} not found or inactive.")

        # Current versioned facts override same-key legacy profile values. Every
        # evaluation and finding receives the exact provenance snapshot used
        # for this run; [] means no explicit fact records were available.
        fact_result = await self.db.execute(
            select(CompanyFact).where(
                CompanyFact.company_id == company_id,
                CompanyFact.is_current.is_(True),
            ).order_by(CompanyFact.created_at.asc(), CompanyFact.id.asc())
        )
        current_facts = list(fact_result.scalars().all())
        used_facts = []
        for fact in current_facts:
            if fact.fact_key in profile_data:
                profile_data[fact.fact_key] = fact.fact_value
                used_facts.append(fact)
        fact_provenance_snapshot = [
            fact.provenance_payload() for fact in used_facts
        ]
        untracked_profile_fields = sorted(
            set(profile_data) - {fact.fact_key for fact in used_facts}
        )
        if untracked_profile_fields:
            fact_provenance_snapshot.append({
                "record_type": "UNATTRIBUTED_PROFILE_FIELDS",
                "fields": untracked_profile_fields,
                "disclosure": (
                    "Some legacy company-profile inputs have no explicit source record. "
                    "Their origin and verification status are unknown; do not treat them as verified."
                ),
            })

        # Convert dict to CompanyProfile dataclass
        try:
            profile = CompanyProfile(**_company_profile_kwargs(profile_data, CompanyProfile))
        except TypeError as exc:
            raise ValueError(f"CompanyProfile assembly failed: {exc}") from exc

        # ── Step 2: Run rule engine ────────────────────────────────
        # Explicit injection supports deterministic tests and controlled
        # evaluation runs. Production callers retain the canonical engine.
        engine = rule_engine if rule_engine is not None else get_rule_engine()
        output = engine.evaluate(profile)
        risk_band_value = getattr(
            output.score_breakdown.risk_band,
            "value",
            output.score_breakdown.risk_band,
        )
        score_is_released = legal_score_is_released() and risk_band_value != "NOT_EVALUATED"
        public_risk_band = risk_band_value if score_is_released else "NOT_EVALUATED"
        api_score = output.score_breakdown.final_score if score_is_released else None
        api_raw_total = output.score_breakdown.raw_total if score_is_released else None

        # ── Step 3: Persist results ────────────────────────────────
        await self._persist_evaluation(
            company_id, output, trigger_source,
            fact_provenance_snapshot=fact_provenance_snapshot,
        )

        logger.info(
            f"[Compliance] Evaluated company={company_id} | "
            f"Score={api_score if score_is_released else 'NOT_RELEASED'} | "
            f"Band={public_risk_band} | "
            f"Flags={len(output.flags)} | Trigger={trigger_source}"
        )

        applied_impacts = _applied_score_impacts(output.flags)

        return {
            "company_id":    str(company_id),
            "score":         api_score,
            "raw_total":     api_raw_total,
            "risk_band":     public_risk_band,
            "exposure_band": output.score_breakdown.exposure_band if score_is_released else None,
            "legal_evaluation_status": (
                "RELEASED" if score_is_released
                else "NOT_EVALUATED_COUNSEL_REVIEW_PENDING"
            ),
            # Unapproved rule triggers are retained only in the internal
            # audit store. They are not exposed as customer-facing flags.
            "flags": [
                {
                    "rule_id": f.rule_id,
                    "severity": f.severity,
                    "description": f.description,
                    "score_impact": f.score_impact,
                    "score_impact_applied": applied_impacts[index]["applied"],
                    "scoring_status": applied_impacts[index]["status"],
                    "revenue_tier": f.revenue_tier,
                    "statutory_basis": f.statutory_basis,
                    "fact_provenance_snapshot": fact_provenance_snapshot,
                    "fact_basis_disclosure": [
                        item["disclosure"] for item in fact_provenance_snapshot
                    ],
                }
                for index, f in enumerate(output.flags)
                if score_is_released and f.rule_id in PRODUCT_SCORING_RULE_IDS
            ],
            "score_breakdown": {
                "risk_band": public_risk_band,
                "agm_score":         output.score_breakdown.agm_score if score_is_released else None,
                "audit_score":       output.score_breakdown.audit_score if score_is_released else None,
                "return_score":      output.score_breakdown.return_score if score_is_released else None,
                "director_score":    output.score_breakdown.director_score if score_is_released else None,
                "shareholding_score": output.score_breakdown.shareholding_score if score_is_released else None,
                "capital_score": output.score_breakdown.capital_score if score_is_released else None,
                "office_score": output.score_breakdown.office_score if score_is_released else None,
                "register_score": output.score_breakdown.register_score if score_is_released else None,
                "tax_score": output.score_breakdown.tax_score if score_is_released else None,
                "bankruptcy_score": output.score_breakdown.bankruptcy_score if score_is_released else None,
                "labour_score": output.score_breakdown.labour_score if score_is_released else None,
                "bsec_score": output.score_breakdown.bsec_score if score_is_released else None,
                "fx_score": output.score_breakdown.fx_score if score_is_released else None,
                "escalation_score": output.score_breakdown.escalation_score if score_is_released else None,
                "raw_total": api_raw_total,
                "final_score": api_score,
                "coverage": output.score_breakdown.coverage if score_is_released else None,
                "active_flag_count": output.score_breakdown.active_flag_count if score_is_released else 0,
                "black_flag_count": output.score_breakdown.black_flag_count if score_is_released else 0,
                "red_flag_count": output.score_breakdown.red_flag_count if score_is_released else 0,
                "yellow_flag_count": output.score_breakdown.yellow_flag_count if score_is_released else 0,
                "override_applied": output.score_breakdown.override_applied if score_is_released else False,
                "override_reason": output.score_breakdown.override_reason if score_is_released else None,
            },
            "rescue_required": bool(score_is_released and _is_rescue_required(output)),
            "rescue_sequence": output.rescue_sequence if score_is_released else None,
            "engine_version":  output.engine_version,
            "ilrmf_version":   output.ilrmf_version,
        }

    async def _persist_evaluation(
        self,
        company_id: uuid.UUID,
        output,  # EngineOutput from C_rule_engine.py
        trigger_source: str,
        fact_provenance_snapshot: list[dict] | None = None,
    ) -> None:
        """
        Persist all evaluation results to DB atomically.
        Order: resolve old flags → insert new flags → score snapshot → update company.
        """
        from app.rule_engine.engine import (
            CATEGORY_CAPS,
            _COVERAGE_FIELDS,
            PRODUCT_SCORING_RULE_IDS,
            legal_score_is_released,
        )

        fact_provenance_snapshot = fact_provenance_snapshot or []
        engine_version = str(getattr(output, "engine_version", "") or "").strip()
        if not engine_version or engine_version.lower() == "unknown":
            raise ValueError("Evaluation cannot be persisted without a concrete engine version.")
        if len(engine_version) > 20:
            raise ValueError("Engine version exceeds the 20-character score-history storage limit.")

        # Serialize evaluations per company so the immutable hash chain cannot fork.
        await self.db.execute(
            select(Company.id).where(Company.id == company_id).with_for_update()
        )
        now = datetime.now(UTC)
        today = date.today()
        score = output.score_breakdown.final_score
        risk_band_value = getattr(output.score_breakdown.risk_band, 'value', output.score_breakdown.risk_band)
        risk_band = RiskBand(risk_band_value)
        if risk_band.value not in ("GREEN", "YELLOW", "RED", "BLACK", "NOT_EVALUATED"):
            # DB enum risk_band has no other values; derive from score instead of failing the UPDATE
            risk_band = RiskBand(
                "BLACK" if score <= 29 else "RED" if score <= 49 else "YELLOW" if score <= 69 else "GREEN"
            )
        # Defense in depth: persistence independently enforces the
        # counsel-approved release switch; a provisional engine band cannot
        # publish a numeric score while legal approval is disabled.
        if not legal_score_is_released():
            risk_band = RiskBand.NOT_EVALUATED
        score_for_current = (
            score
            if legal_score_is_released() and risk_band != RiskBand.NOT_EVALUATED
            else None
        )

        # No remediation workflow may be triggered from a provisional, unreleased score.
        rescue_required = bool(score_for_current is not None and _is_rescue_required(output))
        if rescue_required and not _has_rescue_output(output):
            logger.warning(
                "rescue_required_but_no_sequence company=%s black=%s red=%s override=%s",
                company_id,
                output.score_breakdown.black_flag_count,
                output.score_breakdown.red_flag_count,
                output.score_breakdown.override_applied,
            )

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
        collected_new_flags: list = []
        for flag in output.flags:

            # Check if this flag already exists as ACTIVE
            existing = await self.db.execute(
                select(ComplianceFlag)
                .where(
                    ComplianceFlag.company_id == company_id,
                    ComplianceFlag.rule_id == flag.rule_id,
                    ComplianceFlag.flag_status == FlagStatus.ACTIVE,
                )
                .order_by(ComplianceFlag.created_at.asc(), ComplianceFlag.id.asc())
                .limit(1)
            )
            existing_flag = existing.scalar_one_or_none()
            if existing_flag:
                # Update score impact and description in case rule changed
                approved = legal_score_is_released() and flag.rule_id in PRODUCT_SCORING_RULE_IDS
                existing_flag.severity = (
                    SeverityLevel(flag.severity) if approved else SeverityLevel.NOT_EVALUATED
                )
                existing_flag.score_impact = flag.score_impact if approved else 0
                existing_flag.statutory_basis = (
                    flag.statutory_basis if approved
                    else "Excluded from the product scoring allowlist."
                )
                existing_flag.description = (
                    flag.description if approved
                    else "Internal review signal only. No legal conclusion, breach, liability, penalty or compliance status is determined."
                )
                existing_flag.exposure_band = (
                    getattr(flag, "exposure_band", None) if approved else None
                )
                existing_flag.evaluation_state = str(
                    getattr(flag, "eval_state", "LEGACY_UNCLASSIFIED")
                )
                existing_flag.fact_provenance_snapshot = fact_provenance_snapshot
                self.db.add(existing_flag)
            else:
                # New flag
                new_flag = ComplianceFlag(
                    id=uuid.uuid4(),
                    company_id=company_id,
                    rule_id=flag.rule_id,
                    rule_version=str(getattr(flag, 'rule_version', None) or engine_version),
                    flag_code=flag.rule_id,
                    statutory_basis=(
                        flag.statutory_basis
                        if legal_score_is_released() and flag.rule_id in PRODUCT_SCORING_RULE_IDS
                        else "NOT VALIDATED — independent counsel review required"
                    ),
                    severity=SeverityLevel(flag.severity)
                    if legal_score_is_released() and flag.rule_id in PRODUCT_SCORING_RULE_IDS
                    else SeverityLevel.NOT_EVALUATED,
                    score_impact=flag.score_impact
                    if legal_score_is_released() and flag.rule_id in PRODUCT_SCORING_RULE_IDS
                    else 0,
                    exposure_band=(
                        ExposureBand(getattr(getattr(flag, "exposure_band", None) or output.score_breakdown.exposure_band, "value", getattr(flag, "exposure_band", None) or output.score_breakdown.exposure_band))
                        if legal_score_is_released() and flag.rule_id in PRODUCT_SCORING_RULE_IDS
                        else None
                    ),
                    revenue_tier=RevenueTier(flag.revenue_tier.value if hasattr(flag.revenue_tier, 'value') else flag.revenue_tier),
                    flag_status=FlagStatus.ACTIVE,
                    evaluation_state=str(
                        getattr(flag, "eval_state", "LEGACY_UNCLASSIFIED")
                    ),
                    triggered_date=today,
                    description=(
                        flag.description
                        if legal_score_is_released() and flag.rule_id in PRODUCT_SCORING_RULE_IDS
                        else "Internal review signal only. No legal conclusion, breach, liability, penalty or compliance status is determined."
                    ),
                    detail=getattr(flag, "detail", None),
                    fact_provenance_snapshot=fact_provenance_snapshot,
                    notification_sent=False,
                )
                self.db.add(new_flag)
                collected_new_flags.append(new_flag)

        # ── Score snapshot (monthly, append-only, tamper-evident) ──
        snapshot_month = today.replace(day=1)
        score_hash = hashlib.sha256(
            f"{company_id}{score_for_current}{risk_band}{snapshot_month}{engine_version}".encode()
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
            # Use the engine's validated override count; a BLACK label alone
            # is not authority to trigger BLACK override semantics.
            black_flags = sb.black_flag_count if legal_score_is_released() else 0
            snapshot = ComplianceScoreHistory(
                id=uuid.uuid4(),
                company_id=company_id,
                score=score_for_current,
                risk_band=risk_band,
                snapshot_month=snapshot_month,
                calculated_at=now,
                agm_score=sb.agm_score if score_for_current is not None else None,
                audit_score=sb.audit_score if score_for_current is not None else None,
                return_score=sb.return_score if score_for_current is not None else None,
                director_score=sb.director_score if score_for_current is not None else None,
                shareholding_score=sb.shareholding_score if score_for_current is not None else None,
                active_flags_count=len(output.flags),
                black_flags_count=black_flags,
                override_applied=sb.override_applied,
                score_hash=score_hash,
                engine_version=engine_version,
                trigger_source=trigger_source,
                evaluation_status=("COMPLETED" if score_for_current is not None else "NOT_RELEASED"),
            )
            self.db.add(snapshot)

        # ── Append immutable per-evaluation record ──────────────────
        previous_result = await self.db.execute(
            select(ComplianceEvaluationRun.score_hash)
            .where(ComplianceEvaluationRun.company_id == company_id)
            .order_by(ComplianceEvaluationRun.calculated_at.desc())
            .limit(1)
        )
        previous_hash = previous_result.scalar_one_or_none()
        applied_impacts = _applied_score_impacts(output.flags)
        dispositions = getattr(output, "rescue_dispositions", None) or []
        disposition_by_flag = {
            item.get("flag_code"): item
            for item in dispositions
            if item.get("flag_code")
        }
        flags_snapshot = []
        for flag, applied in zip(output.flags, applied_impacts):
            severity_value = getattr(flag.severity, "value", flag.severity)
            rule_category = next(
                (
                    name
                    for name, (_, prefixes) in CATEGORY_CAPS.items()
                    if flag.rule_id.startswith(prefixes)
                ),
                "OTHER",
            )
            rescue_disposition = disposition_by_flag.get(
                getattr(flag, "flag_code", None), {}
            )
            flags_snapshot.append({
                "rule_id": flag.rule_id,
                "severity": severity_value,
                "rescue_disposition": rescue_disposition.get("disposition"),
                "rescue_reason": rescue_disposition.get("reason"),
                "rescue_id": rescue_disposition.get("rescue_id"),
                "category": rule_category,
                "score_impact": int(flag.score_impact or 0),
                "score_impact_applied": int(applied["applied"]),
                "scoring_status": applied["status"],
                "description": getattr(flag, "description", None),
                "detail": getattr(flag, "detail", None),
                "statutory_basis": getattr(flag, "statutory_basis", None),
                "eval_state": getattr(getattr(flag, "eval_state", None), "value", getattr(flag, "eval_state", None)),
                "state": getattr(getattr(flag, "state", None), "value", getattr(flag, "state", None)),
                "fact_provenance_snapshot": fact_provenance_snapshot,
                "fact_basis_disclosure": [item["disclosure"] for item in fact_provenance_snapshot],
            })

        flags_snapshot = jsonable_encoder(flags_snapshot)
        sb = output.score_breakdown
        score_breakdown_snapshot = None if score_for_current is None else {
            "engine_version": engine_version,
            "ilrmf_version": str(getattr(output, "ilrmf_version", "") or ""),
            "score_hash": sb.score_hash,
            "raw_total": sb.raw_total,
            "final_score": score_for_current,
            "risk_band": risk_band.value,
            "exposure_band": getattr(sb.exposure_band, "value", sb.exposure_band),
            "revenue_tier": getattr(sb.revenue_tier, "value", sb.revenue_tier),
            "override_applied": sb.override_applied,
            "override_reason": sb.override_reason,
            "category_deductions": dict(sb.category_deductions or {}),
            "category_caps": {
                key: {"max_deduction": cap, "prefixes": list(prefixes)}
                for key, (cap, prefixes) in sorted(CATEGORY_CAPS.items())
            },
            "score_model_semantics": (
                "HEADLINE_SCORE_IS_100_MINUS_CAPPED_CATEGORY_DEDUCTIONS; "
                "MODULE_SCORES_ARE_NON_ADDITIVE_DIAGNOSTICS"
            ),
            "module_score_maxima": {
                "agm": 20,
                "audit": 20,
                "annual_return": 20,
                "director": 10,
                "shareholding": 10,
                "capital": 5,
                "office": 5,
                "register": 5,
                "tax": 5,
                "bankruptcy": 5,
                "labour": 5,
                "bsec": 5,
                "foreign_exchange": 5,
                "escalation": 5,
                "total_diagnostic_maximum": 125,
            },
            "module_scores": {
                "agm": sb.agm_score,
                "audit": sb.audit_score,
                "annual_return": sb.return_score,
                "director": sb.director_score,
                "shareholding": sb.shareholding_score,
                "capital": sb.capital_score,
                "office": sb.office_score,
                "register": sb.register_score,
                "tax": sb.tax_score,
                "bankruptcy": sb.bankruptcy_score,
                "labour": sb.labour_score,
                "bsec": sb.bsec_score,
                "foreign_exchange": sb.fx_score,
                "escalation": sb.escalation_score,
            },
            "coverage": {
                "value": sb.coverage,
                "basis": sb.coverage_basis,
                "weights": dict(sorted(_COVERAGE_FIELDS.items())),
            },
            "flag_counts": {
                "active": sb.active_flag_count,
                "black": sb.black_flag_count,
                "red": sb.red_flag_count,
                "yellow": sb.yellow_flag_count,
                "green": sb.green_flag_count,
            },
        }
        hash_material = json.dumps(
            {
                "previous_hash": previous_hash or "GENESIS",
                "company_id": str(company_id),
                "score": score_for_current,
                "risk_band": risk_band.value,
                "calculated_at": now.isoformat(),
                "engine_version": engine_version,
                "trigger_source": trigger_source,
                "flags_snapshot": flags_snapshot,
                "score_breakdown_snapshot": score_breakdown_snapshot,
            },
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        evaluation_hash = hashlib.sha256(hash_material.encode()).hexdigest()
        black_flags = (
            output.score_breakdown.black_flag_count
            if legal_score_is_released() else 0
        )
        evaluation_run = ComplianceEvaluationRun(
            id=uuid.uuid4(),
            company_id=company_id,
            score=score_for_current,
            risk_band=risk_band,
            calculated_at=now,
            engine_version=engine_version,
            score_hash=evaluation_hash,
            previous_hash=previous_hash,
            evaluation_status=("COMPLETED" if score_for_current is not None else "NOT_RELEASED"),
            trigger_source=trigger_source,
            active_flags_count=len(output.flags),
            black_flags_count=black_flags,
            flags_snapshot=flags_snapshot,
            fact_provenance_snapshot=fact_provenance_snapshot,
            score_breakdown_snapshot=score_breakdown_snapshot,
        )
        self.db.add(evaluation_run)

        # ── Update company compliance state ────────────────────────
        company_svc_update: dict = {
            "current_compliance_score": score_for_current,
            "current_risk_band":        risk_band,
            "rescue_required":          rescue_required,
            "last_evaluated_at":        now,
        }
        if rescue_required:
            company_svc_update["rescue_triggered_at"] = now
            
            # Auto-create RescuePlan if not already active
            from app.services.rescue_service import RescueService
            rescue_svc = RescueService(self.db)
            existing_plan = await rescue_svc.get_active_plan(company_id)
            if existing_plan:
                new_titles = {st.get('title') for st in (getattr(output, 'rescue_sequence', None) or [])}
                old_titles = {st.step_title for st in existing_plan.steps}
                untouched = existing_plan.completed_steps == 0 and all(
                    getattr(st.step_status, 'value', st.step_status) == 'PENDING' for st in existing_plan.steps
                )
                if new_titles and new_titles != old_titles:
                    if untouched:
                        existing_plan = None
                    else:
                        logger.warning(f'Rescue plan out of sync with findings for company {company_id}; plan has progress, not regenerated')
            if not existing_plan:
                try:
                    await rescue_svc.generate_rescue_plan(
                        company_id=company_id,
                        engine_output=output,
                        created_by=getattr(self, '_current_user_id', None),
                        engagement_id=None,  # RES-010: explicit linkage, populated by service
                    )
                except ValueError as e:
                    # Engine produced actionable RED/BLACK flags but no rescue
                    # sequence — data-integrity issue, not transient. Persist
                    # the failure so ops/dashboard can see it.
                    actionable = [
                        (f.rule_id, str(f.severity))
                        for f in output.flags
                        if not f.resolved and str(f.severity) in ('BLACK', 'RED')
                    ]
                    logger.error(
                        "rescue_plan_value_error company=%s reason=%s actionable_flags=%s",
                        company_id, e, actionable,
                    )
                    company_svc_update['rescue_generation_error'] = str(e)[:500]
                except Exception as e:
                    logger.error(
                        "rescue_plan_unexpected_error company=%s error=%s",
                        company_id, e, exc_info=True,
                    )
                    company_svc_update['rescue_generation_error'] = f'unexpected: {e}'[:500]

        await self.db.execute(
            update(Company)
            .where(Company.id == company_id)
            .values(**company_svc_update)
        )
        await self.db.flush()

        # ── Queue notifications for new RED/BLACK flags ─────────
        notification_flags = [
            flag for flag in collected_new_flags
            if legal_score_is_released() and flag.rule_id in PRODUCT_SCORING_RULE_IDS
        ]
        if notification_flags:
            notif_svc = NotificationService(self.db)
            await notif_svc.queue_for_new_flags(company_id, notification_flags)

    # ── Flag Management ───────────────────────────────────────────

    async def get_active_flags(self, company_id: uuid.UUID) -> list[ComplianceFlag]:
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

    async def get_flag_summary(self, company_id: uuid.UUID) -> dict:
        """
        Return the existing view metadata plus canonical active-flag counts.
        Severity counts are calculated from active ORM flags, not inferred
        from risk-band or score values.
        """
        from app.models.enums import FlagStatus

        result = await self.db.execute(
            text(
                "SELECT * FROM vw_company_flag_summary WHERE company_id = :cid"
            ),
            {"cid": str(company_id)},
        )
        row = result.mappings().one_or_none()
        summary = dict(row) if row else {}

        flags_result = await self.db.execute(
            select(ComplianceFlag.rule_id, ComplianceFlag.severity).where(
                ComplianceFlag.company_id == company_id,
                ComplianceFlag.flag_status == FlagStatus.ACTIVE,
            )
        )
        rows = flags_result.all()
        from app.rule_engine.engine import PRODUCT_SCORING_RULE_IDS, legal_score_is_released
        verified_severities = [
            str(getattr(severity, "value", severity)).upper()
            for rule_id, severity in rows
            if legal_score_is_released() and rule_id in PRODUCT_SCORING_RULE_IDS
        ]
        black_count = verified_severities.count("BLACK")
        red_count = verified_severities.count("RED")
        yellow_count = verified_severities.count("YELLOW")
        pending_review_count = len(rows) - len(verified_severities)
        summary.update({
            # Customer-facing active counts include only rules approved for release.
            # Unapproved engine flags remain separately visible as review prompts.
            "total_active": len(verified_severities),
            "total_active_flags": len(verified_severities),
            "pending_review": pending_review_count,
            "pending_review_flags": pending_review_count,
            "black": black_count,
            "red": red_count,
            "yellow": yellow_count,
            "black_flags": black_count,
            "red_flags": red_count,
            "yellow_flags": yellow_count,
            "not_evaluated": pending_review_count,
        })
        return summary

    async def resolve_flag(
        self,
        flag_id: uuid.UUID,
        resolved_by: uuid.UUID,
        resolution_notes: str,
    ) -> ComplianceFlag | None:
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
    ) -> ComplianceFlag | None:
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
    ) -> list[dict]:
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
        from app.rule_engine.engine import legal_score_is_released
        history = []
        for row in rows:
            stored_band = getattr(row.risk_band, "value", row.risk_band)
            released = legal_score_is_released() and stored_band != "NOT_EVALUATED"
            history.append({
                "month": row.snapshot_month.isoformat(),
                "score": row.score if released else None,
                "risk_band": row.risk_band if released else "NOT_EVALUATED",
                "agm_score": row.agm_score if released else None,
                "audit_score": row.audit_score if released else None,
                "return_score": row.return_score if released else None,
                "director_score": row.director_score if released else None,
                "shareholding_score": row.shareholding_score if released else None,
                "active_flags": row.active_flags_count,
                "black_flags": row.black_flags_count if released else 0,
                "override": row.override_applied if released else False,
                "calculated_at": row.calculated_at.isoformat(),
            })
        return history


    async def get_compliance_calendar(
        self,
        company_id: uuid.UUID,
        days_ahead: int = 90,
        include_past_days: int = 30,
    ) -> list[dict]:
        from app.services.compliance_calendar import ComplianceCalendarService
        cal = ComplianceCalendarService(self.db)
        return await cal.get_calendar(  # type: ignore
            company_id,
            include_past_days=include_past_days,
            include_future_days=days_ahead,
        )

    async def get_dashboard_kpis(self, user_id=None) -> dict:
        """Return legal risk KPIs only after release; otherwise return evidence-review metrics.

        The unreleased path deliberately does not read or aggregate current_risk_band.
        Evaluation-state counts are operational review signals, not legal findings.
        """
        from app.rule_engine.engine import legal_score_is_released

        if not legal_score_is_released():
            scope = " AND assigned_staff_id = CAST(:uid AS uuid)" if user_id else ""
            params = {"uid": str(user_id)} if user_id else {}

            total_result = await self.db.execute(
                text(
                    "SELECT COUNT(*) FROM companies "
                    "WHERE is_active = true" + scope
                ),
                params,
            )
            total_companies = int(total_result.scalar_one() or 0)

            review_result = await self.db.execute(
                text(
                    """
                    SELECT
                        cf.evaluation_state,
                        COUNT(*)::integer AS item_count
                    FROM companies AS c
                    JOIN compliance_flags AS cf
                      ON cf.company_id = c.id
                     AND cf.flag_status = 'ACTIVE'
                    WHERE c.is_active = true
                    """
                    + (" AND c.assigned_staff_id = CAST(:uid AS uuid)" if user_id else "")
                    + """
                    GROUP BY cf.evaluation_state
                    ORDER BY cf.evaluation_state
                    """
                ),
                params,
            )
            rows = review_result.mappings().all()
            state_counts = {
                str(row["evaluation_state"]): int(row["item_count"] or 0)
                for row in rows
            }
            active_review_items = sum(state_counts.values())
            company_result = await self.db.execute(
                text(
                    """
                    SELECT COUNT(DISTINCT c.id)::integer
                    FROM companies AS c
                    JOIN compliance_flags AS cf
                      ON cf.company_id = c.id
                     AND cf.flag_status = 'ACTIVE'
                    WHERE c.is_active = true
                    """
                    + (" AND c.assigned_staff_id = CAST(:uid AS uuid)" if user_id else "")
                ),
                params,
            )
            companies_with_review_items = int(company_result.scalar_one() or 0)

            return {
                "dashboard_mode": "EVIDENCE_REVIEW",
                "statutory_score_release_status": "NOT_RELEASED",
                "statutory_risk_aggregates_available": False,
                "total_companies": total_companies,
                "green_count": None,
                "yellow_count": None,
                "red_black_count": None,
                "not_evaluated_count": total_companies,
                "companies_with_review_items": companies_with_review_items,
                "active_review_items": active_review_items,
                "evaluation_state_counts": state_counts,
                "upcoming_deadlines": None,
            }

        # Released statutory risk aggregates are available only on the approved path.
        if user_id:
            query = text("""
                SELECT
                    COUNT(*) as total_companies,
                    COUNT(*) FILTER (WHERE current_risk_band = 'GREEN') as green_count,
                    COUNT(*) FILTER (WHERE current_risk_band = 'YELLOW') as yellow_count,
                    COUNT(*) FILTER (WHERE current_risk_band IN ('RED', 'BLACK')) as red_black_count,
                    COUNT(*) FILTER (WHERE current_risk_band = 'NOT_EVALUATED') as not_evaluated_count,
                    0 as upcoming_deadlines
                FROM companies
                WHERE assigned_staff_id = :uid AND is_active = true
            """)
            result = await self.db.execute(query, {"uid": str(user_id)})
        else:
            query = text("""
                SELECT
                    COUNT(*) as total_companies,
                    COUNT(*) FILTER (WHERE current_risk_band = 'GREEN') as green_count,
                    COUNT(*) FILTER (WHERE current_risk_band = 'YELLOW') as yellow_count,
                    COUNT(*) FILTER (WHERE current_risk_band IN ('RED', 'BLACK')) as red_black_count,
                    COUNT(*) FILTER (
                        WHERE current_risk_band = 'NOT_EVALUATED'
                           OR current_risk_band IS NULL
                    ) as not_evaluated_count,
                    0 as upcoming_deadlines
                FROM companies
                WHERE is_active = true
            """)
            result = await self.db.execute(query)
        row = result.mappings().one_or_none()
        result_dict = dict(row) if row else {}
        result_dict.update({
            "dashboard_mode": "STATUTORY_RISK",
            "statutory_score_release_status": "RELEASED",
            "statutory_risk_aggregates_available": True,
        })
        return result_dict
