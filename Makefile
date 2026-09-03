.DEFAULT_GOAL := help

COMPOSE := $(shell docker compose version >/dev/null 2>&1 && echo "docker compose" || echo "docker-compose")
COMPOSE_DEV := $(COMPOSE) -f docker-compose.dev.yml
COMPOSE_PROD := $(COMPOSE) -f docker-compose.prod.yml
COMPOSE_TEST := $(COMPOSE) -f docker-compose.test.yml

.PHONY: help env up prod dev down logs logs-prod test lint seed migrate backup clean build

help:
	@echo "Available commands:"
	@echo "  make dev        Start development stack (hot-reload)"
	@echo "  make up         Start production compose (Traefik ingress; no published 80/443)"
	@echo "  make prod       Alias for make up"
	@echo "  make down       Stop all containers"
	@echo "  make logs       Follow development logs"
	@echo "  make logs-prod  Follow production logs"
	@echo "  make test       Run backend and frontend tests"
	@echo "  make lint       Run backend and frontend linters"
	@echo "  make migrate    Apply Alembic migrations (dev)"
	@echo "  make backup     Run a one-off PostgreSQL dump"
	@echo "  make seed       Seed users and objects"
	@echo "  make clean      Stop containers and remove volumes"
	@echo "  make build      Build production images"

env:
	@test -f .env || cp .env.example .env

up: env
	@docker network inspect $$(grep -E '^TRAEFIK_NETWORK=' .env 2>/dev/null | cut -d= -f2 | tr -d '"' | tr -d "'" || true) >/dev/null 2>&1 \
		|| docker network inspect traefik >/dev/null 2>&1 \
		|| docker network create traefik
	$(COMPOSE_PROD) up -d --build

prod: up

dev: env
	$(COMPOSE_DEV) up -d --build

down:
	-$(COMPOSE_DEV) down --remove-orphans
	-$(COMPOSE_PROD) down --remove-orphans
	-$(COMPOSE) down --remove-orphans

logs:
	$(COMPOSE_DEV) logs -f

logs-prod:
	$(COMPOSE_PROD) logs -f

test:
	$(COMPOSE_TEST) run --rm --build backend-test
	$(COMPOSE_DEV) run --rm frontend npm test

lint:
	$(COMPOSE_DEV) run --rm backend ruff check .
	$(COMPOSE_DEV) run --rm backend black --check .
	$(COMPOSE_DEV) run --rm frontend npm run lint

migrate:
	$(COMPOSE_DEV) run --rm backend alembic upgrade head

backup: env
	$(COMPOSE_PROD) exec backup /bin/sh /scripts/pg_backup.sh

seed:
	$(COMPOSE_DEV) run --rm backend python scripts/seed_data.py

clean:
	-$(COMPOSE_DEV) down -v --remove-orphans
	-$(COMPOSE_PROD) down -v --remove-orphans
	-$(COMPOSE_TEST) down -v --remove-orphans
	-$(COMPOSE) down -v --remove-orphans

build: env
	$(COMPOSE_PROD) build
