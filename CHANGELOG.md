# Changelog

## [2.2.0] — 2026-11-02
### Changed
- Version strings aligned across README, pyproject.toml, app/core/config.py, OpenAPI (was mixed 1.0.0 / 2.1.0 / 2.2.0)
- Rule corpus confirmed at 85 ILRMF rules (Engine ↔ Seed parity)
- CI uses real Redis service container (removed autouse Redis mock)

### Fixed
- Production gate: version consistency, legal audit summary refresh

### Notes
- Runtime idempotent schema safety-net in lifespan retained (Alembic remains source of truth; 43 migrations present)
- Independent Bangladesh company-law lawyer review of full 85-rule corpus still recommended before high-stakes production use


## [Unreleased]
### Fixed
- Rule corpus reconciled (now 85 rules) across engine, seed, API, and tests
- NOT_EVALUATED band added to Severity and RiskBand enums
- 60+ DB columns added for extended rule coverage
- last_evaluated_at shows real timestamp after evaluation
- Disclaimer "not legal advice" added to API responses
- Audit retention set to 7 years (2555 days)

## [2.1.0] — 2026-10-01
### Added
- 60+ compliance columns for BSEC, Bankruptcy, Labour, FDI rules
- NOT_EVALUATED risk band for insufficient data
- CI/CD pipeline (GitHub Actions)
- Sentry error monitoring integration
- OpenAPI docs at /api/v1/docs
- 17 database indexes for performance
- AUDIT_RETENTION_DAYS=365 config (should be 2555)

### Changed
- Rule engine version 2.1 (from 1.0)
- Re-evaluate endpoint returns real timestamps
- Coverage metric based on AGM/audit/return fields

### Fixed
- False GREEN (100/GREEN) eliminated — real scores now shown
- Missing commas in company_service.py (deploy blocker)
- ScoreBreakdown missing coverage field (114 test failures)
- Duplicate get_db_for_user consolidated
- Duplicate sentry-sdk requirement removed
