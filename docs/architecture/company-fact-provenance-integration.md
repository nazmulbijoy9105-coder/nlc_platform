# Company fact provenance and document-vault integration

## Persisted data model

Migration `0104_company_fact_provenance` creates `company_facts`, with a versioned row per asserted fact. Each row records the company, fact key/value, who asserted it, observation date, source reference, trust level, optional existing vault document ID, original uploader and upload timestamp, verification decision, reviewer and verification timestamp.

Only two trust levels are used:

- `USER_ASSERTED`: no document is claimed; always disclosed as not independently verified.
- `AUTHORIZED_DOCUMENT_BACKED`: references an existing active `documents` row and its recorded `created_by` / `created_at`. Upload alone leaves verification `UNVERIFIED`.

A document-backed fact can become `VERIFIED` only through the staff verification endpoint. Rejected and superseded decisions remain explicit. AI-generated drafts are rejected as source evidence.

## API

- `POST /api/v1/documents/facts/company/{company_id}`: record a user-asserted fact; company access and document-management entitlement are enforced.
- `POST /api/v1/documents/facts/document/{document_id}`: attach a fact to an existing vault document; the existing document-company access and entitlement checks are reused.
- `GET /api/v1/documents/facts/company/{company_id}`: list current facts and disclosures.
- `POST /api/v1/documents/facts/{fact_id}/verify`: staff-only verification decision, restricted to assigned company scope.

## Tenant and audit controls

The new table uses the existing signed RLS helpers, enables and forces row-level security, binds inserts to the signed actor, scopes reads and updates to company access, permits verification updates only to staff, and revokes DELETE from the runtime role. It does not create a second upload store or a parallel document authorization system.

## Findings and legacy data

`compliance_flags.fact_provenance_snapshot` and `compliance_evaluation_runs.fact_provenance_snapshot` persist the evaluation input provenance. The evaluator overlays current versioned fact values onto same-key company-profile fields and carries those facts into each finding and immutable evaluation snapshot.

Where existing profile fields have no explicit `company_facts` record, findings carry an `UNATTRIBUTED_PROFILE_FIELDS` disclosure: origin and verification status are unknown and must not be treated as verified. The current snapshot is evaluation-input provenance, not yet a rule-specific causal mapping from each individual flag to the exact subset of profile fields used by that rule.

Legacy finding rows are backfilled with an empty JSON array; this means provenance was not recorded historically, not that facts were verified.

## Operational note

The migration expects the signed RLS helper functions and `nlc_app_role` to exist from the current security baseline. Run Alembic upgrade in staging before production. The migration merges the two existing migration heads (`0093_verified_rule_audit_view` and `b10c91ac6860`) before applying revision `0104_company_fact_provenance`.
