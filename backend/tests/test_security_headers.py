"""P1 hardening regression tests (scope 2026-08-06).

Verifies the security-headers middleware in app.main emits the full
hardened header set on EVERY response, including 4xx error responses.
The Server-banner suppression cannot be unit-tested here: uvicorn adds
that header at the ASGI protocol layer after the app returns, so it only
shows up in a real uvicorn run (covered by the isolated DAST regression).
"""
import os
import sys
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.main import app, SECURITY_HEADERS

client = TestClient(app)

# All seven headers must be present and exact on every response.
EXPECTED_HEADERS = {
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Content-Security-Policy": "default-src 'none'",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    "Cache-Control": "no-store",
}


def _assert_full_header_set(resp):
    for name, value in EXPECTED_HEADERS.items():
        assert resp.headers.get(name) == value, (
            f"missing/mismatched header {name}: "
            f"got {resp.headers.get(name)!r}, want {value!r}"
        )


def test_headers_on_health_ok():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    _assert_full_header_set(resp)


def test_headers_on_auth_denied():
    # Unauthenticated request to a protected endpoint must be rejected (401
    # bearer-gate or 403 since DB_API_ENABLED is off by default here). Headers
    # must still be present on the error response.
    resp = client.get("/api/db/health")
    assert resp.status_code in (401, 403)
    _assert_full_header_set(resp)


def test_headers_on_not_found_404():
    resp = client.get("/does/not/exist")
    assert resp.status_code == 404
    _assert_full_header_set(resp)


def test_headers_module_contract():
    # SECURITY_HEADERS dict is exported from app.main for auditability.
    assert set(EXPECTED_HEADERS) == set(SECURITY_HEADERS)
    # No wildcard values: values are fixed literals, not derived from input.
    for v in SECURITY_HEADERS.values():
        assert "*" not in v, f"wildcard found in header value: {v!r}"
