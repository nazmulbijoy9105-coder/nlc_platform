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
from fastapi.encoders import jsonable_encoder
from dataclasses import fields as dataclass_fields
from datetime import UTC, datetime

from sqlalchemy import select, text, update

from app.models.company import Company
from app.models.compliance import ComplianceEvaluationRun, ComplianceFlag, ComplianceScoreHistory
from app.models.company_fact import CompanyFact
from app.compliance.fact_provenance import (
    business_date_today,
    fact_freshness_max_age_days,
    fact_freshness_status,
    is_internal_profile_fact_key,
    verified_document_fact_keys,
)
from app.models.rules import LegalRule
from app.compliance.fact_provenance import coerce_company_profile_fact_value
from app.compliance.outcome_status import derive_compliance_outcome
from app.compliance.evaluation_integrity import calculate_evaluation_score_hash
from app.models.enums import (
    ExposureBand,
    FlagStatus,
    RevenueTier,
    RiskBand,
    SeverityLevel,
)
from app.services.base import BaseService
from app.services.notification_service import NotificationService

from canonical_architecture.scoring_spec import allocate_flag_deductions, category_for_rule, duplicate_event_indices, SCORING_SPEC_VERSION

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


def _has_unresolved_catalogue_binding(flag) -> bool:
    """True when a finding has no valid active catalogue binding."""
    detail = getattr(flag, "detail", None)
    return (
        isinstance(detail, dict)
        and detail.get("rule_catalogue_binding") in {
            "CATALOGUE_ENTRY_MISSING",
            "RULE_INACTIVE",
            "STATUTORY_BASIS_MISMATCH",
        }
    )


def _persistable_output_flags(flags):
    """Never overwrite a legacy catalogue finding with a mismatched engine identity."""
    return [flag for flag in flags if not _has_unresolved_catalogue_binding(flag)]


def _active_catalogue_rule_ids(catalogue_rows, identity_mismatch_rule_ids):
    """Return active IDs only where the current engine did not detect identity drift."""
    return [
        row.rule_id
        for row in catalogue_rows
        if bool(row.is_active) and row.rule_id not in identity_mismatch_rule_ids
    ]


def _normalise_statutory_basis(value) -> str | None:
    """Use the same conservative normalization as the engine catalogue binder."""
    translation = str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"'})
    normalized = " ".join(str(value or "").translate(translation).split()).casefold()
    return normalized or None


def _catalogue_identity_conflicts(catalogue_rows) -> dict[str, dict]:
    """Compare the complete DB snapshot with every canonical evaluator identity."""
    from canonical_architecture.statutory_rules import STATUTORY_RULE_REGISTRY

    rows_by_id = {row.rule_id: row for row in catalogue_rows}
    conflicts: dict[str, dict] = {}
    for rule_id, canonical_rule in STATUTORY_RULE_REGISTRY.items():
        row = rows_by_id.get(rule_id)
        engine_basis = getattr(canonical_rule, "law", None)
        if row is None:
            reason = "CATALOGUE_ENTRY_MISSING"
            catalogue_basis = None
        elif row.is_active is not True:
            reason = "RULE_INACTIVE"
            catalogue_basis = row.statutory_basis
        elif _normalise_statutory_basis(engine_basis) != _normalise_statutory_basis(row.statutory_basis):
            reason = "STATUTORY_BASIS_MISMATCH"
            catalogue_basis = row.statutory_basis
        else:
            continue
        conflicts[rule_id] = {
            "rule_id": rule_id,
            "resolution_status": "UNRESOLVED_STATUTORY_IDENTITY_MISMATCH",
            "binding_reason": reason,
            "engine_statutory_basis": engine_basis,
            "catalogue_statutory_basis": catalogue_basis,
            "catalogue_rule_version": getattr(row, "rule_version", None) if row else None,
            "catalogue_is_active": bool(row.is_active) if row else False,
        }

    for rule_id, row in rows_by_id.items():
        if rule_id not in STATUTORY_RULE_REGISTRY:
            conflicts[rule_id] = {
                "rule_id": rule_id,
                "resolution_status": "UNRESOLVED_STATUTORY_IDENTITY_MISMATCH",
                "binding_reason": (
                    "RULE_INACTIVE" if row.is_active is not True
                    else "ENGINE_RULE_DEFINITION_MISSING"
                ),
                "engine_statutory_basis": None,
                "catalogue_statutory_basis": row.statutory_basis,
                "catalogue_rule_version": row.rule_version,
                "catalogue_is_active": bool(row.is_active),
            }
    return conflicts


