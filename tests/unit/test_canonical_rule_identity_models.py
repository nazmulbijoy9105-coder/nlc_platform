"""Structural safeguards for the additive canonical rule identity registry."""
from pathlib import Path\n\nfrom sqlalchemy import CheckConstraint, UniqueConstraint

from app.models import LegalRuleAlias, LegalRuleIdentity, LegalRuleRevision


def test_canonical_identity_uses_opaque_uuid_and_quarantined_default():
    table = LegalRuleIdentity.__table__
    assert table.c.id.primary_key
    assert table.c.id.type.__class__.__name__ == "UUID"
    assert table.c.identity_status.server_default is not None
    assert "QUARANTINED" in str(table.c.identity_status.server_default.arg)


def test_alias_is_namespaced_and_can_represent_collisions():
    table = LegalRuleAlias.__table__
    unique_column_sets = {
        frozenset(column.name for column in constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert frozenset(
        {"source_namespace", "historical_rule_id", "canonical_rule_id"}
    ) in unique_column_sets
    assert table.c.historical_rule_id.nullable is False
    assert table.c.resolution_status.server_default is not None
    # Deliberately no uniqueness constraint on namespace + historical ID alone:
    # a legacy collision must remain representable and be resolved as ambiguous.


def test_revision_separates_effective_dates_and_evaluator_identity():
    table = LegalRuleRevision.__table__
    assert {"effective_from", "effective_to"} <= set(table.c.keys())
    assert {"evaluator_name", "evaluator_version", "evaluator_artifact_hash"} <= set(
        table.c.keys()
    )
    assert any(
        isinstance(constraint, CheckConstraint)
        and "effective_to" in str(constraint.sqltext)
        for constraint in table.constraints
    )
    assert table.c.definition_hash.nullable is False


def test_identity_alias_and_revision_relationships_are_lazy_raise():
    assert LegalRuleIdentity.aliases.property.lazy == "raise"
    assert LegalRuleIdentity.revisions.property.lazy == "raise"
    assert LegalRuleAlias.identity.property.lazy == "raise"
    assert LegalRuleRevision.identity.property.lazy == "raise"


def test_registry_created_at_defaults_are_database_now_expressions():
    for model in (LegalRuleIdentity, LegalRuleAlias, LegalRuleRevision):
        default = model.__table__.c.created_at.server_default
        assert default is not None
        assert "now()" in str(default.arg)



def test_revision_effective_intervals_are_database_guarded_against_overlap():
    migration = (
        Path(__file__).resolve().parents[2]
        / "alembic"
        / "versions"
        / "0116_canonical_rule_identity_registry.py"
    )
    source = migration.read_text(encoding="utf-8")
    assert "pg_advisory_xact_lock" in source
    assert "hashtextextended(NEW.canonical_rule_id::text, 0)" in source
    assert "daterange(" in source
    assert "existing.effective_from, existing.effective_to, '[)'" in source
    assert "NEW.effective_from, NEW.effective_to, '[)'" in source
    assert "trg_legal_rule_revision_no_overlap" in source
    assert "BEFORE INSERT ON public.legal_rule_revisions" in source
    assert "Overlapping effective interval" in source
    assert "REVOKE ALL ON FUNCTION public.prevent_legal_rule_revision_overlap()" in source
