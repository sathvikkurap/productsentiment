# Product Sentiment Crawler — common commands
.PHONY: help setup check test run run-example install lint docker-build docker-run

# Default: show help
help:
	@echo "Product Sentiment Crawler — make targets:"
	@echo "  make setup        - Create .venv, install deps, copy .env.example → .env if missing"
	@echo "  make check        - Show which sources are available (run.py --check)"
	@echo "  make test         - Run unit tests"
	@echo "  make lint         - Run ruff check and format check"
	@echo "  make run-example  - Quick run (Notion, free sources only)"
	@echo "  make run PRODUCT='X' - Run crawler for product X"
	@echo "  make install      - pip install -r requirements.txt"
	@echo "  make docker-build - Build Docker image"
	@echo "  make docker-run PRODUCT=X - Run in Docker"

# First-time setup: venv + deps + .env (idempotent)
setup:
	@if [ ! -d .venv ]; then python3 -m venv .venv; echo "Created .venv"; fi
	@.venv/bin/pip install -q -r requirements.txt
	@if [ ! -f .env ]; then cp .env.example .env; echo "Created .env from .env.example"; fi
	@echo "Setup done. Activate with: source .venv/bin/activate"

# Show which sources are available (no fetch)
check:
	.venv/bin/python run.py --check

test:
	python -m unittest tests.test_smoke -v

# Lint (ruff); install dev deps first: pip install -e ".[dev]"
lint:
	python -m ruff check . && python -m ruff format --check .

# Quick run with free sources only (no .env needed)
run-example:
	python run.py "Notion" --sources hackernews,duckduckgo --limit 20

# Run with all configured sources
run:
	@echo "Usage: make run PRODUCT='Your Product'"
	@echo "Or: python run.py \"Your Product\""
	@if [ -n "$(PRODUCT)" ]; then python run.py "$(PRODUCT)"; fi

# Install deps (activate venv first: source .venv/bin/activate)
install:
	pip install -r requirements.txt

# Docker: build image
docker-build:
	docker build -t productreviews .

# Docker: run (e.g. make docker-run PRODUCT=Notion)
docker-run:
	@if [ -z "$(PRODUCT)" ]; then docker run --rm productreviews --help; else docker run --rm productreviews "$(PRODUCT)" --sources hackernews,duckduckgo --limit 20; fi
