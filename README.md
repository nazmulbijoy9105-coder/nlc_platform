# NEUM LEX COUNSEL — RJSC Compliance Intelligence Platform

**Version 2.2.0** | Engine v2.1 | 85 ILRMF Rules | Bangladesh Companies Act 1994

Proprietary Software — Neum Lex Counsel

Automates RJSC corporate compliance monitoring for Bangladeshi companies under the Companies Act 1994.

## What This Is

A full-stack compliance intelligence platform that:
- Evaluates companies against **85 ILRMF rules** across **17 modules**
- Scores 0-100 with risk bands: GREEN / YELLOW / RED / BLACK / NOT_EVALUATED
- Flags violations with statutory basis, section reference, and score impact
- Generates AI-drafted legal documents with mandatory human approval (AI Constitution Article 3)
- Manages corporate rescue pipeline (8-step remediation) for RED/BLACK companies
- Tracks commercial engagements, quotations, and revenue pipeline
- Sends deadline warnings via Dashboard, Email, WhatsApp
- Records immutable compliance score history with hash chain for legal defensibility
- Version-controls all legal rule modifications (SUPER_ADMIN only, with audit trail)

## Risk Bands

| Band | Score | Meaning |
|------|-------|---------|
| GREEN | 70-100 | Compliant — annual compliance cycle |
| YELLOW | 50-69 | Irregular — remediation required |
| RED | 30-49 | Statutory default — structured regularization |
| BLACK | 0-29 | Systemic failure — corporate rescue mandatory |
| NOT_EVALUATED | — | Insufficient data (coverage < 50%) |

**Disclaimer:** Automated compliance screening. Not legal advice. Consult your legal counsel.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| API | FastAPI + Pydantic v2 + uvicorn |
| Database | PostgreSQL 16 + SQLAlchemy 2.0 async (147 columns on companies table) |
| Cache/Queue | Redis 7 + Celery 5 + redbeat |
| Migrations | Alembic revision DAG with explicit forward migrations; inspect `alembic heads` and `python scripts/audit_alembic_graph.py` |
| Auth | JWT (32+ char secret) + TOTP 2FA (AES-256 encrypted) + bcrypt |
| Rate Limiting | slowapi (10/min on login) |
| AI | Anthropic Claude / OpenAI (human approval required) |
| Storage | AWS S3 |
| Email | AWS SES |
| Error Monitoring | Sentry |
| Tests | pytest + pytest-asyncio (288 unit tests + integration tests) |
| CI/CD | GitHub Actions (compile + test + rule parity audit) |
| Code Quality | Ruff linter + mypy type checker |

## Project Structure

nlc_platform/
├── app/
│   ├── main.py              # FastAPI app factory + middleware; no schema migration at startup
│   ├── api/                 # FastAPI routers and versioned endpoints
│   ├── models/              # SQLAlchemy ORM models and RLS-aware schemas
│   ├── services/            # Domain, statutory filing, evidence and compliance services
│   ├── core/                # config, security, dependencies (RBAC + RLS)
│   ├── rule_engine/         # Deterministic 85-rule ILRMF engine v2.2
│   └── worker/              # Celery tasks + beat schedule (7-year retention)
├── alembic/                 # Versioned Alembic revision DAG (including merge revisions)
├── scripts/                 # Audits and development-only utilities; production registry is migration-controlled
├── tests/                   # Unit, PostgreSQL integration, security and runtime regression suites
├── tools/                   # audit_rule_parity.py (canonical AST-based parity check)
├── docs/                    # LEGAL_BASIS_MATRIX.md, LAWYER_LEGAL_REVIEW_PACK.md
├── .github/workflows/       # CI, migration rehearsal, production parity and controlled deployment
├── Dockerfile               # Multi-stage build
├── docker-compose.yml       # Full local stack
├── render.yaml              # Render.com deployment blueprint
├── .env.example             # Example configuration (never production secrets)
├── CHANGELOG.md             # Version history
└── pytest.ini               # Test configuration

## Score freshness and release contract

