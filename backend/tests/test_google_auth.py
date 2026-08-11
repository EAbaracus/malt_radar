"""Tests for POST /api/auth/google (Google id-token login: find-or-create + link).

Token verification is DI'd via `app.state.google_verifier` (a fake) — the real
GoogleIdentityVerifier performs network calls and is never invoked here.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.auth.providers import InvalidTokenError, TokenVerificationUnavailableError
from app.auth.store import DuplicateEmailError, DuplicateIdentityError, UserStore


class FakeGoogleVerifier:
    """Deterministic stand-in for GoogleIdentityVerifier.

    `error` (when set) is raised for every token; otherwise `claims` are
    returned verbatim — the same sub means the same Google user.
    """

    def __init__(
        self,
        claims: Optional[Dict[str, Any]] = None,
        error: Optional[Exception] = None,
    ):
        self.claims = claims or {}
        self.error = error

    def verify_id_token(self, id_token: str) -> Dict[str, Any]:
        if self.error is not None:
            raise self.error
        return dict(self.claims)


@pytest.fixture(autouse=True)
def isolated_state(tmp_path, monkeypatch):
    db = tmp_path / "users.db"
    monkeypatch.setenv("MALT_RADAR_USERS_DB_PATH", str(db))
    # Fresh per-test app state: lazy store init + no DI'd verifier.
    if hasattr(app.state, "user_store"):
        del app.state.user_store
    if hasattr(app.state, "google_verifier"):
        del app.state.google_verifier
    # Disable slowapi global rate limits (same as test_auth.py) so many
    # same-IP calls are deterministic; /google carries a limiter decorator
    # for production parity.
    app.state.limiter.enabled = False
    yield
    if hasattr(app.state, "user_store"):
        del app.state.user_store
    if hasattr(app.state, "google_verifier"):
        del app.state.google_verifier
    app.state.limiter.enabled = True


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def _auth(token: str):
    return {"Authorization": f"Bearer {token}"}


def _google_claims(sub: str, email: str, verified: bool = True, name: Optional[str] = None):
    claims = {"sub": sub, "email": email, "email_verified": verified}
    if name:
        claims["name"] = name
    return claims


def test_google_login_creates_user(client):
    app.state.google_verifier = FakeGoogleVerifier(
        claims=_google_claims("gsub-111", "gmail.user@gmail.com", name="Gmail User")
    )
    r = client.post("/api/auth/google", json={"id_token": "tok-1"})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["token"]
    user = data["user"]
    assert user["email"] == "gmail.user@gmail.com"
    assert user["email_verified"] == 1
    assert user["display_name"] == "Gmail User"
    assert "password_hash" not in user

    store = UserStore.from_env()
    idents = store.get_identities(user["id"])
    assert len(idents) == 1
    assert (idents[0]["provider"], idents[0]["provider_sub"]) == (
        "google",
        "gsub-111",
    )
    # OAuth users must never be able to password-login (oauth: placeholder).
    assert store.get_user_by_id(user["id"])["password_hash"].startswith("oauth:")


def test_google_login_existing_identity(client):
    app.state.google_verifier = FakeGoogleVerifier(
        claims=_google_claims("gsub-222", "x@gmail.com")
    )
    r1 = client.post("/api/auth/google", json={"id_token": "tok-a"})
    r2 = client.post("/api/auth/google", json={"id_token": "tok-b"})
    assert r1.status_code == 200, r1.text
    assert r2.status_code == 200, r2.text
    # Same Google sub -> same account, no second row.
    assert r1.json()["user"]["id"] == r2.json()["user"]["id"]
    store = UserStore.from_env()
    assert len(store.get_identities(r1.json()["user"]["id"])) == 1


def test_google_login_links_by_email(client):
    reg = client.post(
        "/api/auth/register",
        json={
            "email": "link@example.com",
            "password": "s3curePass",
            "age_country": "TR",
            "age_min": 18,
            "privacy_consent": True,
        },
    )
    assert reg.status_code == 201, reg.text
    existing_id = reg.json()["user"]["id"]

    app.state.google_verifier = FakeGoogleVerifier(
        claims=_google_claims("gsub-333", "link@example.com")
    )
    r = client.post("/api/auth/google", json={"id_token": "tok"})
    assert r.status_code == 200, r.text
    # Linked to the existing password account, not a new user.
    assert r.json()["user"]["id"] == existing_id

    store = UserStore.from_env()
    idents = store.get_identities(existing_id)
    assert len(idents) == 1
    assert (idents[0]["provider"], idents[0]["provider_sub"]) == (
        "google",
        "gsub-333",
    )
    # The account still password-logs-in after linking.
    login = client.post(
        "/api/auth/login",
        json={"email": "link@example.com", "password": "s3curePass"},
    )
    assert login.status_code == 200


def test_google_login_invalid_token(client):
    app.state.google_verifier = FakeGoogleVerifier(
        error=InvalidTokenError("bad signature")
    )
    r = client.post("/api/auth/google", json={"id_token": "bad"})
    assert r.status_code == 401
    assert r.json()["detail"] == "Invalid Google token"


def test_google_login_unverified_email(client):
    app.state.google_verifier = FakeGoogleVerifier(
        claims=_google_claims("gsub-444", "u@example.com", verified=False)
    )
    r = client.post("/api/auth/google", json={"id_token": "t"})
    assert r.status_code == 401

    # Missing email_verified claim is also rejected.
    app.state.google_verifier = FakeGoogleVerifier(
        claims={"sub": "gsub-445", "email": "u2@example.com"}
    )
    r2 = client.post("/api/auth/google", json={"id_token": "t"})
    assert r2.status_code == 401


def test_google_delete_me_removes_identity(client):
    app.state.google_verifier = FakeGoogleVerifier(
        claims=_google_claims("gsub-del", "del@gmail.com")
    )
    reg = client.post("/api/auth/google", json={"id_token": "t"}).json()
    uid = reg["user"]["id"]
    token = reg["token"]

    store = UserStore.from_env()
    assert len(store.get_identities(uid)) == 1

    assert client.delete("/api/auth/me", headers=_auth(token)).status_code == 200
    # KVKK erasure also removes the provider identity link.
    assert store.get_identities(uid) == []
    assert client.get("/api/auth/me", headers=_auth(token)).status_code == 401


def test_google_login_verifier_unavailable_is_503(client):
    """Minor #6: a verifier that is down (network/JWKS failure) is NOT the
    client's fault — 503 with a machine-readable detail, not 401."""
    app.state.google_verifier = FakeGoogleVerifier(
        error=TokenVerificationUnavailableError("jwks timeout")
    )
    r = client.post("/api/auth/google", json={"id_token": "t"})
    assert r.status_code == 503
    assert r.json()["detail"] == "verification_unavailable"


