# Company Information & Declaration — Implementation Contract

Status: implementation specification; not yet production functionality.
Scope: Bangladesh private limited companies already managed by NLC. This is an extension of the existing NLC product, not a separate portal.

## Non-negotiable document policy
1. Company users must not upload original RJSC-issued documents, original incorporation records, complete MOA, or complete AOA through the company portal.
2. Originals are presented physically to NLC legal counsel. NLC staff record a scoped examination; the record must not imply authenticity or legal correctness beyond the checks actually performed.
3. Do not add a generic company-document upload field to this workflow. Any future supporting-evidence upload requires a separately approved allow-list and explicit exclusion of originals and complete constitutional documents.
4. The existing Articles upload screen currently accepts an executed Articles PDF. That conflicts with this policy and must be changed to a hard-copy presentation/examination workflow before this feature is released.

## Company-facing mandatory submission
Place the workflow inside the existing company profile/dashboard:
- Company identity: legal name, RJSC registration number, incorporation date, registered office.
- Company structure: directors and their appointment/departure dates; shareholders, share counts/classes and effective dates; authorised and paid-up capital.
- Compliance facts: only fields mapped to current NLC rule inputs, with unknown/not-applicable represented explicitly rather than silently defaulted.
- Change declaration: whether facts have changed since the last accepted submission; effective date and description of changes.
- Submitter: authenticated user identity, full name, designation/capacity, contact, claimed authority basis, and authority evidence reference (not a blanket assertion that identity proves authority).
- Declaration version, acceptance timestamp, submission ID, and effective-as-at date.
The server must derive submitter user ID, company ID, and timestamp from the authenticated request. Never trust client-supplied identity, role, company association, or submission status.

## Declaration and workflow semantics
Separate these states:
- DRAFT
- SUBMITTED
- AUTHORITY_REVIEW
- FACT_REVIEW
- DISCREPANCY
- ACCEPTED_FOR_ASSESSMENT
- REJECTED
- SUPERSEDED
ACCEPTED_FOR_ASSESSMENT means the information passed NLC's defined intake/review gate. It does not mean every fact is independently proven or that the company is legally compliant.
A declaration is evidence that a named authenticated user made a representation. It is not proof of the truth of the representation or the user's authority. Authority validation and factual corroboration are distinct review tasks.
Each submission is an immutable version. Corrections create a new version and supersede the previous version; do not overwrite submitted facts or declarations. Record reviewer, timestamps, decision, reason, and relevant evidence references.

## NLC internal hard-copy examination
Create an internal-only record with:
- company and submission references;
- document category (MOA, AOA, certificate/incorporation record, RJSC filing/return, register, other);
- whether original or certified copy was presented;
- presenter and stated capacity;
- date/time and place of examination;
- examining lawyer and any second reviewer;
- examination scope/checklist (identity, completeness, signatures/seals, dates, internal consistency, comparison source);
- source/provenance of any comparison record;
- outcome: NOT_EXAMINED, EXAMINED_NO_OBVIOUS_DISCREPANCY, DISCREPANCY, INCONCLUSIVE;
- precise observations and limitations;
- custody/return status and confirmation;
- append-only event history.
Do not label a document AUTHENTIC merely because it was viewed. Record exactly what was checked and what was not checked. Do not record unnecessary sensitive personal data in free text.

## Mandatory enforcement
- Client routes require authenticated company access and server-side role/tenant checks.
- Only authorised NLC legal staff can record/review hard-copy examinations.
- Company submission cannot be accepted without required fields and explicit declaration acceptance.
- Assessment initiation and material company-fact updates must be blocked unless a qualifying submission exists, subject to an explicit NLC staff override with reason and audit event. Do not silently block existing read-only access.
- RLS must cover every new company-scoped table. Test both row visibility and writes across two tenants.
- Audit history must be append-only at the database/API layer; normal update/delete routes must not mutate submitted records.
- No file endpoint is to be exposed for original MOA/AOA/RJSC documents in this workflow.

## Suggested persistence model
- company_information_submissions: immutable version, structured fact snapshot, effective date, submitter, declaration version/text hash, state.
- company_submission_review_events: append-only authority/fact review decisions, reviewer, reason, timestamps.
- hardcopy_document_examinations: examination metadata, scope, outcome, limitations, presenter, examiner, custody/return.
- hardcopy_examination_events: append-only amendments/return/custody events.
Where structured facts map to existing Company, Director, and Shareholder fields, retain the submitted snapshot as the evidential record. Apply accepted facts to operational tables only through a reviewed, transactional service with a field-level change log. Never treat the JSON snapshot as the live rule-engine input without that application step.

## Release acceptance tests
1. CLIENT_DIRECTOR can submit only for an assigned company; CLIENT_VIEW_ONLY cannot submit.
2. A user cannot submit for a company without active company access.
3. Forged user/company IDs in the request body are ignored or rejected.
4. Missing declaration, missing effective date, or incomplete required facts cannot be submitted.
5. A submitter cannot approve their own authority/fact review.
6. Legal staff can record hard-copy examination; client roles cannot read internal examination notes or custody details.
7. Cross-tenant reads/writes fail under PostgreSQL RLS.
8. Submitted snapshots and declarations cannot be updated/deleted; corrections create a new version.
9. Assessment gate rejects missing/unaccepted submissions and records any authorised override.
10. Upload attempts for original MOA, AOA, incorporation certificate, or RJSC originals are impossible in this workflow (no UI control and no API route).
11. Examination outcomes distinguish observed condition from authenticity/legal conclusions.
12. Existing Articles review functionality is not broken; its upload control is removed or replaced with hard-copy examination intake.

## Deployment gate
Do not merge or deploy until backend migration, API tests, PostgreSQL RLS integration tests, frontend build/lint, client/staff role tests, and a staging walkthrough pass. Render's current NLC service has auto-deploy disabled; a merge/push alone will not deploy it. Production migration and deploy require a separately reviewed release.