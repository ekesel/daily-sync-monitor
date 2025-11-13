# app/api/dependencies/internal_auth.py
from typing import Annotated

from fastapi import Header, HTTPException
from http import HTTPStatus

from app.core.config import get_settings


async def verify_internal_api_key(
    x_internal_api_key: Annotated[str | None, Header(default=None)],
) -> None:
    """
    Simple guard for /internal endpoints.

    Behavior:
    - If INTERNAL_API_KEY is unset/empty in settings, no authentication is enforced.
    - If INTERNAL_API_KEY is set, the incoming X-Internal-Api-Key header must match,
      otherwise a 401 Unauthorized error is raised.
    """
    settings = get_settings()
    configured_key = settings.INTERNAL_API_KEY

    if not configured_key:
        # Key not configured => protection disabled (useful for local/dev).
        return

    if x_internal_api_key != configured_key:
        raise HTTPException(
            status_code=HTTPStatus.UNAUTHORIZED,
            detail="Invalid or missing X-Internal-Api-Key header.",
        )