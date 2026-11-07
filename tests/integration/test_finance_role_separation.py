"""Database-level separation between legal staff and finance staff."""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.models.database import set_rls_context


@pytest.mark.asyncio
async def test_legal_staff_is_not_finance_staff_under_signed_rls(api_client, db):
    legal_user_id = uuid.uuid5(uuid.NAMESPACE_DNS, "nlc-test-user-LEGAL_STAFF")
    company_id = uuid.uuid4()

async def test_legal_staff_is_not_finance_staff_under_signed_rls(api_client, db, db_company):
    from app.models.company import CompanyUserAccess
    from app.models.enums import UserRole
    from app.models.user import User
    from app.models.database import set_admin_context

    legal_user = User(
        id=uuid.uuid4(),
        email=f"finance-legal-{uuid.uuid4().hex[:8]}@nlctest.com",
        full_name="Legal Staff With Financial Membership",
        password_hash="!test-no-login",
        role=UserRole.LEGAL_STAFF,
        is_active=True,
        totp_enabled=False,
    )
    await set_admin_context(db)
    db.add(legal_user)
    await db.flush()
    db.add(
        CompanyUserAccess(
            user_id=legal_user.id,
            company_id=db_company.id,
            can_edit=True,
            can_view_financials=True,
            is_active=True,
        )
    )
    await db.flush()

    legal_user_id = legal_user.id
    company_id = db_company.id
    await set_rls_context(db, str(legal_user_id))
    result = await db.execute(
        text("""
            SELECT
                public.nlc_current_user_is_staff() AS is_staff,
                public.nlc_current_user_is_finance_staff() AS is_finance,
                public.nlc_can_view_billing_company(:company_id) AS can_view_billing,
                public.nlc_can_submit_payment_company(:company_id) AS can_submit_payment,
                public.nlc_can_manage_billing_company(:company_id) AS can_manage_billing
        """),
        {"company_id": company_id},
    )
    row = result.one()

    assert row.is_staff is True
    assert row.is_finance is False
    assert row.can_view_billing is False
    assert row.can_submit_payment is False
    assert row.can_manage_billing is False


@pytest.mark.asyncio
async def test_admin_staff_has_finance_access_under_signed_user_identity(api_client, db):
    admin_user_id = uuid.uuid5(uuid.NAMESPACE_DNS, "nlc-test-user-ADMIN_STAFF")
    company_id = uuid.uuid4()

    await set_rls_context(db, str(admin_user_id))
    result = await db.execute(
        text("""
            SELECT
                public.nlc_current_user_is_finance_staff() AS is_finance,
                public.nlc_can_view_billing_company(:company_id) AS can_view_billing,
                public.nlc_can_submit_payment_company(:company_id) AS can_submit_payment,
                public.nlc_can_manage_billing_company(:company_id) AS can_manage_billing
        """),
        {"company_id": company_id},
    )
    row = result.one()

    assert row.is_finance is True
    assert row.can_view_billing is True
    assert row.can_submit_payment is True
    assert row.can_manage_billing is True


