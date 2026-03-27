---
description: "NLC Platform development guidelines for consistent, high-quality contributions across APIs, compliance rules, and infrastructure."
---

# NLC Platform Development Guidelines

## Project Overview

**nlc_platform** is a FastAPI-based compliance and filing management system featuring:

- **FastAPI Backend**: REST APIs for company management, filings, documents
- **Rule Engine**: ILRMF compliance rule evaluation and state management
- **Database**: PostgreSQL with Alembic migrations
- **Tasks**: Celery workers for background jobs with beat scheduler
- **Deployment**: Multi-platform support (Render, Fly.io, Vercel)

## Quick Reference by Task

### 🔧 I'm Working On...

**API Endpoints** → See `.github/agents/fastapi-backend.agent.md`
- Use `/app/api/` patterns
- Follow Pydantic validation
- Implement service layer

**Compliance Rules** → See `.github/agents/rule-engine.agent.md`
- Define rules in `app/rule_engine/`
- Extend `RulesService`
- Test with unit tests

**Infrastructure/Deployment** → See `.github/agents/devops-deployment.agent.md`
- Manage Docker and migrations
- Configure environment
- Monitor health

**Database Schema** → Use FastAPI Backend agent
- Create SQLAlchemy models
- Generate migrations with Alembic
- Add Pydantic schemas

**Background Jobs** → Use DevOps agent
- Configure Celery tasks: `app/worker/tasks.py`
- Define schedules: `app/worker/beat_schedule.py`
- Monitor execution

## Code Standards

### Naming Conventions
- **Files**: `snake_case` (models.py, services.py)
- **Classes**: `PascalCase` (Company, RulesService)
- **Functions**: `snake_case` (get_company, validate_filing)
- **Constants**: `UPPER_CASE` (MAX_RETRY_COUNT, DEFAULT_TIMEOUT)

### Folder Structure
```
app/api/           # FastAPI routes
app/models/        # SQLAlchemy models
app/services/      # Business logic
app/rule_engine/   # Rule evaluation
app/worker/        # Celery tasks
app/core/          # Config, security, dependencies
tests/             # Unit and integration tests
```

### Import Organization
```python
# 1. Standard library
import os
import json
from datetime import datetime

# 2. Third-party
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

# 3. Local
from app.models import Company
from app.services import CompanyService
from app.core.security import get_current_user
```

## Common Workflows

### Creating a New API Endpoint
1. **Define models** in `app/models/`
2. **Create service** in `app/services/`
3. **Route logic** in `app/api/`
4. **Write tests** in `tests/integration/`
5. **Document** in docstring

### Adding Database Schema
1. Create SQLAlchemy model in `app/models/`
2. Generate migration: `alembic revision --autogenerate -m "description"`
3. Review migration file
4. Apply: `alembic upgrade head`
5. Create Pydantic schemas for API

### Implementing Compliance Rule
1. Design rule structure
2. Extend `RulesService` with evaluation logic
3. Add to `app/rule_engine/engine.py`
4. Create/update database migration
5. Write comprehensive tests
6. Integrate with API endpoint

### Deploying Changes
1. (Local) Verify tests pass
2. (Local) Run against test database
3. (Local) Commit and push changes
4. (GitHub) Create pull request
5. (CI) Wait for automated checks
6. (GitHub) Request review
7. (DevOps) Deploy to staging first
8. (DevOps) Run smoke tests
9. (DevOps) Deploy to production
10. (Monitoring) Verify health checks

## Environment Configuration

### Required Environment Variables
```bash
DATABASE_URL=postgresql://user:pass@host/dbname
REDIS_URL=redis://host:port
SECRET_KEY=your-secret-key
ENVIRONMENT=development|staging|production
```

### Configuration Loading
- Development: `.env` file (via `app/core/config.py`)
- Production: Platform-specific (Render, Fly.io env vars)
- See `app/core/config.py` for all variables

## Testing Standards

### Unit Tests
- Location: `tests/unit/`
- Focus: Individual functions, logic
- Tools: pytest, fixtures in `conftest.py`

### Integration Tests
- Location: `tests/integration/`
- Focus: API endpoints, service interactions
- Requirements: Test database, fixtures

### Running Tests
```bash
# All tests
pytest

# Specific file
pytest tests/unit/test_rule_engine.py

# With coverage
pytest --cov=app

# Verbose output
pytest -v
```

