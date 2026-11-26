import hashlib
import importlib.util
import json
import re
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
MIGRATION = (
    ROOT
    / "alembic"
    / "versions"
    / "0125_reconcile_agm001_catalogue_identity.py"
)
INTEGRATION_TEST = ROOT / "tests" / "integration" / "test_services.py"


class FakeCatalogueConnection:
    def __init__(self):
        self.rules: dict[str, dict] = {}
        self.archive: list[dict] = []
        self.events: list[str] = []
        self.ddl: list[str] = []

    def execute(self, statement, params):
        sql = " ".join(str(statement).split())
        if sql == (
            "SELECT to_jsonb(r) AS payload FROM public.legal_rules AS r "
            "WHERE r.rule_id = :rule_id FOR UPDATE"
        ):
            row = self.rules.get(params["rule_id"])
            result = {"payload": deepcopy(row)} if row is not None else None
            return SimpleNamespace(mappings=lambda: SimpleNamespace(first=lambda: result))

        insert = re.fullmatch(
            r"INSERT INTO public\.legal_rule_identity_archive \((.*?)\) VALUES \((.*)\)",
            sql,
        )
        if insert:
            columns = [column.strip() for column in insert[1].split(",")]
            values = [value.strip() for value in insert[2].split(",")]
            archived = {
                column: self._resolve(value, params)
                for column, value in zip(columns, values, strict=True)
            }
            self.archive.append(archived)
            self.events.append("archive_insert")
            return SimpleNamespace(rowcount=1)

        update = re.fullmatch(r"UPDATE public\.legal_rules SET (.*?) WHERE (.*)", sql)
        if update:
            assignments = {}
            for assignment in update[1].split(","):
                assignment = assignment.strip()
                if assignment == "statutory_basis = :canonical_basis":
                    assignments["statutory_basis"] = params["canonical_basis"]
                elif assignment == "updated_at = now()":
                    assignments["updated_at"] = "NOW"
                else:
                    raise AssertionError(f"unexpected SQL: {sql}")
            conditions = []
            for condition in update[2].split(" AND "):
                if condition == "rule_id = :rule_id":
                    conditions.append(lambda row: row["rule_id"] == params["rule_id"])
                elif condition == "is_active IS TRUE":
                    conditions.append(lambda row: row["is_active"] is True)
                elif condition == "statutory_basis = :legacy_basis":
                    conditions.append(
                        lambda row: row["statutory_basis"] == params["legacy_basis"]
                    )
                else:
                    raise AssertionError(f"unexpected SQL: {sql}")
            rowcount = 0
            for row in self.rules.values():
                if all(condition(row) for condition in conditions):
                    row.update(assignments)
                    rowcount += 1
            self.events.append("update")
            return SimpleNamespace(rowcount=rowcount)

        if sql == "SELECT statutory_basis FROM public.legal_rules WHERE rule_id = :rule_id":
            row = self.rules.get(params["rule_id"])
            basis = row["statutory_basis"] if row is not None else None
            self.events.append("verify")
            return SimpleNamespace(scalar_one_or_none=lambda: basis)

        raise AssertionError(f"unexpected SQL: {sql}")

    @staticmethod
    def _resolve(value, params):
        if re.fullmatch(r":\w+", value):
            return params[value[1:]]
        cast = re.fullmatch(r"CAST\(:(\w+) AS jsonb\)", value)
        if cast:
            return json.loads(params[cast[1]])
        if re.fullmatch(r"'[^']*'", value):
            return value[1:-1]
        if value == "now()":
            return "NOW"
        raise AssertionError(f"unexpected SQL: {value}")

    def execute_ddl(self, statement):
        sql = " ".join(str(statement).split())
        if not (
            sql.startswith("DO $policy$")
            and sql.endswith("$policy$")
            and "legal_rule_identity_archive_migration_insert" in sql
            and "nlc_migration_owner" in sql
        ):
            raise AssertionError(f"unexpected SQL: {sql}")
        self.ddl.append(sql)
        self.events.append("policy")


@pytest.fixture
def catalogue():
    return FakeCatalogueConnection()


@pytest.fixture
def migration(monkeypatch, catalogue):
    spec = importlib.util.spec_from_file_location("agm001_reconciliation", MIGRATION)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(
        module,
        "op",
        SimpleNamespace(get_bind=lambda: catalogue, execute=catalogue.execute_ddl),
    )
    return module


def _rule(migration, **overrides):
    return {
        "id": "5c1e0201-752c-44f6-8bf0-32bdfe35bc97",
        "rule_id": "AGM-001",
        "name": "Annual general meeting deadline",
        "severity": "HIGH",
        "is_active": True,
        "statutory_basis": migration.LEGACY_BASIS,
        "updated_at": "2026-01-15T12:34:56+00:00",
        "metadata": {"tags": ["annual", "meeting"], "grace_days": 0},
        **overrides,
    }


def _assert_no_writes(catalogue, before):
    assert catalogue.rules == before
    assert catalogue.archive == []
    assert catalogue.events == []
    assert catalogue.ddl == []


