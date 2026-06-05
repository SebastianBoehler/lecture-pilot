.PHONY: test test-api test-web build dev-api dev-web

test: test-api test-web

test-api:
	pytest apps/api/tests

test-web:
	npm run test --workspace apps/web

build:
	npm run build --workspace apps/web

dev-api:
	uvicorn lecturepilot.app:app --app-dir apps/api/src --reload

dev-web:
	npm run dev --workspace apps/web

