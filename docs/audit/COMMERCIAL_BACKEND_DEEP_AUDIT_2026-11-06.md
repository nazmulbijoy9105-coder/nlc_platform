# NLC Commercial Backend Deep Audit

**Date:** 2026-11-06  
**Scope:** Existing commercial/revenue backend before implementing two-sided workspace and Bangladesh payments.  
**Method:** Inspected current default-branch source for commercial ORM, API router, commercial service, entitlement dependency, model registry, app router registration, signed-identity migration and commercial/RLS verification code. This is a source audit, not a live-database, production or CI certification.

## Executive result

**NOT READY for payment processing or subscription enforcement.** Existing commercial functionality is a pipeline/quotation/task foundation, not a complete billing, collection, payment-ledger or subscription system. Do not connect live bKash, Nagad, SSLCommerz or activate paid entitlements on this baseline.

## Confirmed findings

### P0 — Entitlement check is explicitly fail-open
File: `app/core/entitlement.py`

- `_check_subscription_active()` returns `True` unconditionally.
- Source comment says subscription query is TODO and permissive until a Subscription model exists.
- Staff users without `company_id` are allowed through the dependency.
- Therefore any route relying on `require_entitlement()` does not enforce a paid subscription today.
- Required: implement actual company membership + active subscription + feature/package + effective-date query; fail closed on missing company/plan/database error; staff bypass must be explicit and permission-scoped, not implicit.

### P0 — No canonical payment/ledger model demonstrated
Files: `app/models/commercial.py`, `app/models/__init__.py`, migrations and model search.

- Commercial ORM currently registers Task, Engagement and Quotation.
- Existing `payments`, `invoices`, `commercial_packages` and `commercial_subscriptions` appear in legacy verification/migration references, but they are not imported in the current ORM model registry excerpt and no current payment/invoice ORM domain was identified in the inspected model search.
- No provider transaction lifecycle, payment intent, allocation, offline verification, refund/reversal or append-only financial ledger implementation was identified.
- Required: map actual deployed tables and every migration before adding schema; do not assume those legacy table names represent working application features.

### P0 — Customer-facing commercial visibility is architecturally incomplete
Files: `app/models/commercial.py`, `app/api/commercial.py`, `0050_signed_rls_identity_hardening.py`.

- Engagement is explicitly documented and RLS-protected as staff-only.
- Quotation RLS permits company SELECT through `nlc_can_access_company(company_id)`, but writes are staff-only.
- API module declares commercial endpoints admin/staff gated. A customer workspace cannot be built by exposing the internal revenue router.
- Required: a separate customer billing/quotation API with tenant-scoped ownership checks and safe response schemas; do not weaken staff-only Engagement or revenue RLS.

### P1 — Money values cross API/service boundaries as binary floats
Files: `app/api/commercial.py`, `app/services/commercial_service.py`.

- Engagement/quotation request schemas and service signatures use `float` for BDT.
- Pipeline analytics convert SQL Decimal-like values to float.
- This is inappropriate for authoritative monetary calculation/reconciliation.
- Required: Decimal parsing and SQL NUMERIC with explicit rounding/tax policy, or integer poisha. Never use float for persisted or reconciled money.

### P1 — Quotation validity calculation is defective
File: `app/services/commercial_service.py`

- `create_quotation()` sets `valid_until` to `date.today().replace(day=date.today().day)`, which is simply today, not today plus `valid_days`.
- Required: timezone/business-date policy and `timedelta(days=valid_days)`; tests for month/year boundaries and expired quotations.

### P1 — Quotation number generation is race-prone
File: `app/services/commercial_service.py`

- `_next_quotation_number()` uses COUNT(*) + 1 without locking/sequence allocation.
- Concurrent requests can calculate the same number and collide on the unique constraint.
- Required: database sequence or dedicated locked counter / collision-safe retry with unique constraint.

### P1 — Revenue pipeline is not a cash ledger
File: `app/services/commercial_service.py`, `app/models/commercial.py`

