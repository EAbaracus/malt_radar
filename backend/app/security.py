"""Shared security primitives for the Malt Radar API.

Kept in a separate module to avoid a circular import between `app.main`
(which defines the FastAPI app and includes the routers) and the routers
(which need `verify_api_key` / `limiter`).
"""
import os
from typing import Optional

from fastapi import HTTPException, Header
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

# Configure rate limiter (default: 60 requests per minute per IP)
limiter = Limiter(key_func=get_remote_address)

# Server-side secret. If unset, all key-protected endpoints reject (fail-closed).
API_KEY = os.getenv("MALT_RADAR_API_KEY")

# Header name used to identify the caller. The admin review API derives its
# audit-trail `reviewer` field from this verified identity rather than from a
# client-supplied request body, so the audit log cannot be forged.
API_KEY_HEADER = "x-api-key"


async def verify_api_key(x_api_key: Optional[str] = Header(None, alias=API_KEY_HEADER)):
    """Verify the request API key and return the verified caller identity.

    Returns the API key string (the canonical caller identity for this app's
    env-var based auth model). Raises 403 if the server key is unconfigured or
    the supplied key is missing/invalid. Callers that need an audit identity
    should use this return value, never a client-supplied field.
    """
    if not API_KEY:
        raise HTTPException(status_code=403, detail="Server API Key not configured")
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid or missing API Key")
    return x_api_key
