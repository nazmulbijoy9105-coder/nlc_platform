# Rule-Identity Discrepancies: Seed Data vs Engine

## Summary

The `legal_rules` seed data (`alembic/versions/0002_seed_ilrmf_rules.py`,
`0003_add_reg_004_rule.py`) disagrees with the live rule engine
(`app/rule_engine/engine.py`) on **5 rule_id assignments**. Tests have been
patched to match the engine (the production code), but the seed data — which
populates the `legal_rules` table shown to users via `GET /rules` — still
shows the wrong rule_ids and descriptions.

This means: **the API tells users one rule_id, the engine fires a different one.**

## Impact

- **User-facing**: `GET /rules` returns rule metadata that doesn't match what compliance flags actually fire.
- **Audit trail**: `compliance_flags.rule_id` stores the engine's rule_id, but `GET /rules/{rule_id}` for that ID returns a different rule's metadata.
- **Legal accuracy**: Several statutory_basis strings disagree on section numbers (Section 85 vs 86, Section 26 vs 34/83/87/90).

## The 5 Discrepancies

### 1. AGM-006 vs AUD-004 — "Auditor not reappointed at AGM"

| Field | Seed Data | Engine |
|---|---|---|
| rule_id | AGM-006 | AUD-004 |
| rule_name | Auditor Not Reappointed at AGM | (same concept, different ID) |
| statutory_basis | Section 210 | Section 210(2) |

Engine fires AUD-004 (line 542) for auditor-not-reappointed. Engine's AGM-006 (line 635) = "AGM Minutes Not Prepared" (Section 83).

**Fix**: Update seed AGM-006 to AUD-004.

### 2. AUD-001 vs AUD-002 — Swapped rule_ids

| Concept | Seed Data | Engine |
|---|---|---|
| First auditor not appointed within 30 days (Sec 210(1)) | AUD-002 | AUD-001 |
| Audit not complete before AGM (Sec 151) | AUD-001 | AUD-002 |

The seed data has AUD-001 and AUD-002 **swapped** relative to the engine.

**Fix**: Swap AUD-001 and AUD-002 in seed data to match engine.

### 3. REG-004 vs REG-002 — "Core statutory registers missing"

| Field | Seed Data | Engine |
|---|---|---|
| rule_id | REG-004 | REG-002 |
| statutory_basis | Section 26 | Sections 34, 83, 87, 90 |

Engine fires REG-002 (line 927) for core registers missing. REG-004 is never fired by the engine.

**Fix**: Update seed REG-004 to REG-002.

### 4. REG-002 vs SH-002 — "Share certificates not issued"

| Concept | Seed Data | Engine |
|---|---|---|
| Share certificates not issued within 60 days | REG-002 (Section 82) | SH-002 (Section 46) |
| Core statutory registers missing | REG-004 (Section 26) | REG-002 (Sections 34, 83, 87, 90) |

Seed data's REG-002 references Section 82 (share transfers), but engine's REG-002 = core registers. Share certificate non-issuance is SH-002 (line 782).

**Fix**: Update seed REG-002 to match engine's core-registers definition.

### 5. AGM-003/AGM-004 — Section 85 vs Section 86

| Rule | Seed Section | Engine Section |
|---|---|---|
| AGM-003 | Section 86 | Section 85 |
| AGM-004 | Section 86 | Section 85 |

Engine uses Section 85 (correct — notice of AGM). Seed uses Section 86 (shorter notice with consent).

**Fix**: Update seed to Section 85 for AGM-003 and AGM-004.

## Additional Statutory Basis Discrepancies

| Rule ID | Seed Section | Engine Section | Issue |
|---|---|---|---|
| AR-001 | 190 | 119 | Annual return filing is Section 119 |
| AR-002 | 190, 396 | 119, 304 | Strike-off is Section 304 |
| AR-003 | 190, 396 | 119, 304 | Same |
| AR-004 | 190 | 119 | Same as AR-001 |
| DIR-001 | 115 | 92 | Director filing is Section 92 |
| DIR-002 | 115 | 92 | Same |
| DIR-003 | 115 | 92 | Same |
| DIR-004 | 115 | 92 | Same |
| ESC-001 | 396 | 304 | Strike-off is Section 304 |
| ESC-002 | 396 | 304 | Same |
| OFF-001 | 77 | 81 | Office change filing is Section 81 |
| TR-001 | 82 | 108 | Transfer instrument is Section 108 |
| TR-004 | 82 | 34 | Register update is Section 34 |

## Recommended Resolution

1. Create migration `0010_fix_rule_identities.py` that UPDATEs `legal_rules` to match the engine.
2. Run the migration against all environments.
3. Verify by comparing `SELECT rule_id, rule_name, statutory_basis FROM legal_rules ORDER BY rule_id` against engine rule definitions.
4. Do NOT change the engine — it is the authoritative source for compliance flag rule_ids.
