"""Pytest configuration: isolated temp database + deterministic settings.

IMPORTANT: environment variables are set BEFORE any app import, because
``app.config.settings`` and the SQLAlchemy engine are created at import
time. The app under test therefore always uses a throwaway database.
"""
import os
import tempfile
from pathlib import Path

_TMP_DIR = Path(tempfile.mkdtemp(prefix="autom8r-test-"))
os.environ["DATABASE_URL"] = f"sqlite:///{(_TMP_DIR / 'test.db').as_posix()}"
os.environ["ADMIN_TOKEN"] = "test-admin-token"
os.environ["WEBHOOK_SECRET"] = "test-webhook-secret"
os.environ["LLM_ENABLED"] = "false"

import pytest
from fastapi.testclient import TestClient

from app.db.database import Base, engine
from app.main import app

ADMIN_HEADERS = {"Authorization": "Bearer test-admin-token"}
WEBHOOK_HEADERS = {"X-Webhook-Secret": "test-webhook-secret"}


@pytest.fixture(autouse=True)
def _clean_database():
    """Give every test a fresh schema (drop + recreate all tables)."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture()
def client() -> TestClient:
    """A TestClient with the app lifespan (table creation) executed."""
    with TestClient(app) as test_client:
        yield test_client
