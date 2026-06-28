#!/bin/bash
set -e

echo "Installing dependencies..."
pip install -e ".[dev]"

echo "Setting up pre-commit..."
pre-commit install || true

echo "Waiting for PostgreSQL..."
until pg_isready -h "${DB_HOST:-localhost}" -p "${DB_PORT:-5432}" -U "${DB_USER:-postgres}" 2>/dev/null; do
  sleep 1
done

echo "Running migrations..."
alembic upgrade head

echo "Done!"