@pytest.mark.asyncio
async def test_finance_rows_are_tenant_scoped_and_hidden_from_legal_staff(
    api_client, db, db_company, db_other_company, db_client_user, db_user
):
    """Exercise actual invoice rows, not only authorization helper functions."""
    from decimal import Decimal

    from sqlalchemy import select
    from app.models.finance import Invoice
    from app.services.finance_service import FinanceService

    service = FinanceService(db)
    created = []
    for company in (db_company, db_other_company):
        invoice = await service.create_invoice(
            company_id=company.id,
            engagement_id=None,
            lines=[{
                "description": "Tenant isolation test",
                "quantity": "1",
                "unit_price_bdt": "100.00",
            }],
            tax_bdt=Decimal("0.00"),
            due_at=None,
            notes=None,
            actor_id=db_user.id,
        )
        created.append(await service.issue_invoice(invoice.id))

    # A real client identity can read its own invoice, but not another tenant's.
    await set_rls_context(db, str(db_client_user.id))
    visible_ids = set((await db.execute(select(Invoice.id))).scalars().all())
    assert created[0].id in visible_ids
    assert created[1].id not in visible_ids

    # A client must not create a payment claim against another tenant's invoice,
    # even when the foreign invoice UUID and company UUID are known.
    with pytest.raises(DBAPIError):
        async with db.begin_nested():
            await db.execute(
                text("""
                    INSERT INTO public.payment_submissions
                        (id, company_id, invoice_id, submitted_by, method,
                         amount_bdt, currency, status)
                    VALUES
                        (:id, :company_id, :invoice_id, :submitted_by,
                         'CASH', 1.00, 'BDT', 'PENDING_REVIEW')
                """),
                {
                    "id": uuid.uuid4(),
                    "company_id": db_other_company.id,
                    "invoice_id": created[1].id,
                    "submitted_by": db_client_user.id,
                },
            )

    # Legal staff has no billing visibility and cannot mutate finance rows.
    legal_user_id = uuid.uuid5(uuid.NAMESPACE_DNS, "nlc-test-user-LEGAL_STAFF")
    await set_rls_context(db, str(legal_user_id))
    legal_visible_ids = set((await db.execute(select(Invoice.id))).scalars().all())
    assert created[0].id not in legal_visible_ids
    result = await db.execute(
        text("UPDATE public.invoices SET notes = 'unauthorized' WHERE id = :invoice_id"),
        {"invoice_id": created[0].id},
    )
    assert result.rowcount == 0

    # No invoice INSERT policy exists for legal staff; PostgreSQL must reject it.
    with pytest.raises(DBAPIError):
        async with db.begin_nested():
            await db.execute(
                text("""
                    INSERT INTO public.invoices
                        (id, company_id, invoice_number, currency, subtotal_bdt,
                         tax_bdt, total_bdt, paid_bdt, balance_bdt, status)
                    VALUES
                        (:id, :company_id, :number, 'BDT', 1.00, 0.00, 1.00,
                         0.00, 1.00, 'DRAFT')
                """),
                {
                    "id": uuid.uuid4(),
                    "company_id": db_company.id,
                    "number": f"LEGAL-DENIED-{uuid.uuid4().hex[:10]}",
                },
            )
            await db.flush()


@pytest.mark.asyncio
async def test_finance_table_privileges_enforce_append_only_boundaries(api_client, db, db_user):
    """Inspect effective PostgreSQL grants, not just migration source text."""
    await set_rls_context(db, str(db_user.id))
    result = await db.execute(text("""
        SELECT
            has_table_privilege(current_user, 'public.payment_allocations', 'UPDATE') AS allocation_update,
            has_table_privilege(current_user, 'public.payment_allocations', 'DELETE') AS allocation_delete,
            has_table_privilege(current_user, 'public.payment_ledger_events', 'UPDATE') AS ledger_update,
            has_table_privilege(current_user, 'public.payment_ledger_events', 'DELETE') AS ledger_delete,
            has_table_privilege(current_user, 'public.payment_provider_events', 'UPDATE') AS provider_event_update,
            has_table_privilege(current_user, 'public.payment_provider_events', 'DELETE') AS provider_event_delete,
            has_table_privilege(current_user, 'public.payment_provider_events', 'INSERT') AS provider_event_insert
    """))
    row = result.one()
    assert row.allocation_update is False
    assert row.allocation_delete is False
    assert row.ledger_update is False
    assert row.ledger_delete is False
    assert row.provider_event_update is False
    assert row.provider_event_delete is False
    assert row.provider_event_insert is True


