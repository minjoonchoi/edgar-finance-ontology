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

select-tags: ## Run select_xbrl_tags.py (default: FY=2024, --use-api, --fy-tol-days=90, --debug enabled)
	@mkdir -p $$(dirname $(DEFAULT_OUTPUT_CSV))
	$(PYTHON) $(SCRIPTS_DIR)/select_xbrl_tags.py \
		--fy $(or $(FY),$(DEFAULT_FY)) \
		--use-api \
		--fy-tol-days $(or $(FY_TOL_DAYS),$(DEFAULT_FY_TOL_DAYS)) \
		$$(if [ -n "$(TICKERS)" ]; then echo --tickers $(TICKERS); fi) \
		$$(if [ -n "$(METRICS)" ]; then echo --metrics $(METRICS); fi) \
		$$(if [ -n "$(CIKS)" ]; then echo --ciks $(CIKS); fi) \
		$$(if [ -n "$(SUGGESTIONS)" ]; then echo --suggestions $(SUGGESTIONS); fi) \
		$$(if [ -n "$(DUMP_SUGGESTIONS)" ]; then echo --dump-suggestions $(DUMP_SUGGESTIONS); fi) \
		$$(if [ "$(DUMP_SUGGESTIONS_APPEND)" = "1" ]; then echo --dump-suggestions-append; fi) \
		$$(if [ "$(DUMP_EXT_ONLY)" = "1" ]; then echo --dump-ext-only; fi) \
		$$(if [ "$(DEBUG)" != "0" ]; then echo --debug; fi) \
		$$(if [ -n "$(DEBUG_FILE)" ]; then echo --debug-file $(DEBUG_FILE); fi) \
		$$(if [ "$(FORCE)" = "1" ]; then echo --force; fi) \
		$$(if [ -n "$(LIMIT)" ]; then echo --limit $(LIMIT); fi) \
		--prefer-unit $(or $(PREFER_UNIT),$(DEFAULT_PREFER_UNIT)) \
		--cache-dir $(or $(CACHE_DIR),$(DEFAULT_CACHE_DIR)) \
		$$(if [ -n "$(FACTS)" ]; then echo --facts $(FACTS); fi) \
		$$(if [ -n "$(FACTS_DIR)" ]; then echo --facts-dir $(FACTS_DIR); fi) \
		$$(if [ -n "$(USER_AGENT)" ]; then echo --user-agent $(USER_AGENT); fi) \
		--out $(or $(OUT),$(DEFAULT_OUTPUT_CSV))

create-instances: ## Run create_instance_ttl.py
	@mkdir -p $$(dirname $(DEFAULT_OUTPUT_TTL))
	$(PYTHON) $(SCRIPTS_DIR)/create_instance_ttl.py \
		--csv $(or $(CSV),$(DEFAULT_OUTPUT_CSV)) \
		--out $(or $(OUT),$(DEFAULT_OUTPUT_TTL)) \
		--base $(or $(BASE),$(DEFAULT_BASE)) \
		--min-confidence $(or $(MIN_CONFIDENCE),$(DEFAULT_MIN_CONFIDENCE)) \
		$$(if [ -n "$(IMPORT_SCHEMA)" ]; then echo --import-schema $(IMPORT_SCHEMA); fi) \
		$$(if [ "$(MATERIALIZE_COMPONENTS)" = "1" ]; then echo --materialize-components; fi) \
		$$(if [ "$(DEBUG)" = "1" ]; then echo --debug; fi)

yaml-to-ttl: ## Convert YAML schema to TTL format
	@mkdir -p $$(dirname $(or $(OUT),$(DEFAULT_SCHEMA_TTL)))
	$(PYTHON) $(SCRIPTS_DIR)/yaml_to_ttl.py \
		--yaml $(or $(YAML),$(DEFAULT_SCHEMA_YAML)) \
		--out $(or $(OUT),$(DEFAULT_SCHEMA_TTL)) \
		$$(if [ "$(DEBUG)" = "1" ]; then echo --debug; fi)

workflow: select-tags create-instances ## Run select-tags then create-instances in sequence
	@echo "Workflow completed: tags selected and instances created"

clean: ## Clean cache and temporary files
	@echo "Cleaning cache and temporary files..."
	@rm -rf .cache
	@rm -f *.log
	@rm -f debug.log
	@echo "Clean completed"

