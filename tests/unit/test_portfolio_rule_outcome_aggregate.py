from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.api.portfolio_compliance import (
    RuleOutcomeAggregateRequest,
    aggregate_rule_outcomes,
)
from app.compliance.evaluation_integrity import calculate_evaluation_score_hash
from app.compliance.rule_outcome_ledger import hash_rule_outcomes_snapshot
from app.rule_engine.engine import RULE_ENGINE_VERSION
from canonical_architecture.scoring_spec import SCORING_SPEC_VERSION


class _Result:
    def __init__(self, rows=None, scalar=None):
        self._rows = rows or []
        self._scalar = scalar

    def scalars(self):
        return self

    def all(self):
        return self._rows

    def scalar_one_or_none(self):
        return self._scalar


class _PortfolioDB:
    def __init__(self, runs, companies, active_rule_ids):
        self.runs = runs
        self.companies = companies
        self.active_rule_ids = active_rule_ids
        self.current_run = None
        self.execute_count = 0

    async def execute(self, _statement):
        self.execute_count += 1
        if self.execute_count == 1:
            return _Result(rows=self.runs)
        if self.execute_count == 2:
            return _Result(rows=self.active_rule_ids)
        return _Result(scalar=self.current_run.id)

    async def get(self, model, entity_id):
        company = self.companies[entity_id]
        self.current_run = next(run for run in self.runs if run.company_id == entity_id)
        return company


def _portfolio_fixture(company_count=23, rule_count=85):
    rule_ids = [f"RULE-{index:03d}" for index in range(rule_count)]
    runs = []
    companies = {}
    calculated_at = datetime(2026, 11, 13, tzinfo=timezone.utc)

    for _ in range(company_count):
        company_id = uuid4()
        run_id = uuid4()
        snapshot = [
            {
                "rule_id": rule_id,
                "rule_version": "2.2",
                "verification_status": "PENDING",
                "outcome_state": "NOT_EVALUATED",
                "assessment_source": "NO_FINDING_EMITTED_NOT_PROOF_OF_COMPLIANCE",
                "findings": [],
            }
            for rule_id in rule_ids
        ]
        # An orphan finding is retained for audit, but is not a catalogue row.
        snapshot.append({
            "rule_id": "ORPHAN-999",
            "rule_version": None,
            "verification_status": "UNMAPPED",
            "outcome_state": "UNKNOWN",
            "assessment_source": "ENGINE_FINDING_WITHOUT_ACTIVE_CATALOGUE_RULE",
            "findings": [{"outcome_state": "UNKNOWN"}],
        })
        run = SimpleNamespace(
            id=run_id,
            company_id=company_id,
            evaluation_status="COMPLETED",
            previous_hash=None,
            trigger_source="UNIT_TEST",
            flags_snapshot=[],
            fact_provenance_snapshot=[],
            rule_outcomes_snapshot=snapshot,
            rule_catalogue_count=rule_count,
            rule_outcomes_hash=hash_rule_outcomes_snapshot(snapshot),
            score_hash="",
            engine_version=RULE_ENGINE_VERSION,
            scoring_spec_version=SCORING_SPEC_VERSION,
            score=77,
            risk_band="GREEN",
            calculated_at=calculated_at,
            score_breakdown_snapshot={
                "scoring_spec_version": SCORING_SPEC_VERSION,
                "score_reconciles": True,
                "final_score": 77,
            },
        )
        run.score_hash = calculate_evaluation_score_hash(
            previous_hash=run.previous_hash,
            company_id=run.company_id,
            score=run.score,
            risk_band=run.risk_band,
            calculated_at=run.calculated_at,
            engine_version=run.engine_version,
            trigger_source=run.trigger_source,
            flags_snapshot=run.flags_snapshot,
            fact_provenance_snapshot=run.fact_provenance_snapshot,
            score_breakdown_snapshot=run.score_breakdown_snapshot,
            rule_outcomes_hash=run.rule_outcomes_hash,
            rule_outcomes_snapshot=run.rule_outcomes_snapshot,
        )
        company = SimpleNamespace(
            id=company_id,
            company_name=f"Company {len(companies) + 1}",
            current_compliance_score=77,
            current_risk_band="GREEN",
            last_evaluated_at=calculated_at,
        )
        runs.append(run)
        companies[company_id] = company

    return runs, companies, rule_ids


@pytest.mark.asyncio
async def test_23_company_aggregate_counts_85_catalogue_rows_and_separates_unmapped():
    runs, companies, rule_ids = _portfolio_fixture()
    db = _PortfolioDB(runs, companies, rule_ids)

    result = await aggregate_rule_outcomes(
        RuleOutcomeAggregateRequest(run_ids=[run.id for run in runs]),
        db,
    )

    assert result["requested_runs"] == 23
    assert result["validated_runs"] == 23
    assert result["rejected_runs"] == 0
    assert result["active_catalogue_rule_count"] == 85
    assert result["validated_rule_company_rows"] == 1_955
    assert result["expected_rule_company_rows"] == 1_955
    assert result["potential_rule_company_rows"] == 1_955
    assert result["portfolio_reconciles"] is True
    assert result["aggregate_counts"] == {"NOT_EVALUATED": 1_955}
    assert result["unmapped_rule_id_rows"] == 23
    assert result["unmapped_engine_outcome_counts"] == {"UNKNOWN": 23}
    assert all(item["rule_catalogue_count"] == 85 for item in result["results"])


@pytest.mark.asyncio
async def test_aggregate_rejects_run_with_catalogue_id_set_mismatch():
    runs, companies, rule_ids = _portfolio_fixture(company_count=1)
    runs[0].rule_outcomes_snapshot[0]["rule_id"] = "WRONG-RULE"
    runs[0].rule_outcomes_hash = hash_rule_outcomes_snapshot(runs[0].rule_outcomes_snapshot)
    db = _PortfolioDB(runs, companies, rule_ids)

    result = await aggregate_rule_outcomes(
        RuleOutcomeAggregateRequest(run_ids=[runs[0].id]),
        db,
    )

    assert result["validated_runs"] == 0
    assert result["rejected_runs"] == 1
    assert result["validated_rule_company_rows"] == 0
    assert result["portfolio_reconciles"] is False
    assert "ACTIVE_CATALOGUE_ID_SET_MISMATCH" in result["results"][0]["problems"]
