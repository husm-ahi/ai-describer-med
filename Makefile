# AI Describer Medical - Development

.PHONY: help dev-up dev-down dev-logs dev-shell dev-migrate dev-test dev-clean

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# Development environment
dev-up: ## Start development environment
	docker compose -f docker-compose.dev.yml up -d

dev-down: ## Stop development environment
	docker compose -f docker-compose.dev.yml down

dev-logs: ## Show development logs
	docker compose -f docker-compose.dev.yml logs -f backend

dev-shell: ## Open shell in backend container
	docker compose -f docker-compose.dev.yml exec backend bash

dev-migrate: ## Run database migrations
	docker compose -f docker-compose.dev.yml exec backend python manage.py migrate

dev-makemigrations: ## Create new migrations
	docker compose -f docker-compose.dev.yml exec backend python manage.py makemigrations

dev-createsuperuser: ## Create superuser
	docker compose -f docker-compose.dev.yml exec backend python manage.py createsuperuser

dev-collectstatic: ## Collect static files
	docker compose -f docker-compose.dev.yml exec backend python manage.py collectstatic --noinput

dev-test: ## Run tests
	docker compose -f docker-compose.dev.yml exec backend python manage.py test

dev-check: ## Check Django configuration
	docker compose -f docker-compose.dev.yml exec backend python manage.py check

dev-clean: ## Clean development environment (including volumes)
	docker compose -f docker-compose.dev.yml down -v

dev-rebuild: ## Rebuild development containers
	docker compose -f docker-compose.dev.yml build --no-cache

# Database operations
db-shell: ## Open PostgreSQL shell
	docker compose -f docker-compose.dev.yml exec db psql -U aimedical -d aimedical_db

redis-cli: ## Open Redis CLI
	docker compose -f docker-compose.dev.yml exec redis redis-cli

# Production environment
prod-up: ## Start production environment
	docker compose up -d

prod-down: ## Stop production environment
	docker compose down

prod-logs: ## Show production logs
	docker compose logs -f

prod-clean: ## Clean production environment (including volumes)
	docker compose down -v
