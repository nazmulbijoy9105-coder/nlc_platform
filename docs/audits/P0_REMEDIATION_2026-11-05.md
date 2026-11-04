# NLC P0 remediation evidence — 5 November 2026

## Scope and safety

This audit used GitHub source/CI metadata and read-only Neon catalog/data queries.
A disposable Neon branch `p0-remediation-20261105` was created from production.
No production rows, schema, environment variables or deployments were changed.

## Confirmed backend defect

The rule engine's ordinary score deduction path filters by `VERIFIED_RULE_IDS`,
but the BLACK override path previously allowed any active flag with
`is_black_override=True` to force a score of zero, without requiring its rule
ID to be approved. Production contains active BLACK flags for rule IDs outside
the source allowlist:

| Rule | Active BLACK flags | Companies |
|---|---:|---:|
| AUD-001 | 6 | 6 |
| DEF-001 | 1 | 1 |
| ESC-003 | 8 | 8 |
| **Total** | **15** | **15 flag rows** |

PR #116 changes the override gate and the rescue/BLACK count to require the rule
ID in the verified allowlist. It also makes the score-impact reconciliation
exclude unapproved BLACK rules.

## Score-history mismatch reclassification

The earlier comparison of current company state against the latest monthly
history snapshot found 14 score/band differences. A follow-up read-only query
established:

- Companies compared: 23
- Score/band differences: 14
- Differences where `companies.last_evaluated_at > compliance_score_history.calculated_at`: 14
- Differences where the company evaluation was at or before the snapshot: 0

The model enforces one immutable snapshot per company/month. Therefore those 14
differences are explained by later evaluations in the same month; they are not
evidence of corruption in the same evaluation. The prior P0 classification was
incorrect. The report must label the monthly hash as monthly-history metadata,
not as the hash of the latest live evaluation.

## Production schema drift

Production branch marker: `0042_dedup_key`. Read-only catalog checks found:

| Object expected by current migrations | Production | Vercel dev |
|---|---|---|
| `companies.member_count` | missing | present |
| `notifications.deduplication_key` | missing | present |
| `webhook_endpoints` | missing | present |
| `webhook_deliveries` | missing | present |
| `companies.rescue_generation_error` | missing | present |

This is a genuine schema/catalog mismatch. Do not infer schema state from
`alembic_version` alone.

## Expanded production schema and rule-catalog drift

A second catalog comparison against migrations 0031–0036 found ten absent company fields:
`last_board_meeting_date`, `board_meeting_notice_given`,
`board_minutes_prepared`, `financial_statements_presented`,
`financial_statements_filed`, `books_of_account_kept`,
`director_consent_filed`, `director_office_of_profit`,
`managing_director_appointment_date`, and
`business_commencement_declaration_filed`. Migration 0049 adds these as
nullable fields with no TRUE defaults, so missing source evidence remains
unknown rather than being treated as compliance.

The production `legal_rules` table also lacks the 0035 verification metadata
(`verification_status`, `verified_by`, `verified_at`,
`verification_notes`). Migration 0049 restores these with existing/new rules
pending by default.

Canonical rule registry comparison:
- Seed registry: 85 IDs
- Production DB registry: 75 IDs
- Missing from DB: BOD-001, BOD-002, BOD-003, ACC-001, ACC-002, ACC-003,
  DIR-007, DIR-008, DIR-010, MEM-001, INC-007
- Extra legacy DB ID: INC-002

Migration 0049 restores the 11 missing canonical rows as PENDING and preserves
INC-002 but deactivates it pending counsel review. The API parity audit now
queries only active rules, so it compares the same active registry set.

## Alembic graph defect

Current source has two migration heads:

- `0046_legal_evidence_provenance`
- `0047_agm_unknown_defaults`

Both descend from `0045_agm_held_fields`. Migration `0048_merge_legal_evidence_and_agm_defaults`
is added as a merge-only revision so `alembic upgrade head` has one target.

This does not itself repair production. Before running migrations, inspect all
preconditions and ensure no partially-created constraints/tables will cause
non-idempotent migrations to fail. In particular, `b10c91ac6860` adds
`companies.rescue_generation_error` without an IF NOT EXISTS guard, and
`0046` adds provenance constraints without IF NOT EXISTS guards.

## Remaining release gates

- CI for PR #116 must pass, including unit, integration, canonical integrity,
  migration and rule-verification checks.
- Verify production schema preconditions against the exact DB URL used by Render.
- Execute the migration chain only on the disposable Neon branch first.
- Run authenticated DB/API parity and RLS cross-tenant negative tests.
- Consolidate PRs #114/#115 with the P0 fix; do not merge overlapping heads
  independently.
- Deploy only an approved commit; verify Render SHA and live health afterward.
- Obtain independent legal approval for every rule that is to influence scores.
