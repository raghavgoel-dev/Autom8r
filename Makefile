# Autom8r convenience commands.
# Windows note: make is OPTIONAL — README.md has the native PowerShell
# equivalents for every target.

.PHONY: install backend frontend mcp seed test

install:
	pip install -r backend/requirements.txt
	pip install -r mcp_server/requirements.txt
	cd frontend && npm install

backend:
	cd backend && uvicorn app.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

mcp:
	python -m mcp_server.server

seed:
	cd backend && python -m app.db.seed

test:
	cd backend && python -m pytest -q
	cd mcp_server && python -m pytest -q
