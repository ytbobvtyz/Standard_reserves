.DEFAULT_GOAL := help

COMPOSE := $(shell docker compose version >/dev/null 2>&1 && echo "docker compose" || echo "docker-compose")
COMPOSE_DEV := $(COMPOSE) -f docker-compose.dev.yml
COMPOSE_TEST := $(COMPOSE) -f docker-compose.test.yml

.PHONY: help env up dev down logs test lint seed migrate clean build

help:
	@echo "Available commands:"
	@echo "  make dev      Start development stack (hot-reload)"
	@echo "  make up       Start production stack"
	@echo "  make down     Stop all containers"
	@echo "  make logs     Follow development logs"
	@echo "  make test     Run backend and frontend tests"
	@echo "  make lint     Run backend and frontend linters"
	@echo "  make migrate  Apply Alembic migrations"
	@echo "  make seed     Seed users and objects"
	@echo "  make clean    Stop containers and remove volumes"
	@echo "  make build    Build production images"

env:
	@test -f .env || cp .env.example .env

up: env
	$(COMPOSE) up -d --build

dev: env
	$(COMPOSE_DEV) up -d --build

down:
	-$(COMPOSE_DEV) down --remove-orphans
	-$(COMPOSE) down --remove-orphans

logs:
	$(COMPOSE_DEV) logs -f

test:
	$(COMPOSE_TEST) run --rm --build backend-test
	$(COMPOSE_DEV) run --rm frontend npm test

lint:
	$(COMPOSE_DEV) run --rm backend ruff check .
	$(COMPOSE_DEV) run --rm backend black --check .
	$(COMPOSE_DEV) run --rm frontend npm run lint

migrate:
	$(COMPOSE_DEV) run --rm backend alembic upgrade head

seed:
	$(COMPOSE_DEV) run --rm backend python scripts/seed_data.py

clean:
	-$(COMPOSE_DEV) down -v --remove-orphans
	-$(COMPOSE) down -v --remove-orphans
	-$(COMPOSE_TEST) down -v --remove-orphans

build: env
	$(COMPOSE) build
