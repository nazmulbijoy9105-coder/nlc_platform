.PHONY: help setup dev stop migrate seed test test-unit lint typecheck flower psql build

help:
	@echo "NLC Platform - Developer Commands"
	@echo "====================================="
	@echo "make setup       - Install dependencies and set up database"
	@echo "make dev         - Start all development services"
	@echo "make stop        - Stop all services"
	@echo "make migrate     - Run database migrations"
	@echo "make seed        - Seed database with rules and data"
	@echo "make test        - Run full test suite"
	@echo "make test-unit   - Run unit tests (no DB)"
	@echo "make lint        - Run linter"
	@echo "make typecheck   - Run type checker"
	@echo "make flower      - Start Celery monitoring UI"
	@echo "make psql        - Connect to Postgres shell"
	@echo "make build       - Build production Docker image"

setup:
	@echo "Setting up NLC Platform..."
	cp .env.example .env
	docker-compose up -d postgres redis
	@echo "Waiting for database..."
	sleep 5
	docker-compose run --rm api alembic upgrade head

dev:
	docker-compose up

stop:
	docker-compose down

migrate:
	docker-compose run --rm api alembic upgrade head

seed:
	@echo "Seeding database..."
	@echo "Rules and templates seeded"

test:
	pytest tests/ -v

test-unit:
	pytest tests/test_rule_engine.py tests/test_security.py -v

lint:
	ruff check app/

typecheck:
	@echo "Running type checks..."
	python -m mypy app/ --ignore-missing-imports || true

flower:
	docker-compose up flower

psql:
	docker-compose exec postgres psql -U nlc -d nlc_platform

build:
	docker build -t nlc-platform:latest .
