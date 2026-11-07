"""Derive commercial pipeline invoiced/collected amounts from verified finance ledger.

Revision ID: 0066_verified_revenue_pipeline
Revises: 0065_rescue_audit_log_restrict_delete
"""
from alembic import op

revision = "0066_verified_revenue_pipeline"
down_revision = "0065_rescue_audit_log_restrict_delete"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Engagement.invoiced_bdt and collected_bdt are legacy manually maintained
    # fields. They are not evidence of an issued invoice or settled receipt.
    # Derive both metrics from the canonical finance ledger instead.
    op.execute("""
        CREATE OR REPLACE VIEW public.vw_revenue_pipeline\n        WITH (security_invoker = true) AS
        WITH invoice_totals AS (
            SELECT
                engagement_id,
                company_id,
                SUM(total_bdt) AS total_invoiced_bdt
            FROM public.invoices
            WHERE engagement_id IS NOT NULL
              AND status NOT IN ('DRAFT', 'VOID')
            GROUP BY engagement_id, company_id
        ),
        collected_totals AS (
            SELECT
                i.engagement_id,
                i.company_id,
                SUM(a.amount_bdt) AS total_collected_bdt
            FROM public.invoices i
            JOIN public.payment_allocations a
              ON a.invoice_id = i.id
             AND a.company_id = i.company_id
            JOIN public.payments p
              ON p.id = a.payment_id
             AND p.company_id = a.company_id
            WHERE i.engagement_id IS NOT NULL
              AND i.status NOT IN ('DRAFT', 'VOID')
              AND p.status = 'SETTLED'
            GROUP BY i.engagement_id, i.company_id
        )
        SELECT
            e.revenue_tier,
            e.engagement_status,
            COUNT(*) AS engagement_count,
            SUM(e.estimated_fee_bdt) AS total_estimated_bdt,
            SUM(e.quoted_fee_bdt) AS total_quoted_bdt,
            SUM(e.confirmed_fee_bdt) AS total_confirmed_bdt,
            SUM(COALESCE(it.total_invoiced_bdt, 0)) AS total_invoiced_bdt,
            SUM(COALESCE(ct.total_collected_bdt, 0)) AS total_collected_bdt
        FROM public.engagements e
        LEFT JOIN invoice_totals it
          ON it.engagement_id = e.id
         AND it.company_id = e.company_id
        LEFT JOIN collected_totals ct
          ON ct.engagement_id = e.id
         AND ct.company_id = e.company_id
        WHERE e.is_active IS TRUE
        GROUP BY e.revenue_tier, e.engagement_status
        ORDER BY e.revenue_tier, e.engagement_status
    """)


def downgrade() -> None:
    # Forward-only: restoring manually maintained invoiced/collected fields
    # would make revenue intelligence diverge from the verified finance ledger.
    pass
