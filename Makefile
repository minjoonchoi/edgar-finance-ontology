.PHONY: help setup select-tags create-instances yaml-to-ttl workflow clean

# Python interpreter
PYTHON := python3

# Scripts directory
SCRIPTS_DIR := scripts

# Default values
DEFAULT_OUTPUT_CSV := data/tags.csv
DEFAULT_OUTPUT_TTL := ontology/efin_instances.ttl
DEFAULT_SCHEMA_YAML := ontology/efin_schema.yaml
DEFAULT_SCHEMA_TTL := ontology/efin_schema.ttl
DEFAULT_FY := 2024
DEFAULT_FY_TOL_DAYS := 120
DEFAULT_PREFER_UNIT := USD
DEFAULT_BASE := https://w3id.org/edgar-fin/2024\#
DEFAULT_MIN_CONFIDENCE := 0.0
DEFAULT_CACHE_DIR := .cache/companyfacts
DEBUG_FILE := debug.log
DEBUG := 1

# Scope flags (Industry on, Sector off by default)
WITH_INDUSTRY_SCOPE ?= 1
WITH_SECTOR_SCOPE ?= 0

help: ## Show this help message
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

setup: ## Install Python dependencies
	@if command -v uv > /dev/null 2>&1; then \
		echo "Installing dependencies with uv..."; \
		uv sync; \
	elif command -v pip > /dev/null 2>&1; then \
		echo "Installing dependencies with pip..."; \
		pip install -r requirements.txt; \
	else \
		echo "Error: Neither uv nor pip found. Please install one of them."; \
		exit 1; \
	fi

# Optional arguments
ARGS_TICKERS := $(if $(TICKERS),--tickers $(TICKERS),)
ARGS_METRICS := $(if $(METRICS),--metrics $(METRICS),)
ARGS_CIKS := $(if $(CIKS),--ciks $(CIKS),)
ARGS_SUGGESTIONS := $(if $(SUGGESTIONS),--suggestions $(SUGGESTIONS),)
ARGS_DUMP_SUGGESTIONS := $(if $(DUMP_SUGGESTIONS),--dump-suggestions $(DUMP_SUGGESTIONS),)
ARGS_DUMP_SUGGESTIONS_APPEND := $(if $(filter 1,$(DUMP_SUGGESTIONS_APPEND)),--dump-suggestions-append,)
ARGS_DUMP_EXT_ONLY := $(if $(filter 1,$(DUMP_EXT_ONLY)),--dump-ext-only,)
ARGS_DEBUG := $(if $(filter-out 0,$(DEBUG)),--debug,)
ARGS_DEBUG_FILE := $(if $(DEBUG_FILE),--debug-file $(DEBUG_FILE),)
ARGS_FORCE := $(if $(filter 1,$(FORCE)),--force,)
ARGS_LIMIT := $(if $(LIMIT),--limit $(LIMIT),)
ARGS_FACTS := $(if $(FACTS),--facts $(FACTS),)
ARGS_FACTS_DIR := $(if $(FACTS_DIR),--facts-dir $(FACTS_DIR),)
ARGS_USER_AGENT := $(if $(USER_AGENT),--user-agent $(USER_AGENT),)
ARGS_INCLUDE_INDUSTRY_SCOPE := $(if $(filter 1,$(WITH_INDUSTRY_SCOPE)),--include-industry-scope,)
ARGS_INCLUDE_SECTOR_SCOPE := $(if $(filter 1,$(WITH_SECTOR_SCOPE)),--include-sector-scope,)

# Aggregate all optional arguments
CMD_ARGS := \
	$(ARGS_TICKERS) \
	$(ARGS_METRICS) \
	$(ARGS_CIKS) \
	$(ARGS_SUGGESTIONS) \
	$(ARGS_DUMP_SUGGESTIONS) \
	$(ARGS_DUMP_SUGGESTIONS_APPEND) \
	$(ARGS_DUMP_EXT_ONLY) \
	$(ARGS_DEBUG) \
	$(ARGS_DEBUG_FILE) \
	$(ARGS_FORCE) \
	$(ARGS_LIMIT) \
	$(ARGS_FACTS) \
	$(ARGS_FACTS_DIR) \
	$(ARGS_USER_AGENT) \
	$(ARGS_INCLUDE_INDUSTRY_SCOPE) \
	$(ARGS_INCLUDE_SECTOR_SCOPE)

select-tags: ## Run select_xbrl_tags.py (default: FY=2024, --use-api, --fy-tol-days=90, --debug enabled). Industry scope Benchmarks/TopRankings are included by default; set WITH_INDUSTRY_SCOPE=0 to disable, WITH_SECTOR_SCOPE=1 to enable sector scope.
	@mkdir -p $$(dirname $(DEFAULT_OUTPUT_CSV))
	@mkdir -p $$(dirname $(DEFAULT_OUTPUT_TTL))
	$(PYTHON) $(SCRIPTS_DIR)/select_xbrl_tags.py \
		--fy $(or $(FY),$(DEFAULT_FY)) \
		--use-api \
		--fy-tol-days $(or $(FY_TOL_DAYS),$(DEFAULT_FY_TOL_DAYS)) \
		--prefer-unit $(or $(PREFER_UNIT),$(DEFAULT_PREFER_UNIT)) \
		--cache-dir $(or $(CACHE_DIR),$(DEFAULT_CACHE_DIR)) \
		--out-tags $(or $(OUT),$(DEFAULT_OUTPUT_CSV)) \
		--emit-ttl $(or $(TTL),$(DEFAULT_OUTPUT_TTL)) \
		$(CMD_ARGS)

workflow: select-tags ## Run the complete workflow (data collection -> processing -> TTL generation)
	@echo "Workflow completed: tags selected and instances created"

clean: ## Clean cache and temporary files
	@echo "Cleaning cache and temporary files..."
	@rm -rf .cache
	@rm -f *.log
	@rm -f debug.log
	@echo "Clean completed"

