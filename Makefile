# =============================================================================
# NEUM LEX COUNSEL — Developer Makefile
# =============================================================================
#
# Prerequisites: docker, docker compose, python3
#
# Quick start:
#   make setup    — First-time: build images, migrate DB, seed rules + templates
#   make dev      — Start all services in dev mode (with logs)
#   make dev-bg   — Start all services in background
#   make stop     — Stop all services
#   make logs     — Tail logs from all services
#
# Daily workflow:
#   make migrate  — Run pending Alembic migrations
#   make seed     — Re-seed rules + templates (safe to run multiple times)
#   make test     — Run full test suite
#   make lint     — Run ruff + mypy
#
# =============================================================================

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

COMPOSE         := docker compose
COMPOSE_PROD    := docker compose --profile production
COMPOSE_MONITOR := docker compose --profile monitoring
COMPOSE_FULL    := docker compose --profile full

API_SERVICE     := api
WORKER_SERVICE  := worker

# Shell colours
GREEN  := \033[0;32m
YELLOW := \033[0;33m
RED    := \033[0;31m
CYAN   := \033[0;36m
BOLD   := \033[1m
RESET  := \033[0m

.DEFAULT_GOAL := help
.PHONY: help setup dev dev-bg stop restart logs logs-api logs-worker logs-beat \
        build build-no-cache migrate migrate-down migrate-history \
        seed seed-rules seed-templates seed-all \
        shell shell-db shell-redis \
        test test-unit test-integration test-coverage lint format typecheck \
        clean clean-all psql redis-cli \
        flower monitoring \
        prod prod-stop prod-logs \
        ssl-cert check-env backup evaluate-all \
        status health-check

# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------

help:
	@echo ""
	@echo "$(BOLD)$(CYAN)NEUM LEX COUNSEL — Developer Commands$(RESET)"
	@echo "$(CYAN)══════════════════════════════════════════════════════════$(RESET)"
	@echo ""
	@echo "$(BOLD)SETUP$(RESET)"
	@echo "  $(GREEN)make setup$(RESET)           First-time setup: build → migrate → seed"
	@echo "  $(GREEN)make build$(RESET)           Build all Docker images"
	@echo "  $(GREEN)make build-no-cache$(RESET)  Rebuild images without cache"
	@echo "  $(GREEN)make ssl-cert$(RESET)         Generate self-signed SSL cert for local dev"
	@echo "  $(GREEN)make check-env$(RESET)        Validate .env file has all required variables"
	@echo ""
	@echo "$(BOLD)DEVELOPMENT$(RESET)"
	@echo "  $(GREEN)make dev$(RESET)             Start all services (foreground, with logs)"
	@echo "  $(GREEN)make dev-bg$(RESET)          Start all services (background)"
	@echo "  $(GREEN)make stop$(RESET)            Stop all services"
	@echo "  $(GREEN)make restart$(RESET)         Stop then start all services"
	@echo "  $(GREEN)make status$(RESET)          Show service container status"
	@echo "  $(GREEN)make health-check$(RESET)    Hit /api/v1/health and show result"
	@echo ""
	@echo "$(BOLD)LOGS$(RESET)"
	@echo "  $(GREEN)make logs$(RESET)            Tail all service logs"
	@echo "  $(GREEN)make logs-api$(RESET)        Tail API logs only"
	@echo "  $(GREEN)make logs-worker$(RESET)     Tail Celery worker logs"
	@echo "  $(GREEN)make logs-beat$(RESET)       Tail Celery beat logs"
	@echo ""
	@echo "$(BOLD)DATABASE$(RESET)"
	@echo "  $(GREEN)make migrate$(RESET)         Run pending Alembic migrations"
	@echo "  $(GREEN)make migrate-down$(RESET)    Rollback last migration"
	@echo "  $(GREEN)make migrate-history$(RESET) Show migration history"
	@echo "  $(GREEN)make psql$(RESET)            Open PostgreSQL interactive shell"
	@echo "  $(GREEN)make redis-cli$(RESET)       Open Redis interactive CLI"
	@echo ""
	@echo "$(BOLD)SEEDING$(RESET)"
	@echo "  $(GREEN)make seed$(RESET)            Seed rules + prompt templates (safe to repeat)"
	@echo "  $(GREEN)make seed-rules$(RESET)      Seed/update 32 ILRMF rules only"
	@echo "  $(GREEN)make seed-templates$(RESET)  Seed/update 9 AI prompt templates only"
	@echo "  $(GREEN)make seed-all$(RESET)        Same as make seed"
	@echo ""
	@echo "$(BOLD)TESTING$(RESET)"
	@echo "  $(GREEN)make test$(RESET)            Run full test suite"
	@echo "  $(GREEN)make test-unit$(RESET)       Unit tests only (rule engine + services)"
	@echo "  $(GREEN)make test-integration$(RESET) Integration tests (requires running DB)"
	@echo "  $(GREEN)make test-coverage$(RESET)   Run tests with coverage report"
	@echo ""
	@echo "$(BOLD)CODE QUALITY$(RESET)"
	@echo "  $(GREEN)make lint$(RESET)            Run ruff linter"
	@echo "  $(GREEN)make format$(RESET)          Auto-format with ruff + isort"
	@echo "  $(GREEN)make typecheck$(RESET)       Run mypy type checker"
	@echo ""
	@echo "$(BOLD)MONITORING$(RESET)"
	@echo "  $(GREEN)make flower$(RESET)          Start with Flower monitoring UI"
	@echo "  $(GREEN)make monitoring$(RESET)      Same as make flower"
	@echo ""
	@echo "$(BOLD)PRODUCTION$(RESET)"
	@echo "  $(GREEN)make prod$(RESET)            Start in production mode (with nginx)"
	@echo "  $(GREEN)make prod-stop$(RESET)       Stop production services"
	@echo "  $(GREEN)make prod-logs$(RESET)       Tail production logs"
	@echo ""
	@echo "$(BOLD)MAINTENANCE$(RESET)"
	@echo "  $(GREEN)make backup$(RESET)          Trigger manual S3 activity log backup"
	@echo "  $(GREEN)make evaluate-all$(RESET)    Trigger portfolio-wide compliance evaluation"
	@echo "  $(GREEN)make clean$(RESET)           Remove stopped containers + dangling images"
	@echo "  $(GREEN)make clean-all$(RESET)       DANGEROUS: also removes volumes (data loss!)"
	@echo ""


# =============================================================================
# SETUP
# =============================================================================

setup: check-env build
	@echo "$(CYAN)Starting infrastructure...$(RESET)"
	$(COMPOSE) up -d postgres redis
	@echo "$(YELLOW)Waiting for postgres to be ready...$(RESET)"
	@sleep 5
	@$(MAKE) migrate
	@$(MAKE) seed
	@echo "$(CYAN)Starting remaining services...$(RESET)"
	$(COMPOSE) up -d
	@echo ""
	@echo "$(GREEN)$(BOLD)✅ Setup complete!$(RESET)"
	@echo ""
	@echo "  API:     http://localhost:8000"
	@echo "  Docs:    http://localhost:8000/api/v1/docs"
	@echo "  Health:  http://localhost:8000/api/v1/health"
	@echo ""
	@echo "Run '$(CYAN)make flower$(RESET)' to start Celery monitoring at http://localhost:5555"


# =============================================================================
# BUILD
# =============================================================================

build:
	@echo "$(CYAN)Building Docker images...$(RESET)"
	$(COMPOSE) build --parallel
	@echo "$(GREEN)Build complete.$(RESET)"

build-no-cache:
	@echo "$(CYAN)Building images (no cache)...$(RESET)"
	$(COMPOSE) build --no-cache --parallel
	@echo "$(GREEN)Build complete.$(RESET)"


# =============================================================================
# DEVELOPMENT — START / STOP
# =============================================================================

dev: check-env
	@echo "$(CYAN)Starting NLC services (foreground)...$(RESET)"
	$(COMPOSE) up

dev-bg: check-env
	@echo "$(CYAN)Starting NLC services (background)...$(RESET)"
	$(COMPOSE) up -d
	@echo "$(GREEN)Services started.$(RESET)"
	@$(MAKE) status

stop:
	@echo "$(YELLOW)Stopping all services...$(RESET)"
	$(COMPOSE) down
	@echo "$(GREEN)All services stopped.$(RESET)"

restart: stop dev-bg

status:
	$(COMPOSE) ps

health-check:
	@echo "$(CYAN)Checking API health...$(RESET)"
	@curl -sf http://localhost:$${API_EXTERNAL_PORT:-8000}/api/v1/health | python3 -m json.tool 2>/dev/null || \
		echo "$(RED)API not reachable. Is it running? Try: make dev-bg$(RESET)"


# =============================================================================
# LOGS
# =============================================================================

logs:
	$(COMPOSE) logs -f --tail=100

logs-api:
	$(COMPOSE) logs -f --tail=100 $(API_SERVICE)

logs-worker:
	$(COMPOSE) logs -f --tail=100 $(WORKER_SERVICE)

logs-beat:
	$(COMPOSE) logs -f --tail=100 beat

logs-db:
	$(COMPOSE) logs -f --tail=50 postgres


# =============================================================================
# DATABASE — MIGRATIONS
# =============================================================================

migrate:
	@echo "$(CYAN)Running Alembic migrations...$(RESET)"
	$(COMPOSE) run --rm $(API_SERVICE) alembic upgrade head
	@echo "$(GREEN)Migrations complete.$(RESET)"

migrate-down:
	@echo "$(YELLOW)Rolling back last migration...$(RESET)"
	$(COMPOSE) run --rm $(API_SERVICE) alembic downgrade -1
	@echo "$(GREEN)Rollback complete.$(RESET)"

migrate-history:
	$(COMPOSE) run --rm $(API_SERVICE) alembic history --verbose

migrate-current:
	$(COMPOSE) run --rm $(API_SERVICE) alembic current

# Generate a new empty migration
# Usage: make migrate-new MSG="add_column_x_to_table_y"
migrate-new:
	@if [ -z "$(MSG)" ]; then echo "$(RED)Error: provide MSG. Usage: make migrate-new MSG='your message'$(RESET)"; exit 1; fi
	$(COMPOSE) run --rm $(API_SERVICE) alembic revision --autogenerate -m "$(MSG)"
	@echo "$(GREEN)Migration file created.$(RESET)"

psql:
	@echo "$(CYAN)Opening PostgreSQL shell (database: $$POSTGRES_DB)...$(RESET)"
	$(COMPOSE) exec postgres psql -U $${POSTGRES_USER:-nlc_user} -d $${POSTGRES_DB:-nlc_db}

redis-cli:
	@echo "$(CYAN)Opening Redis CLI...$(RESET)"
	$(COMPOSE) exec redis redis-cli -a $${REDIS_PASSWORD} --no-auth-warning


# =============================================================================
# SEEDING
# =============================================================================

seed: seed-rules seed-templates
	@echo "$(GREEN)$(BOLD)✅ All seeds complete.$(RESET)"

seed-rules:
	@echo "$(CYAN)Seeding 32 ILRMF legal rules...$(RESET)"
	$(COMPOSE) run --rm $(API_SERVICE) python scripts/seed_rules.py --verbose
	@echo "$(GREEN)Rules seeded.$(RESET)"

seed-templates:
	@echo "$(CYAN)Seeding 9 AI prompt templates...$(RESET)"
	$(COMPOSE) run --rm $(API_SERVICE) python scripts/seed_prompt_templates.py --verbose
	@echo "$(GREEN)Templates seeded.$(RESET)"

seed-all: seed

# Dry run — validates without writing to DB
seed-dry-run:
	@echo "$(YELLOW)DRY RUN — validating seeds (no DB writes)...$(RESET)"
	$(COMPOSE) run --rm $(API_SERVICE) python scripts/seed_rules.py --dry-run
	$(COMPOSE) run --rm $(API_SERVICE) python scripts/seed_prompt_templates.py --dry-run


# =============================================================================
# SHELL ACCESS
# =============================================================================

shell:
	@echo "$(CYAN)Opening shell in API container...$(RESET)"
	$(COMPOSE) exec $(API_SERVICE) /bin/bash

shell-worker:
	$(COMPOSE) exec $(WORKER_SERVICE) /bin/bash

# Python REPL inside API container (with app context)
python:
	$(COMPOSE) exec $(API_SERVICE) python3


# =============================================================================
# TESTING
# =============================================================================

test:
	@echo "$(CYAN)Running full test suite...$(RESET)"
	$(COMPOSE) run --rm -e TESTING=true $(API_SERVICE) \
		python -m pytest tests/ -v --tb=short
	@echo "$(GREEN)Tests complete.$(RESET)"

test-unit:
	@echo "$(CYAN)Running unit tests...$(RESET)"
	$(COMPOSE) run --rm -e TESTING=true $(API_SERVICE) \
		python -m pytest tests/unit/ -v --tb=short

test-integration:
	@echo "$(CYAN)Running integration tests (requires running DB)...$(RESET)"
	$(COMPOSE) run --rm -e TESTING=true $(API_SERVICE) \
		python -m pytest tests/integration/ -v --tb=short

test-coverage:
	@echo "$(CYAN)Running tests with coverage...$(RESET)"
	$(COMPOSE) run --rm -e TESTING=true $(API_SERVICE) \
		python -m pytest tests/ \
		--cov=app \
		--cov-report=html:/tmp/coverage_report \
		--cov-report=term-missing \
		--cov-fail-under=70
	@echo "$(GREEN)Coverage report: open coverage_report/index.html$(RESET)"

test-rule-engine:
	@echo "$(CYAN)Running rule engine unit tests...$(RESET)"
	$(COMPOSE) run --rm -e TESTING=true $(API_SERVICE) \
		python -m pytest tests/unit/test_rule_engine.py -v --tb=long


# =============================================================================
# CODE QUALITY
# =============================================================================

lint:
	@echo "$(CYAN)Running ruff linter...$(RESET)"
	$(COMPOSE) run --rm $(API_SERVICE) python -m ruff check app/ scripts/ tests/ --output-format=concise
	@echo "$(GREEN)Lint complete.$(RESET)"

format:
	@echo "$(CYAN)Auto-formatting with ruff...$(RESET)"
	$(COMPOSE) run --rm $(API_SERVICE) python -m ruff check app/ scripts/ tests/ --fix
	$(COMPOSE) run --rm $(API_SERVICE) python -m ruff format app/ scripts/ tests/
	@echo "$(GREEN)Format complete.$(RESET)"

typecheck:
	@echo "$(CYAN)Running mypy type checker...$(RESET)"
	$(COMPOSE) run --rm $(API_SERVICE) python -m mypy app/ --ignore-missing-imports --no-strict-optional
	@echo "$(GREEN)Type check complete.$(RESET)"

security-scan:
	@echo "$(CYAN)Running pip-audit vulnerability scan...$(RESET)"
	$(COMPOSE) run --rm $(API_SERVICE) pip-audit
	@echo "$(GREEN)Security scan complete.$(RESET)"


# =============================================================================
# MONITORING
# =============================================================================

flower:
	@echo "$(CYAN)Starting services with Flower monitoring...$(RESET)"
	$(COMPOSE_MONITOR) up -d
	@echo "$(GREEN)Flower UI: http://localhost:$${FLOWER_EXTERNAL_PORT:-5555}/flower$(RESET)"

monitoring: flower


# =============================================================================
# CELERY
# =============================================================================

worker-status:
	@echo "$(CYAN)Celery worker status...$(RESET)"
	$(COMPOSE) exec $(WORKER_SERVICE) celery -A app.worker.celery_app inspect active

worker-stats:
	$(COMPOSE) exec $(WORKER_SERVICE) celery -A app.worker.celery_app inspect stats

beat-schedule:
	@echo "$(CYAN)Current redbeat schedule:$(RESET)"
	$(COMPOSE) run --rm $(API_SERVICE) python3 -c \
		"from app.worker.beat_schedule import BEAT_SCHEDULE; [print(f'  {k}') for k in BEAT_SCHEDULE]"

# Purge all pending tasks (DANGEROUS)
worker-purge:
	@echo "$(RED)WARNING: This will purge ALL pending Celery tasks.$(RESET)"
	@read -p "Are you sure? [y/N] " confirm && [ "$$confirm" = "y" ] || exit 1
	$(COMPOSE) exec $(WORKER_SERVICE) celery -A app.worker.celery_app purge -f


# =============================================================================
# PRODUCTION
# =============================================================================

prod: check-env ssl-check
	@echo "$(CYAN)Starting production stack (with nginx)...$(RESET)"
	$(COMPOSE_PROD) up -d
	@echo "$(GREEN)Production stack running.$(RESET)"
	@$(MAKE) status

prod-stop:
	$(COMPOSE_PROD) down

prod-logs:
	$(COMPOSE_PROD) logs -f --tail=100

ssl-check:
	@if [ ! -f "infra/nginx/ssl/nlc.crt" ]; then \
		echo "$(YELLOW)SSL cert not found. Generating self-signed cert...$(RESET)"; \
		$(MAKE) ssl-cert; \
	fi

ssl-cert:
	@echo "$(CYAN)Generating self-signed SSL certificate for development...$(RESET)"
	@mkdir -p infra/nginx/ssl
	@openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
		-keyout infra/nginx/ssl/nlc.key \
		-out infra/nginx/ssl/nlc.crt \
		-subj "/C=BD/ST=Dhaka/L=Dhaka/O=Neum Lex Counsel/CN=localhost" \
		2>/dev/null
	@echo "$(GREEN)SSL cert generated: infra/nginx/ssl/nlc.crt$(RESET)"
	@echo "$(YELLOW)Note: This is a self-signed cert for development only.$(RESET)"
	@echo "$(YELLOW)For production, use Let's Encrypt (certbot).$(RESET)"


# =============================================================================
# ADMIN OPERATIONS (hit the API)
# =============================================================================

backup:
	@echo "$(CYAN)Triggering S3 activity log backup via API...$(RESET)"
	@curl -sf -X POST \
		-H "Authorization: Bearer $${SUPER_ADMIN_TOKEN}" \
		http://localhost:$${API_EXTERNAL_PORT:-8000}/api/v1/admin/maintenance/backup \
		| python3 -m json.tool || echo "$(RED)Failed. Is API running and SUPER_ADMIN_TOKEN set?$(RESET)"

evaluate-all:
	@echo "$(CYAN)Triggering full portfolio compliance evaluation...$(RESET)"
	@curl -sf -X POST \
		-H "Authorization: Bearer $${SUPER_ADMIN_TOKEN}" \
		http://localhost:$${API_EXTERNAL_PORT:-8000}/api/v1/admin/maintenance/evaluate-all \
		| python3 -m json.tool || echo "$(RED)Failed. Is API running and SUPER_ADMIN_TOKEN set?$(RESET)"


# =============================================================================
# ENV VALIDATION
# =============================================================================

check-env:
	@if [ ! -f ".env" ]; then \
		echo "$(RED)Error: .env file not found.$(RESET)"; \
		echo "$(YELLOW)Run: cp .env.example .env  then fill in the required values.$(RESET)"; \
		exit 1; \
	fi
	@python3 -c "
import re, sys
required = [
    'DATABASE_URL', 'POSTGRES_PASSWORD', 'JWT_SECRET_KEY', 'TOTP_ENCRYPTION_KEY',
    'REDIS_URL', 'REDIS_PASSWORD', 'AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY',
    'S3_BUCKET_NAME', 'EMAIL_FROM', 'ANTHROPIC_API_KEY'
]
env = {}
with open('.env') as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, _, v = line.partition('=')
            env[k.strip()] = v.strip()

missing, placeholder = [], []
for r in required:
    if r not in env or not env[r]:
        missing.append(r)
    elif 'CHANGE_ME' in env[r]:
        placeholder.append(r)

if missing:
    print(f'\033[0;31mMissing required env vars: {missing}\033[0m')
    sys.exit(1)
if placeholder:
    print(f'\033[0;33mWarning: These still have placeholder values: {placeholder}\033[0m')
    print(f'\033[0;33mPlease update them in .env before running in production.\033[0m')
else:
    print('\033[0;32m.env looks good.\033[0m')
"


# =============================================================================
# CLEANUP
# =============================================================================

clean:
	@echo "$(YELLOW)Removing stopped containers and dangling images...$(RESET)"
	$(COMPOSE) down --remove-orphans
	docker image prune -f
	@echo "$(GREEN)Clean complete.$(RESET)"

clean-all:
	@echo "$(RED)$(BOLD)WARNING: This will delete ALL containers, images, AND volumes (DATABASE WILL BE WIPED).$(RESET)"
	@read -p "Type 'DELETE' to confirm: " confirm && [ "$$confirm" = "DELETE" ] || exit 1
	$(COMPOSE_FULL) down -v --remove-orphans
	docker image prune -af
	@echo "$(GREEN)Full clean complete.$(RESET)"
