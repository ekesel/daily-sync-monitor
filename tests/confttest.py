# tests/conftest.py
import pytest
from fastapi.testclient import TestClient

from app.db.session import init_db
from app.main import create_app

DB_URL="postgresql+asyncpg://dailysync_test:pwd@db:5432/dailysync_test"

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

# @pytest.fixture(autouse=True, scope="function")
# async def _reset_db():
#     """
#     Automatically reset the DB before each test.

#     This means:
#     - you don't need to manually call `await init_db()` in tests
#     - every test gets a clean schema + empty tables
#     """
#     await init_db()