# Product-controlled scoring release — 10 November 2026

## Release configuration

- `LEGAL_SCORE_RELEASED = True`: product scoring is enabled.
- `PRODUCT_SCORING_RULE_IDS`: 82 score-bearing rules from the 85-rule engine catalogue.
- `AR-001` and `SH-002` remain informational and are excluded from score deductions.
- `ESC-003` is the surcharge/escalation rule itself, not a finding, and is excluded from the scoring allowlist.
- `VERIFIED_RULE_IDS = frozenset()` remains a separate legal-verification inventory. Product scoring eligibility does not imply independent legal certification or change the pending status in the legal approval register.
- `AUTHORIZED_BLACK_OVERRIDE_RULE_IDS` remains separately controlled and empty; a BLACK severity label alone cannot force a zero score.

## Runtime paths updated

The product scoring allowlist is used consistently by the engine, persisted score reconciliation, company score/dashboard responses, PDF score reconciliation, rule-linked notifications and rescue generation/validation. The product allowlist is included in the deterministic score hash so configuration changes alter the audit fingerprint.

The Super Admin rule-management routes now follow the enabled product release switch. Existing role checks, tenant isolation, evidence-state guards, category caps and the explicit BLACK-override authorization check remain in place.

## Data and deployment scope

This change is code/configuration only. It does not run a database migration, rewrite historical scores, promote legal-rule verification records, or alter production database seed rows. The legal approval register and the 85 pending review records remain unchanged. Calendar release is separate and remains unchanged.

## Verification

CI must confirm:
- the 85-rule engine/seed/register inventory remains aligned;
- exactly 82 score-bearing IDs are in the product allowlist;
- the three non-scoring IDs remain excluded;
- the legal verification allowlist remains empty;
- product scoring and rescue regressions pass.
