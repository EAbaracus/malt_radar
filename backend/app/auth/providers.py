"""OAuth identity-token verification + provider registry.

Providers verify an OAuth id-token and return the identity claims the auth
routes need (``sub``, ``email``, ``email_verified``, optionally ``name``).

The registry maps provider names to verifier *classes*. Instances are only
created when a route actually needs to verify a token (lazy), so importing
this module never pulls in google-auth — the ``google.auth`` imports happen
inside ``GoogleIdentityVerifier.__init__``. Verification is network-bound
(Google's public JWKS), so tests inject a fake verifier via
``app.state.google_verifier`` instead of calling these directly.
"""
from __future__ import annotations

import os
from typing import Any, Dict, Protocol, Type

GOOGLE_CLIENT_ID_ENV = "GOOGLE_CLIENT_ID"


class InvalidTokenError(Exception):
    """Raised when an id-token fails signature/audience/expiry validation.

    This is the client's fault (bad/expired/mis-audienced token): routes map
    it to 401.
    """


class TokenVerificationUnavailableError(Exception):
    """Raised when a verifier cannot complete verification through no fault
    of the token: network failure, JWKS fetch timeout, provider outage.

    Routes map it to 503 so clients can distinguish "your token is bad"
    (retry won't help) from "the provider is down" (retry later will).
    """


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
        # Because the registry stores a *class* reference (not an instance),
        # these imports only happen when a token is actually verified.
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
                # Google's JWT `iat` is stamped with Google server time; a
                # client machine clock only a couple of seconds behind makes
                # the strict default (0s skew) reject valid tokens with
                # "Token used too early". Allow ±5 minutes, matching the
                # tolerance google-auth documents for distributed clocks.
                clock_skew_in_seconds=300,
            )
            return dict(claims)
        except InvalidTokenError:
            raise
        except Exception as exc:  # noqa: BLE001 — google-auth raises ValueError
            # on any bad token and transport errors on network/JWKS failures.
            # A ValueError is a malformed token (client fault -> 401); anything
            # else (requests.ConnectionError, Timeout, ...) means verification
            # could not be completed -> 503.
            if isinstance(exc, ValueError):
                raise InvalidTokenError(str(exc)) from exc
            raise TokenVerificationUnavailableError(str(exc)) from exc


#: Provider registry. Only google is wired today; other providers get their
#: own verifier entry when implemented (no stubs). Values are CLASSES, not
#: instances: constructing a verifier imports google-auth, so it is deferred
#: until the route needs it (see ``routes._get_verifier``).
PROVIDER_VERIFIERS: Dict[str, Type[OAuthIdentityVerifier]] = {
    "google": GoogleIdentityVerifier,
}
