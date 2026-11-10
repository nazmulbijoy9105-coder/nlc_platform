"""add statutory calendar legal provenance

Revision ID: 0091_calendar_legal_provenance
Revises: 0090_rule_registry_drift_quarantine
"""
from alembic import op
import sqlalchemy as sa

revision = "0091_calendar_legal_provenance"
down_revision = "0090_rule_registry_drift_quarantine"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("compliance_calendar_events", sa.Column("legal_rule_id", sa.String(length=100), nullable=True))
    op.add_column("compliance_calendar_events", sa.Column("legal_source_citation", sa.Text(), nullable=True))
    op.add_column("compliance_calendar_events", sa.Column("legal_source_version", sa.String(length=100), nullable=True))
    op.add_column("compliance_calendar_events", sa.Column("legal_effective_from", sa.Date(), nullable=True))
    op.add_column("compliance_calendar_events", sa.Column("legal_effective_to", sa.Date(), nullable=True))
    op.add_column("compliance_calendar_events", sa.Column("legal_trigger_date", sa.Date(), nullable=True))
    op.add_column("compliance_calendar_events", sa.Column("trigger_evidence_ref", sa.Text(), nullable=True))
    op.add_column("compliance_calendar_events", sa.Column("legal_manifest_sha256", sa.String(length=64), nullable=True))
    op.create_index(
        "ix_compliance_calendar_events_legal_rule_id",
        "compliance_calendar_events",
        ["legal_rule_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_compliance_calendar_events_legal_rule_id", table_name="compliance_calendar_events")
    op.drop_column("compliance_calendar_events", "legal_manifest_sha256")
    op.drop_column("compliance_calendar_events", "trigger_evidence_ref")
    op.drop_column("compliance_calendar_events", "legal_trigger_date")
    op.drop_column("compliance_calendar_events", "legal_effective_to")
    op.drop_column("compliance_calendar_events", "legal_effective_from")
    op.drop_column("compliance_calendar_events", "legal_source_version")
    op.drop_column("compliance_calendar_events", "legal_source_citation")
    op.drop_column("compliance_calendar_events", "legal_rule_id")
