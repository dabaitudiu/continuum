.PHONY: setup test test-e2e dev

setup:
	uv sync --project backend --group dev
	npm --prefix frontend ci

test:
	uv run --project backend pytest backend/tests --cov=app --cov-branch --cov-report=term-missing
	npm --prefix frontend run test:run
	npm --prefix frontend run build

test-e2e:
	cd frontend && env -u NO_COLOR npx playwright test

dev:
	./scripts/dev.sh
