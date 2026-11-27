# Technical parity and fail-closed check record

**Recorded:** 2026-11-28  
**Tested code commit:** `fbe2e69b62e36b201bf2b3f08ddfdb91233d651b`  
**Test PR:** https://github.com/nazmulbijoy9105-coder/nlc_platform/pull/443  
**Note:** This is a record of the completed PR-A CI run against the application code. The authority-register and discrepancy PRs are documentation-only and do not alter application code.

## GitHub Actions runs

| Workflow | Run ID | Conclusion |
|---|---:|---|
| Legal engine assurance | 46023335076 | SUCCESS |
| CI | 46023335357 | SUCCESS |
| Security closure structure | 46023335259 | SUCCESS |

## Legal-engine assurance jobs

All completed successfully:

- `legal-rule-catalogue-parity`
- `rjsc-scope-isolation`
- `score-provenance-integrity`
- `fail-closed-publication`
- `legal-engine-p0`

The logs report:
- Engine AST: 85 rules.
- Seed AST: 85 rules.
- Static engine/seed parity: 85/85.
- RJSC scope registry and OUT_OF_SCOPE injection-invariance step: passed.
- Evaluation integrity and score-hash step: passed.
- Rule-outcome ledger step: passed.
- Withheld / not-released score visibility step: passed.
- Score-release evidence-gate step: passed.

## CI jobs

All completed successfully:

- `lint`
- `docker-runtime-smoke`
- `unit-tests`
- `integration-tests`

The unit-test job also completed:
- Current statutory citation anchor audit.
- Static rule registry parity audit.
- Six-state rule coverage report.
- Rule verification status check.
- Engine guard tripwire.

The integration-test job completed fresh PostgreSQL migration rehearsals and PostgreSQL-required security/tenant-isolation integration tests.

The scope-registry test step reported 37 passing tests.

## Status separation confirmed by the run

The unit-test log reported:
- Exact engine/seed inventory parity: 85/85.
- 85 catalogue rules match engine, seed and legal register.
- Product-active / score-eligible IDs: 85.
- Counsel-verified IDs: **0**.
- `VERIFIED_RULE_IDS` and the independent counsel register remain fail-closed.

Product scoring eligibility is a technical/product configuration and must not be represented as legal approval. The zero counsel-verified count is the relevant legal-approval boundary.

## Limitations

- These checks prove the tested code commit passed the named CI jobs; they do not prove the legal correctness of every rule.
- The tests do not convert any row in the 59-rule authority register to `VERIFIED` or `APPROVED`.
- They do not establish commencement, amendment, repeal, or operative-period completeness for the 59 provisions.
- They do not replace immutable source-file capture or independent legal review.
- No production scoring configuration, score, risk band, rescue trigger, or release gate was changed by the evidence work.

## Result

<badge>PASS</badge> Technical parity and fail-closed checks passed on the recorded code commit. Legal approval remains separate and unchanged.