A company score is a product risk indicator only — not legal advice and not a certification. The API may publish a score or risk band only when the latest evaluation is completed, uses the current engine and scoring specification, passes evaluation-ledger integrity checks, reconciles to its score snapshot, and matches the company's cached score, band and evaluation timestamp. Changes to company profile, facts, directors, shareholders, share transfers, AGM, audit, annual-return, statutory-register or share-evidence inputs invalidate the cached statutory score. Until a new valid evaluation completes, the current score and risk band are withheld as `NOT_EVALUATED` or `STALE`.

`NOT_EVALUATED` is an evaluation/data status. It is not a GREEN result, a legal conclusion, or evidence that a company is compliant.

## 85 ILRMF Rules — 17 Modules

| Module | Rules | Statutory Basis |
|--------|-------|-----------------|
| AGM (7) | AGM-001 to AGM-007 | Companies Act 1994, Sections 81-85 |
| Annual Return (4) | AR-001 to AR-004 | Sections 36 and 346 (separate Registrar strike-off process) |
| Auditor (5) | AUD-001 to AUD-005 | Sections 151, 210 |
| Bankruptcy (3) | BNK-001 to BNK-003 | Bankruptcy Act 1997 |
| BSEC Governance (4) | BSEC-001 to BSEC-004 | BSEC CG Code 2023 |
| Capital & Charges (5) | CAP-001 to CAP-004, CHG-001 | Sections 54, 87, 100 |
| Default (2) | DEF-001, DEF-002 | Sections 297, 447 |
| Directors (6) | DIR-001 to DIR-008, DIR-010 | Sections 92, 93, 97, 98, 104, 110 |
| Escalation (5) | ESC-001 to ESC-005 | Sections 196, 199, 304 |
| Foreign Exchange (1) | FX-001 | FE Regulation Act 1947 |
| Incorporation (6) | INC-001 to INC-007 | Sections 11, 81, 90(2), 150 |
| Labour (3) | LBR-001 to LBR-003 | Labour Act 2006 |
| Office (1) | OFF-001 | Section 77 (28-day filing) |
| Registers (3) | REG-001 to REG-003 | Sections 34, 83, 87, 90 |
| Shareholders (3) | SH-001 to SH-003 | Sections 46, 50, 52 |
| Structural (3) | STR-001 to STR-003 | Sections 17, 18, 20 |
| Tax & VAT (6) | TAX-001 to TAX-004, VAT-002, VAT-003 | ITA 2023, VAT Act 2012 |
| Trade License (2) | TL-001, TL-002 | City Corp Ordinance 1983 |
| Transfers (6) | TR-001 to TR-006 | Sections 34, 47, 108 |

**BLACK Override Rules:** INC-003, INC-004, AUD-003, TR-005, ESC-002, ESC-003, ESC-004, BNK-001, BNK-002, BNK-003, CAP-003, DEF-001

## Quick Start

