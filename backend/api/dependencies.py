"""
API authentication dependencies for Folio backend.
"""

import hmac
import os
from typing import Annotated

from fastapi import Header, HTTPException, status


def require_api_key(
    x_api_key: Annotated[str | None, Header()] = None,
) -> None:
    """
    Validate API key from X-API-Key header.

    Graceful dev-mode fallback: if FOLIO_API_KEY is unset, auth is disabled.
    This ensures zero breaking changes for existing users.

    Raises:
        HTTPException: 401 if API key is invalid or missing (when auth is enabled)
    """
    expected_key = os.getenv("FOLIO_API_KEY")

    # Dev mode: auth disabled when FOLIO_API_KEY is unset
    if not expected_key:
        return

    # Production mode: require valid API key
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header",
        )

    # Use constant-time comparison to prevent timing attacks
    if not hmac.compare_digest(x_api_key, expected_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
