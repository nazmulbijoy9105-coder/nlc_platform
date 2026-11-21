# Screened private-beta legal release workflow

## Purpose and authority

NLC's operational private beta publishes deterministic **screening scores**. An authenticated `SUPER_ADMIN` product owner may accept a product rule/source mapping for that screened-beta workflow. This product-owner acceptance is the operational product-release authority; it is not represented as independent Bangladesh legal-counsel verification, a legal opinion, a compliance certificate, or an RJSC determination.

The API therefore reports two separate states:

- `verification_status`: `ACTIVE` only after a complete product-owner acceptance snapshot; otherwise `PENDING`.
- `independent_legal_verification_status`: remains `PENDING` until the separate counsel-verification process records a genuine legal review.

When product acceptance is absent, `verified_at` is null. When accepted, `verified_at` is the actual append-only product-owner acceptance event timestamp and `verification_basis` is `PRODUCT_OWNER_ACCEPTANCE_SCREENING_ONLY`. It is not a statutory verification timestamp.

## Rule-level acceptance sequence

1. Register a source using `POST /api/v1/legal-provenance/sources`.
   - Record jurisdiction, instrument title, issuing authority, official URL, formal citation, version label, publication date, effective-from and effective-to dates.
   - Provide the source artifact URI and its SHA-256 together. Scoring acceptance rejects a source without both and an explicit effective-from date.
   - A recorded URI/hash is a reference supplied to NLC. The current workflow does not independently fetch or verify artifact bytes; the acceptance record says so explicitly.

2. Map each canonical rule using `POST /api/v1/legal-provenance/mappings` (or the bulk mapping endpoint).
   - Supply the exact rule ID, source ID, provision citation, mapping kind and mapping rationale.
   - Do not infer citations, effective dates or source versions from an unrelated source entry.

3. Record the product-owner decision using `POST /api/v1/legal-provenance/decisions`.
   - For scoring, use `release_scope=SCORING` and `decision=APPROVED`.
   - The API verifies that the rule is in the 85-rule product scoring set and that the source artifact reference/hash, effective period, provision citation and rationale are present.
   - The append-only event captures reviewer ID/name/role, rule ID, source version, source hash/URI, citation, effective period, mapping rationale, acceptance rationale, event timestamp and event hash.
   - A `REVOKED` event supersedes the prior approval; prior events are not overwritten.

4. Check `GET /api/v1/legal-provenance/product-release-status`.
   - It compares the runtime database rule IDs with the canonical 85 scoring IDs.
   - It returns missing, unexpected, active and inactive database IDs.
   - It returns the latest owner decision for each rule and its recorded source snapshot.
   - A rule is `ACTIVE` only when its latest approval event contains the complete required snapshot.

5. Accept the product version using `POST /api/v1/legal-provenance/product-versions/accept`.
   - Supply a stable version label and a reason.
   - The API fails closed unless exactly the expected canonical set is present, active and individually owner-accepted.
   - It creates an append-only version-acceptance event containing all 85 rule IDs, reviewer identity, the per-rule source/citation/effective-period manifest and the manifest SHA-256.
   - Reusing a version label with a different manifest is rejected. Repeating the same label and identical manifest is idempotent.

## Legal changes and supersession

A new amendment, commencement order, correction or source consolidation receives a new source version. Update the affected rule mappings, record a new owner decision for each affected rule, and accept a new product version. Never rewrite a prior source record, owner decision, version-acceptance event or historical score snapshot. The old version remains auditable. The version-acceptance endpoint records the immutable release manifest; it does not rewrite or retroactively re-version existing score snapshots.

## Score and report labelling

Company, compliance, finding, score-history and evaluation-run API responses identify outputs as screening-only and state that they are not legal advice, legal opinions or compliance certificates. The frontend must display the disclaimer alongside every score and finding, including exports and historical views.

## Release limitations

- Product-owner acceptance is the operational approval record for screened-beta product use. It does not change the independent counsel-verification register or itself alter the existing score-engine release switch.
- A supplied source hash is recorded exactly but is not proof that the source bytes were independently fetched, authenticated or preserved.
- This workflow does not automatically create missing statutory rule rows or activate inactive rules. The parity endpoint identifies the exact IDs requiring controlled repair.
- No production migration or data mutation is part of this workflow.
