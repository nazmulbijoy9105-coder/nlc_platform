# NEUM LEX COUNSEL — RJSC Compliance Intelligence Platform

Proprietary Software — Neum Lex Counsel
Automates RJSC corporate compliance monitoring for Bangladeshi companies under the Companies Act 1994.

## What This Is

A full-stack compliance intelligence backend that:
- Evaluates companies against 32 ILRMF rules across 9 modules
- Scores 0-100 with risk band GREEN / YELLOW / RED / BLACK
- Flags violations with statutory basis and score impact
- Generates AI-drafted legal documents with mandatory human approval before release
- Manages corporate rescue pipeline for RED/BLACK companies
- Tracks commercial engagements and revenue pipeline
- Sends deadline warnings via Dashboard, Email, WhatsApp

## Tech Stack

| Layer | Technology |
|-------|-----------|
| API | FastAPI + Pydantic v2 + uvicorn |
| Database | PostgreSQL 16 + SQLAlchemy 2.0 async |
| Cache/Queue | Redis 7 + Celery 5 + redbeat |
| Migrations | Alembic |
| Auth | JWT + TOTP (2FA mandatory) |
| AI | Anthropic Claude / OpenAI |
| Storage | AWS S3 |
| Email | AWS SES |
| Tests | pytest + pytest-asyncio |

## Project Structure

```
nlc_platform/
├── app/
│   ├── main.py              # FastAPI app factory + middleware
│   ├── api/                 # 10 routers, 80 endpoints
│   ├── models/              # 28 SQLAlchemy ORM tables
│   ├── services/            # 11 service files, 122 async functions
│   ├── core/                # config, security, dependencies
│   ├── rule_engine/         # Deterministic 32-rule ILRMF engine
│   └── worker/              # Celery tasks + beat schedule
├── alembic/                 # Database migrations
├── scripts/                 # Seeders (rules + AI templates)
├── tests/                   # 194 tests (unit + integration)
├── infra/nginx/             # Nginx reverse proxy config
├── Dockerfile               # 6-stage multi-target build
├── docker-compose.yml       # Full local stack
├── render.yaml              # Render.com deployment blueprint
├── Makefile                 # Developer shortcuts
└── .env.example             # All 62 config variables documented
```

## Quick Start

```bash
git clone https://github.com/YOUR_ORG/nlc-platform.git
cd nlc-platform
cp .env.example .env
# Edit .env - fill required secrets (see DEPLOY.md)

make setup    # build + migrate + seed + start
curl http://localhost:8000/api/v1/health
```

## Key Commands

```bash
make dev              # Start all services
make stop             # Stop all services
make migrate          # Run migrations
make seed             # Seed 32 rules + 9 AI templates
make test             # Full test suite
make test-unit        # Rule engine tests (no DB)
make flower           # Celery monitoring UI
make psql             # Postgres shell
make lint             # Ruff linter
```

## Generating Secrets

```bash
JWT secret:   openssl rand -hex 64
TOTP key:     python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
DB password:  openssl rand -base64 32
```

## API: 80 Endpoints

| Router | Endpoints |
|--------|-----------|
| /api/v1/auth | 8 |
| /api/v1/companies | 14 |
| /api/v1/filings | 10 |
| /api/v1/rescue | 6 |
| /api/v1/documents | 7 |
| /api/v1/commercial | 11 |
| /api/v1/rules | 6 |
| /api/v1/admin | 15 |
| /api/v1/health | 3 |

## User Roles

SUPER_ADMIN > ADMIN_STAFF > LEGAL_STAFF > CLIENT_DIRECTOR > CLIENT_VIEW_ONLY

See DEPLOY.md for full deployment instructions (Render.com, Docker VPS, AWS).

All rights reserved - Neum Lex Counsel.
# nlc_platform