def test_agm001_reconciliation_archives_the_complete_before_image(migration, catalogue):
    assert migration.LEGACY_BASIS == "Section 81, Companies Act 1994 (Bangladesh)"
    assert migration.CANONICAL_BASIS == "Section 81(1), Companies Act 1994 (Bangladesh)"
    catalogue.rules = {
        "AGM-001": _rule(migration),
        "AGM-002": _rule(migration, rule_id="AGM-002", id="another-rule"),
    }
    before = deepcopy(catalogue.rules)

    migration.upgrade()

    assert catalogue.rules["AGM-001"] == {
        **before["AGM-001"],
        "statutory_basis": migration.CANONICAL_BASIS,
        "updated_at": "NOW",
    }
    assert catalogue.rules["AGM-002"] == before["AGM-002"]
    assert catalogue.events == ["policy", "archive_insert", "update", "verify"]
    expected_hash = hashlib.sha256(
        json.dumps(before["AGM-001"], sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    assert catalogue.archive == [{
        "legacy_identity_key": "legacy:AGM-001:section-81-to-81-1:0125",
        "legacy_rule_id": "AGM-001",
        "original_payload": before["AGM-001"],
        "payload_sha256": expected_hash,
        "disposition": "CANONICAL_BASIS_RECONCILIATION",
        "historical_resolution": "UNATTRIBUTED_PENDING_RECORD_LEVEL_REVIEW",
        "captured_at": "NOW",
    }]


def test_agm001_reconciliation_policy_does_not_require_the_migration_owner_role(
    migration, catalogue
):
    catalogue.rules["AGM-001"] = _rule(migration)

    migration.upgrade()

    (policy,) = catalogue.ddl
    guard = "IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'nlc_migration_owner') THEN"
    assert guard in policy
    assert "RAISE" not in policy
    assert policy.index(guard) < policy.index("CREATE POLICY")


def test_agm001_reconciliation_is_idempotent(migration, catalogue):
    catalogue.rules["AGM-001"] = _rule(migration)
    migration.upgrade()
    before = deepcopy(catalogue.rules)
    archive = deepcopy(catalogue.archive)
    events = catalogue.events.copy()

    migration.upgrade()

    assert catalogue.rules == before
    assert catalogue.rules["AGM-001"]["statutory_basis"] == migration.CANONICAL_BASIS
    assert len(catalogue.archive) == 1
    assert catalogue.archive == archive
    assert catalogue.events == events


@pytest.mark.parametrize("basis", [
    "Section 81(2), Companies Act 1994 (Bangladesh)",
    "Section 81, Companies Act 1994",
    "",
    None,
])
def test_agm001_reconciliation_refuses_conflicting_basis(migration, catalogue, basis):
    catalogue.rules["AGM-001"] = _rule(migration, statutory_basis=basis)
    before = deepcopy(catalogue.rules)

    with pytest.raises(RuntimeError, match="unrecognized AGM-001 statutory basis"):
        migration.upgrade()

    _assert_no_writes(catalogue, before)


@pytest.mark.parametrize("is_active", [False, None])
@pytest.mark.parametrize("basis", ["LEGACY_BASIS", "CANONICAL_BASIS"])
def test_agm001_reconciliation_refuses_inactive_row(migration, catalogue, is_active, basis):
    catalogue.rules["AGM-001"] = _rule(
        migration, is_active=is_active, statutory_basis=getattr(migration, basis)
    )
    before = deepcopy(catalogue.rules)

    with pytest.raises(RuntimeError, match="requires active AGM-001"):
        migration.upgrade()

    _assert_no_writes(catalogue, before)


def test_agm001_reconciliation_refuses_missing_row(migration, catalogue):
    with pytest.raises(RuntimeError, match="requires the migrated AGM-001 catalogue row"):
        migration.upgrade()

    _assert_no_writes(catalogue, {})


def test_agm001_reconciliation_leaves_canonical_row_unchanged(migration, catalogue):
    catalogue.rules["AGM-001"] = _rule(migration, statutory_basis=migration.CANONICAL_BASIS)
    before = deepcopy(catalogue.rules)

    migration.upgrade()

    _assert_no_writes(catalogue, before)


def test_agm001_reconciliation_is_forward_only(migration):
    with pytest.raises(RuntimeError, match="forward-only"):
        migration.downgrade()


def test_release_redaction_fixture_uses_migrated_catalogue_without_mutating_it():
    source = INTEGRATION_TEST.read_text(encoding="utf-8")
    marker = 'canonical_agm_basis = STATUTORY_RULE_REGISTRY["AGM-001"].law'
    pos = source.index(marker)
    end = source.index("mock_engine.evaluate.assert_called_once()", pos)
    fixture = source[pos:end]

    assert "catalogue_rule.statutory_basis = canonical_agm_basis" not in fixture
    assert "MATCHED_CATALOGUE_IDENTITY" in fixture
    assert "score_impact_applied" in fixture
    assert "NOT_EVALUATED_PRODUCT_SCORING_DISABLED" in fixture
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


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
    assert (
        "catalogue_rule.statutory_basis == canonical_agm_001_basis" in fixture
        or "catalogue_rule.statutory_basis == canonical_agm_basis" in fixture
    )
    assert "_catalogue_identity_conflicts([catalogue_rule])" in fixture
    assert '"MATCHED_CATALOGUE_IDENTITY"' in fixture
    assert "\n        catalogue_rule.statutory_basis = " not in fixture
    assert "LegalRule(" not in fixture
    assert fixture.index('"MATCHED_CATALOGUE_IDENTITY"') < fixture.index(
        '["score_impact_applied"] == 0'
    )
