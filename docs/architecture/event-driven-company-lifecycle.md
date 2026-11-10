# Event-driven company lifecycle integration

## Purpose

Connect existing NLC company, people, shareholding, charge, registered-office,
filing, evidence, compliance and client-dashboard modules without replacing their
domain services or bypassing tenant authorization.

A service appends a domain event in the same SQLAlchemy transaction as its source
mutation. The publisher flushes but never commits. A failed source mutation cannot
leave a durable event, and a failed outbox insert cannot silently leave an
unannounced source mutation.

## Event contract

The outbox is `domain_event_outbox` (migration
`0105_domain_event_outbox`). Events contain an immutable UUID, event type and
schema version, tenant company ID, optional actor ID, aggregate type/UUID, compact
JSON payload, optional correlation ID, occurrence/availability timestamps, retry
metadata and processing state.

Payloads must not contain credentials, NID/passport values, raw personal data,
document contents, or presigned storage URLs. Consumers load source records by
aggregate ID when additional detail is required.

## Event producers

| Source mutation | Event |
|---|---|
| Company creation | `company.created` |
| Company fact assertion / verification | `company.fact.asserted`, `company.fact.verified` |
| Director appointment / departure | `company.director.changed` |
| Shareholder addition / holding update | `company.shareholder.changed` |
| Share transfer recorded | `company.share_transfer.changed` |
| Registered address update | `company.registered_office.changed` |
| Charge recorded / charge evidence reviewed | `company.charge.recorded`, `company.charge.evidence_verified` |
| AGM record / held status | `filing.agm.recorded`, `filing.agm.held_recorded` |
| AGM / annual return receipt details | `filing.receipt.recorded` |
| Annual return record / filed status | `filing.annual_return.recorded`, `filing.annual_return.filed` |
| Share or charge evidence verification | `evidence.verification.completed` |
| Approved calendar event | `deadline.calendar.generated` |
| AI document generated / approved / released | `evidence.document.generated`, `evidence.document.approved`, `evidence.document.released` |

Lifecycle producer payloads carry state metadata only; they do not carry director,
shareholder, transferor, transferee, charge-holder or office-address values.

## Dispatch and consumers

Celery task `app.worker.tasks.dispatch_domain_event_outbox` drains pending rows
with `FOR UPDATE SKIP LOCKED` and is scheduled once per minute. Company, people,
share, office, charge and filing mutations trigger deterministic company
reevaluation. Deadline events route to the existing deadline-warning scanner;
generated AI documents route to the existing human-review queue.

Filing receipts have a dedicated `consume_filing_receipt_event` consumer.
Evidence verification has a dedicated `consume_evidence_verification_event`
consumer. Each consumer claims the pair (event UUID, consumer name) in
`domain_event_consumptions` under a unique database constraint and performs its
compliance reevaluation in the same transaction. A repeated delivery therefore
does not repeat that consumer's database side effect.

Delivery is at-least-once. The dispatcher uses stable task IDs and bounded
exponential retry. Dispatch attempts are capped at eight; terminal failures are
marked dead-lettered. Consumer tasks retry transient failures and also mark the
source event dead-lettered after exhausting retries.

## Operations and replay

Migration `0106_domain_event_processing_controls` adds dead-letter timestamps and
reasons, replay count and last-replay timestamp, plus the idempotent consumer
receipt table.

Super-admin operations endpoints:

- `GET /api/v1/admin/domain-events?status=all|pending|dispatched|dead_lettered`
  returns counts and event metadata without exposing payloads.
- `POST /api/v1/admin/domain-events/{event_id}/replay` requeues only an
  unprocessed dead-lettered event. It preserves the event UUID and payload,
  clears transient dispatch state and increments the replay counter.

The client-facing `GET /api/v1/companies/{company_id}/activity` endpoint returns
a company-scoped, payload-free lifecycle timeline. Its query is constrained by
company ID and the outbox's forced tenant RLS.

## Evidence and legal safeguards

- Uploading a document does not verify it or prove that a statutory act occurred.
- AI-generated drafts remain excluded as source evidence.
- Fact and evidence verification remains an explicit staff action with reviewer
  provenance.
- A filing-receipt event records whether a receipt reference was supplied; it does
  not claim an authenticated RJSC integration.
- An event is a notification that a source record changed, not a legal conclusion.
- Deadline generation retains its existing approved calendar manifest and
  statutory provenance controls.
- The outbox has forced tenant RLS; runtime roles cannot delete or truncate event
  history. Consumer receipts are admin-worker-only and immutable to the app role.

## Remaining integration work

1. Generate/update first-class obligation instances from the event stream, with
   effective-date and applicability provenance.
2. Connect obligation remediation to explicit owner assignment, due dates,
   reassignment and completion evidence; do not silently infer legal verification
   from task completion.
3. Connect the frontend client dashboard to the new activity endpoint and expose
   actionable obligation/remediation states.
4. Add broader PostgreSQL end-to-end tests for worker dispatch, consumer retries,
   safe replay and real tenant visibility under the production runtime role.
5. Add operator metrics/alerts for queue age, retry volume, consumer lag and
   dead-letter growth.

This PR connects the backend lifecycle producers, dedicated receipt/evidence
consumers, dead-letter/replay controls and the tenant-scoped activity API. It does
not claim that obligation ownership or the frontend dashboard UI is complete.