- Pipeline reads `vw_revenue_pipeline` and sums engagement denormalized estimated/quoted/confirmed/invoiced/collected BDT fields.
- No demonstrated link from collected amounts to verified payment records, allocations, gateway settlement, bank reconciliation or refunds.
- A `collected_bdt` engagement field is not proof of money received.
- Required: calculate collections from verified payment/ledger allocations; separate cash collected, receivables, deferred revenue and recognised revenue.

### P1 — Quotation company/engagement consistency needs a server-side invariant
Files: `app/api/commercial.py`, `app/services/commercial_service.py`

- Quotation creation accepts both `engagement_id` and `company_id`.
- Service inserts both values but the inspected implementation does not first prove that the engagement belongs to the supplied company.
- Required: derive company_id from the locked engagement row; reject mismatches; add cross-tenant and mismatch tests.

### P1 — Quotation sequence and lifecycle need stronger transactional controls
- Accept/reject methods load by quotation ID and update status without an observed conditional state transition/row lock in the inspected service.
- Required: lock row, validate current status and validity, record actor/timestamp, and perform atomic state transition.

### P1 — Entitlement model mismatch with intended paid plans
- Entitlement dependency expects `commercial_subscriptions` and `commercial_packages`, but the current model registry imports only Task/Engagement/Quotation from commercial.py and no Subscription/Package models were identified in the inspected registry.
- Required: reconcile deployed schema vs ORM vs Alembic before migration design.

## Security/migration observations

- Migration `0050_signed_rls_identity_hardening.py` establishes signed identity helper functions and staff-only policies for `engagements`; quotations have company-read and staff-write policies.
- Do not assume a new financial table inherits protection automatically. Every new table requires explicit RLS enable + FORCE, signed-identity policies, grants, ownership and runtime-role tests.
- `verify_commercial.py` includes static checks for commercial lifecycle, tenant document access and entitlement checks, but static source scanning is not proof of runtime enforcement.
- The migration's global grants to `nlc_app_role` are broad and depend on RLS; new financial records must have restrictive row policies and column/operation constraints. Financial append-only rules need DB-level enforcement, not UI convention.
- Need inspect exact deployed schema, migration heads, policy catalog, role attributes, and tests on the actual production/staging database before asserting RLS readiness.

## Required implementation order

1. Freeze payment-provider integration and paid feature activation.
2. Establish exact main SHA, CI results, Alembic heads/current, live schema parity and runtime role.
3. Reconcile every existing commercial/package/subscription/invoice/payment table and migration with ORM registry.
4. Fix entitlement fail-open and add tests before relying on any subscription gate.
5. Correct quotation validity, concurrency, Decimal and engagement/company binding.
6. Design invoice, payment intent, verified payment, allocation, offline submission/review, refunds/reversals, immutable ledger, provider events and reconciliation with tenant RLS.
7. Implement sandbox-only gateway adapters after ledger and security tests.
8. Add separate customer billing APIs and staff finance APIs.
9. Build frontend only against the verified API contract.

## Acceptance gates

- Entitlement checks fail closed and test company membership, plan feature, date window, suspended/expired states, staff roles and missing records.
- Quotation company is derived from engagement; mismatch and cross-tenant access denied.
- Quotation validity adds the requested number of days; sequence survives concurrent creation.
- All financial amounts use exact decimal/poisha arithmetic.
- Settled payments require authenticated provider evidence or authorized offline finance approval.
- Duplicate provider events are idempotent.
- Invoice balances reconcile to allocations, refunds and reversals.
- New financial tables have forced RLS and pass direct runtime-role cross-tenant tests.
- Revenue dashboard reconciles to the ledger, never engagement estimates.
- No live gateway until merchant onboarding and end-to-end settlement reconciliation are proven.

## Limitations

This report does not claim live database access, current CI success, full Alembic graph validation, production deployment parity, or exhaustive line-by-line review of all backend modules. Those require a reproducible checkout and database/CI evidence.