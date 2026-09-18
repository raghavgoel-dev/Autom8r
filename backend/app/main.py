"""Autom8r FastAPI application entrypoint.

Run from the backend directory:
    uvicorn app.main:app --reload --port 8000

Responsibilities of this file (and only these):
  * build the app and wire shared services onto app.state
  * CORS + request logging
  * global exception handlers -> the one predictable error envelope
  * mount routers
"""
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

from app.api.routes import admin, chat, health, leads, webhooks
from app.config import settings
from app.db.database import create_all_tables
from app.logging_config import get_logger
from app.schemas.common import ErrorBody, ErrorResponse
from app.services.agent_service import AgentService
from app.services.llm_service import build_llm_service
from app.services.mcp_client_service import MCPClientService
from app.services.retrieval_service import RetrievalService
from app.utils.errors import AppError

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup: create tables and build services. Shutdown: nothing to close."""
    create_all_tables()
    mcp = MCPClientService(settings.mcp_server_url)
    app.state.mcp = mcp
    app.state.agent = AgentService(
        settings=settings,
        llm=build_llm_service(settings),
        mcp=mcp,
        retrieval=RetrievalService(),
    )
    logger.info(
        "autom8r backend up: env=%s llm_mode=%s mcp=%s",
        settings.app_env, settings.llm_mode, settings.mcp_server_url,
    )
    yield


app = FastAPI(
    title="Autom8r",
    description="AI-powered lead qualification & customer support automation (demo).",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS: the Vite dev server runs on another origin, so the browser blocks
# calls unless we explicitly allow it. Origins come from env — never "*"
# with credentials in a real deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next: RequestResponseEndpoint) -> Response:
    """One line per request: method, path, status, duration."""
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "%s %s -> %s (%.1fms)",
        request.method, request.url.path, response.status_code, duration_ms,
    )
    return response


def _envelope(status_code: int, code: str, message: str) -> JSONResponse:
    """Build the standard error envelope for any failure."""
    body = ErrorResponse(error=ErrorBody(code=code, message=message))
    return JSONResponse(status_code=status_code, content=body.model_dump())


@app.exception_handler(AppError)
def handle_app_error(_request: Request, exc: AppError) -> JSONResponse:
    """Our own typed errors already know their status + code."""
    return _envelope(exc.status_code, exc.code, exc.message)


@app.exception_handler(RequestValidationError)
def handle_validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
    """Pydantic rejected the payload -> 422 with a safe, generic message.

    The field-level detail stays in the logs; clients get a clean envelope
    (no internal paths or schema internals leak out).
    """
    logger.info("validation error: %s", exc.errors()[0] if exc.errors() else "unknown")
    return _envelope(422, "VALIDATION_ERROR", "Request payload failed validation")


@app.exception_handler(Exception)
def handle_unexpected_error(_request: Request, exc: Exception) -> JSONResponse:
    """Last-resort handler: full traceback to logs, generic 500 to client."""
    logger.exception("unhandled error: %r", exc)
    return _envelope(500, "INTERNAL_ERROR", "Something went wrong on our side")


app.include_router(health.router)
app.include_router(leads.router)
app.include_router(chat.router)
app.include_router(webhooks.router)
app.include_router(admin.router)
