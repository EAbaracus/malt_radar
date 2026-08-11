"""OAuth identity-token verification + provider registry.

Providers verify an OAuth id-token and return the identity claims the auth
routes need (``sub``, ``email``, ``email_verified``, optionally ``name``).

The registry maps provider names to verifier instances. Verification is
network-bound (Google's public JWKS), so tests inject a fake verifier via
``app.state.google_verifier`` instead of calling these directly.
"""
from __future__ import annotations

import os
from typing import Any, Dict, Protocol

GOOGLE_CLIENT_ID_ENV = "GOOGLE_CLIENT_ID"


class InvalidTokenError(Exception):
    """Raised when an id-token fails signature/audience/expiry validation."""


class OAuthIdentityVerifier(Protocol):
    """Protocol shared by every provider verifier and test doubles."""

    def verify_id_token(self, id_token: str) -> Dict[str, Any]:
        """Return validated identity claims or raise InvalidTokenError."""
        ...


class GoogleIdentityVerifier:
    """Verify a Google id-token with google-auth and return its claims.

    The audience is the backend's Google OAuth client id, read from the
    ``GOOGLE_CLIENT_ID`` env var. If that env var is unset the verifier
    cannot do its job: routes must inject a verifier (DI) rather than rely
    on this default in test/dev environments.
    """

    def __init__(self, audience: str = "") -> None:
        # Late imports: google-auth is a heavy dependency and the module must
        # stay importable in environments that only run the test suite.
        from google.auth.transport import requests as google_requests
        from google.oauth2 import id_token as google_id_token

        self._id_token = google_id_token
        self._requests = google_requests
        self.audience = audience or os.getenv(GOOGLE_CLIENT_ID_ENV, "").strip()

    def verify_id_token(self, id_token: str) -> Dict[str, Any]:
        if not self.audience:
            raise InvalidTokenError("GOOGLE_CLIENT_ID is not configured")
        try:
            claims = self._id_token.verify_oauth2_token(
                id_token,
                self._requests.Request(),
                audience=self.audience,
            )
            return dict(claims)
        except Exception as exc:  # noqa: BLE001 — google-auth raises ValueError on any bad token
            raise InvalidTokenError(str(exc)) from exc


#: Provider registry. Only google is wired today; other providers get their
#: own verifier entry when implemented (no stubs).
PROVIDER_VERIFIERS: Dict[str, OAuthIdentityVerifier] = {
    "google": GoogleIdentityVerifier(),
}