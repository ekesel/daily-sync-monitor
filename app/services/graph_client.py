# app/services/graph_client.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import httpx

from app.core.config import get_settings


class GraphClientError(RuntimeError):
    """
    Raised when the GraphClient cannot obtain an access token or when a
    Graph API call fails in a non-recoverable way.
    """


@dataclass
class _TokenState:
    access_token: str
    expires_at: datetime


class GraphClient:
    """
    Minimal Microsoft Graph API client using client-credentials flow.

    Responsibilities
    ----------------
    - Fetch and cache an access token using the OAuth2 client-credentials flow.
    - Provide thin convenience methods for GET/POST requests to Graph.
    - Avoid leaking HTTP client details into the rest of the codebase.

    Notes
    -----
    - Token caching is in-memory for this process only.
    - A small safety margin is applied when calculating token expiry to avoid
      edge cases near expiration.
    """

    def __init__(
        self,
        tenant_id: str,
        client_id: str,
        client_secret: str,
        base_url: str = "https://graph.microsoft.com",
        scope: str = "https://graph.microsoft.com/.default",
        timeout_seconds: float = 10.0,
    ) -> None:
        if not tenant_id or not client_id or not client_secret:
            raise ValueError("tenant_id, client_id and client_secret are required")

        self._tenant_id = tenant_id
        self._client_id = client_id
        self._client_secret = client_secret
        self._base_url = base_url.rstrip("/")
        self._scope = scope
        self._timeout_seconds = timeout_seconds

        self._token_state: Optional[_TokenState] = None

    @property
    def token_url(self) -> str:
        """
        Returns the OAuth2 token endpoint for the configured tenant.
        """
        return f"https://login.microsoftonline.com/{self._tenant_id}/oauth2/v2.0/token"

    async def _fetch_token(self) -> _TokenState:
        """
        Fetch a fresh access token from Azure AD using client credentials.

        Returns
        -------
        _TokenState
            Newly obtained token and its expiry.
        """
        data = {
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "grant_type": "client_credentials",
            "scope": self._scope,
        }

        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            resp = await client.post(self.token_url, data=data)

        if resp.status_code != 200:
            raise GraphClientError(
                f"Failed to obtain Graph token (status={resp.status_code}): {resp.text}"
            )

        payload = resp.json()
        access_token = payload.get("access_token")
        expires_in = payload.get("expires_in")

        if not access_token or not isinstance(expires_in, (int, float)):
            raise GraphClientError(
                "Invalid token response from Azure AD (missing access_token/expires_in)"
            )

        # Apply a small safety margin so we refresh slightly before real expiry.
        now = datetime.now(tz=timezone.utc)
        safety_margin = 60  # seconds
        expires_at = now + timedelta(seconds=float(expires_in) - safety_margin)

        return _TokenState(access_token=access_token, expires_at=expires_at)

    async def get_access_token(self) -> str:
        """
        Return a valid access token, using a cached value if still valid.

        A new token is fetched when:
        - No token is cached yet
        - The cached token is expired or about to expire
        """
        now = datetime.now(tz=timezone.utc)
        if self._token_state and self._token_state.expires_at > now:
            return self._token_state.access_token

        self._token_state = await self._fetch_token()
        return self._token_state.access_token

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json: Any = None,
    ) -> httpx.Response:
        """
        Low-level helper for issuing an authenticated HTTP request to Graph.

        Parameters
        ----------
        method:
            HTTP method (GET, POST, etc.).
        path:
            Either an absolute URL or a path relative to the configured base_url.
        params:
            Optional query string parameters.
        json:
            Optional JSON body.

        Returns
        -------
        httpx.Response
            The raw HTTP response object.
        """
        token = await self.get_access_token()

        # If path is not an absolute URL, treat it as relative to base_url.
        if path.startswith("http://") or path.startswith("https://"):
            url = path
        else:
            url = f"{self._base_url.rstrip('/')}/{path.lstrip('/')}"

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }

        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            resp = await client.request(
                method=method.upper(),
                url=url,
                headers=headers,
                params=params,
                json=json,
            )

        # Do not raise here automatically – callers may want to inspect JSON
        # error payloads. Instead, expose a cleaner error in helper methods.
        return resp

    async def get_json(
        self,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Issue a GET request to a Graph endpoint and return the JSON payload.

        Raises GraphClientError on non-2xx responses.
        """
        resp = await self._request("GET", path, params=params)
        if resp.status_code // 100 != 2:
            raise GraphClientError(
                f"Graph GET failed (status={resp.status_code}): {resp.text}"
            )
        return resp.json()

    async def post_json(
        self,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json: Any = None,
    ) -> Dict[str, Any]:
        """
        Issue a POST request to a Graph endpoint and return the JSON payload.

        Raises GraphClientError on non-2xx responses.
        """
        resp = await self._request("POST", path, params=params, json=json)
        if resp.status_code // 100 != 2:
            raise GraphClientError(
                f"Graph POST failed (status={resp.status_code}): {resp.text}"
            )
        return resp.json()


# Simple singleton-style accessor wired to app settings
_graph_client_instance: Optional[GraphClient] = None


def get_graph_client() -> GraphClient:
    """
    Lazily construct a GraphClient instance using application settings.

    This is intended for use in background services or dependency injection
    when integrating with the DailySync evaluation logic.
    """
    global _graph_client_instance
    if _graph_client_instance is None:
        settings = get_settings()
        if not settings.GRAPH_TENANT_ID or not settings.GRAPH_CLIENT_ID or not settings.GRAPH_CLIENT_SECRET:
            raise GraphClientError(
                "GRAPH_TENANT_ID, GRAPH_CLIENT_ID and GRAPH_CLIENT_SECRET must be "
                "configured in settings to use the shared Graph client."
            )
        _graph_client_instance = GraphClient(
            tenant_id=settings.GRAPH_TENANT_ID,
            client_id=settings.GRAPH_CLIENT_ID,
            client_secret=settings.GRAPH_CLIENT_SECRET,
            base_url=str(settings.GRAPH_BASE_URL or "https://graph.microsoft.com"),
        )
    return _graph_client_instance