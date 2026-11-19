PYTHON  ?= python3
IMAGE   ?= ghcr.io/ste-haus/still-watching
VERSION := $(shell tr -d '[:space:]' < VERSION)

.PHONY: help install test docker-build docker-push publish clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) \
		| awk -F':.*## ' '{printf "  %-14s %s\n", $$1, $$2}'

install: ## Install runtime and test dependencies
	$(PYTHON) -m pip install -r requirements-dev.txt

test: ## Run the test suite
	$(PYTHON) -m pytest

docker-build: ## Build the container image, tagged with VERSION and latest
	docker build -t $(IMAGE):$(VERSION) -t $(IMAGE):latest .

docker-push: ## Push the VERSION and latest image tags (requires prior login)
	docker push $(IMAGE):$(VERSION)
	docker push $(IMAGE):latest

publish: docker-build docker-push ## Build and push the image

clean: ## Remove caches
	rm -rf .pytest_cache
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
