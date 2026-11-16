"""Structural safeguards for the additive canonical rule identity registry."""
from sqlalchemy import CheckConstraint, UniqueConstraint

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
