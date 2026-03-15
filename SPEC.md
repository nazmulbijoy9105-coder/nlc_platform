# NLC Platform - SPEC.md

## Project Overview

**Project Name:** Neum Lex Counsel (NLC) - RJSC Compliance Intelligence Platform  
**Type:** Full-stack Backend API  
**Core Functionality:** Automates RJSC corporate compliance monitoring for Bangladeshi companies under the Companies Act 1994  
**Target Users:** Legal firms, corporate compliance officers, company secretaries in Bangladesh

## Technical Architecture

### Tech Stack
| Layer | Technology |
|-------|------------|
| API | FastAPI + Pydantic v2 + uvicorn |
| Database | PostgreSQL 16 + SQLAlchemy 2.0 async |
| Cache/Queue | Redis 7 + Celery 5 + redbeat |
| Migrations | Alembic |
| Auth | JWT + TOTP (2FA mandatory) |
| AI | Anthropic Claude / OpenAI |
| Storage | AWS S3 |
| Email | AWS SES |
| Tests | pytest + pytest-asyncio |

## Functionality Specification

### 1. Compliance Evaluation Engine
- Evaluate companies against 32 ILRMF rules across 9 modules
- Calculate compliance score 0-100
- Assign risk bands: GREEN (80-100), YELLOW (60-79), RED (40-59), BLACK (0-39)
- Flag violations with statutory basis and score impact

### 2. ILRMF Rule Modules (9 Modules, 32 Rules)
1. **Board Composition** (4 rules) - Director qualifications, board diversity
2. **Financial Reporting** (4 rules) - Annual returns, financial statements
3. **Shareholder Meetings** (3 rules) - AGM/EGM requirements
4. **Statutory Filings** (4 rules) - RJSC form submissions
5. **Capital Requirements** (3 rules) - Paid-up capital, authorized capital
6. **Directors Meetings** (3 rules) - Board meeting frequency, quorum
7. **Corporate Governance** (4 rules) - Policies, audits
8. **Charges & Mortgages** (3 rules) - Registered charges
9. **Miscellaneous** (4 rules) - Other compliance items

### 3. Legal Document Generation
- AI-drafted legal documents (notices, resolutions, applications)
- Mandatory human approval workflow before release
- Document versioning and audit trail

### 4. Corporate Rescue Pipeline
- Track RED/BLACK flagged companies
- Rescue workflow: Assessment → Strategy → Execution → Monitoring
- Timeline and milestone tracking

### 5. Commercial Engagement
- Track client engagements
- Revenue pipeline management
- Billing and invoicing

### 6. Notification System
- Dashboard notifications
- Email notifications via AWS SES
- WhatsApp notifications (Twilio)
- Deadline warnings and reminders

## API Endpoints (80 Total)

### /api/v1/auth (8 endpoints)
- POST /register
- POST /login
- POST /logout
- POST /refresh
- POST /totp/setup
- POST /totp/verify
- POST /totp/disable
- GET /me

### /api/v1/companies (14 endpoints)
- POST /companies
- GET /companies
- GET /companies/{id}
- PUT /companies/{id}
- DELETE /companies/{id}
- POST /companies/{id}/evaluate
- GET /companies/{id}/score
- GET /companies/{id}/violations
- GET /companies/{id}/documents
- POST /companies/{id}/filings
- GET /companies/{id}/filings
- GET /companies/{id}/rescue-status
- PUT /companies/{id}/status
- GET /companies/{id}/timeline

### /api/v1/filings (10 endpoints)
- POST /filings
- GET /filings
- GET /filings/{id}
- PUT /filings/{id}
- DELETE /filings/{id}
- GET /filings/company/{company_id}
- GET /filings/upcoming
- GET /filings/overdue
- POST /filings/{id}/submit
- GET /filings/{id}/history

### /api/v1/rescue (6 endpoints)
- POST /rescue
- GET /rescue
- GET /rescue/{id}
- PUT /rescue/{id}
- PUT /rescue/{id}/status
- GET /rescue/company/{company_id}

### /api/v1/documents (7 endpoints)
- POST /documents
- GET /documents
- GET /documents/{id}
- PUT /documents/{id}
- DELETE /documents/{id}
- POST /documents/{id}/approve
- GET /documents/{id}/download

### /api/v1/commercial (11 endpoints)
- POST /commercial/engagements
- GET /commercial/engagements
- GET /commercial/engagements/{id}
- PUT /commercial/engagements/{id}
- POST /commercial/pipeline
- GET /commercial/pipeline
- PUT /commercial/pipeline/{id}
- POST /commercial/invoices
- GET /commercial/invoices
- GET /commercial/invoices/{id}
- GET /commercial/dashboard

### /api/v1/rules (6 endpoints)
- GET /rules
- GET /rules/{id}
- GET /rules/modules
- GET /rules/module/{module_id}
- GET /rules/{id}/criteria
- POST /rules/{id}/test

### /api/v1/admin (15 endpoints)
- GET /admin/users
- POST /admin/users
- PUT /admin/users/{id}
- DELETE /admin/users/{id}
- GET /admin/users/{id}/activity
- GET /admin/companies/all
- PUT /admin/companies/{id}/verify
- GET /admin/analytics/compliance
- GET /admin/analytics/filings
- GET /admin/analytics/rescue
- GET /admin/analytics/revenue
- GET /admin/settings
- PUT /admin/settings
- GET /admin/audit-log
- GET /admin/health

### /api/v1/health (3 endpoints)
- GET /health
- GET /health/db
- GET /health/redis

## Database Models (28 Tables)

### Core Tables
1. users - User accounts with roles
2. user_sessions - Active sessions
3. companies - Company records
4. company_contacts - Company contact persons

### Compliance Tables
5. compliance_scores - Calculated scores
6. violations - Rule violations
7. rule_definitions - 32 ILRMF rules
8. rule_modules - 9 rule modules
9. rule_criteria - Individual rule criteria

### Filing Tables
10. filings - RJSC filings
11. filing_history - Filing status changes
12. filing_deadlines - Scheduled deadlines

### Document Tables
13. documents - Legal documents
14. document_versions - Document versions
15. document_approvals - Approval workflow

### Rescue Tables
16. rescue_cases - Corporate rescue cases
17. rescue_milestones - Rescue milestones
18. rescue_documents - Rescue-related documents

### Commercial Tables
19. engagements - Client engagements
20. pipeline - Sales pipeline
21. invoices - Invoices
22. invoice_items - Invoice line items

### Notification Tables
23. notifications - Dashboard notifications
24. notification_preferences - User preferences
25. email_queue - Queued emails
26. whatsapp_queue - Queued WhatsApp messages

### Audit & Settings
27. audit_logs - Audit trail
28. system_settings - Configuration

## User Roles
- SUPER_ADMIN
- ADMIN_STAFF
- LEGAL_STAFF
- CLIENT_DIRECTOR
- CLIENT_VIEW_ONLY

## Acceptance Criteria

1. FastAPI server starts without errors
2. All 80 endpoints respond correctly
3. JWT + TOTP authentication works end-to-end
4. ILRMF rule engine evaluates companies correctly
5. Compliance scores calculate accurately (0-100)
6. Risk bands assign correctly (GREEN/YELLOW/RED/BLACK)
7. Document generation workflow functions
8. Rescue pipeline tracks companies
9. Notifications queue and send
10. All tests pass
