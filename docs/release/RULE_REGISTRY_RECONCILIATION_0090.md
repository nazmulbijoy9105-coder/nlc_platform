# Rule registry reconciliation — migration 0090

## Scope

- Parent revision: `0089_unique_active_compliance_flags`.
- New revision: `0090_rule_registry_drift_quarantine`.
- Historical migrations `0002` and `0003` are intentionally unchanged.
- The two confirmed live registry metadata corrections are:
  - `SH-001`: legacy Section 50 / 30-day metadata → maintained catalogue identity Section 151 / 60 days.
  - `SH-002`: legacy Section 46 / 60-day metadata → maintained catalogue identity Section 158 / 90 days.
- The migration also quarantines every existing `legal_rules` row, including inactive legacy rows, by setting `verification_status=PENDING`, `default_severity=NOT_EVALUATED`, `score_impact=0`, and `is_black_override=false`. It clears citation-verification actor/date fields. Existing active/inactive membership is preserved.

The share-rule text and condition values are copied from the maintained `scripts/seed_rules.py` catalogue. This establishes technical catalogue parity only; it is not a statement that the cited statutory provisions or deadlines have been independently verified.

## Audit evidence

For every row changed, the migration writes complete JSONB `before_definition` and `after_definition` snapshots to `public.legal_rule_reconciliation_audit`, with the revision, actor type/identifier, timestamp, and reason. The table is forced-RLS, signed finance-staff read-only for the application, and protected against UPDATE, DELETE, and TRUNCATE. Runtime users receive no write privileges.

The migration is transactional and forward-only. Downgrade is a no-op so that it cannot restore unapproved scoring/BLACK metadata or erase audit evidence.

## Release invariants

- `VERIFIED_RULE_IDS` remains empty and `LEGAL_SCORE_RELEASED` remains false.
- The legal approval register remains unapproved.
- PDF, legal deadline/calendar and rescue release gates are not changed or enabled.
- Existing score history is not rewritten or deleted. API and evaluation release controls continue to suppress unreleased score values.
- The `GET /rules` and `GET /rules/{rule_id}` tests require identical rule identities and generic review-only copy for unapproved rules.

## Verification

The PostgreSQL integration tests compare active database rule IDs with the engine registry and maintained seed catalogue, check the two corrected metadata records, assert every DB row is non-scoring/non-BLACK/PENDING, and verify one before/after audit record per row.

Do not apply this migration to production until the exact target database, backup/restore point, Alembic lineage, and migration role have been independently confirmed under the production release runbook.