def test_google_login_concurrent_same_sub(client):
    """B1-fix regression: two requests with the same (google, sub) that BOTH
    reach create_oauth_user. The loser gets DuplicateIdentityError from the
    UNIQUE(provider, provider_sub) constraint and the route must still answer
    200 with the SAME user — never 500/409."""
    app.state.google_verifier = FakeGoogleVerifier(
        claims=_google_claims("gsub-race", "race@example.com")
    )
    r1 = client.post("/api/auth/google", json={"id_token": "t1"})
    assert r1.status_code == 200, r1.text
    uid1 = r1.json()["user"]["id"]

    store = UserStore.from_env()
    # Simulate the losing half of the race: a concurrent request inserted the
    # identity+user between this request's check and its insert, so the
    # insert must raise — exactly what the sqlite UNIQUE(provider, provider_sub)
    # constraint does. (A different email is used so only the identity
    # constraint collides; with the same email the users.email UNIQUE trips
    # first and surfaces as DuplicateEmailError — covered by the sibling test.)
    with pytest.raises(DuplicateIdentityError):
        store.create_oauth_user(
            email="stale-email@example.com",
            provider="google",
            provider_sub="gsub-race",
        )
    # The real route then re-resolves by identity and answers 200 idempotent.
    r2 = client.post("/api/auth/google", json={"id_token": "t2"})
    assert r2.status_code == 200, r2.text
    assert r2.json()["user"]["id"] == uid1
    assert len(store.get_identities(uid1)) == 1


def test_google_login_concurrent_same_email(client):
    """B1-fix regression (the DuplicateEmailError half): two requests, same
    email but DIFFERENT (google, sub). Both call create_oauth_user; the loser
    hits the UNIQUE users.email constraint -> DuplicateEmailError. The route
    must then link the identity to the EXISTING user and answer 200 — a user
    who just registered by email and immediately double-taps Google login
    must get into their own account, not a 500."""
    app.state.google_verifier = FakeGoogleVerifier(
        claims=_google_claims("gsub-mail-a", "shared@example.com")
    )
    r1 = client.post("/api/auth/google", json={"id_token": "t1"})
    assert r1.status_code == 200, r1.text
    uid1 = r1.json()["user"]["id"]

    store = UserStore.from_env()
    with pytest.raises(DuplicateEmailError):
        store.create_oauth_user(
            email="shared@example.com",
            provider="google",
            provider_sub="gsub-mail-b",
        )

    # The second sub now logs in: must resolve to the SAME account (identity
    # linked to the existing user) and answer 200 — not 500.
    app.state.google_verifier = FakeGoogleVerifier(
        claims=_google_claims("gsub-mail-b", "shared@example.com")
    )
    r2 = client.post("/api/auth/google", json={"id_token": "t2"})
    assert r2.status_code == 200, r2.text
    assert r2.json()["user"]["id"] == uid1

    idents = store.get_identities(uid1)
    assert {i["provider_sub"] for i in idents} == {"gsub-mail-a", "gsub-mail-b"}


def test_google_login_limiter_disabled(client):
    # autouse fixture sets app.state.limiter.enabled = False; the route still
    # carries the @limiter.limit decorator for production.
    app.state.google_verifier = FakeGoogleVerifier(
        claims=_google_claims("gsub-lim", "lim@gmail.com")
    )
    for _ in range(3):
        r = client.post("/api/auth/google", json={"id_token": "t"})
        assert r.status_code == 200, r.text