## Common Patterns

### API Endpoint Pattern
```python
@router.post("/companies", response_model=CompanyResponse)
async def create_company(
    data: CompanyCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new company."""
    return CompanyService(db).create(data, current_user)
```

### Service Pattern
```python
class CompanyService(BaseService):
    def create(self, data: CompanyCreate, user: User) -> Company:
        company = Company(**data.dict())
        company.created_by = user.id
        self.db.add(company)
        self.db.commit()
        return company
```

### Model Pattern
```python
class Company(Base):
    __tablename__ = "companies"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
    filings: Mapped[List["Filing"]] = relationship(back_populates="company")
```

### Pydantic Schema Pattern
```python
class CompanyBase(BaseModel):
    name: str = Field(..., min_length=1)
    description: Optional[str] = None

class CompanyCreate(CompanyBase):
    pass

class CompanyResponse(CompanyBase):
    id: int
    created_at: datetime
```

## Error Handling

### API Error Responses
```python
from fastapi import HTTPException

# 404 - Not Found
raise HTTPException(status_code=404, detail="Company not found")

# 400 - Bad Request
raise HTTPException(status_code=400, detail="Invalid company name")

# 403 - Forbidden
raise HTTPException(status_code=403, detail="Insufficient permissions")

# 500 - Server Error
raise HTTPException(status_code=500, detail="Internal server error")
```

### Exception Patterns
```python
try:
    result = service.operation()
except SpecificException as e:
    logger.error(f"Error: {e}")
    raise HTTPException(status_code=400, detail=str(e))
except Exception as e:
    logger.error(f"Unexpected error: {e}", exc_info=True)
    raise HTTPException(status_code=500, detail="Internal error")
```

## Documentation

### Docstring Format
```python
def create_company(self, data: CompanyCreate, user: User) -> Company:
    """Create a new company with validation.
    
    Args:
        data: Company creation data (name, description, etc.)
        user: Current authenticated user for audit trail
        
    Returns:
        Created Company object with generated id
        
    Raises:
        ValueError: If company name already exists
        ValidationError: If data fails validation
    """
```

### API Documentation
- FastAPI auto-generates docs at `/docs`
- Include docstrings in endpoint handlers
- Use descriptive parameter names
- Include response examples where helpful

## Git Workflow

### Commit Messages
```
feat: add company filing validation endpoint
fix: correct compliance rule evaluation logic
docs: update deployment procedures
refactor: simplify rule engine predicates
test: add integration tests for filing service
```

### Branch Naming
```
feature/add-filing-validation
fix/correct-compliance-logic
docs/update-deployment-guide
refactor/simplify-rules-engine
```

## Specialized Agents

For detailed guidance on specific domains, see `.github/AGENTS.md`:

- **DevOps & Deployment Specialist**: Infrastructure, deployments, database operations
- **Rule Engine & Compliance Specialist**: Compliance rules, business logic
- **FastAPI Backend Developer**: APIs, services, models

## Performance Considerations

### Database
- Add indexes for frequently queried columns
- Use pagination for large result sets
- Implement query result caching where appropriate

### API
- Keep response payloads lean
- Use pagination for list endpoints
- Implement request timeouts
- Monitor query performance

### Celery
- Set appropriate task timeouts
- Implement retry logic for failed tasks
- Monitor queue depth and worker count
- Use task routing for different work types

## Security Practices

✅ **DO:**
- Hash passwords with bcrypt
- Use JWT tokens with appropriate expiration
- Validate all user input
- Check permissions on every operation
- Use environment variables for secrets
- Implement rate limiting on public endpoints

❌ **DON'T:**
- Store passwords in plain text
- Expose sensitive data in logs
- Trust client-provided user IDs
- Skip permission checks
- Hardcode secrets in code
- Return detailed error messages to clients

## Troubleshooting

### Tests Failing
1. Check database connection
2. Verify test fixtures are correct
3. Ensure test database is clean
4. Run individual test for isolation

### API Errors
1. Check application logs
2. Verify request format
3. Check database constraints
4. Review error response details

### Deployment Issues
1. Check environment variables
2. Verify database migrations ran
3. Check health endpoint
4. Review platform-specific logs

---

**Need help?** Ask the specialized agents or consult `.github/AGENTS.md` for domain-specific guidance.
