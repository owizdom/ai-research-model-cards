COMPOSE = docker compose -f infra/compose/docker-compose.yml
DEV     = $(COMPOSE) -f infra/compose/docker-compose.dev.yml

.PHONY: setup dev up down logs migrate seed build

setup:
	bash scripts/dev_setup.sh

dev:
	$(DEV) up --build

up:
	$(COMPOSE) up -d

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f

build:
	$(COMPOSE) build

migrate:
	bash scripts/migrate.sh

seed:
	python scripts/seed_db.py

collect:
	$(DEV) run --rm collector python -m src.scheduler.runner

LOCAL_DB = DATABASE_URL=postgresql+asyncpg://policy:policy@localhost:5433/policy_intel REDIS_URL=redis://localhost:6379

probe:
	@echo "Seeding new models into DB..."
	$(DEV) exec db psql -U policy -d policy_intel -c "DELETE FROM ai_models;" > /dev/null 2>&1 || true
	cd packages/db && $(LOCAL_DB) .venv/bin/python ../../scripts/seed_db.py
	@echo "Triggering probe run..."
	cd packages/db && $(LOCAL_DB) .venv/bin/python ../../scripts/trigger_probe.py

test-api:
	curl -s http://localhost:8000/api/v1/labs | python -m json.tool
