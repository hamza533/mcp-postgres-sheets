# Standard commands for humans and every AI tool. See AGENTS.md.
#
# Needs `uv` and Docker. No uv on your machine? Run any target with DOCKER=1
# (e.g. `make check DOCKER=1`): uv then runs inside a container on the compose network.

COMPOSE ?= docker compose

ifeq ($(DOCKER),1)
UV := scripts/uvd.sh
DB_HOST := db:5432
else
UV ?= uv
DB_HOST := localhost:$(or $(DB_PORT),5544)
endif

TEST_DATABASE_URL ?= postgresql://mcp_readonly:mcp_readonly@$(DB_HOST)/shop
export TEST_DATABASE_URL

.PHONY: help setup dev down db seed test test-unit lint format typecheck check eval eval-safety \
        eval-latency inspector tools-json build remote-smoke site-setup site-build site-test bicep

help:             ## list targets
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | sed 's/:.*##/\t/'

setup:            ## install Python dependencies (frozen lockfile)
	$(UV) sync --frozen

dev:              ## start Postgres + the remote-mode stack (MCP server over HTTP + Keycloak)
	$(COMPOSE) --profile remote up --build

down:             ## stop everything
	$(COMPOSE) --profile remote down

db:               ## start only the sample Postgres (waits until seeded)
	$(COMPOSE) up -d db --wait

seed:             ## rebuild the sample database from scratch (drops the volume)
	$(COMPOSE) rm -sfv db
	-docker volume rm mcp-postgres-sheets_db-data
	$(COMPOSE) up -d db --wait

test: db          ## unit + integration + safety + MCP protocol tests against real Postgres
	REQUIRE_INTEGRATION=1 $(UV) run pytest -q

test-unit:        ## tests that need no database
	$(UV) run pytest -q -m "not integration"

lint:             ## ruff (lint + format check) and mypy
	$(UV) run ruff check .
	$(UV) run ruff format --check .
	$(UV) run mypy

typecheck:
	$(UV) run mypy

format:
	$(UV) run ruff format .
	$(UV) run ruff check --fix .

check: lint test  ## must pass before every commit

eval: db          ## safety suite + 20 NL tasks (Gemini, needs GEMINI_API_KEY) + latency → eval/results.{md,json}
	$(UV) run python -m eval.run

eval-safety: db   ## safety suite only (no API key needed)
	$(UV) run python -m eval.run --only safety

eval-latency: db  ## latency benchmark only
	$(UV) run python -m eval.run --only latency

inspector:        ## open the MCP Inspector against the local stdio server (needs Node)
	npx -y @modelcontextprotocol/inspector@0.17.2 uv run mcp-postgres-sheets

tools-json:       ## regenerate site/src/data/tools.json from tools/list
	$(UV) run python -m scripts.export_tools site/src/data/tools.json

build:            ## build the wheel + sdist into dist/
	$(UV) build

remote-smoke:     ## end-to-end OAuth checks against `docker compose --profile remote up`
	$(UV) run python -m scripts.remote_smoke

site-setup:       ## install website dependencies
	cd site && npm ci

site-build:       ## static export of the website into site/out
	cd site && npm run build

site-test:        ## Playwright smoke test of the website
	cd site && npm run test:e2e

bicep:            ## validate the Azure production profile
	az bicep build --file deploy/azure/main.bicep --stdout > /dev/null
	az bicep lint --file deploy/azure/main.bicep
