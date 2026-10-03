PYTHON := .venv/bin/python
UV := $(if $(wildcard .cache/uv-bootstrap/bin/uv),.cache/uv-bootstrap/bin/uv,uv)
UV_CACHE_DIR ?= .cache/uv
UV_PYTHON_INSTALL_DIR ?= .python
DELIVERY_SCRIPTS := scripts/build_report.py scripts/audit_provider_usage.py scripts/replay_case_leg.py scripts/clean_checkout.py scripts/submission_check.py scripts/prepare_diagnosis.py scripts/init_langfuse.py scripts/export_langfuse.py

.PHONY: setup data check core-check contracts dev evaluate-live reproduce reproduce-pilot report report-draft clean-checkout submission-check probe-setup probe-check probe-live probe-seeds probe-tool-playback probe-replay

setup: probe-setup
	npm --prefix frontend ci --ignore-scripts --no-fund

contracts:
	$(PYTHON) scripts/export_contracts.py
	cd frontend && node scripts/generate-contracts.mjs

check: core-check
	.venv/bin/ruff check $(DELIVERY_SCRIPTS)
	.venv/bin/ruff format --check $(DELIVERY_SCRIPTS)
	.venv/bin/mypy $(DELIVERY_SCRIPTS)
	$(PYTHON) scripts/export_contracts.py --check
	cd frontend && node scripts/generate-contracts.mjs --check
	npm --prefix frontend test
	npm --prefix frontend run build
	npm --prefix frontend run lint

dev:
	$(PYTHON) scripts/dev.py

evaluate-live:
	PYTHONHASHSEED=0 $(PYTHON) -u -m housing.evaluation run --cohort configs/headline-cohort-v1.json --directory artifacts/campaigns/headline-live-v1

reproduce:
	PYTHONHASHSEED=0 $(PYTHON) scripts/reproduce_campaign.py

reproduce-pilot:
	PYTHONHASHSEED=0 $(PYTHON) scripts/reproduce_campaign.py --pilot --reference artifacts/campaigns/pilot-live-v1

report:
	$(PYTHON) scripts/build_report.py

report-draft:
	$(PYTHON) scripts/build_report.py --draft

clean-checkout:
	$(PYTHON) scripts/clean_checkout.py

submission-check: check
	$(PYTHON) scripts/submission_check.py

data:
	$(PYTHON) -m housing.cli data

core-check:
	.venv/bin/ruff check src tests --exclude test_probe_guards.py
	.venv/bin/ruff format --check src tests --exclude test_probe_guards.py
	.venv/bin/mypy src/housing tests --exclude test_probe_guards.py
	$(PYTHON) -m pytest -q tests

probe-setup:
	UV_CACHE_DIR="$(UV_CACHE_DIR)" UV_PYTHON_INSTALL_DIR="$(UV_PYTHON_INSTALL_DIR)" $(UV) sync --frozen

probe-check:
	.venv/bin/ruff check --select E4,E7,E9,F scripts tests/unit/test_probe_guards.py
	.venv/bin/mypy --follow-imports=skip scripts/probe_fast_agent.py scripts/probe_tools.py scripts/probe_support.py scripts/probe_tool_playback.py scripts/replay_environment.py
	$(PYTHON) -m pytest -q tests/unit/test_probe_guards.py

probe-live:
	$(PYTHON) -u scripts/probe_fast_agent.py --stage agents-tools

probe-seeds:
	$(PYTHON) -u scripts/probe_fast_agent.py --stage decision

probe-tool-playback:
	$(PYTHON) -u scripts/probe_tool_playback.py

probe-replay:
	$(PYTHON) scripts/replay_environment.py

LANGFUSE_COMPOSE := docker compose -f observability/langfuse/compose.yaml --env-file observability/langfuse/.env

.PHONY: langfuse-init langfuse-up langfuse-down langfuse-export langfuse-watch
langfuse-init:
	$(PYTHON) scripts/init_langfuse.py

langfuse-up: langfuse-init
	$(LANGFUSE_COMPOSE) up -d

langfuse-down:
	$(LANGFUSE_COMPOSE) stop

langfuse-export:
	$(PYTHON) scripts/export_langfuse.py --campaign headline-live-v1 --verify

langfuse-watch:
	$(PYTHON) -u scripts/export_langfuse.py --campaign headline-live-v1 --include-web --watch --verify
