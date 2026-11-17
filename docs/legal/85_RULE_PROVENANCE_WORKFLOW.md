# Bangladesh legal provenance and evidence workflow

## Purpose

`85_rule_provenance_manifest.json` is the controlled intake register for the canonical 85 NLC rule IDs. It is deliberately incomplete and fail-closed. It does not create legal identities, determine operative dates, certify citations, approve evaluator logic, or authorize statutory scoring.

The JSON Schema in this directory defines the record shape. The unit tests enforce the initial 85-ID inventory and ensure that missing source data cannot be mistaken for legal approval.

## Source hierarchy

For Bangladesh legislation, use the authentic Bangla text published through the official Laws of Bangladesh portal and the relevant Bangladesh Gazette. Use an English translation as a research aid only; resolve any difference against the authentic Bangla text.

Starting points (not a substitute for the actual instrument and Gazette evidence):

- Laws of Bangladesh — Companies Act, 1994 (Act XVIII of 1994): https://bdlaws.minlaw.gov.bd/act-details-788.html
- Registrar of Joint Stock Companies and Firms (RJSC): https://app.roc.gov.bd/
- RJSC guidance / FAQ: https://app.roc.gov.bd/Guidlines/faq.html

For each rule, capture the original instrument and every amendment, substitution, repeal, commencement notification, saving provision or transitional provision that affects the rule. Record publication and commencement dates separately. Do not infer commencement from assent, publication, a later consolidated-text date, a database timestamp or the date the evaluator was written.

Draft bills, consultation documents, circulars, FAQs and professional commentary must not be represented as enacted law. Record them as interpretive or research sources only where appropriate, and never let them replace the primary legal instrument.

## Source namespace and historical identity

A source namespace must identify an immutable source artifact, not a mutable branch name such as `main`, a display label such as `seed`, or a current database row.

Recommended forms:

- `nlc-engine:git:<full-commit-sha>:<path>`
- `nlc-seed:git:<full-commit-sha>:<path>`
- `nlc-production:neon:<branch-id>:<read-only-snapshot-id>`
- `external:<publisher>:<instrument-id>:<artifact-sha256>`

The namespace is unresolved until the full immutable identifier and artifact can be retrieved. Never invent a namespace or backfill one from memory.

A historical ID is meaningful only together with its namespace. The same string (for example, `INC-001`) in two source namespaces may describe different propositions. Preserve both records and mark attribution ambiguous until the source lineage is proven.

## Rule-by-rule completion procedure

1. Pin the source commit or read-only database snapshot that contains the historical ID and definition.
2. Assign or reconcile a permanent canonical UUID only after the legal obligation has been distinguished from similarly named obligations.
3. Identify the Bangladesh entity classes and factual conditions to which the provision applies, including exceptions and exclusions.
4. Identify the operative date interval. Use half-open intervals `[effective_from, effective_to)`; leave the end open only when the source supports continuing operation. Preserve separate historical intervals where amendments change the legal rule.
5. Attach the exact primary instrument, provision, Gazette/publication details and the complete amendment/commencement chain.
6. Define every required company fact, its type, purpose and decision role (applicability, trigger, exception, calculation, status or identity).
7. For every fact, define evidence roles, acceptable evidence types, source authority and verification standard. Distinguish user assertions from authenticated or independently checked records.
8. Pin the evaluator commit and artifact hash. Test the actual emitted rule IDs and legal decision cases, including applicability, exceptions, missing facts, contradictory evidence and historical dates.
9. Obtain independent Bangladesh counsel review of the exact canonical payload digest. The reviewer must not be the author.
10. Obtain a separate product-owner decision for product visibility and scoring. Neither approval substitutes for the other.

## Status and release rules

- `UNRESOLVED`: source identity, legal content, applicability, effective date or evidence contract is incomplete.
- `READY_FOR_LEGAL_REVIEW`: all source and operational fields are populated and independently reproducible; this is not approval.
- `LEGAL_REVIEWED`: use only after a qualified independent reviewer has approved the exact payload digest. The manifest schema separately records reviewer, timestamp, basis and digest.
- `REJECTED`, `DISPUTED` or `QUARANTINED`: do not score or silently map.

A rule is not score-releasable merely because its record is complete or counsel-reviewed. The independent legal approval register, product-owner release decision and runtime release gate must all agree. Until then, the engine must fail closed and expose an explicit not-evaluated / review-required state rather than GREEN or a legal-compliance conclusion.

## Legacy records

- `INC-001`: currently recorded as an identity conflict between two different statutory propositions in the 2026-11-15 reconciliation. Preserve both source records; do not merge or reassign historical findings without evidence.
- `INC-002`: a production-only legacy candidate outside the canonical 85. Keep quarantined pending source namespace, identity and disposition review.

Do not delete, overwrite, bulk-rekey or retroactively reinterpret historical findings as part of this manifest intake.

## Validation

Run:

```bash
python -m pytest tests/unit/test_legal_provenance_manifest.py -q
```

The test is a structural/fail-closed baseline. It does not validate legal meaning, the truth of a citation, Gazette authenticity, database parity, counsel qualifications or production release readiness.
