# NLC Two-Sided Commercial Platform — Architecture Contract

**Status:** Design baseline; implementation not yet released  
**Date:** 2026-11-05  
**Scope:** Customer workspace, internal business workspace, Bangladesh online/offline payments

## 1. Existing-system constraints

The backend already mounts `app.api.commercial` and has commercial Engagement, Quotation and Task models/services. Extend these canonical domains; do not create a parallel CRM or engagement subsystem.

Preserve the deterministic RJSC compliance engine, counsel approval/release gates, evaluation snapshots, signed RLS identity and the non-superuser `nlc_app_role`. New financial tables must be included in the signed-identity/RLS design and tested using the actual runtime role.

The latest inspected backend main is `b2a27bb5903d238e1a9241d970dded2f15aeb7dc`. The latest inspected frontend main is `5ba7c30ead4b738e06a77ea6c5b5c7b1bcc2a01a`. This document is not evidence that CI or production deployment is green.

## 2. Product surfaces

### Customer workspace

- Company portfolio and authorized company switching
- Compliance overview, statutory deadlines and filing status
- Filings, document vault and service requests
- Subscription plan, renewal date and entitlements
- Invoices, payment instructions, payment submission, receipts and payment history
- Clear pending/verified/failed/reversed states

Customers may access only companies explicitly granted to their authenticated identity. Customer UI and API responses must not expose internal leads, staff notes, other tenants, finance approvals, cost/margin data or internal revenue analytics.

### Internal business workspace

- Leads, prospects, clients and conversion pipeline
- Quotations, engagements and service catalogue
- Service delivery milestones, assigned staff and counsel review
- Invoice issuance, receivables, collections and reconciliation
- Refunds, reversals, credit notes and write-off approvals
- Revenue intelligence and audit reports
- Role-controlled finance, legal operations and system administration

Separate permissions for sales/CRM, legal delivery, finance approval and system administration. UI hiding is not authorization; every API endpoint must enforce server-side role and object access.

## 3. Financial domain model

Use explicit normalized records with stable UUIDs and immutable identifiers. Proposed entities (subject to audit of existing schema before migration):

- `service_catalogue_items` and versioned `subscription_plans`
- `client_subscriptions` and `subscription_events`
- `invoices` and `invoice_lines`
- `payment_intents` for online checkout initiation
- `payments` for verified receipts/settlements
- `payment_allocations` to apply a payment to one or more invoices
- `payment_provider_events` for idempotent webhook/event ingestion
- `offline_payment_submissions` for customer-entered transfer/cash/cheque details and proof
- `payment_reversals` / refund records and immutable `financial_ledger_entries`
- `reconciliation_batches` and `audit_events`

Do not duplicate any existing equivalent entity. First map the current Engagement, Quotation, Task, user, company and activity-log schema.

### Money and status rules

- Initial currency: BDT. Persist exact amounts as integer poisha or SQL NUMERIC/Decimal; never binary float.
- Store provider amount/currency and compare them to the expected invoice amount/currency server-side.
- Invoice lifecycle and payment lifecycle are separate state machines.
- Suggested invoice states: DRAFT, ISSUED, PARTIALLY_PAID, PAID, VOID, OVERDUE.
- Suggested payment states: INITIATED, PENDING_PROVIDER, PENDING_REVIEW, SETTLED, FAILED, REVERSED, REFUNDED, DISPUTED.
- A payment is not settled because the browser returns to a success URL, the customer uploads a screenshot, or a client supplies a transaction reference.
- Partial payments, overpayments, unapplied credits, duplicate detection, allocation, reversals and refunds must reconcile exactly.
- Corrections use reversal/adjustment ledger entries; never mutate or delete a settled financial event.
- Subscription activation/extension is a separate idempotent entitlement event triggered only by confirmed settlement and successful invoice allocation.
- Distinguish gross invoice value, cash collected, gateway fees, refunds, receivables, deferred subscription revenue and recognised revenue. Forecasts are not actual revenue.

## 4. Bangladesh payment methods

### Online gateway adapters

Implement a provider-neutral interface first. Candidate providers for merchant eligibility and technical evaluation:

- SSLCommerz hosted checkout
- bKash merchant checkout/API
- Nagad merchant payment API

Provider selection is not final until merchant onboarding, current provider documentation, settlement terms, fees, sandbox access and production callback requirements are verified.

Required adapter operations: create checkout, verify transaction/status, parse and authenticate webhook/callback, query transaction, and request refund where supported.

