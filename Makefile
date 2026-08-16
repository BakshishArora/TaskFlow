.PHONY: all install-uv install-deps run dev test lint lint-fix format format-check celery help

.DEFAULT_GOAL := help

UV := uv

all: install-deps test

install-uv:
	@command -v $(UV) >/dev/null 2>&1 || brew install $(UV)

install-deps:
	$(UV) sync

run:
	$(UV) run taskflow

dev:
	$(UV) run uvicorn taskflow.main:app --reload

test:
	$(UV) run pytest

lint:
	$(UV) run ruff check

lint-fix:
	$(UV) run ruff check --fix

format:
	$(UV) run ruff format

format-check:
	$(UV) run ruff format --check

celery:
	$(UV) run celery -A taskflow.celery_app worker --loglevel=info

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-10s\033[0m %s\n", $$1, $$2}'
