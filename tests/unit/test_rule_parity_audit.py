"""Regression tests for strict canonical rule parity auditing."""
import importlib.util
import sys
import pytest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[2] / "tools" / "audit_rule_parity.py"
SPEC = importlib.util.spec_from_file_location("nlc_rule_parity_audit", SCRIPT)
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)



def test_engine_parser_includes_tuple_declared_rule_ids():
    monkeypatch = pytest.MonkeyPatch()
    try:
        monkeypatch.setattr(AUDIT.Path, "read_text", lambda self, **kwargs: """
def rules():
    candidates = (
        ("BSEC-001", "FLAG", None, "description"),
        ("BSEC-002", "FLAG2", None, "description"),
    )
    return candidates
""")
        assert AUDIT.get_engine_rules() == {"BSEC-001", "BSEC-002"}
    finally:
        monkeypatch.undo()


def test_static_mode_compares_engine_and_seed_without_live_sources(monkeypatch):
    monkeypatch.setattr(AUDIT, "get_engine_rules", lambda: {"AGM-001", "INC-001"})
    monkeypatch.setattr(AUDIT, "get_seed_rules", lambda: {"AGM-001", "INC-001"})
    monkeypatch.setattr(AUDIT, "get_db_rules", lambda: (_ for _ in ()).throw(AssertionError("DB must be skipped")))
    monkeypatch.setattr(AUDIT, "get_api_rules", lambda: (_ for _ in ()).throw(AssertionError("API must be skipped")))
    monkeypatch.setattr(sys, "argv", ["audit_rule_parity.py", "--no-db", "--no-api"])

    assert AUDIT.main() == 0


def test_unavailable_requested_live_api_fails_audit(monkeypatch):
    monkeypatch.setattr(AUDIT, "get_engine_rules", lambda: {"AGM-001"})
    monkeypatch.setattr(AUDIT, "get_seed_rules", lambda: {"AGM-001"})
    monkeypatch.setattr(AUDIT, "get_api_rules", lambda: None)
    monkeypatch.setattr(sys, "argv", ["audit_rule_parity.py", "--no-db"])

    assert AUDIT.main() == 2


def test_engine_seed_rule_mismatch_fails_static_audit(monkeypatch):
    monkeypatch.setattr(AUDIT, "get_engine_rules", lambda: {"AGM-001", "INC-001"})
    monkeypatch.setattr(AUDIT, "get_seed_rules", lambda: {"AGM-001"})
    monkeypatch.setattr(sys, "argv", ["audit_rule_parity.py", "--no-db", "--no-api"])

    assert AUDIT.main() == 1
