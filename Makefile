PYTHON := .venv/bin/python
UV := $(if $(wildcard .cache/uv-bootstrap/bin/uv),.cache/uv-bootstrap/bin/uv,uv)

.PHONY: setup data check core-check contracts dev evaluate-live reproduce reproduce-pilot probe-setup probe-check probe-live probe-seeds probe-tool-playback probe-replay

setup: probe-setup
	npm --prefix frontend ci --ignore-scripts --no-fund

contracts:
	$(PYTHON) scripts/export_contracts.py
	cd frontend && node scripts/generate-contracts.mjs

check: core-check
	$(PYTHON) scripts/export_contracts.py --check
	cd frontend && node scripts/generate-contracts.mjs --check
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

data:
	$(PYTHON) -m housing.cli data

core-check:
	.venv/bin/ruff check src tests --exclude test_probe_guards.py
	.venv/bin/ruff format --check src tests --exclude test_probe_guards.py
	.venv/bin/mypy src/housing tests --exclude test_probe_guards.py
	$(PYTHON) -m pytest -q tests

probe-setup:
	UV_CACHE_DIR=.cache/uv UV_PYTHON_INSTALL_DIR=.python $(UV) sync --frozen

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
