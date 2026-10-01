# NEUM LEX COUNSEL — RJSC Compliance Intelligence Platform

**Version 2.1.0** | Engine v2.1 | 75 ILRMF Rules | Bangladesh Companies Act 1994

Proprietary Software — Neum Lex Counsel

Automates RJSC corporate compliance monitoring for Bangladeshi companies under the Companies Act 1994.

## What This Is

A full-stack compliance intelligence platform that:
- Evaluates companies against **75 ILRMF rules** across **17 modules**
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
| Migrations | Alembic (22 migrations, auto-applied on deploy) |
| Auth | JWT (32+ char secret) + TOTP 2FA (AES-256 encrypted) + bcrypt |
| Rate Limiting | slowapi (10/min on login) |
| AI | Anthropic Claude / OpenAI (human approval required) |
| Storage | AWS S3 |
| Email | AWS SES |
| Error Monitoring | Sentry |
| Tests | pytest + pytest-asyncio (211 tests) |
| CI/CD | GitHub Actions (compile + test + rule parity audit) |
| Code Quality | Ruff linter + mypy type checker |

## Project Structure

nlc_platform/
├── app/
│   ├── main.py              # FastAPI app factory + middleware + auto-migration
│   ├── api/                 # 11 routers, 80+ endpoints
│   ├── models/              # 28 SQLAlchemy ORM tables (147+ columns on companies)
│   ├── services/            # 12 service files (CompanyService, ComplianceService, etc.)
│   ├── core/                # config, security, dependencies (RBAC + RLS)
│   ├── rule_engine/         # Deterministic 75-rule ILRMF engine v2.1
│   └── worker/              # Celery tasks + beat schedule (7-year retention)
├── alembic/                 # 22 migrations (0001-0022)
├── scripts/                 # Seeders (75 rules + AI templates)
├── tests/                   # 211 tests (unit + integration)
├── tools/                   # audit_rule_parity.py (canonical AST-based parity check)
├── docs/                    # LEGAL_BASIS_MATRIX.md, LAWYER_LEGAL_REVIEW_PACK.md
├── .github/workflows/       # CI: compile + pytest + parity audit
├── Dockerfile               # Multi-stage build
├── docker-compose.yml       # Full local stack
├── render.yaml              # Render.com deployment blueprint
├── .env.example             # All config variables documented (v2.1)
├── CHANGELOG.md             # Version history
└── pytest.ini               # Test configuration

## 75 ILRMF Rules — 17 Modules

| Module | Rules | Statutory Basis |
|--------|-------|-----------------|
| AGM (7) | AGM-001 to AGM-007 | Companies Act 1994, Sections 81-85 |
| Annual Return (4) | AR-001 to AR-004 | Sections 36, 190, 304 |
| Auditor (5) | AUD-001 to AUD-005 | Sections 151, 210 |
| Bankruptcy (3) | BNK-001 to BNK-003 | Bankruptcy Act 1997 |
| BSEC Governance (4) | BSEC-001 to BSEC-004 | BSEC CG Code 2023 |
| Capital & Charges (5) | CAP-001 to CAP-004, CHG-001 | Sections 54, 87, 100 |
| Default (2) | DEF-001, DEF-002 | Sections 297, 447 |
| Directors (6) | DIR-001 to DIR-006 | Sections 92, 97, 98 |
| Escalation (5) | ESC-001 to ESC-005 | Sections 196, 199, 304 |
| Foreign Exchange (1) | FX-001 | FE Regulation Act 1947 |
| Incorporation (6) | INC-001 to INC-006 | Sections 11, 81, 90(2), 150 |
| Labour (3) | LBR-001 to LBR-003 | Labour Act 2006 |
| Office (1) | OFF-001 | Section 81 |
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

# Install + run
pip install -r requirements.txt
alembic upgrade head
python scripts/seed_rules.py
uvicorn app.main:app --reload

