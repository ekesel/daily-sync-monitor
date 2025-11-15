# app/api/dependencies/internal_auth.py
from typing import Annotated
from typing import Optional
from http import HTTPStatus
from fastapi import Header, HTTPException, status
from app.core.config import get_settings

from app.core.config import get_settings


async def verify_internal_api_key(
    internal_api_key: Optional[str] = Header(
        default=None,
        alias="X-Internal-Api-Key",
        description="Internal API key required for /internal endpoints in non-local environments.",
    ),
) -> None:
    """
    Dependency to protect /internal endpoints.

    Rules
    -----
    - APP_ENV in ("local", "test"):
        - If INTERNAL_API_KEY is not set -> no auth enforced (convenient for local dev).
        - If INTERNAL_API_KEY is set      -> header must match the configured key.
    - APP_ENV not in ("local", "test")  [e.g. dev/stage/prod]:
        - INTERNAL_API_KEY must be set, otherwise 500 (misconfiguration).
        - Header must be present and match INTERNAL_API_KEY, otherwise 401.
    """
    settings = get_settings()
    env = (settings.APP_ENV or "local").lower()
    expected = getattr(settings, "INTERNAL_API_KEY", None)

    # Local / test: optional, but enforce if key is configured
    if env in ("local", "test"):
        if not expected:
            # No key configured => internal endpoints open in local/test
            return

        # Key configured => enforce it
        if not internal_api_key or internal_api_key != expected:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing internal API key.",
            )
        return

    # Non-local (dev / stage / prod): key must exist and must match
    if not expected:
        # Misconfigured environment: fail fast instead of silently exposing internals
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="INTERNAL_API_KEY not configured for this environment.",
        )

    if not internal_api_key or internal_api_key != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing internal API key.",
        )