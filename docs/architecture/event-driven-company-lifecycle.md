# Event-driven company lifecycle integration

## Purpose

Connect the existing company, fact-provenance, statutory filing, deadline-calendar,
document-vault, compliance-evaluation and notification modules without replacing
their current domain services or tenant authorization boundaries.

The integration uses a transactional outbox. A service appends a domain event in
the same SQLAlchemy transaction as its source-row mutation. The service does not
commit; the request/task transaction remains the single commit boundary. A failed
source mutation therefore cannot leave a published event, and a failed event insert
cannot silently leave an unannounced source mutation.

## Event contract

Table: `domain_event_outbox` (migration `0105_domain_event_outbox`).

Each event carries:

- immutable event UUID, event type and schema version;
- tenant `company_id` and nullable actor ID;
- aggregate type and aggregate UUID;
- compact JSON payload containing identifiers, state and provenance metadata;
- optional correlation ID;
- occurrence/availability timestamps, attempts, processed timestamp and last error.

Payloads must not contain credentials, raw personal data, document contents, or
presigned storage URLs. Event consumers load authorized source records by ID when
they need further information.

## Events currently emitted

| Source mutation | Event |
|---|---|
| Company creation | `company.created` |
| User-asserted or document-backed company fact | `company.fact.asserted` |
| Staff fact verification/rejection | `company.fact.verified` |
| AGM record created | `filing.agm.recorded` |
| AGM marked held | `filing.agm.held_recorded` |
| Annual return record created | `filing.annual_return.recorded` |
| Annual return marked filed | `filing.annual_return.filed` |
| Approved calendar event created/rescheduled | `deadline.calendar.generated` |
| AI document generated | `evidence.document.generated` |
| AI document approved | `evidence.document.approved` |
| Document released to client | `evidence.document.released` |

## Dispatcher and delivery semantics

Celery task `app.worker.tasks.dispatch_domain_event_outbox` drains pending rows
using `FOR UPDATE SKIP LOCKED` and is scheduled once per minute. It routes fact,
company and filing events to deterministic compliance reevaluation; AI document
generation routes to the existing human-review queue. Delivery is at-least-once:
a worker crash after broker publication but before the database commit can result
in redelivery. Consumers must therefore be idempotent and use the stable event UUID.

Failed broker publication retains the event and applies bounded exponential
backoff. Processed events remain in the table for auditability. Deadline and
document approval/release events are persisted for their dedicated downstream
consumers; they are not treated as proof of filing or legal verification.

## Evidence and legal safeguards

- Uploading a document does not verify it or prove that a statutory act occurred.
- AI-generated drafts remain excluded as source evidence.
- Fact verification remains a staff action with recorded reviewer provenance.
- An event is a notification that a source record changed, not a legal conclusion.
- Deadline generation still uses the existing approved calendar manifest and
  statutory provenance; this integration does not bypass its release gate.
- Annual-return filing events record whether an RJSC receipt number was supplied;
  they do not claim an authenticated RJSC integration.
- Tenant RLS is forced on the outbox and reuses the signed identity/company-access
  helpers. Runtime roles cannot delete or truncate event history.

## Remaining vertical-slice work

1. Add dedicated consumers for deadline-created/rescheduled, filing-receipt and
   evidence-verification events, with idempotency and dead-letter handling.
2. Add event-driven generation of obligation instances and owned UNKNOWN-applicability
   resolution tasks, retaining the existing rule/effective-date provenance.
3. Add director, shareholder, share-transfer, registered-office and charge events.
4. Add end-to-end tests proving one transaction creates the source row and outbox
   event, dispatcher retries safely, and downstream effects remain tenant-isolated.
5. Add operator visibility for pending, retried and failed events, plus replay tooling.

The current delivery is the shared integration backbone and initial connected
vertical slice; it does not claim that every remaining consumer or lifecycle domain
is complete.
