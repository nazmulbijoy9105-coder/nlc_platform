"""Invalidate legacy company-level statutory scores while counsel approval is pending.

Revision ID: 0052_invalidate_unreleased_legacy_scores
Revises: 0051_nullable_unreleased_score_history

Historical monthly snapshots remain immutable. Current company state is cleared
so legacy, unapproved scores cannot be mistaken for a current legal assessment.
The API independently applies the release gate to historical rows as well.

The NOT_EVALUATED enum label is introduced by revision 0021. The Alembic
environment commits its per-migration transaction before later revisions run,
so this revision must not re-add the enum value or cross an autocommit boundary.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0052_invalidate_unreleased_legacy_scores"
down_revision: Union[str, Sequence[str], None] = "0051_nullable_unreleased_score_history"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE public.companies
        SET current_compliance_score = NULL,
            current_risk_band = 'NOT_EVALUATED',
            current_exposure_band = NULL,
            rescue_required = FALSE
        WHERE current_compliance_score IS NOT NULL
           OR current_risk_band IS DISTINCT FROM 'NOT_EVALUATED'
           OR current_exposure_band IS NOT NULL
           OR rescue_required IS TRUE
        """
    )


def downgrade() -> None:
    # Forward-only: prior scores were produced before the counsel-approved
    # rule release gate. Reconstructing them would falsely certify their status.
    pass
