.PHONY: help install dev up down test lint demo

help: ## Show this help
	@grep -E '^[a-z][a-z0-9_-]*:.*##' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*##"}{printf "  %-12s %s\n", $$1, $$2}'

install: ## Install Python deps (editable + dev)
	pip install -e ".[dev]"

dev: ## Run API locally with reload
	uvicorn api.main:app --reload --port 8000

up: ## Boot full stack (API + Redis + UI) via docker-compose
	docker-compose -f infra/docker-compose.yml up --build

down: ## Stop the stack
	docker-compose -f infra/docker-compose.yml down

test: ## Run core loop tests
	pytest tests/ -v

lint: ## Ruff lint
	ruff check agent api gbrain control_plane payments procurement tests

demo: ## Run the end-to-end demo dry-run on seed data
	python -m fixtures.demo_runner

reality: ## Print the live integration status matrix
	python3 verification/reality_report.py

tenant-list: ## List all configured tenants
	python3 -c "from agent.tenancy import list_tenants; slugs = list_tenants(); print('\n'.join(slugs) if slugs else '(no tenants found)')"

tenant-run: ## Load TENANT and print resolved config + routing decision (TENANT=<slug>)
	PYTHONPATH=. python3 scripts/tenant_run.py $(TENANT)

tenant-analyze: ## Run full analysis pipeline for TENANT (ingest → graph → P&L → findings → report)
	PYTHONPATH=. python3 scripts/tenant_analyze.py $(TENANT)

tenant-loop: ## Run ingestion+analysis cycle for TENANT and MODE (weekly|monthly)
	PYTHONPATH=. python3 scripts/tenant_loop.py $(TENANT) $(MODE)

tenant-dashboard: ## View tenant P&L dashboard locally
	@echo "1. Generate analysis:  make tenant-analyze TENANT=_sample_str"
	@echo "2. Start API:          make dev"
	@echo "3. Start UI:           cd ui && npm run dev"
	@echo "4. Open browser:       http://localhost:5173 → click 'Tenant P&L'"
	@echo "   To switch tenant:   VITE_TENANT=<slug> npm run dev (in ui/)"
