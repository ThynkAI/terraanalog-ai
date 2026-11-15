.PHONY: setup dev fixtures validate test test-api test-web test-e2e build screenshots docker zip

setup:
	python3 -m venv .venv && .venv/bin/pip install -r backend/requirements-dev.txt
	cd web && npm ci && npx playwright install chromium

dev:
	./scripts/dev.sh

fixtures:
	.venv/bin/python scripts/build_fixtures.py

validate:
	.venv/bin/python scripts/validate_data.py $${DATA_DIR:-data/research}

test-api:
	cd backend && ../.venv/bin/python -m pytest -q

test-web:
	cd web && npx tsc --noEmit && npx vitest run

# Starts both servers automatically (ports 8000/3000) unless BASE_URL is set.
test-e2e:
	cd web && npx playwright test

test: test-api test-web test-e2e

build:
	cd web && npm run build

screenshots:
	cd web && BASE_URL=$${BASE_URL:-http://127.0.0.1:3000} node scripts/screenshots.mjs

docker:
	docker compose up --build

zip:
	git archive --format=zip -o ../terraanalog-ai.zip HEAD
