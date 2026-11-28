---
name: evidence-provenance-review
description: Assess provenance, authenticity limits, completeness and traceability of evidence used in NLC compliance evaluations, legal research or court-facing RJSC records.
---

# Evidence provenance review

## Objective
Determine what an evidence item can and cannot establish. Evidence registration is not proof of authenticity, truth or legal sufficiency.

## Method
1. Assign an immutable evidence ID and record submitter, role, tenant, collection channel and timestamp.
2. Preserve original bytes where lawfully held; calculate a cryptographic hash and record MIME type, size and storage locator.
3. Record source, custodian, acquisition method, transformation history, OCR/extraction method, version and access log.
4. Separate user assertion, third-party document, official record, system observation and independently authenticated source.
5. Identify scope: which fact, date, entity and rule the item may support.
6. Assess completeness, currency, legibility, tampering indicators and corroboration; do not overstate.
7. Record chain-of-custody gaps, conflicts, missing originals and authentication requirements.
8. Return an evidence state distinct from legal applicability and legal verification.

## Output
Evidence ID/hash; provenance class; origin; custodian; collection and transformation events; asserted fact; date coverage; rules/facts linked; corroboration; limitations; authentication status; reviewer; next action.

## Prohibitions
A hash proves byte identity after hashing, not authorship or truth. OCR is an extraction aid, not authentication. A user checkbox is an assertion, not independent verification. Never silently convert missing evidence into an adverse legal finding.
