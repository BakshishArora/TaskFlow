.PHONY: all install-uv install-deps run dev test help

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

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-10s\033[0m %s\n", $$1, $$2}'
