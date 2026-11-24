"""Reconcile the legacy AGM-001 statutory citation to canonical identity.

Revision ID: 0125_reconcile_agm001_statutory_basis
Revises: 0124_restore_85_rule_catalogue_parity

Only the exact known legacy citation is rewritten. Any unexpected value fails
closed rather than being silently overwritten.
"""
from alembic import op
import sqlalchemy as sa

revision = "0125_reconcile_agm001_statutory_basis"
down_revision = "0124_restore_85_rule_catalogue_parity"
branch_labels = None
depends_on = None

LEGACY_BASIS = "Section 81, Companies Act 1994 (Bangladesh)"
CANONICAL_BASIS = "Section 81(1), Companies Act 1994 (Bangladesh)"


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            UPDATE public.legal_rules
               SET statutory_basis = :canonical_basis,
                   updated_at = now()
             WHERE rule_id = 'AGM-001'
               AND statutory_basis = :legacy_basis
            """
        ),
        {
            "canonical_basis": CANONICAL_BASIS,
            "legacy_basis": LEGACY_BASIS,
        },
    )

    actual_basis = bind.execute(
        sa.text(
            """
            SELECT statutory_basis
              FROM public.legal_rules
             WHERE rule_id = 'AGM-001'
            """
        )
    ).scalar_one_or_none()

    if actual_basis != CANONICAL_BASIS:
        raise RuntimeError(
            "0125 refuses AGM-001 identity drift: "
            f"expected={CANONICAL_BASIS!r}, actual={actual_basis!r}"
        )


def downgrade() -> None:
    raise RuntimeError(
        "0125 is forward-only: reverting the canonical AGM-001 identity "
        "would reintroduce a known statutory-basis mismatch."
    )
