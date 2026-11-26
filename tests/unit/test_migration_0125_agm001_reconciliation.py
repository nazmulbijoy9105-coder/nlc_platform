import copy
import importlib.util
import json
import re
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _load_migration_0125():
    spec = importlib.util.spec_from_file_location(
        "migration_0125_agm001_under_test",
        ROOT / "alembic" / "versions" / "0125_reconcile_agm001_statutory_basis.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MIGRATION_0125 = _load_migration_0125()


class _Result:
    def __init__(self, rows=()):
        self._rows = list(rows)

    def mappings(self):
        return self

    def one_or_none(self):
        return self._rows[0] if self._rows else None

    def all(self):
        return list(self._rows)


class _FakeBind:
    def __init__(self, current, history):
        self.current = current
        self.history = history
        self.writes = []

    def execute(self, statement, params=None):
        sql = " ".join(str(statement).split())
        if sql.startswith(("INSERT", "UPDATE")):
            self.writes.append(sql)
            return _Result()
        if "FOR UPDATE" in sql:
            return _Result([self.current])
        if sql.startswith("SELECT version") and "legal_rule_versions" in sql:
            return _Result(self.history)
        raise AssertionError(f"unexpected SQL: {sql}")


def _install_fake_op(monkeypatch, bind):
    def noop(*args, **kwargs):
        return None

    monkeypatch.setattr(
        MIGRATION_0125,
        "op",
        SimpleNamespace(
            get_bind=lambda: bind,
            add_column=noop,
            alter_column=noop,
            create_check_constraint=noop,
        ),
    )


def _legacy_before_image(**overrides):
    image = {
        "rule_id": MIGRATION_0125.RULE_ID,
        "statutory_basis": MIGRATION_0125.LEGACY_BASIS,
        "rule_version": "1.0.0",
        **copy.deepcopy(MIGRATION_0125.LEGACY_DEFINITION),
    }
    image.update(overrides)
    return image


def _history_row(**overrides):
    row = {
        "version": "1.0.0",
        "change_reason": MIGRATION_0125.CHANGE_REASON,
        "changed_by": None,
        "actor_type": "MIGRATION",
        "migration_revision": MIGRATION_0125.revision,
        "previous_definition": _legacy_before_image(),
    }
    row.update(overrides)
    return row


def _canonical_row(**overrides):
    row = {
        **copy.deepcopy(MIGRATION_0125.LEGACY_DEFINITION),
        "statutory_basis": MIGRATION_0125.CANONICAL_BASIS,
        "rule_version": "1.0.1",
    }
    row.update(overrides)
    return row


def test_agm001_migration_is_fingerprint_scoped_and_version_audited():
    migration = (
        ROOT
        / "alembic"
        / "versions"
        / "0125_reconcile_agm001_statutory_basis.py"
    ).read_text(encoding="utf-8")

    assert 'revision = "0125_reconcile_agm001_statutory_basis"' in migration
    assert 'down_revision = "0124_restore_85_rule_catalogue_parity"' in migration
    assert 'LEGACY_BASIS = "Section 81, Companies Act 1994 (Bangladesh)"' in migration
    assert (
        'CANONICAL_BASIS = "Section 81(1), Companies Act 1994 (Bangladesh)"'
        in migration
    )
    assert "if _definition(current) != LEGACY_DEFINITION:" in migration
    assert "to_jsonb(rule) AS previous_definition" in migration
    assert "INSERT INTO public.legal_rule_versions" in migration
    assert "'MIGRATION', :migration_revision" in migration
    assert migration.index("INSERT INTO public.legal_rule_versions") < migration.index(
        "UPDATE public.legal_rules"
    )
    assert "AND statutory_basis = :legacy_basis" in migration
    assert "rule_version = :next_version" in migration
    assert "def downgrade() -> None:" in migration
    assert "0125 is forward-only" in migration


def test_agm001_release_redaction_fixture_uses_migrated_catalogue_identity():
    source = (
        ROOT / "tests" / "integration" / "test_services.py"
    ).read_text(encoding="utf-8")
    start = source.index("async def test_evaluate_company_full_pipeline")
    next_boundary = re.compile(r"\n {0,4}(?:@|#|async def |def |class )")
    boundary = next_boundary.search(source, start + 1)
    fixture = source[start : boundary.start() if boundary else None]

    assert "catalogue_rule = catalogue_result.scalar_one()" in fixture
    assert "catalogue_rule.statutory_basis == canonical_agm_001_basis" in fixture
    assert "_catalogue_identity_conflicts([catalogue_rule])" in fixture
    assert '"MATCHED_CATALOGUE_IDENTITY"' in fixture
    assert "\n        catalogue_rule.statutory_basis = " not in fixture
    assert "LegalRule(" not in fixture
    assert fixture.index('"MATCHED_CATALOGUE_IDENTITY"') < fixture.index(
        '["score_impact_applied"] == 0'
    )


def _drifted_trigger_before_image():
    image = _legacy_before_image()
    image["rule_condition"]["trigger"] = (
        "first_agm_held == False AND days_since_incorporation > 549"
    )
    return image


def test_agm001_canonical_row_is_accepted_with_exactly_one_valid_migration_history(
    monkeypatch,
):
    bind = _FakeBind(_canonical_row(), [_history_row()])
    _install_fake_op(monkeypatch, bind)

    MIGRATION_0125.upgrade()

    assert bind.writes == []


def test_agm001_canonical_row_accepts_json_text_before_image(monkeypatch):
    history = _history_row(previous_definition=json.dumps(_legacy_before_image()))
    bind = _FakeBind(_canonical_row(), [history])
    _install_fake_op(monkeypatch, bind)

    MIGRATION_0125.upgrade()

    assert bind.writes == []


@pytest.mark.parametrize(
    ("current_overrides", "history", "message"),
    [
        pytest.param({}, [], "found 0", id="no-history"),
        pytest.param(
            {}, [_history_row(), _history_row()], "found 2", id="duplicate-history"
        ),
        pytest.param(
            {},
            [_history_row(actor_type="USER")],
            "provenance is invalid",
            id="user-actor",
        ),
        pytest.param(
            {},
            [_history_row(changed_by=uuid.uuid4())],
            "provenance is invalid",
            id="named-changer",
        ),
        pytest.param(
            {},
            [_history_row(migration_revision="0001_another_revision")],
            "provenance is invalid",
            id="other-revision",
        ),
        pytest.param(
            {},
            [_history_row(change_reason="Manual citation edit")],
            "provenance is invalid",
            id="other-reason",
        ),
        pytest.param(
            {},
            [_history_row(previous_definition=None)],
            "not a JSON object",
            id="missing-before-image",
        ),
        pytest.param(
            {},
            [_history_row(previous_definition=_legacy_before_image(rule_id="AGM-002"))],
            "another rule ID",
            id="other-rule-before-image",
        ),
        pytest.param(
            {},
            [
                _history_row(
                    previous_definition=_legacy_before_image(
                        statutory_basis=MIGRATION_0125.CANONICAL_BASIS
                    )
                )
            ],
            "exact legacy citation",
            id="before-image-not-legacy-citation",
        ),
        pytest.param(
            {},
            [_history_row(version="0.9.0")],
            "does not match its before-image",
            id="before-image-version-mismatch",
        ),
        pytest.param(
            {},
            [_history_row(previous_definition=_drifted_trigger_before_image())],
            "exact known legacy definition",
            id="before-image-drifted-trigger",
        ),
        pytest.param(
            {},
            [
                _history_row(
                    previous_definition=_legacy_before_image(
                        description="First AGM not held within 18 months."
                    )
                )
            ],
            "exact known legacy definition",
            id="before-image-drifted-description",
        ),
        pytest.param(
            {"rule_version": "1.0.0"},
            [_history_row()],
            "does not follow its migration history",
            id="version-not-advanced",
        ),
        pytest.param(
            {"rule_version": "1.0.2"},
            [_history_row()],
            "does not follow its migration history",
            id="version-skipped-ahead",
        ),
    ],
)
def test_agm001_canonical_row_is_rejected_without_valid_migration_history(
    monkeypatch, current_overrides, history, message
):
    bind = _FakeBind(_canonical_row(**current_overrides), history)
    _install_fake_op(monkeypatch, bind)

    with pytest.raises(RuntimeError, match=message):
        MIGRATION_0125.upgrade()

    assert bind.writes == []


def test_agm001_reconciliation_rejects_any_drift_from_exact_legacy_definition():
    migration = (
        ROOT / "alembic/versions/0125_reconcile_agm001_statutory_basis.py"
    ).read_text(encoding="utf-8")

    assert '"description": (' in migration
    assert '"First AGM not held within 18 months (548 days) of incorporation. "' in migration
    assert '"trigger": "first_agm_held == False AND days_since_incorporation > 548"' in migration
    validation = migration.index("if _definition(current) != LEGACY_DEFINITION:")
    canonical_update = migration.index("UPDATE public.legal_rules")
    assert validation < canonical_update


def test_agm001_reconciliation_uses_version_ledger_without_changing_identity_archive_count():
    migration = (
        ROOT / "alembic/versions/0125_reconcile_agm001_statutory_basis.py"
    ).read_text(encoding="utf-8")
    parity_audit = (
        ROOT / "tools/audit_production_release_parity.py"
    ).read_text(encoding="utf-8")

    assert "INSERT INTO public.legal_rule_versions" in migration
    assert "INSERT INTO public.legal_rule_identity_archive" not in migration
    assert 'result.get("identity_archive_rows") != 2' in parity_audit


class _WriteResult(_Result):
    def __init__(self, rowcount=0, rows=()):
        super().__init__(rows)
        self.rowcount = rowcount

    def scalar_one(self):
        return 0


class _LegacyExecutionBind:
    """Small SQL-aware fake that exercises the migration's real upgrade path."""

    def __init__(self, current):
        self.current = copy.deepcopy(current)
        self.history = []
        self.writes = []
        self.archive_writes = []
        self.identity_archive_rows = 2

    def execute(self, statement, params=None):
        sql = " ".join(str(statement).split())
        params = params or {}
        if sql.startswith("SELECT to_jsonb(rule)"):
            return _Result([self.current])
        if sql.startswith("SELECT count(*)") and "legal_rule_versions" in sql:
            return _WriteResult()
        if sql.startswith("INSERT INTO public.legal_rule_versions"):
            expected_sql = (
                "INSERT INTO public.legal_rule_versions "
                "(rule_id, version, change_reason, changed_by, changed_at, "
                "previous_definition, sro_reference, actor_type, migration_revision) "
                "VALUES (:rule_id, :previous_version, :change_reason, NULL, "
                "now(), CAST(:previous_definition AS jsonb), NULL, "
                "'MIGRATION', :migration_revision)"
            )
            assert sql == expected_sql, "unexpected rule-version INSERT semantics"
            assert params == {
                "rule_id": MIGRATION_0125.RULE_ID,
                "previous_version": self.current["rule_version"],
                "change_reason": MIGRATION_0125.CHANGE_REASON,
                "migration_revision": MIGRATION_0125.revision,
                "previous_definition": json.dumps(
                    self.current["previous_definition"],
                    sort_keys=True,
                    separators=(",", ":"),
                    default=str,
                ),
            }
            before_image = json.loads(params["previous_definition"])
            assert before_image == self.current["previous_definition"]
            self.writes.append((sql, copy.deepcopy(params)))
            self.history.append({
                "version": params["previous_version"],
                "change_reason": params["change_reason"],
                "changed_by": None,
                "actor_type": "MIGRATION",
                "migration_revision": params["migration_revision"],
                "previous_definition": before_image,
            })
            return _WriteResult()
        if sql.startswith("UPDATE public.legal_rules"):
            expected_sql = (
                "UPDATE public.legal_rules "
                "SET statutory_basis = :canonical_basis, "
                "rule_version = :next_version, "
                "last_modified_at = now(), updated_at = now() "
                "WHERE rule_id = :rule_id "
                "AND statutory_basis = :legacy_basis "
                "AND rule_version = :previous_version "
                "AND is_active IS TRUE"
            )
            assert sql == expected_sql, "unexpected or insufficiently scoped rule UPDATE"
            assert params == {
                "canonical_basis": MIGRATION_0125.CANONICAL_BASIS,
                "next_version": "1.0.1",
                "rule_id": MIGRATION_0125.RULE_ID,
                "legacy_basis": MIGRATION_0125.LEGACY_BASIS,
                "previous_version": "1.0.0",
            }
            matches_predicates = (
                self.current.get("rule_id") == params["rule_id"]
                and self.current.get("statutory_basis") == params["legacy_basis"]
                and self.current.get("rule_version") == params["previous_version"]
                and self.current.get("is_active") is True
            )
            self.writes.append((sql, copy.deepcopy(params)))
            if not matches_predicates:
                return _WriteResult(rowcount=0)
            self.current["statutory_basis"] = params["canonical_basis"]
            self.current["rule_version"] = params["next_version"]
            return _WriteResult(rowcount=1)
        if sql.startswith("SELECT version") and "legal_rule_versions" in sql:
            return _Result(self.history)
        if sql.startswith("SELECT rule.rule_name"):
            return _Result([self.current])
        if "legal_rule_identity_archive" in sql or sql.startswith(
            "INSERT INTO public.legal_rule_identity_archive"
        ):
            self.archive_writes.append(sql)
            return _WriteResult()
        raise AssertionError(f"unexpected SQL in migration execution: {sql}")


def _legacy_current_row(**overrides):
    row = {
        "rule_id": MIGRATION_0125.RULE_ID,
        **copy.deepcopy(MIGRATION_0125.LEGACY_DEFINITION),
        "statutory_basis": MIGRATION_0125.LEGACY_BASIS,
        "rule_version": "1.0.0",
        "previous_definition": {
            "rule_id": MIGRATION_0125.RULE_ID,
            "statutory_basis": MIGRATION_0125.LEGACY_BASIS,
            "rule_version": "1.0.0",
            **copy.deepcopy(MIGRATION_0125.LEGACY_DEFINITION),
        },
    }
    row.update(overrides)
    return row


def test_legacy_execution_fake_rejects_update_with_dropped_predicates():
    bind = _LegacyExecutionBind(_legacy_current_row())
    unsafe_sql = (
        "UPDATE public.legal_rules "
        "SET statutory_basis = :canonical_basis, rule_version = :next_version"
    )
    with pytest.raises(AssertionError, match="rule UPDATE"):
        bind.execute(
            unsafe_sql,
            {
                "canonical_basis": MIGRATION_0125.CANONICAL_BASIS,
                "next_version": "1.0.1",
                "rule_id": MIGRATION_0125.RULE_ID,
                "legacy_basis": MIGRATION_0125.LEGACY_BASIS,
                "previous_version": "1.0.0",
            },
        )
    assert bind.current["statutory_basis"] == MIGRATION_0125.LEGACY_BASIS
    assert bind.current["rule_version"] == "1.0.0"


def test_legacy_execution_fake_rejects_incorrect_migration_provenance():
    bind = _LegacyExecutionBind(_legacy_current_row())
    unsafe_sql = (
        "INSERT INTO public.legal_rule_versions "
        "(rule_id, version, change_reason, changed_by, changed_at, "
        "previous_definition, sro_reference, actor_type, migration_revision) "
        "VALUES (:rule_id, :previous_version, :change_reason, NULL, "
        "now(), CAST(:previous_definition AS jsonb), NULL, "
        "'USER', :migration_revision)"
    )
    with pytest.raises(AssertionError, match="INSERT semantics"):
        bind.execute(
            unsafe_sql,
            {
                "rule_id": MIGRATION_0125.RULE_ID,
                "previous_version": "1.0.0",
                "change_reason": MIGRATION_0125.CHANGE_REASON,
                "migration_revision": MIGRATION_0125.revision,
                "previous_definition": json.dumps(_legacy_before_image()),
            },
        )
    assert bind.history == []


def test_agm001_upgrade_executes_reconciliation_and_advances_version(monkeypatch):
    bind = _LegacyExecutionBind(_legacy_current_row())
    _install_fake_op(monkeypatch, bind)

    MIGRATION_0125.upgrade()

    assert bind.current["statutory_basis"] == MIGRATION_0125.CANONICAL_BASIS
    assert bind.current["rule_version"] == "1.0.1"
    assert len(bind.history) == 1
    assert bind.history[0]["version"] == "1.0.0"
    assert bind.history[0]["actor_type"] == "MIGRATION"
    assert bind.history[0]["changed_by"] is None
    assert bind.history[0]["migration_revision"] == MIGRATION_0125.revision
    assert bind.history[0]["previous_definition"] == _legacy_before_image()
    assert len([sql for sql, _ in bind.writes if sql.startswith("UPDATE")]) == 1
    assert bind.archive_writes == []
    assert bind.identity_archive_rows == 2


@pytest.mark.parametrize(
    "overrides",
    [
        pytest.param(
            {"rule_condition": {
                **copy.deepcopy(MIGRATION_0125.LEGACY_DEFINITION["rule_condition"]),
                "trigger": "first_agm_held == False AND days_since_incorporation > 549",
            }},
            id="changed-548-day-trigger",
        ),
        pytest.param({"is_active": False}, id="inactive-legacy-row"),
        pytest.param({"rule_type": "POLICY"}, id="wrong-legacy-rule-type"),
    ],
)
def test_agm001_upgrade_rejects_drifted_legacy_definition_before_writes(
    monkeypatch, overrides
):
    bind = _LegacyExecutionBind(_legacy_current_row(**overrides))
    _install_fake_op(monkeypatch, bind)

    with pytest.raises(RuntimeError, match="conflicting AGM-001 legal definition"):
        MIGRATION_0125.upgrade()

    assert bind.writes == []
    assert bind.history == []
    assert bind.current["statutory_basis"] == MIGRATION_0125.LEGACY_BASIS
    assert bind.archive_writes == []
    assert bind.identity_archive_rows == 2


def test_agm001_legacy_rule_type_contract_is_explicit():
    assert MIGRATION_0125.LEGACY_DEFINITION["rule_type"] == "DEADLINE"
    assert MIGRATION_0125.LEGACY_DEFINITION["is_active"] is True
    assert (
        MIGRATION_0125.LEGACY_DEFINITION["rule_condition"]["trigger"]
        == "first_agm_held == False AND days_since_incorporation > 548"
    )
