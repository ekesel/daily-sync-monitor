# tests/test_graph_client.py
import asyncio
from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from typing import Any, Dict, Optional

import pytest

from app.services.graph_client import GraphClient, GraphClientError


class _FakeResponse:
    def __init__(self, status_code: int, json_data: Dict[str, Any]):
        self.status_code = status_code
        self._json_data = json_data
        # For debugging / error messages
        self.text = str(json_data)

    def json(self) -> Dict[str, Any]:
        return self._json_data


class _FakeAsyncClient:
    """
    Minimal stand-in for httpx.AsyncClient used in tests.

    Allows us to:
    - Capture method/path/headers
    - Return predictable responses without real I/O
    """

    # class-level counters/last-call info to assert against in tests
    last_request: Dict[str, Any] = {}
    token_call_count: int = 0
    graph_call_count: int = 0

    def __init__(self, timeout: float | None = None):
        self._timeout = timeout

    async def __aenter__(self) -> "_FakeAsyncClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: D401
        # No cleanup required for the fake client.
        return None

    async def post(self, url: str, data: Optional[Dict[str, Any]] = None, **kwargs) -> _FakeResponse:
        """
        Fake token endpoint handler.
        """
        _FakeAsyncClient.last_request = {
            "method": "POST",
            "url": url,
            "data": data,
            "kwargs": kwargs,
        }
        _FakeAsyncClient.token_call_count += 1

        # Simulate a valid token response with 5 minutes expiry
        return _FakeResponse(
            status_code=HTTPStatus.OK,
            json_data={
                "access_token": "fake-token-123",
                "expires_in": 300,
                "token_type": "Bearer",
            },
        )

    async def request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        json: Any = None,
    ) -> _FakeResponse:
        """
        Fake generic request handler used for Graph API GET/POST.
        """
        _FakeAsyncClient.last_request = {
            "method": method,
            "url": url,
            "headers": headers,
            "params": params,
            "json": json,
        }
        _FakeAsyncClient.graph_call_count += 1

        # Simulate a successful Graph call echoing back key info
        return _FakeResponse(
            status_code=HTTPStatus.OK,
            json_data={
                "ok": True,
                "echo": {
                    "method": method,
                    "url": url,
                    "params": params,
                },
            },
        )


@pytest.mark.asyncio
async def test_graph_client_fetches_and_caches_token(monkeypatch):
    """
    First call to get_access_token() should hit the token endpoint.
    Subsequent calls within expiry window should reuse the cached token.
    """
    from app import services as _  # noqa: F401  # ensure package import works

    # Patch httpx.AsyncClient to our fake implementation
    import httpx

    monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)

    client = GraphClient(
        tenant_id="tenant-123",
        client_id="client-123",
        client_secret="secret-xyz",
    )

    _FakeAsyncClient.token_call_count = 0

    token1 = await client.get_access_token()
    token2 = await client.get_access_token()

    assert token1 == "fake-token-123"
    assert token2 == "fake-token-123"
    # Only one network call to token endpoint due to caching
    assert _FakeAsyncClient.token_call_count == 1


@pytest.mark.asyncio
async def test_graph_client_get_json_builds_correct_url_and_headers(monkeypatch):
    """
    Ensure that get_json() builds the expected URL and authorization header
    when called with a relative path.
    """
    import httpx

    monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)

    client = GraphClient(
        tenant_id="tenant-123",
        client_id="client-123",
        client_secret="secret-xyz",
        base_url="https://graph.microsoft.com/v1.0",
    )

    _FakeAsyncClient.graph_call_count = 0

    data = await client.get_json("/me/events", params={"top": 5})

    assert data["ok"] is True
    assert _FakeAsyncClient.graph_call_count == 1

    last = _FakeAsyncClient.last_request
    assert last["method"].upper() == "GET"
    # URL should be correctly joined
    assert last["url"] == "https://graph.microsoft.com/v1.0/me/events"
    # Authorization header should be present
    headers = last["headers"] or {}
    assert "Authorization" in headers
    assert headers["Authorization"].startswith("Bearer ")


@pytest.mark.asyncio
async def test_graph_client_raises_on_bad_token_response(monkeypatch):
    """
    If the token endpoint returns a non-200 status, GraphClientError should be raised.
    """
    import httpx

    class _BadTokenClient(_FakeAsyncClient):
        async def post(self, url: str, data=None, **kwargs) -> _FakeResponse:
            return _FakeResponse(
                status_code=HTTPStatus.BAD_REQUEST,
                json_data={"error": "invalid_client"},
            )

    monkeypatch.setattr(httpx, "AsyncClient", _BadTokenClient)

    client = GraphClient(
        tenant_id="tenant-123",
        client_id="client-123",
        client_secret="secret-xyz",
    )

    with pytest.raises(GraphClientError):
        await client.get_access_token()