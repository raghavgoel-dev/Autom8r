"""Per-request database session (FastAPI dependency injection).

``get_db`` is a generator dependency: FastAPI calls it before the route,
hands the route the session, and guarantees the ``finally`` runs after the
response — so connections never leak, even on exceptions.
"""
from collections.abc import Generator

from sqlalchemy.orm import Session, sessionmaker

from app.db.database import engine

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    """Yield one short-lived session per HTTP request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
