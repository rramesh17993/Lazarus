.PHONY: help install dev test lint format clean build docker-build docker-push deploy

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install production dependencies
	poetry install --no-dev

dev: ## Install development dependencies
	poetry install
	poetry run pre-commit install

test: ## Run tests with coverage
	poetry run pytest -v --cov=src/lazarus_operator --cov-report=html --cov-report=term

test-fast: ## Run tests without coverage
	poetry run pytest -v -x

lint: ## Run linters
	poetry run ruff check src tests
	poetry run mypy src

format: ## Format code
	poetry run black src tests
	poetry run ruff check --fix src tests

clean: ## Clean build artifacts
	rm -rf dist/ build/ *.egg-info .pytest_cache .coverage htmlcov
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

build: clean ## Build Python package
	poetry build

docker-build: ## Build Docker image
	docker build -t lazarus-operator:latest .

docker-push: ## Push Docker image
	docker tag lazarus-operator:latest ghcr.io/yourusername/lazarus-operator:latest
	docker push ghcr.io/yourusername/lazarus-operator:latest

kind-setup: ## Setup Kind cluster for local testing
	kind create cluster --name lazarus-dev --config deploy/kind-config.yaml
	kubectl cluster-info --context kind-lazarus-dev

kind-teardown: ## Teardown Kind cluster
	kind delete cluster --name lazarus-dev

deploy-dev: ## Deploy to local Kind cluster
	kubectl apply -f deploy/namespace.yaml
	kubectl apply -f deploy/crd.yaml
	kubectl apply -f deploy/rbac.yaml
	kubectl apply -f deploy/configmap.yaml
	kubectl apply -f deploy/deployment.yaml

helm-lint: ## Lint Helm chart
	helm lint helm/lazarus

helm-template: ## Template Helm chart
	helm template lazarus helm/lazarus --debug

helm-install: ## Install with Helm
	helm upgrade --install lazarus helm/lazarus \
		--namespace lazarus-system \
		--create-namespace \
		--wait

helm-uninstall: ## Uninstall Helm chart
	helm uninstall lazarus --namespace lazarus-system

logs: ## Tail operator logs
	kubectl logs -n lazarus-system -l app.kubernetes.io/name=lazarus-operator -f

watch: ## Watch LaziusRestoreTest resources
	kubectl get lazarusrestoretests -A -w

describe: ## Describe all LaziusRestoreTest resources
	kubectl describe lazarusrestoretests -A

metrics: ## Port-forward to metrics endpoint
	kubectl port-forward -n lazarus-system svc/lazarus-operator-metrics 8080:8080