```bash
git clone https://github.com/nazmulbijoy9105-coder/nlc_platform.git
cd nlc_platform
cp .env.example .env
# Edit .env - fill required secrets

# Required environment variables:
#   JWT_SECRET_KEY     (32+ chars, openssl rand -hex 64)
#   DATABASE_URL       (postgresql+asyncpg://...)
#   REDIS_URL          (redis://...)
#   FERNET_KEY         (python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
#   ADMIN_EMAIL        (admin@yourdomain.com)
#   ADMIN_PASSWORD     (strong password)
# Optional:
#   SENTRY_DSN         (https://xxx@oXXX.ingest.sentry.io/XXX)
#   ALLOW_PUBLIC_SIGNUP (default: true, role: CLIENT_VIEW_ONLY)

# Install + run (LOCAL DEVELOPMENT ONLY)
pip install -r requirements.txt
# For a disposable local development database only:
alembic upgrade head
# Development fixture/bootstrap utility only; never a production release step:
python scripts/seed_rules.py
uvicorn app.main:app --reload

# Production migrations are not run from this Quick Start or at app startup.
# They execute only through the approved controlled release workflow after
# fresh-DB validation and an isolated production-derived Neon rehearsal.

# Verify
curl http://localhost:8000/api/v1/health/ready
# OpenAPI docs at http://localhost:8000/api/v1/docs
# Development (local disposable database only)
uvicorn app.main:app --reload          # Start API server
alembic upgrade head                   # Local schema setup; NOT a production command

celery -A app.worker.celery_app worker -l info  # Start Celery worker
celery -A app.worker.celery_app beat -l info     # Start beat scheduler

# Testing
python -m pytest tests/unit -q          # 288 unit tests
python -m pytest tests/unit -v          # Verbose with test names
DATABASE_URL=dummy python -m pytest tests/unit -q  # No DB needed

# Code Quality
ruff check app/                        # Lint
python -m compileall app/              # Compile check
python tools/audit_rule_parity.py --no-db  # Rule parity (AST-based)

# Deployment (Render.com)
# Render native autoDeploy is disabled. GitHub Actions releases only after successful CI, exact-SHA assurance, and production approval.
# Automatic release requires NLC_AUTO_DEPLOY to equal exact lowercase "true", plus NLC_MIGRATION_DATABASE_URL and RENDER_API_KEY secrets.
# Missing migration or Render API credentials abort before the exact-SHA Render deploy request; API startup performs no migration or seed.
# Production legal-rule registry changes are forward-only, reviewed Alembic migrations; seed scripts are development-only.
# Production rollback is not "alembic downgrade -1": use a reviewed forward-fix,
# or restore PITR to a separate branch and validate before controlled cutover.
# An old app may be redeployed only after schema/data compatibility is proven.
# See docs/MIGRATION_RELEASE_CONTRACT.md for mandatory evidence and gates.

## API router inventory

These are the routers mounted by `app/main.py` on current `main`. The prefix is not a promise that every operation is available to every role; route-level dependencies and company authorization are authoritative.

| Prefix | Main capabilities | Access boundary |
|---|---|---|
| `/api/v1/health` | Liveness and readiness | Public |
| `/api/v1/auth` | Login, signup, refresh, logout, profile, 2FA and password changes | Login/signup public; authenticated operations protected |
| `/api/v1/companies` | Company CRUD, evaluation, compliance, flags, score history and dashboard | RBAC + company scope/RLS |
| `/api/v1/portfolio/compliance` | Portfolio evaluation, rule-outcome aggregation and reactivation controls | SUPER_ADMIN |
| `/api/v1/filings` | AGM, audit, annual return, statutory registers and filing evidence | RBAC + company scope |
| `/api/v1/rescue` | Rescue plans, steps and engagements | Staff roles + company scope |
| `/api/v1/documents` | Document listing, generation, approval, release and download | RBAC + company scope |
| `/api/v1/commercial` | Pipeline, funnel, engagements and quotations | Staff roles |
| `/api/v1/finance` | Invoices, payment submissions, payment approval/rejection and company payment history | RBAC + company scope; payment review is staff-controlled |
| `/api/v1/subscriptions` | Plans, subscription state and entitlement operations | RBAC; plan administration is staff-controlled |
| `/api/v1/rjsc-forms` | RJSC forms, pending and overdue filings | RBAC + company scope |
| `/api/v1/calendar` | Company compliance calendar and deadline generation | Entitlement + company scope; generation requires a released deadline manifest |
| `/api/v1/legal-provenance` | Legal source catalogue, provision mappings, deadline definitions and owner decisions | SUPER_ADMIN governance writes; authenticated scoped reads |
| `/api/v1/rules` | Rule catalogue, history, summaries and override administration | Authenticated read; privileged rule changes |
| `/api/v1/admin` | Administrative dashboard, user management, activity logs and maintenance operations | Administrative roles |
| `/api/v1/notifications` | Current-user notifications, pending items and acknowledgement | Authenticated current user |
| `/api/v1/webhooks` | Webhook registration, update, test and delivery history | RBAC + endpoint ownership/admin scope |

Finance/subscription routes do not establish an automated payment-gateway integration. Treat customer billing activation and payment processing as staff-assisted until the complete payment provider, reconciliation and entitlement workflow is independently verified.

## Security

- **RBAC:** five roles — `SUPER_ADMIN`, `ADMIN_STAFF`, `LEGAL_STAFF`, `CLIENT_DIRECTOR`, `CLIENT_VIEW_ONLY`.
- **RLS:** PostgreSQL row-level security is enabled and forced on protected tables; policies and grants must be re-audited against the deployed revision.
- **JWT:** access and refresh tokens; Redis-backed revocation/blacklist on logout.
- **2FA:** TOTP secrets encrypted with AES-256-GCM; mandatory for `SUPER_ADMIN`.
- **Rate limiting:** login attempts are rate-limited per IP.
- **CORS:** configured through `ALLOWED_ORIGINS`; production should contain only the deployed frontend origin(s).
- **Audit trail:** append-only activity logging with configured retention.
- **AI governance:** AI cannot modify statutory rules; generated legal documents require human approval.


## Database migration status

- Current `main` contains **119 Alembic revision files** under `alembic/versions/` and has source head `0117_canonical_registry_runtime_read`.
- A read-only production inspection on **17 November 2026** observed Alembic revision `0112_runtime_acl_and_alembic_rls`; revisions 0113–0117 were not yet deployed at that observation time.
- CI must prove one Alembic head, audit the revision DAG, upgrade independent fresh PostgreSQL databases, and rehearse supported historical baselines. Do not infer production migration state from the source tree.
- Re-check `alembic_version` in the target environment before every release. Production migrations run only through the controlled deployment workflow; never use hand-written SQL or runtime seed scripts to reconcile the legal-rule registry.

## Deployment

**Render.com (Production)**

     Backend: https://nlc-platform.onrender.com
     Frontend: https://nlc-frontend.vercel.app
     Database: Neon PostgreSQL (confirm PITR/snapshot schedule in Neon console; do not assume retention)
     Redis: Render Redis
     Native Render autoDeploy is disabled; GitHub Actions releases only after successful CI, exact-SHA assurance, and production approval
     Automatic releases require exact lowercase NLC_AUTO_DEPLOY=true and the NLC_MIGRATION_DATABASE_URL and RENDER_API_KEY secrets
     Missing migration credentials abort before the Render deploy hook; API startup does not migrate or seed
     Apply reviewed Alembic migrations before application release
Docker (Local/On-Premise)
docker-compose up -d
Rule Parity Audit

The platform includes a canonical AST-based rule parity audit tool:
python tools/audit_rule_parity.py --no-db    # Engine + Seed
python tools/audit_rule_parity.py            # Engine + Seed + DB + API
This parses Python source files using ast.parse() (not grep) to extract rule IDs from:

    Engine: rule_id="..." keyword arguments in engine.py
    Seed: rule_id dict keys in seed_rules.py
    Database: SELECT rule_id FROM legal_rules WHERE is_active = true
    API: GET /api/v1/rules

All 4 sources must agree. This runs in CI on every push.
Documentation
Document
	
Purpose
docs/LEGAL_BASIS_MATRIX.md	Maps all 85 rules to statutory basis (PENDING legal review)
docs/LAWYER_LEGAL_REVIEW_PACK.md	Materials for Bangladesh lawyer to verify citations
CHANGELOG.md	Version history (v2.2.0)
.env.example	All configuration variables documented
/api/v1/docs	OpenAPI Swagger UI (live)
/api/v1/redoc	ReDoc API documentation (live)
 
 
Legal Notice

This platform provides automated compliance screening based on the Bangladesh Companies Act 1994 and related statutes. It is not legal advice. All rule citations are engine-derived and pending verification by a Bangladesh-qualified lawyer.

Companies with insufficient data are shown as NOT_EVALUATED (not compliant). Companies with complete data receive real compliance scores.

Status: LEGAL_BASIS_MATRIX.md is UNVERIFIED. Commercial use requires lawyer verification of all 85 rule citations.

All rights reserved — Neum Lex Counsel.