def _quarantine_catalogue_conflict_findings(flags, catalogue_identity_conflicts):
    """Make every finding for a conflicted ID non-scoring and non-actionable."""
    from canonical_architecture.statutory_rules import STATUTORY_RULE_REGISTRY
    from app.rule_engine.engine import RuleState, Severity

    for flag in flags:
        if flag.rule_id not in STATUTORY_RULE_REGISTRY:
            catalogue_identity_conflicts.setdefault(flag.rule_id, {
                "rule_id": flag.rule_id,
                "resolution_status": "UNRESOLVED_STATUTORY_IDENTITY_MISMATCH",
                "binding_reason": "ENGINE_RULE_DEFINITION_MISSING",
                "engine_statutory_basis": getattr(flag, "statutory_basis", None),
                "catalogue_statutory_basis": None,
                "catalogue_rule_version": None,
                "catalogue_is_active": False,
            })
        detail = dict(getattr(flag, "detail", None) or {})
        binding_reason = detail.get("rule_catalogue_binding")
        if (
            not catalogue_identity_conflicts.get(flag.rule_id)
            and binding_reason in {
                "CATALOGUE_ENTRY_MISSING",
                "RULE_INACTIVE",
                "STATUTORY_BASIS_MISMATCH",
            }
        ):
            catalogue_identity_conflicts[flag.rule_id] = {
                "rule_id": flag.rule_id,
                "resolution_status": "UNRESOLVED_STATUTORY_IDENTITY_MISMATCH",
                "binding_reason": binding_reason,
                "engine_statutory_basis": detail.get(
                    "engine_flag_statutory_basis",
                    getattr(flag, "statutory_basis", None),
                ),
                "catalogue_statutory_basis": detail.get(
                    "catalogue_rule_statutory_basis"
                ),
                "catalogue_rule_version": getattr(flag, "rule_version", None),
                "catalogue_is_active": binding_reason != "RULE_INACTIVE",
            }
        conflict = catalogue_identity_conflicts.get(flag.rule_id)
        if not conflict:
            continue
        detail["rule_catalogue_binding"] = conflict["binding_reason"]
        detail["engine_flag_statutory_basis"] = getattr(flag, "statutory_basis", None)
        detail["catalogue_rule_statutory_basis"] = conflict.get("catalogue_statutory_basis")
        flag.detail = detail
        flag.severity = Severity.NOT_EVALUATED
        flag.score_impact = 0
        flag.state = RuleState.UNKNOWN
        flag.eval_state = "UNKNOWN"
        flag.is_black_override = False
        flag.conditional_applies = False
        flag.applicability_state = "UNKNOWN"
        flag.applicability_reason = (
            "Catalogue/evaluator identity conflict; this finding is quarantined "
            "and cannot support applicability, scoring or rescue."
        )