@pytest.mark.asyncio
async def test_runtime_role_is_nonprivileged_and_finance_tables_force_rls(api_client, db, db_user):
    """Prove the effective runtime role cannot bypass or own finance RLS tables."""
    await set_rls_context(db, str(db_user.id))

    role_result = await db.execute(text("""
        SELECT current_user AS role_name,
               r.rolsuper AS is_superuser,
               r.rolbypassrls AS bypasses_rls,
               r.rolcreaterole AS can_create_roles,
               r.rolcreatedb AS can_create_databases,
               r.rolinherit AS inherits_role_privileges,
               r.rolreplication AS can_replicate,
               has_schema_privilege(current_user, 'nlc_private', 'USAGE') AS can_use_private_schema,
               has_table_privilege(
                   current_user,
                   (SELECT c.oid
                      FROM pg_class c
                      JOIN pg_namespace n ON n.oid = c.relnamespace
                     WHERE n.nspname = 'nlc_private'
                       AND c.relname = 'rls_signing_key'),
                   'SELECT'
               ) AS can_read_rls_signing_key,
               has_table_privilege(
                   current_user,
                   (SELECT c.oid
                      FROM pg_class c
                      JOIN pg_namespace n ON n.oid = c.relnamespace
                     WHERE n.nspname = 'nlc_private'
                       AND c.relname = 'rls_signing_key'),
                   'INSERT'
               ) AS can_insert_rls_signing_key,
               has_table_privilege(
                   current_user,
                   (SELECT c.oid
                      FROM pg_class c
                      JOIN pg_namespace n ON n.oid = c.relnamespace
                     WHERE n.nspname = 'nlc_private'
                       AND c.relname = 'rls_signing_key'),
                   'UPDATE'
               ) AS can_update_rls_signing_key,
               EXISTS (
                   SELECT 1
                     FROM pg_roles target_role
                    WHERE (target_role.rolsuper OR target_role.rolbypassrls OR target_role.rolcreaterole)
                      AND pg_has_role(current_user, target_role.oid, 'MEMBER')
               ) AS member_of_privileged_role
          FROM pg_roles r
         WHERE r.rolname = current_user
    """))
    role = role_result.one()
    assert role.role_name == "nlc_app_role"
    assert role.is_superuser is False
    assert role.bypasses_rls is False
    assert role.can_create_roles is False
    assert role.can_create_databases is False
    assert role.inherits_role_privileges is False
    assert role.can_replicate is False
    assert role.can_use_private_schema is False
    assert role.can_read_rls_signing_key is False
    assert role.can_insert_rls_signing_key is False
    assert role.can_update_rls_signing_key is False
    assert role.member_of_privileged_role is False

    tables_result = await db.execute(text("""
        SELECT count(*) AS protected_table_count,
               count(*) FILTER (WHERE c.relrowsecurity AND c.relforcerowsecurity) AS forced_rls_count,
               count(*) FILTER (WHERE c.relowner <> (SELECT oid FROM pg_roles WHERE rolname = current_user)) AS not_owned_by_runtime_count
          FROM pg_class c
          JOIN pg_namespace n ON n.oid = c.relnamespace
         WHERE n.nspname = 'public'
           AND c.relname = ANY(ARRAY[
               'invoices', 'invoice_lines', 'payment_submissions', 'payments',
               'payment_allocations', 'payment_ledger_events', 'payment_intents',
               'payment_provider_events', 'client_subscriptions'
           ])
           AND c.relkind = 'r'
    """))
    tables = tables_result.one()
    assert tables.protected_table_count == 9
    assert tables.forced_rls_count == 9
    assert tables.not_owned_by_runtime_count == 9

@pytest.mark.asyncio
async def test_signed_rls_identity_rejects_session_variable_impersonation(api_client, db, db_user):
    """Caller-controlled GUC values cannot impersonate another user or staff."""
    await set_rls_context(db, str(db_user.id))

    valid = await db.execute(text("""
        SELECT public.nlc_current_user_id() AS verified_id,
               public.nlc_current_user_context_valid() AS context_valid,
               current_setting('app.current_user_signature', true) AS own_signature
    """))
    valid_row = valid.one()
    assert valid_row.verified_id == db_user.id
    assert valid_row.context_valid is True

    forged_id = uuid.uuid4()
    await db.execute(
        text("SELECT set_config('app.current_user_id', :uid, true)"),
        {"uid": str(forged_id)},
    )
    forged = await db.execute(text("""
        SELECT public.nlc_current_user_principal() AS principal,
               public.nlc_current_user_id() AS verified_id,
               public.nlc_current_user_context_valid() AS context_valid,
               public.nlc_current_user_is_staff() AS is_staff
    """))
    forged_row = forged.one()
    assert forged_row.principal is None
    assert forged_row.verified_id is None
    assert forged_row.context_valid is False
    assert forged_row.is_staff is False

    # Even a syntactically valid signature is useless without the database key.
    await db.execute(
        text("""
            SELECT set_config('app.current_user_id', :uid, true),
                   set_config('app.current_user_signature', :signature, true)
        """),
        {"uid": str(forged_id), "signature": "0" * 64},
    )
    forged_again = await db.execute(text("""
        SELECT public.nlc_current_user_principal() AS principal,
               public.nlc_current_user_id() AS verified_id
    """))
    forged_again_row = forged_again.one()
    assert forged_again_row.principal is None
    assert forged_again_row.verified_id is None

    # Reusing a valid signature for a different principal must not elevate a
    # tenant identity to the privileged ADMIN service principal.
    await db.execute(
        text("""
            SELECT set_config('app.current_user_id', 'ADMIN', true),
                   set_config('app.current_user_signature', :signature, true)
        """),
        {"signature": valid_row.own_signature},
    )
    admin_spoof = await db.execute(text("""
        SELECT public.nlc_current_user_principal() AS principal,
               public.nlc_current_user_is_staff() AS is_staff,
               public.nlc_current_user_is_finance_staff() AS is_finance_staff
    """))
    admin_spoof_row = admin_spoof.one()
    assert admin_spoof_row.principal is None
    assert admin_spoof_row.is_staff is False
    assert admin_spoof_row.is_finance_staff is False
