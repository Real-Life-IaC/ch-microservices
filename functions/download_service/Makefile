SHELL=/bin/bash

AWS_PROFILE ?= $(error AWS_PROFILE is not set. Please provide an AWS_PROFILE. Example usage: make alembic-upgrade AWS_PROFILE=your-aws-profile)
MESSAGE ?= $(error MESSAGE is not set. Please provide a message for the Alembic revision. Example usage: make alembic-revision MESSAGE="Your message")
DB_SECRET_NAME=/microservices/aurora-db/storage/cluster/credentials

.PHONY: alembic-revision
alembic-revision: ## Create a new Alembic revision
	poetry run alembic revision --autogenerate -m "$(MESSAGE)"
	@echo "Please review the new Alembic revision and when satisfied run 'make alembic-upgrade' to apply it"


.PHONY: alembic-upgrade
alembic-upgrade: ## Upgrade the database with Alembic using a specific AWS_PROFILE
	@echo "Running Alembic upgrade for $(AWS_PROFILE)"
	DB_SECRET_NAME=$(DB_SECRET_NAME) \
	AWS_PROFILE=$(AWS_PROFILE) \
	poetry run alembic upgrade head


.PHONY: alembic-downgrade
alembic-downgrade: ## Downgrade the database with Alembic using a specific AWS_PROFILE
	@echo "Running Alembic downgrade for $(AWS_PROFILE)"
	DB_SECRET_NAME=$(DB_SECRET_NAME) \
	AWS_PROFILE=$(AWS_PROFILE) \
	poetry run alembic downgrade -1
