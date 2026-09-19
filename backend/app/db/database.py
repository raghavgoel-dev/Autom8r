"""Database engine and declarative base.

WHY SQLite + WAL?
  WHAT: a single-file relational database opened in Write-Ahead Logging mode.
  WHY: zero-install local demo, and WAL lets the FastAPI process and the MCP
       server process share one file without 'database is locked' errors.
  TRADEOFF: fine for a demo; a multi-instance production deployment would use
       a managed client/server database (PostgreSQL) instead — see README.
"""
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    """Declarative base every ORM model inherits from."""


def _make_engine(database_url: str) -> Engine:
    """Create the SQLAlchemy engine for a SQLite URL."""
    return create_engine(
        database_url,
        # SQLite connections are thread-bound by default; FastAPI handles
        # requests on a thread pool, so allow cross-thread use. Sessions are
        # still short-lived per request.
        connect_args={"check_same_thread": False, "timeout": 15},
    )


engine = _make_engine(settings.database_url)


@event.listens_for(engine, "connect")
def _set_sqlite_pragmas(dbapi_connection: object, _connection_record: object) -> None:
    """Enable WAL + a busy timeout on every new SQLite connection.

    WAL is the key setting that lets two processes (backend + MCP server)
    read/write the same file concurrently.
    """
    cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=15000")
    cursor.close()


def create_all_tables() -> None:
    """Create tables for every registered model (idempotent)."""
    # Import models so they register on Base.metadata before create_all.
    from app.models import lead, webhook_event  # noqa: F401

    Base.metadata.create_all(bind=engine)
