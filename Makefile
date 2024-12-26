SHELL=/bin/bash

.DEFAULT_GOAL := help

.PHONY: help
help: ## Shows this help text
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

.PHONY: init
init: clean install checkov test ## Clean the environment and install all project dependencies

.PHONY: clean
clean: ## Removes project virtual env and untracked files
	rm -rf .venv **/.venv **/.venv.docker cdk.out build dist **/*.egg-info .pytest_cache node_modules .coverage **/__pycache__ **/*.pyc
	@find functions -maxdepth 1 -mindepth 1 -type d ! -name "__pycache__" | while read dir; do \
		echo "Removing $$dir venvs"; \
		(cd "$$dir" && poetry env remove --all); \
	done
	poetry env remove --all

.PHONY: install
install: ## Install the project dependencies using Poetry.
	@find functions -maxdepth 1 -mindepth 1 -type d ! -name "__pycache__" | while read dir; do \
		echo "Installing $$dir"; \
		(cd "$$dir" && poetry install --with test); \
	done;
	poetry install --with lint,test,checkov
	poetry run pre-commit install --hook-type pre-commit --hook-type commit-msg --hook-type pre-push

.PHONY: update
update: ## Update the project dependencies using Poetry.
	@find functions -maxdepth 1 -mindepth 1 -type d ! -name "__pycache__" | while read dir; do \
		echo "Updating $$dir"; \
		(cd "$$dir" && poetry update --with test); \
	done;
	poetry update --with lint,test,checkov

.PHONY: test
test: ## Run tests
	@find functions -maxdepth 1 -mindepth 1 -type d ! -name "__pycache__" | while read dir; do \
		echo "Running $$dir tests"; \
		(cd "$$dir" && poetry run python -m pytest); \
	done
	poetry run python -m pytest

.PHONY: lint
lint: ## Apply linters to all files
	poetry run pre-commit run --all-files

.PHONY: synth
synth: ## Synthetize all Cdk stacks
	poetry run cdk synth

.PHONY: checkov
checkov: synth ## Run Checkov against IAC code
	poetry run checkov --config-file .checkov --baseline .checkov.baseline

.PHONY: checkov-baseline
checkov-baseline: synth ## Run checkov and create a new baseline for future checks
	poetry run checkov --config-file .checkov --create-baseline --soft-fail
	mv cdk.out/.checkov.baseline .checkov.baseline

.PHONY: snapshot-update
snapshot-update: ## Run tests and update the snapshots baseline
	poetry run python -m pytest --snapshot-update


.PHONY: up
up: ## Run the live API server locally
	docker compose --file docker-compose.yaml up --no-deps --build --force-recreate

.PHONY: down
down:  ## Kill the local app with Docker Compose
	docker compose --file docker-compose.yaml down --volumes
