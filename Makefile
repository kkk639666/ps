.PHONY: install install-backend install-frontend dev dev-backend dev-frontend test clean

## Install all dependencies
install: install-backend install-frontend

install-backend:
	cd web/backend && pip install -r requirements.txt

install-frontend:
	cd web/frontend && npm install

## Start backend dev server (port 8000)
dev-backend:
	cd web/backend && cp -n .env.example .env || true && python main.py

## Start frontend dev server (port 5173)
dev-frontend:
	cd web/frontend && npm run dev

## Run backend tests
test:
	cd web/backend && pip install pytest httpx Pillow -q && pytest tests/test_api.py -v

## Build frontend for production
build-frontend:
	cd web/frontend && npm run build

## Clean generated files
clean:
	find web/backend -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	rm -f web/backend/history.db web/backend/test_history.db
	rm -rf web/backend/storage
	rm -rf web/frontend/dist
