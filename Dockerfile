# Autom8r — all-in-one image (backend by default, MCP via command override).
#
# Build:  docker build -t autom8r .
# Run backend:  docker run -p 8000:8000 autom8r
# Run MCP:      docker run -p 8001:8001 -e MCP_HOST=0.0.0.0 autom8r python -m mcp_server.server
#
# Cloud Run note: one process per container. Deploy this image twice —
# once with the default CMD (backend), once with the MCP command — and set
# MCP_SERVER_URL on the backend service to the MCP service URL. Secrets go
# to the platform's secret manager, never into the image.
FROM python:3.12-slim

WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
COPY mcp_server/requirements.txt mcp_server/requirements.txt
RUN pip install --no-cache-dir \
    -r backend/requirements.txt \
    -r mcp_server/requirements.txt

COPY backend ./backend
COPY mcp_server ./mcp_server
COPY data ./data

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "backend"]