# Verify
curl http://localhost:8000/api/v1/health/ready
# OpenAPI docs at http://localhost:8000/api/v1/docs
# Development
uvicorn app.main:app --reload          # Start API server
alembic upgrade head                   # Run migrations
python scripts/seed_rules.py           # Seed 75 rules
celery -A app.worker.celery_app worker -l info  # Start Celery worker
celery -A app.worker.celery_app beat -l info     # Start beat scheduler

# Testing
python -m pytest tests/unit -q          # 211 unit tests
python -m pytest tests/unit -v          # Verbose with test names
DATABASE_URL=dummy python -m pytest tests/unit -q  # No DB needed

# Code Quality
ruff check app/                        # Lint
python -m compileall app/              # Compile check
python tools/audit_rule_parity.py --no-db  # Rule parity (AST-based)

# Deployment (Render.com)
# Auto-deploys on push to main branch
# Migrations run automatically on startup
# Rules auto-seed if count < 75
API Endpoints
Router
	
Endpoints
	
Auth
/api/v1/auth	login, signup, refresh, logout, me, verify-2fa, change-password	Public (login/signup)
/api/v1/companies	CRUD, evaluate, compliance, flags, score-history, dashboard	RBAC + RLS
/api/v1/filings	AGM, audit, annual-return, statutory-register CRUD	RBAC
/api/v1/rescue	plans CRUD, step updates, engagement creation	Admin+
/api/v1/documents	list, generate, approve, release, download	RBAC
/api/v1/commercial	pipeline, funnel, engagements, quotations	Admin only
/api/v1/rules	list, get, update, history, black-overrides, summary	Public list, Admin edit
/api/v1/admin	dashboard, users CRUD, activity-logs, cron evaluate-all	Admin only
/api/v1/health	live, ready	Public
/api/v1/rjsc-forms	list, create, pending, overdue	RBAC
 
 
Security

     RBAC: 5 roles (SUPER_ADMIN > ADMIN_STAFF > LEGAL_STAFF > CLIENT_DIRECTOR > CLIENT_VIEW_ONLY)
     RLS: Row-Level Security on 15 company-scoped tables
     JWT: 32+ char secret, access + refresh tokens, Redis blacklist on logout
     2FA: TOTP with AES-256-GCM encryption (optional, mandatory for SUPER_ADMIN)
     Rate Limiting: 10 login attempts/minute per IP
     Password Policy: 8+ chars, complexity requirements enforced
     CORS: Locked to frontend origin
     Audit Trail: Append-only activity logs, 7-year retention (Bangladesh requirement)
     AI Constitution: AI cannot modify rules; AI documents require human approval

Deployment
Render.com (Production)

     Backend: https://nlc-platform.onrender.com
     Frontend: https://nlc-frontend.vercel.app
     Database: Neon PostgreSQL (7-day PITR backups)
     Redis: Render Redis
     Auto-deploys on push to main
     Migrations + rule seeding run on startup
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
docs/LEGAL_BASIS_MATRIX.md	Maps all 75 rules to statutory basis (PENDING legal review)
docs/LAWYER_LEGAL_REVIEW_PACK.md	Materials for Bangladesh lawyer to verify citations
CHANGELOG.md	Version history (v2.1.0)
.env.example	All configuration variables documented
/api/v1/docs	OpenAPI Swagger UI (live)
/api/v1/redoc	ReDoc API documentation (live)
 
 
Legal Notice

This platform provides automated compliance screening based on the Bangladesh Companies Act 1994 and related statutes. It is not legal advice. All rule citations are engine-derived and pending verification by a Bangladesh-qualified lawyer.

Companies with insufficient data are shown as NOT_EVALUATED (not compliant). Companies with complete data receive real compliance scores.

Status: LEGAL_BASIS_MATRIX.md is UNVERIFIED. Commercial use requires lawyer verification of all 75 rule citations.

All rights reserved — Neum Lex Counsel.
