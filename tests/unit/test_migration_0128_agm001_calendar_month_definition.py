import copy
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
MIGRATION_PATH = ROOT / "alembic" / "versions" / "0128_agm001_calendar_month_definition.py"


def _load_migration():
    spec = importlib.util.spec_from_file_location("migration_0128_agm001_under_test", MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MIGRATION = _load_migration()


class _Result:
    def __init__(self, rows=(), rowcount=0, scalar=None):
        self.rows = list(rows)
        self.rowcount = rowcount
        self.scalar = scalar

    def mappings(self):
        return self

    def one_or_none(self):
        return self.rows[0] if self.rows else None

    def all(self):
        return list(self.rows)

    def scalar_one(self):
        return self.scalar


def _legacy_definition():
    return {
        "rule_name": "First AGM Default",
        "rule_type": "DEADLINE",
        "description": MIGRATION.LEGACY_DESCRIPTION,
        "rule_condition": copy.deepcopy(MIGRATION.LEGACY_CONDITION),
        "is_active": True,
    }


def _history_before_image():
    return {
        "rule_id": MIGRATION.RULE_ID,
        "statutory_basis": MIGRATION.LEGACY_BASIS,
        "rule_version": "1.1",
        **_legacy_definition(),
        **copy.deepcopy(MIGRATION.EXPECTED_LEGACY_ATTRIBUTES),
    }


def _current_row(**overrides):
    row = {
        "rule_id": MIGRATION.RULE_ID,
        "statutory_basis": MIGRATION.CANONICAL_BASIS,
        "rule_version": "1.2",
        **_legacy_definition(),
        "default_severity": "NOT_EVALUATED",
        "score_impact": 0,
        "revenue_tier": "STRUCTURED_REGULARIZATION",
        **copy.deepcopy(MIGRATION.EXPECTED_LEGACY_ATTRIBUTES),
    }
    row.update(overrides)
    return row


def _history_row(**overrides):
    row = {
        "version": "1.1",
        "change_reason": MIGRATION.PREVIOUS_CHANGE_REASON,
        "changed_by": None,
        "actor_type": "MIGRATION",
        "migration_revision": MIGRATION.PREVIOUS_REVISION,
        "previous_definition": _history_before_image(),
    }
    row.update(overrides)
    return row


class _Bind:
    def __init__(self, current=None, history=None, migration_count=0):
        self.current = copy.deepcopy(current if current is not None else _current_row())
        self.history = [copy.deepcopy(x) for x in (history if history is not None else [_history_row()])]
        self.migration_count = migration_count
        self.writes = []
        self.version_history = []

    def execute(self, statement, params=None):
        sql = " ".join(str(statement).split())
        params = params or {}
        if sql.startswith("SELECT to_jsonb(rule)"):
            return _Result([{"previous_definition": copy.deepcopy(self.current)}])
        if sql.startswith("SELECT version") and "legal_rule_versions" in sql:
            return _Result(self.history)
        if sql.startswith("SELECT count(*)") and "legal_rule_versions" in sql:
            return _Result(scalar=self.migration_count)
        if sql.startswith("INSERT INTO public.legal_rule_versions"):
            self.writes.append(("history", copy.deepcopy(params)))
            self.version_history.append({
                "version": params["previous_version"],
                "change_reason": params["change_reason"],
                "changed_by": None,
                "actor_type": "MIGRATION",
                "migration_revision": params["migration_revision"],
                "previous_definition": json.loads(params["previous_definition"]),
            })
            return _Result()
        if sql.startswith("UPDATE public.legal_rules"):
            self.writes.append(("update", copy.deepcopy(params)))
            assert params["previous_version"] == self.current["rule_version"]
            assert params["legacy_description"] == self.current["description"]
            assert json.loads(params["legacy_condition"]) == self.current["rule_condition"]
            self.current["description"] = params["canonical_description"]
            self.current["rule_condition"] = json.loads(params["canonical_condition"])
            self.current["rule_version"] = params["next_version"]
            return _Result(rowcount=1)
        if sql.startswith("SELECT statutory_basis"):
            return _Result([{
                key: self.current[key]
                for key in (
                    "statutory_basis", "description", "rule_condition",
                    "rule_version", "rule_name", "rule_type", "is_active"
                )
            }])
        raise AssertionError(f"unexpected SQL: {sql}")


def _install(monkeypatch, bind):
    monkeypatch.setattr(
        MIGRATION,
        "op",
        SimpleNamespace(get_bind=lambda: bind),
    )


def test_0128_reconciles_exact_0125_state_and_preserves_complete_before_image(monkeypatch):
    bind = _Bind()
    original = copy.deepcopy(bind.current)
    _install(monkeypatch, bind)

    MIGRATION.upgrade()

    assert bind.current["description"] == MIGRATION.CANONICAL_DESCRIPTION
    assert bind.current["rule_condition"] == MIGRATION.CANONICAL_CONDITION
    assert bind.current["rule_version"] == "1.3"
    assert bind.current["statutory_basis"] == MIGRATION.CANONICAL_BASIS
    assert bind.current["score_impact"] == original["score_impact"]
    assert bind.current["default_severity"] == original["default_severity"]
    assert len(bind.version_history) == 1
    history = bind.version_history[0]
    assert history["version"] == "1.2"
    assert history["actor_type"] == "MIGRATION"
    assert history["changed_by"] is None
    assert history["migration_revision"] == MIGRATION.revision
    assert history["previous_definition"] == original
    assert [kind for kind, _ in bind.writes] == ["history", "update"]


@pytest.mark.parametrize(
    "overrides",
    [
        {"description": "operator-edited definition"},
        {"rule_condition": {"trigger": "days_since_incorporation > 549"}},
        {"rule_version": "1.2.1"},
        {"statutory_basis": "Section 81, Companies Act 1994 (Bangladesh)"},
        {"is_active": False},
        {"rule_type": "POLICY"},
        {"default_severity": "RED"},
        {"score_impact": 25},
        {"revenue_tier": "CORPORATE_RESCUE"},
        {"is_black_override": True},
    ],
)
def test_0128_rejects_catalogue_drift_before_writes(monkeypatch, overrides):
    bind = _Bind(current=_current_row(**overrides))
    _install(monkeypatch, bind)

    with pytest.raises(RuntimeError, match="unexpected AGM-001 catalogue drift"):
        MIGRATION.upgrade()

    assert bind.writes == []
    assert bind.version_history == []


def test_0128_requires_exactly_one_valid_0125_history_row(monkeypatch):
    bind = _Bind(history=[])
    _install(monkeypatch, bind)

    with pytest.raises(RuntimeError, match="exactly one 0125"):
        MIGRATION.upgrade()

    assert bind.writes == []


def test_0128_rejects_non_migration_0125_provenance(monkeypatch):
    bind = _Bind(history=[_history_row(actor_type="USER")])
    _install(monkeypatch, bind)

    with pytest.raises(RuntimeError, match="invalid 0125"):
        MIGRATION.upgrade()

    assert bind.writes == []


def test_0128_rejects_changed_0125_change_reason(monkeypatch):
    bind = _Bind(history=[_history_row(change_reason="operator edited history")])
    _install(monkeypatch, bind)

    with pytest.raises(RuntimeError, match="invalid 0125"):
        MIGRATION.upgrade()

    assert bind.writes == []


def test_0128_refuses_existing_0128_history_with_legacy_catalogue(monkeypatch):
    bind = _Bind(migration_count=1)
    _install(monkeypatch, bind)

    with pytest.raises(RuntimeError, match="pre-existing AGM-001 migration history"):
        MIGRATION.upgrade()

    assert bind.writes == []


def test_0128_is_forward_only():
    with pytest.raises(RuntimeError, match="forward-only"):
        MIGRATION.downgrade()


def test_0128_is_the_single_forward_head_and_matches_seed_rule():
    migration = MIGRATION_PATH.read_text(encoding="utf-8")
    seed = (ROOT / "scripts" / "seed_rules.py").read_text(encoding="utf-8")

    assert 'revision = "0128_agm001_calendar_month_definition"' in migration
    assert 'down_revision = "0127_one_active_rescue_plan_per_company"' in migration
    assert MIGRATION.CANONICAL_DESCRIPTION in seed
    assert MIGRATION.CANONICAL_CONDITION["trigger"] in seed
    assert "days_since_incorporation > 548" not in MIGRATION.CANONICAL_CONDITION["trigger"]
    assert "add_calendar_months(incorporation_date, 18)" in MIGRATION.CANONICAL_CONDITION["trigger"]
