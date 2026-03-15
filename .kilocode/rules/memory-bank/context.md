# Context - NLC Platform Backend

## Current State

**Project Status**: ✅ NLC Platform backend scaffolded

The NLC Platform backend is a FastAPI application for RJSC compliance monitoring. The template is ready for development with Docker.

## Recently Completed

- [x] Created SPEC.md for NLC Platform (RJSC Compliance Intelligence Platform)
- [x] Set up Python project structure with FastAPI, SQLAlchemy, Redis, Celery
- [x] Created 28 database models across 6 model files
- [x] Built 8 API routers with ~70 endpoints
- [x] Implemented ILRMF rule engine with 32 compliance rules across 9 modules
- [x] Created JWT + TOTP authentication system
- [x] Set up Celery workers with beat schedule
- [x] Created Docker and docker-compose configuration
- [x] Wrote unit tests for rule engine and security

## Current Structure

| Directory/File | Purpose | Status |
|----------------|---------|--------|
| `nlc_platform/app/main.py` | FastAPI app factory | ✅ |
| `nlc_platform/app/core/` | Config, security, DB | ✅ |
| `nlc_platform/app/models/` | 28 SQLAlchemy tables | ✅ |
| `nlc_platform/app/api/v1/` | 8 API routers | ✅ |
| `nlc_platform/app/rule_engine/` | 32 ILRMF rules | ✅ |
| `nlc_platform/app/services/` | Auth service | ✅ |
| `nlc_platform/app/worker/` | Celery tasks | ✅ |
| `nlc_platform/tests/` | Unit tests | ✅ |
| `nlc_platform/docker-compose.yml` | Local dev stack | ✅ |
| `nlc_platform/.env.example` | Environment template | ✅ |

## Tech Stack

- **API**: FastAPI + Pydantic v2 + uvicorn
- **Database**: PostgreSQL 16 + SQLAlchemy 2.0 async
- **Cache/Queue**: Redis 7 + Celery 5 + redbeat
- **Auth**: JWT + TOTP (2FA mandatory)
- **AI**: Anthropic Claude / OpenAI ready
- **Storage**: AWS S3 ready
- **Notifications**: Email (SES), WhatsApp (Twilio)

## Quick Start

```bash
cd nlc_platform
cp .env.example .env
# Edit .env with your secrets

# Start services
make dev

# Or with Docker
docker-compose up -d
```

## API Endpoints

- `/api/v1/auth` - Authentication (8 endpoints)
- `/api/v1/companies` - Company management (14 endpoints)
- `/api/v1/filings` - RJSC filings (10 endpoints)
- `/api/v1/rescue` - Corporate rescue (6 endpoints)
- `/api/v1/documents` - Legal documents (7 endpoints)
- `/api/v1/commercial` - Commercial pipeline (11 endpoints)
- `/api/v1/rules` - ILRMF rules (6 endpoints)
- `/api/v1/admin` - Admin analytics (15 endpoints)
- `/api/v1/health` - Health checks (3 endpoints)

## Session History

| Date | Changes |
|------|---------|
| 2026-03-15 | Created NLC Platform backend with FastAPI, 28 models, 32 rules, auth, Docker |
