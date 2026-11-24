"""Seeder governance regression tests: operator activation decisions are preserved.

History: the legacy bootstrap seeder re-armed every disabled catalogue row on
each run (``UPDATE legal_rules SET is_active = TRUE ...``). The engine honours
operator deactivation by downgrading findings for inactive catalogue entries
(``RULE_INACTIVE`` → ``NOT_EVALUATED``, zero score impact), so the seeder-side
reactivation silently reversed audited Super Admin decisions taken through the
RulesService workflow.

These tests lock in the insert-only contract:
  * the seeder never issues an UPDATE against ``legal_rules``;
  * new canonical rows may still be inserted as active (no prior operator
    decision exists for a row that does not exist yet);
  * ``scripts/check_rule_verification.py`` fails closed if the reactivation
    statement is ever reintroduced.
"""
import importlib.util
import re
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SEED_PATH = ROOT / "scripts" / "seed_rules.py"
GUARD_PATH = ROOT / "scripts" / "check_rule_verification.py"

SEED_SOURCE = SEED_PATH.read_text(encoding="utf-8")

# Files check_rule_verification.py requires relative to the repo root, copied
# into tmp trees so the negative test can poison the seeder copy in isolation.
GUARD_INPUT_FILES = [
    "app/rule_engine/engine.py",
    "scripts/seed_rules.py",
    "docs/product/product_rule_approval_register.yaml",
    "docs/legal/legal_approval_register.yaml",
    "docs/legal/NLC_BD_COMPANIES_LAW_RULES_v1.0.csv",
    "docs/legal/NLC_BD_COMPANIES_LAW_RULES_v1.0.json",
    "canonical_architecture/statutory_rules.py",
    "docs/LEGAL_BASIS_MATRIX.md",
    ".env.example",
]

# A legacy-style reactivation statement, used to prove the guard fails closed.
REACTIVATION_TRIPWIRE = (
    "\n\n_LEGACY_REACTIVATION_TRIPWIRE = "
    "\"UPDATE legal_rules SET is_active = TRUE, updated_at = :now "
    "WHERE rule_id = :rid\"\n"
)


def _load_guard_module():
    spec = importlib.util.spec_from_file_location(
        "nlc_check_rule_verification", GUARD_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_seeder_contains_no_legal_rules_update_statement():
    """The seeder is insert-only: existing rows are never written back."""
    assert "UPDATE legal_rules" not in SEED_SOURCE, (
        "seed_rules.py must never UPDATE legal_rules; definitions and the "
        "operator-controlled is_active state of existing rows are immutable"
    )


def test_seeder_inserts_missing_rows_as_active_only():
    """New rows have no prior operator decision, so insert-as-active is allowed."""
    assert "TRUE, :now, :now" in SEED_SOURCE


def test_seeder_reactivation_guard_regex_catches_legacy_statement():
    """The guard regex used in check_rule_verification detects the legacy UPDATE."""
    pattern = r"UPDATE\s+legal_rules\b[^;]*?is_active"
    legacy = (
        "UPDATE legal_rules SET is_active = TRUE, "
        "updated_at = :now WHERE rule_id = :rid"
    )
    assert re.search(pattern, legacy, re.DOTALL)


def test_guard_passes_on_current_repository_state(monkeypatch):
    """The full verification guard must be green after the governance fix."""
    monkeypatch.chdir(ROOT)
    guard = _load_guard_module()
    assert guard.main() == 0


def _materialize_guard_tree(tmp_path: Path) -> Path:
    for relative in GUARD_INPUT_FILES:
        source = ROOT / relative
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(source, target)
    return tmp_path


def test_guard_fails_closed_if_reactivation_is_reintroduced(monkeypatch, tmp_path):
    """Reintroducing the legacy UPDATE must fail the verification guard."""
    tree = _materialize_guard_tree(tmp_path)
    seed_copy = tree / "scripts" / "seed_rules.py"
    seed_copy.write_text(
        seed_copy.read_text(encoding="utf-8") + REACTIVATION_TRIPWIRE,
        encoding="utf-8",
    )
    monkeypatch.chdir(tree)
    guard = _load_guard_module()
    assert guard.main() == 1


def test_guard_failure_message_names_preserved_operator_decisions(
    monkeypatch, tmp_path, capsys
):
    """The failure output must explain which contract was violated."""
    tree = _materialize_guard_tree(tmp_path)
    seed_copy = tree / "scripts" / "seed_rules.py"
    seed_copy.write_text(
        seed_copy.read_text(encoding="utf-8") + REACTIVATION_TRIPWIRE,
        encoding="utf-8",
    )
    monkeypatch.chdir(tree)
    guard = _load_guard_module()
    guard.main()
    captured = capsys.readouterr()
    assert "operator activation decisions are preserved" in captured.out


@pytest.mark.parametrize("statement", [
    "UPDATE legal_rules SET is_active = TRUE WHERE rule_id = :rid",
    "UPDATE legal_rules SET is_active = FALSE WHERE rule_id = :rid",
    "UPDATE legal_rules SET updated_at = :now, is_active = TRUE WHERE rule_id = :rid",
])
def test_guard_rejects_any_is_active_write_direction(monkeypatch, tmp_path, statement):
    """Neither re-arming nor disabling via the seeder is permitted."""
    tree = _materialize_guard_tree(tmp_path)
    seed_copy = tree / "scripts" / "seed_rules.py"
    seed_copy.write_text(
        seed_copy.read_text(encoding="utf-8")
        + f"\n\n_TRIPWIRE = \"{statement}\"\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tree)
    guard = _load_guard_module()
    assert guard.main() == 1
