.PHONY: setup lint test test-db

setup:
	cd workers && uv sync
	cd web && npm ci

lint:
	cd workers && uv run ruff check . && uv run ruff format --check .
	cd web && npm run lint

test:
	cd workers && uv run pytest -q

test-db:
	supabase test db
