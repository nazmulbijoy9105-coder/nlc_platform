import re
from pathlib import Path

from canonical_architecture.statutory_rules import STATUTORY_RULE_REGISTRY


def test_canonical_identity_seed_matches_exact_85_rule_engine_registry():
    migration = (
        Path(__file__).resolve().parents[2]
        / "alembic"
        / "versions"
        / "0116_canonical_rule_identity_registry.py"
    ).read_text(encoding="utf-8")
    match = re.search(
        r"WITH engine_rule_ids\(rule_id\) AS \(\s*VALUES(?P<values>.*?)"
        r"\)\s*INSERT INTO public\.legal_rule_identities",
        migration,
        flags=re.DOTALL,
    )
    assert match is not None, "0116 must contain the deterministic engine identity seed."

    seeded_ids = re.findall(r"\('([A-Z]+-\d+)'\)", match.group("values"))
    assert len(seeded_ids) == 85
    assert len(set(seeded_ids)) == 85
    assert set(seeded_ids) == set(STATUTORY_RULE_REGISTRY)
    assert "INC-001" in seeded_ids
    assert "INC-002" not in seeded_ids


def test_seeded_identity_aliases_are_candidate_only_not_historical_attribution():
    migration = (
        Path(__file__).resolve().parents[2]
        / "alembic"
        / "versions"
        / "0116_canonical_rule_identity_registry.py"
    ).read_text(encoding="utf-8")

    assert "'NLC_ENGINE_REGISTRY_V2'" in migration
    assert "'UNRESOLVED'" in migration
    assert "split_part(obligation_key, ':', 3)" in migration
    assert "not a resolution to any legacy legal_rules row" in migration
    assert "historical finding" in migration
