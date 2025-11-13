# tests/conftest.py
import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture(scope="session")
def client() -> TestClient:
    """
    Shared TestClient fixture for all tests.

    Uses the application factory so future configuration (DB, deps, etc.)
    remains test-friendly.
    """
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client