def _applied_score_impacts(flags) -> list[dict]:
    """Reconcile every finding to the same versioned score allocation as the engine.

    Returned entries remain aligned to the original flags. Only confirmed,
    active, product-eligible findings enter the allocation; per-category caps
    and the global 100-point budget are both applied by scoring_spec.
    """
    from app.rule_engine.engine import (
        AUTHORIZED_BLACK_OVERRIDE_RULE_IDS,
        PRODUCT_SCORING_RULE_IDS,
        SCORE_DEDUCTION_RULE_IDS,
        RuleState,
        legal_score_is_released,
    )

    results: list[dict] = [{} for _ in flags]
    eligible: list[tuple[int, str, int, str | None]] = []
    for index, flag in enumerate(flags):
        state = getattr(flag, "state", None)
        active = not getattr(flag, "resolved", False) and getattr(flag, "conditional_applies", True)
        if not active:
            results[index] = {"applied": 0, "status": "INACTIVE"}
            continue
        confirmed_violation = (
            state in (RuleState.NON_COMPLIANT, RuleState.VERIFIED_ABSENT)
            and getattr(flag, "eval_state", "VIOLATION") == "VIOLATION"
        )
        if not confirmed_violation:
            results[index] = {"applied": 0, "status": "NOT_A_CONFIRMED_VIOLATION"}
            continue
        if not PRODUCT_SCORING_RULE_IDS:
            results[index] = {"applied": 0, "status": "LEGAL_SCORE_NOT_RELEASED"}
            continue
        # Match NLCRuleEngine._eligible_scoring_flags exactly. The engine's
        # deterministic deduction catalogue is SCORE_DEDUCTION_RULE_IDS;
        # PRODUCT_SCORING_RULE_IDS controls public catalogue visibility, not
        # whether an already-scored finding is allocated in the audit ledger.
        if flag.rule_id not in SCORE_DEDUCTION_RULE_IDS:
            results[index] = {"applied": 0, "status": "EXCLUDED_FROM_PRODUCT_SCORING"}
            continue
        if not legal_score_is_released():
            results[index] = {"applied": 0, "status": "LEGAL_SCORE_NOT_RELEASED"}
            continue
        severity_value = getattr(
            getattr(flag, "severity", None),
            "value",
            getattr(flag, "severity", None),
        )
        authorised_black_override = (
            flag.rule_id in AUTHORIZED_BLACK_OVERRIDE_RULE_IDS
            and getattr(flag, "is_black_override", False) is True
            and severity_value == "BLACK"
        )
        if authorised_black_override:
            results[index] = {"applied": 0, "status": "BLACK_OVERRIDE_APPLIED"}
            continue

        if category_for_rule(flag.rule_id) is None:
            results[index] = {"applied": 0, "status": "NO_SCORING_CATEGORY"}
            continue
        detail = getattr(flag, "detail", None)
        scoring_event_key = (
            detail.get("scoring_event_key") if isinstance(detail, dict) else None
        )
        eligible.append((
            index,
            flag.rule_id,
            max(0, int(flag.score_impact or 0)),
            scoring_event_key,
        ))

    allocation_items = [
        (rule_id, impact, event_key)
        for _, rule_id, impact, event_key in eligible
    ]
    allocations = allocate_flag_deductions(allocation_items)
    duplicate_indices = duplicate_event_indices(allocation_items)
    for local_index, ((index, _, _, _), applied) in enumerate(zip(eligible, allocations)):
        results[index] = {
            "applied": applied,
            "status": (
                "DUPLICATE_EVENT_SUPPRESSED"
                if local_index in duplicate_indices
                else "APPLIED" if applied else "CATEGORY_CAP_REACHED"
            ),
        }
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
            PRODUCT_SCORING_RULE_IDS,
            VERIFIED_RULE_IDS,
            RuleState,
            Severity,
            legal_score_is_released,
        )
        from app.services.company_service import CompanyService

        # ── Step 1: Build profile ──────────────────────────────────
        company_svc = CompanyService(self.db)
        profile_data = await company_svc.build_company_profile(company_id)
        if not profile_data:
            raise ValueError(f"Company {company_id} not found or inactive.")

        # Current versioned facts override same-key legacy profile values. Every
        # evaluation and finding receives the exact explicit fact inputs plus
        # a disclosure/value snapshot for legacy profile inputs without provenance.
        fact_result = await self.db.execute(
            select(CompanyFact).where(
                CompanyFact.company_id == company_id,
            ).order_by(CompanyFact.fact_key.asc(), CompanyFact.created_at.desc(), CompanyFact.id.desc())
        )
        latest_facts: dict[str, CompanyFact] = {}
        for fact in fact_result.scalars().all():
            latest_facts.setdefault(fact.fact_key, fact)
        current_facts = [
            fact for fact in latest_facts.values()
            if fact.verification_status not in {"REJECTED", "SUPERSEDED"}
        ]
        used_facts = []
        profile_field_names = {
            field.name
            for field in dataclass_fields(CompanyProfile)
            if not is_internal_profile_fact_key(field.name)
        } - {"company_id", "company_name"}
        for fact in current_facts:
            if fact.fact_key in profile_field_names:
                profile_data[fact.fact_key] = coerce_company_profile_fact_value(fact.fact_key, fact.fact_value)
                used_facts.append(fact)
        evaluation_date = getattr(rule_engine, "today", business_date_today())
        fact_provenance_snapshot = []
        for fact in used_facts:
            payload = fact.provenance_payload()
            payload["freshness_status"] = fact_freshness_status(
                fact.fact_key, fact.observed_on, evaluation_date
            )
            payload["freshness_max_age_days"] = fact_freshness_max_age_days(
                fact.fact_key
            )
            fact_provenance_snapshot.append(payload)
        normalized_profile_data = _company_profile_kwargs(profile_data, CompanyProfile)
        untracked_profile_fields = sorted(
            set(normalized_profile_data)
            - {fact.fact_key for fact in used_facts}
            - {"company_id", "company_name"}
        )
        if untracked_profile_fields:
            fact_provenance_snapshot.append({
                "record_type": "UNATTRIBUTED_PROFILE_FIELDS",
                "fields": untracked_profile_fields,
                "field_values": jsonable_encoder({
                    key: normalized_profile_data[key] for key in untracked_profile_fields
                }),
                "disclosure": (
                    "Some legacy company-profile inputs have no explicit source record. "
                    "Their origin and verification status are unknown; do not treat them as verified."
                ),
            })

        # Convert dict to CompanyProfile dataclass
        try:
            profile = CompanyProfile(**normalized_profile_data)
        except TypeError as exc:
            raise ValueError(f"CompanyProfile assembly failed: {exc}") from exc

        # Only independently verified, authorized document-backed facts can
        # authorize negative findings from legacy profile booleans. User
        # assertions and unattributed company-table defaults remain unknown.
        profile.verified_fact_keys = verified_document_fact_keys(
            used_facts, as_of=evaluation_date
        )
        profile.verified_fact_context = {
            fact.fact_key: {
                "document_id": str(fact.document_id) if fact.document_id else None,
                "source_reference": fact.source_reference,
            }
            for fact in used_facts
            if fact.fact_key in profile.verified_fact_keys
        }

        # Bind the evaluator to the exact active/inactive catalogue snapshot
        # used for this run. Engine logic remains deployed Python; DB metadata
        # cannot rewrite evaluator code. A missing/inactive row is fail-closed.
        catalogue_rows = list((
            await self.db.execute(
                select(LegalRule).order_by(LegalRule.rule_id)
            )
        ).scalars().all())
        catalogue_identity_conflicts = _catalogue_identity_conflicts(catalogue_rows)
        profile.catalogue_binding_required = True
        profile.catalogue_rule_versions = {
            row.rule_id: row.rule_version for row in catalogue_rows
        }
        profile.catalogue_rule_active = {
            row.rule_id: bool(row.is_active) for row in catalogue_rows
        }
        profile.catalogue_rule_bases = {
            row.rule_id: row.statutory_basis for row in catalogue_rows
        }
        # Rescue-plan and ordinary evaluation paths consume the same immutable
        # binding object; no alternate profile may silently run unbound.
        profile.catalogue_identity_conflicts = catalogue_identity_conflicts
        catalogue_binding = {
            "record_type": "LEGAL_RULE_CATALOGUE_SNAPSHOT",
            "rules": [
                {
                    "rule_id": row.rule_id,
                    "rule_version": row.rule_version,
                    "is_active": bool(row.is_active),
                    "statutory_basis": row.statutory_basis,
                    "verification_status": row.verification_status,
                }
                for row in catalogue_rows
            ],
            "identity_conflicts": [
                catalogue_identity_conflicts[rule_id]
                for rule_id in sorted(catalogue_identity_conflicts)
            ],
            "disclosure": (
                "This snapshot binds finding metadata and activation to the "
                "database catalogue. It does not prove statutory correctness "
                "or independent counsel approval."
            ),
        }
        fact_provenance_snapshot.append(catalogue_binding)

        # Prepare verified fact inputs before evaluation. Applicability is built
        # after engine evaluation so an identity collision can be excluded from
        # the canonical active-rule set before any applicability is attributed.
        verified_fact_records = {}
        for fact in current_facts:
            fact_record = fact.to_fact_record()
            if fact_record.is_verified_document_fact():
                verified_fact_records[fact.fact_key] = fact_record

        # ── Step 2: Run rule engine ────────────────────────────────
        # Explicit injection supports deterministic tests and controlled
        # evaluation runs. Production callers retain the canonical engine.
        engine = rule_engine if rule_engine is not None else get_rule_engine()
        output = engine.evaluate(profile)

        # Catalogue identity conflicts remain authoritative even when no finding is emitted.
        _quarantine_catalogue_conflict_findings(
            output.flags, catalogue_identity_conflicts
        )
        profile.catalogue_identity_conflicts = catalogue_identity_conflicts
        for provenance_record in fact_provenance_snapshot:
            if provenance_record.get("record_type") == "LEGAL_RULE_CATALOGUE_SNAPSHOT":
                provenance_record["identity_conflicts"] = [
                    catalogue_identity_conflicts[rule_id]
                    for rule_id in sorted(catalogue_identity_conflicts)
                ]

        from app.compliance.rule_applicability import build_rule_applicability_results

        identity_mismatch_rule_ids = set(catalogue_identity_conflicts) | {
            flag.rule_id for flag in output.flags
            if _has_unresolved_catalogue_binding(flag)
        }
        active_rule_ids = _active_catalogue_rule_ids(
            catalogue_rows, identity_mismatch_rule_ids
        )
        applicability_results = build_rule_applicability_results(
            active_rule_ids, verified_fact_records
        )
        applicability_fact_ids = {
            evidence.get("fact_id")
            for result in applicability_results.values()
            for evidence in result.get("fact_evidence", [])
            if evidence.get("fact_id")
        }
        already_snapshotted_fact_ids = {str(fact.id) for fact in used_facts}
        for fact in current_facts:
            if (
                str(fact.id) in applicability_fact_ids
                and str(fact.id) not in already_snapshotted_fact_ids
            ):
                fact_provenance_snapshot.append(fact.provenance_payload())
        risk_band_value = getattr(
            output.score_breakdown.risk_band,
            "value",
            output.score_breakdown.risk_band,
        )
        score_is_released = (
            legal_score_is_released()
            and risk_band_value != "NOT_EVALUATED"
            and not identity_mismatch_rule_ids
        )
        public_risk_band = risk_band_value if score_is_released else "NOT_EVALUATED"
        api_score = output.score_breakdown.final_score if score_is_released else None
        api_raw_total = output.score_breakdown.raw_total if score_is_released else None

        # ── Step 3: Persist results ────────────────────────────────
        evaluation_run = await self._persist_evaluation(
            company_id, output, trigger_source,
            fact_provenance_snapshot=fact_provenance_snapshot,
            applicability_results=applicability_results,
            catalogue_snapshot=catalogue_rows,
            catalogue_identity_conflicts=catalogue_identity_conflicts,
        )

        logger.info(
            f"[Compliance] Evaluated company={company_id} | "
            f"Score={api_score if score_is_released else 'NOT_RELEASED'} | "
            f"Band={public_risk_band} | "
            f"Flags={len(output.flags)} | Trigger={trigger_source}"
        )

        applied_impacts = _applied_score_impacts(output.flags)
        applied_total = sum(item["applied"] for item in applied_impacts)
        category_deductions = dict(output.score_breakdown.category_deductions or {})
        category_total = sum(category_deductions.values())
        if score_is_released and category_total != applied_total:
            raise ValueError(
                "Scoring reconciliation failed: per-finding applied deductions "
                f"({applied_total}) do not match category deductions ({category_total})."
            )
        override_adjustment = (
            max(0, 100 - category_total - int(api_score or 0))
            if score_is_released else None
        )
        score_reconciliation = {
            "scoring_spec_version": SCORING_SPEC_VERSION,
            "base_score": 100 if score_is_released else None,
            "category_deductions": category_deductions if score_is_released else None,
            "total_applied_category_deduction": category_total if score_is_released else None,
            "risk_policy_override_adjustment": override_adjustment,
            "final_score": api_score,
            "reconciles": (
                100 - category_total - int(override_adjustment or 0) == api_score
                if score_is_released else None
            ),
            "diagnostic_module_scores_are_additive": False,
        }

        return {
            "company_id":    str(company_id),
            "score":         api_score,
            "scoring_spec_version": SCORING_SPEC_VERSION,
            "score_reconciliation": score_reconciliation,
            "raw_total":     api_raw_total,
            "risk_band":     public_risk_band,
            "risk_band_semantics": "NLC_INTERNAL_RISK_CLASSIFICATION_NOT_LEGAL_LIABILITY",
            "exposure_band": output.score_breakdown.exposure_band if score_is_released else None,
            "legal_evaluation_status": (
                "RELEASED" if score_is_released
                else "NOT_EVALUATED_PRODUCT_SCORING_DISABLED"
            ),
            # Product-allowlisted findings are exposed as internal product-risk
            # signals. Counsel approval remains a separate field/status and is
            # never implied by product scoring release.
            "flags": [
                {
                    "rule_id": f.rule_id,
                    "severity": f.severity,
                    "risk_severity": f.severity,
                    "legal_state": getattr(f.state, "value", f.state),
                    "evaluation_state": getattr(f.eval_state, "value", f.eval_state),
                    "compliance_outcome": derive_compliance_outcome(
                        f, counsel_verified_rule=f.rule_id in VERIFIED_RULE_IDS
                    ),
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
                if score_is_released and f.rule_id in PRODUCT_SCORING_RULE_IDS and not _has_unresolved_catalogue_binding(f)
            ],
            "review_findings": [
                {
                    "rule_id": flag.rule_id,
                    "engine_state": getattr(flag.state, "value", flag.state),
                    "engine_evaluation_state": getattr(flag.eval_state, "value", flag.eval_state),
                    "compliance_outcome": derive_compliance_outcome(
                        flag, counsel_verified_rule=flag.rule_id in VERIFIED_RULE_IDS
                    ),
                    "review_status": applied_impacts[index]["status"],
                    "identity_binding_status": (
                        (getattr(flag, "detail", None) or {}).get("rule_catalogue_binding")
                        if _has_unresolved_catalogue_binding(flag)
                        else "MATCHED_CATALOGUE_IDENTITY"
                    ),
                    "message": (
                        "No statutory conclusion is issued. Evidence review is required. Product scoring "
                        "release is not independent legal verification, legal advice or certification."
                    ),
                    "score_impact_applied": 0,
                }
                for index, flag in enumerate(output.flags)
                if _has_unresolved_catalogue_binding(flag) or not (
                    score_is_released
                    and flag.rule_id in PRODUCT_SCORING_RULE_IDS
                )
            ],
            "excluded_rule_findings": [
                {
                    "rule_id": flag.rule_id,
                    "engine_state": getattr(flag.state, "value", flag.state),
                    "engine_evaluation_state": getattr(flag.eval_state, "value", flag.eval_state),
                    "compliance_outcome": derive_compliance_outcome(
                        flag, counsel_verified_rule=False  # Product eligibility is not counsel approval
                    ),
                    "risk_severity": "NOT_EVALUATED",
                    "description": "Internal review signal only. No legal conclusion, breach, liability or penalty is determined.",
                    "statutory_basis": "Independent legal/source verification pending; statutory basis not released.",
                    "score_impact_applied": 0,
                    "scoring_eligibility": "EXCLUDED_FROM_PRODUCT_SCORING",
                    "scoring_status": applied_impacts[index]["status"],
                }
                for index, flag in enumerate(output.flags)
                if score_is_released and flag.rule_id not in PRODUCT_SCORING_RULE_IDS and not _has_unresolved_catalogue_binding(flag)
            ],
            "score_breakdown": {
                "risk_band": public_risk_band,
                "scoring_spec_version": SCORING_SPEC_VERSION,
                "category_deductions": category_deductions if score_is_released else None,
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
            "evaluation_run_id": str(evaluation_run.id),
            "evaluation_hash": evaluation_run.score_hash,
            "evaluation_run_status": evaluation_run.evaluation_status,
            "evaluation_calculated_at": evaluation_run.calculated_at.isoformat(),
        }

    async def _persist_evaluation(
        self,
        company_id: uuid.UUID,
        output,  # EngineOutput from C_rule_engine.py
        trigger_source: str,
        fact_provenance_snapshot: list[dict] | None = None,
        applicability_results: dict[str, dict] | None = None,
        catalogue_snapshot: list[LegalRule] | None = None,
        catalogue_identity_conflicts: dict[str, dict] | None = None,
    ) -> ComplianceEvaluationRun:
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
        today = business_date_today()
        score = output.score_breakdown.final_score
        risk_band_value = getattr(output.score_breakdown.risk_band, 'value', output.score_breakdown.risk_band)
        risk_band = RiskBand(risk_band_value)
        if risk_band.value not in ("GREEN", "YELLOW", "RED", "BLACK", "NOT_EVALUATED"):
            # DB enum risk_band has no other values; derive from score instead of failing the UPDATE
            risk_band = RiskBand(
                "BLACK" if score <= 29 else "RED" if score <= 49 else "YELLOW" if score <= 69 else "GREEN"
            )
        # Defense in depth: persistence independently enforces the
        # product-controlled release switch; a provisional engine band cannot
        # publish a numeric score while product scoring is disabled.
        if not legal_score_is_released() or catalogue_identity_conflicts:
            risk_band = RiskBand.NOT_EVALUATED
        score_for_current = (
            score
            if (
                legal_score_is_released()
                and not catalogue_identity_conflicts
                and risk_band != RiskBand.NOT_EVALUATED
            )
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
        identity_mismatch_rule_ids = set(catalogue_identity_conflicts or {})
        persistable_flags = [
            flag for flag in _persistable_output_flags(output.flags)
            if flag.rule_id not in identity_mismatch_rule_ids
        ]
        current_rule_ids = {f.rule_id for f in persistable_flags}
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
        for flag in persistable_flags:

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
                    else "Independent legal/source verification pending; statutory basis not released."
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
                        else "Independent legal/source verification pending; statutory basis not released."
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
                active_flags_count=len(persistable_flags),
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
            .order_by(
                ComplianceEvaluationRun.calculated_at.desc(),
                ComplianceEvaluationRun.id.desc(),
            )
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
            "scoring_spec_version": SCORING_SPEC_VERSION,
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
            "total_applied_category_deduction": sum((sb.category_deductions or {}).values()),
            "risk_policy_override_adjustment": (
                max(0, 100 - sum((sb.category_deductions or {}).values()) - int(score_for_current))
                if sb.override_applied and score_for_current is not None else 0
            ),
            "score_reconciles": (
                100 - sum((sb.category_deductions or {}).values())
                - (
                    max(0, 100 - sum((sb.category_deductions or {}).values()) - int(score_for_current))
                    if score_for_current is not None else 0
                ) == score_for_current
                if score_for_current is not None else None
            ),
            "diagnostic_module_scores_are_additive": False,
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
            "diagnostic_module_score_semantics": "NON_ADDITIVE_DIAGNOSTICS_NOT_HEADLINE_SCORE_COMPONENTS",
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
        # Persist the active catalogue and each rule's emitted engine finding.
        # Rules with no emitted finding remain NOT_EVALUATED, never COMPLIANT.
        from app.compliance.rule_outcome_ledger import (
            build_rule_outcomes_snapshot,
            hash_rule_outcomes_snapshot,
        )

        # Persist against the exact catalogue rows used to bind the engine.
        # Never reload here: a concurrent catalogue edit must not rewrite this run.
        if catalogue_snapshot is None:
            catalogue_result = await self.db.execute(
                select(LegalRule).where(LegalRule.is_active.is_(True)).order_by(LegalRule.rule_id)
            )
            active_legal_rules = list(catalogue_result.scalars().all())
        else:
            active_legal_rules = [
                row for row in catalogue_snapshot if bool(row.is_active)
            ]
        rule_outcomes_snapshot = jsonable_encoder(
            build_rule_outcomes_snapshot(
                active_legal_rules,
                output.flags,
                applicability_results=applicability_results,
                catalogue_identity_conflicts=catalogue_identity_conflicts or {},
            )
        )
        rule_outcomes_hash = hash_rule_outcomes_snapshot(rule_outcomes_snapshot)

        evaluation_hash = calculate_evaluation_score_hash(
            previous_hash=previous_hash,
            company_id=company_id,
            score=score_for_current,
            risk_band=risk_band,
            calculated_at=now,
            engine_version=engine_version,
            trigger_source=trigger_source,
            flags_snapshot=flags_snapshot,
            fact_provenance_snapshot=fact_provenance_snapshot,
            score_breakdown_snapshot=score_breakdown_snapshot,
            rule_outcomes_hash=rule_outcomes_hash,
            rule_outcomes_snapshot=rule_outcomes_snapshot,
        )
        black_flags = (
            output.score_breakdown.black_flag_count
            if score_for_current is not None else 0
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
            rule_outcomes_snapshot=rule_outcomes_snapshot,
            rule_outcomes_hash=rule_outcomes_hash,
            rule_catalogue_count=len(active_legal_rules),
        )
        self.db.add(evaluation_run)

        # ── Update company compliance state ────────────────────────
        company_svc_update: dict = {
            "current_compliance_score": score_for_current,
            "current_risk_band":        risk_band,
            "rescue_required":          rescue_required,
            "last_evaluated_at":        now,
            # Keep the profile freshness marker exactly aligned with this run.
            # Any later company-profile update advances updated_at and makes
            # the cached score fail closed until a new evaluation completes.
            "updated_at":               now,
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
                    assigned_staff_result = await self.db.execute(
                        select(Company.assigned_staff_id).where(Company.id == company_id)
                    )
                    assigned_staff_id = assigned_staff_result.scalar_one_or_none()
                    await rescue_svc.generate_rescue_plan(
                        company_id=company_id,
                        engine_output=output,
                        assigned_staff_id=assigned_staff_id,
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

        return evaluation_run

    # ── Flag Management ───────────────────────────────────────────

    async def get_latest_evaluation_run(
        self, company_id: uuid.UUID
    ) -> ComplianceEvaluationRun | None:
        """Return the latest immutable evaluation run for this tenant company."""
        result = await self.db.execute(
            select(ComplianceEvaluationRun)
            .where(ComplianceEvaluationRun.company_id == company_id)
            .order_by(
                ComplianceEvaluationRun.calculated_at.desc(),
                ComplianceEvaluationRun.id.desc(),
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_latest_evaluation_runs(
        self, company_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, ComplianceEvaluationRun]:
        """Return one latest immutable evaluation run per requested company."""
        if not company_ids:
            return {}
        result = await self.db.execute(
            select(ComplianceEvaluationRun)
            .where(ComplianceEvaluationRun.company_id.in_(company_ids))
            .distinct(ComplianceEvaluationRun.company_id)
            .order_by(
                ComplianceEvaluationRun.company_id,
                ComplianceEvaluationRun.calculated_at.desc(),
                ComplianceEvaluationRun.id.desc(),
            )
        )
        return {
            row.company_id: row
            for row in result.scalars().all()
        }

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
        from app.rule_engine.engine import (
            PRODUCT_SCORING_RULE_IDS,
            VERIFIED_RULE_IDS,
            legal_score_is_released,
        )
        score_released = legal_score_is_released()
        product_severities = [
            str(getattr(severity, "value", severity)).upper()
            for rule_id, severity in rows
            if score_released and rule_id in PRODUCT_SCORING_RULE_IDS
        ]
        pending_review_count = sum(
            1 for rule_id, _severity in rows if rule_id not in VERIFIED_RULE_IDS
        )
        not_evaluated_count = sum(
            1 for rule_id, _ in rows
            if not score_released or rule_id not in PRODUCT_SCORING_RULE_IDS
        )
        black_count = product_severities.count("BLACK")
        red_count = product_severities.count("RED")
        yellow_count = product_severities.count("YELLOW")
        summary.update({
            # Product scoring and counsel review are independent dimensions.
            "total_active": len(product_severities),
            "total_active_flags": len(product_severities),
            "pending_review": pending_review_count,
            "pending_review_flags": pending_review_count,
            "black": black_count,
            "red": red_count,
            "yellow": yellow_count,
            "black_flags": black_count,
            "red_flags": red_count,
            "yellow_flags": yellow_count,
            "not_evaluated": not_evaluated_count,
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
        flag.resolved_date = business_date_today()
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
            run_status = str(getattr(row, "evaluation_status", "NOT_RELEASED") or "NOT_RELEASED")
            released = (
                legal_score_is_released()
                and run_status == "COMPLETED"
                and stored_band != "NOT_EVALUATED"
                and row.score is not None
            )
            history.append({
                "month": row.snapshot_month.isoformat(),
                "score": row.score if released else None,
                "risk_band": row.risk_band if released else "NOT_EVALUATED",
                "evaluation_status": run_status,
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
        """Return KPIs for the same authorised company scope as the company list.

        Legal staff may have access through either an explicit staff assignment
        or an active company_user_access membership. Keep this scope identical
        in evidence-review and released-risk modes.
        """
        from app.rule_engine.engine import (
            RULE_ENGINE_VERSION,
            SCORING_SPEC_VERSION,
            legal_score_is_released,
        )

        scope = ""
        params = {}
        if user_id:
            scope = """
                AND (
                    c.assigned_staff_id = CAST(:uid AS uuid)
                    OR EXISTS (
                        SELECT 1
                        FROM company_user_access AS cua
                        WHERE cua.company_id = c.id
                          AND cua.user_id = CAST(:uid AS uuid)
                          AND cua.is_active IS TRUE
                    )
                )
            """
            params = {"uid": str(user_id)}

        if not legal_score_is_released():
            total_result = await self.db.execute(
                text(
                    "SELECT COUNT(*) FROM companies AS c "
                    "WHERE c.is_active IS TRUE" + scope
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
                    WHERE c.is_active IS TRUE
                    """
                    + scope
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
                    WHERE c.is_active IS TRUE
                    """
                    + scope
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

        query = text(
            """
            WITH latest_run AS (
                SELECT DISTINCT ON (company_id)
                    company_id, evaluation_status, score, risk_band, calculated_at,
                    engine_version, score_breakdown_snapshot
                FROM compliance_evaluation_runs
                ORDER BY company_id, calculated_at DESC, id DESC
            ),
            current_company_state AS (
                SELECT
                    c.id,
                    CASE
                        WHEN lr.evaluation_status = 'COMPLETED'
                         AND lr.score IS NOT NULL
                         AND lr.risk_band <> 'NOT_EVALUATED'
                         AND lr.engine_version = :engine_version
                         AND lr.score_breakdown_snapshot ->> 'scoring_spec_version' = :scoring_spec_version
                         AND lr.score_breakdown_snapshot ->> 'score_reconciles' = 'true'
                         AND lr.score_breakdown_snapshot ->> 'final_score' = lr.score::text
                         AND c.last_evaluated_at = lr.calculated_at
                             AND c.updated_at <= c.last_evaluated_at
                         AND c.current_compliance_score = lr.score
                         AND c.current_risk_band = lr.risk_band
                        THEN lr.risk_band
                        ELSE 'NOT_EVALUATED'::risk_band
                    END AS risk_band
                FROM companies AS c
                LEFT JOIN latest_run AS lr ON lr.company_id = c.id
                WHERE c.is_active IS TRUE
                """
            + scope
            + """
            )
            SELECT
                COUNT(*) AS total_companies,
                COUNT(*) FILTER (WHERE risk_band = 'GREEN') AS green_count,
                COUNT(*) FILTER (WHERE risk_band = 'YELLOW') AS yellow_count,
                COUNT(*) FILTER (WHERE risk_band IN ('RED', 'BLACK')) AS red_black_count,
                COUNT(*) FILTER (WHERE risk_band = 'NOT_EVALUATED') AS not_evaluated_count,
                0 AS upcoming_deadlines
            FROM current_company_state
            """
        )
        released_params = {
            **params,
            "engine_version": RULE_ENGINE_VERSION,
            "scoring_spec_version": SCORING_SPEC_VERSION,
        }
        result = await self.db.execute(query, released_params)
        row = result.mappings().one_or_none()
        result_dict = dict(row) if row else {}
        result_dict.update({
            "dashboard_mode": "STATUTORY_RISK",
            "statutory_score_release_status": "RELEASED",
            "statutory_risk_aggregates_available": True,
        })
        return result_dict