Security requirements:
- Keep merchant secrets server-side only.
- Prefer hosted checkout/tokenized provider flows; never store card PAN/CVV.
- Authenticate callbacks using the provider's documented signature/token/IP/status verification; additionally query provider status server-to-server where supported.
- Enforce idempotency on checkout creation and provider event/transaction IDs.
- Verify merchant/order reference, invoice, amount, currency and final provider status.
- Persist redacted provider event evidence and correlation IDs.
- Browser redirect is informational only; settlement occurs only after verified server-side evidence.
- Rate-limit public initiation/status endpoints and protect against replay.

### Offline and assisted payments

Support:
- Bank transfer / BEFTN / RTGS / NPSB where applicable
- Cash received by authorized staff
- Cheque (not settled until cleared)
- Manual merchant bKash/Nagad receipt

Customer submission fields: invoice, amount, method, payer/reference, payment date, optional evidence file. Submission status remains PENDING_REVIEW. Authorized finance staff verifies against bank/merchant/cash records, records reviewer, timestamp, decision and reason, then posts a settlement and allocation transaction atomically. A submitted receipt or screenshot alone is not proof of settlement.

## 5. API boundaries

Proposed route families, to align with existing router conventions after source audit:

- `/api/v1/customer/*`: customer-visible company workspace
- `/api/v1/billing/*`: customer invoices, plans and payment history
- `/api/v1/payments/*`: checkout initiation, status, offline submissions
- `/api/v1/webhooks/payments/{provider}`: provider callback ingestion
- `/api/v1/commercial/*`: staff CRM, quotations, engagements and service delivery
- `/api/v1/finance/*`: invoices, approvals, allocations, refunds and reconciliation
- `/api/v1/revenue/*`: staff-only analytics and exports

Do not create these route groups until existing routes are mapped and duplicate capabilities are ruled out.

## 6. Revenue reporting definitions

Every metric must have a written definition and reproducible query:

- Collected revenue/cash receipts: verified settled receipts net/gross clearly labelled, with fees and refunds separately disclosed.
- Accounts receivable: issued invoice balance less verified allocations and credits.
- MRR: active recurring contract value normalized to a monthly period; exclude one-off services.
- ARR: eligible recurring run-rate, not cash collected.
- New paying clients: first verified settlement within the reporting period.
- Churn/renewals: subscription events, not arbitrary invoice status.
- Service-line profitability: only when direct costs are captured; otherwise show revenue, not profit.
- Recognised revenue: follow the adopted accounting policy; do not equate invoice issue or payment receipt automatically with earned revenue.

## 7. Security and audit

- Tenant isolation and signed RLS identity on every customer-owned financial row.
- Runtime database role remains non-superuser and NOBYPASSRLS.
- Finance approval/refund/write-off permissions separated from client and general staff roles.
- Append-only ledger/provider-event audit; sensitive fields and secrets redacted from logs.
- Secure evidence upload with content-type/size validation, malware scanning strategy, private object storage and authorization on download.
- No cross-tenant object references through invoice IDs, payment IDs or uploaded evidence.
- Every manual action records actor, role, timestamp, reason and before/after state where appropriate.

## 8. Delivery gates

1. Verify current main CI, Alembic single-head status, signed RLS identity, production DB/API parity and deployment state.
2. Audit existing commercial models, services, routers, permissions, migrations and frontend route/component structure.
3. Publish the canonical API contract and migration design.
4. Implement invoice/ledger/allocation and offline review first, with migration, unit, integration and RLS tests.
5. Implement gateway adapter in sandbox mode with replay/idempotency and reconciliation tests.
6. Implement responsive customer and internal workspace surfaces, with role-aware navigation.
7. Add revenue reports only after ledger reconciliation tests pass.
8. Deploy staging and run end-to-end synthetic transactions; enable live gateways only after merchant approval, production credentials, callback configuration and verified settlement evidence.

## 9. Minimum acceptance tests

- Cross-tenant invoice, payment, subscription and evidence access is denied at API and database layers.
- Client role cannot access CRM, finance approval, collections or revenue reports.
- Forged, stale, duplicate and mismatched-amount callbacks cannot settle invoices.
- Callback retry is idempotent and cannot duplicate payment, ledger or subscription events.
- Offline payment stays pending until an authorized reviewer approves it.
- Cheque remains pending until clearance evidence is recorded.
- Partial payments and reversals produce exact invoice balances.
- Gateway fees, refunds, cash/bank receipts and allocations reconcile.
- Revenue metrics reconcile to source ledger entries and disclose their definitions.
- Frontend builds cleanly; 360px, 390px and 430px viewports have no horizontal overflow; mobile navigation uses a drawer.
- Existing legal-engine release gates and compliance-score approval semantics remain unchanged.

## 10. Live payment activation prerequisites

Live processing remains disabled until the business has active merchant accounts, approved KYC/onboarding, provider-issued production credentials, configured callback URLs, tested sandbox transactions, verified settlement/reconciliation and approved operational refund/dispute procedures.
