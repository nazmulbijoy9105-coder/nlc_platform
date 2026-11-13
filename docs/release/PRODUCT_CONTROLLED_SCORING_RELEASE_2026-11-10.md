# Product-controlled scoring release — 10 November 2026

## Release configuration

- `LEGAL_SCORE_RELEASED` is read from the deployment environment. Values `true`, `1`, `yes`, and `on` enable product scoring; all other values, including an unset variable, disable score-bearing output. `.env.example` defaults to `LEGAL_SCORE_RELEASED=false`. A product owner must explicitly set the deployment value to enable scoring.
- `PRODUCT_SCORING_RULE_IDS`: 82 score-bearing rules from the 85-rule engine catalogue.
- `AR-001` and `SH-002` remain informational and are excluded from score deductions.
- `ESC-003` is the surcharge/escalation rule itself, not a finding, and is excluded from the scoring allowlist.
- `VERIFIED_RULE_IDS = frozenset()` remains a separate legal-verification inventory. Product scoring eligibility does not imply independent legal certification or change the pending status in the legal approval register. The product release switch never populates or edits this set.
- `AUTHORIZED_BLACK_OVERRIDE_RULE_IDS = {"INC-003"}` is a product-owner policy allowlist, separate from legal citation verification. INC-003 only forces the BLACK override when its finding is active, applicable, a confirmed violation and supported by the required director-count evidence. A BLACK severity label alone cannot force a zero score.

## Runtime paths updated

The product scoring allowlist is used consistently by the engine, persisted score reconciliation, company score/dashboard responses, PDF score reconciliation, rule-linked notifications and rescue generation/validation. The product allowlist is included in the deterministic score hash so configuration changes alter the audit fingerprint. The independent counsel inventory is used only for legal-review status and review queues, not as a scoring prerequisite.

Super Admins can inspect and maintain the versioned rule catalogue regardless of whether customer-facing scoring is enabled. Changes remain audit-logged and do not publish a score while the product release switch is off. Existing role checks, tenant isolation, evidence-state guards, category caps and the product-owner BLACK-override allowlist remain in place.

## Customer-facing disclosure

- The dashboard labels the value a **Product risk score** and explains that product-owner release is not independent Bangladesh company-law verification, a legal opinion or a compliance certificate.
- If the backend returns a null score or `NOT_EVALUATED`, the frontend withholds the score rather than displaying a stale or placeholder value.
- Every generated PDF carries the red `UNSIGNED — FOR COUNSEL REVIEW ONLY — NO NLC LIABILITY WITHOUT SIGNATURE` banner, a reliance/liability notice, a Lawyer Review & Signature block (counsel name, date, comments, approval checkboxes and signature line), and `Status: UNSIGNED` in the footer. The PDF is not represented as counsel-approved until the review block is completed and signed.

## Data and deployment scope

This change is code/configuration only. It does not run a database migration, rewrite historical scores, promote legal-rule verification records, or alter production database seed rows. The legal approval register and the 85 pending review records remain unchanged. Calendar release is separate and remains unchanged.

## Verification

CI must confirm:
- the 85-rule engine/seed/register inventory remains aligned;
- exactly 82 score-bearing IDs are in the product allowlist;
- the three non-scoring IDs remain excluded;
- the legal verification allowlist remains empty and does not block product scoring or the product-owner INC-003 override;
- product scoring and rescue regressions pass.
