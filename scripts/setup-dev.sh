#!/bin/bash
set -e

# Development Environment Setup Script

echo "Lazarus Operator - Development Setup"
echo "========================================="
echo ""

# Check prerequisites
echo "Checking prerequisites..."

command -v python3 >/dev/null 2>&1 || { echo "ERROR: Python 3.11+ is required. Aborting." >&2; exit 1; }
command -v poetry >/dev/null 2>&1 || { echo "ERROR: Poetry is required. Install: curl -sSL https://install.python-poetry.org | python3 -" >&2; exit 1; }

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
if (( $(echo "$PYTHON_VERSION < 3.11" | bc -l) )); then
    echo "ERROR: Python 3.11+ required. Found: $PYTHON_VERSION"
    exit 1
fi

echo "Prerequisites satisfied"
echo ""

# Install dependencies
echo "Installing dependencies with Poetry..."
poetry install

# Install pre-commit hooks
echo "Setting up pre-commit hooks..."
poetry run pre-commit install

# Run tests
echo "Running tests..."
poetry run pytest -v

# Run linters
echo "Running linters..."
poetry run ruff check src tests || true
poetry run black --check src tests || true

echo ""
echo "Development environment ready!"
echo ""
echo "Available commands:"
echo "==================="
echo ""
echo "make dev          - Install dev dependencies"
echo "make test         - Run tests with coverage"
echo "make lint         - Run linters"
echo "make format       - Format code"
echo "make docker-build - Build Docker image"
echo "make kind-setup   - Setup local Kind cluster"
echo "make deploy-dev   - Deploy to local cluster"
echo "make logs         - View operator logs"
echo ""
echo "Happy coding!"
