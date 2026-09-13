"""Password reset (6-digit code) — API + store behaviour.

Threat model under test: a 6-digit code is guessable, so the guards are
attempt-limit, short TTL, single active code per user, and session invalidation
after a successful reset.
"""
from __future__ import annotations

import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.auth.store import RESET_MAX_ATTEMPTS, UserStore

PASSWORD = "s3curePass"
NEW_PASSWORD = "even-more-s3cure"


@pytest.fixture(autouse=True)
def isolated_users_db(tmp_path, monkeypatch):
    db = tmp_path / "users.db"
    monkeypatch.setenv("MALT_RADAR_USERS_DB_PATH", str(db))
    if hasattr(app.state, "user_store"):
        del app.state.user_store
    app.state.limiter.enabled = False
    yield {"db": str(db)}
    if hasattr(app.state, "user_store"):
        del app.state.user_store
    app.state.limiter.enabled = True


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def sent_codes(monkeypatch):
    """Capture reset codes instead of sending mail."""
    codes: list[tuple[str, str]] = []
    monkeypatch.setattr(
        "app.auth.routes._send_reset_code_email",
        lambda email, code: codes.append((email, code)),
    )
    return codes


def _register(client, email="user@example.com") -> dict:
    r = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": PASSWORD,
            "age_country": "TR",
            "age_min": 18,
            "privacy_consent": True,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _reset(client, email, code, password=NEW_PASSWORD):
    return client.post(
        "/api/auth/reset-password",
        json={"email": email, "code": code, "new_password": password},
    )


# --- request step -------------------------------------------------------
def test_forgot_password_does_not_reveal_whether_email_exists(client, sent_codes):
    r = client.post("/api/auth/forgot-password", json={"email": "nobody@example.com"})
    assert r.status_code == 200
    assert r.json() == {"ok": True}
    assert sent_codes == []  # nothing sent, nothing stored


def test_forgot_password_sends_one_code_for_a_known_email(client, sent_codes):
    _register(client)
    r = client.post("/api/auth/forgot-password", json={"email": "USER@example.com"})
    assert r.status_code == 200
    assert r.json() == {"ok": True}
    assert len(sent_codes) == 1
    email, code = sent_codes[0]
    assert email == "user@example.com"
    assert len(code) == 6 and code.isdigit()


def test_forgot_password_rejects_a_malformed_email(client, sent_codes):
    r = client.post("/api/auth/forgot-password", json={"email": "not-an-email"})
    assert r.status_code == 422
    assert sent_codes == []


def test_a_second_request_replaces_the_first_code(client, sent_codes):
    _register(client)
    client.post("/api/auth/forgot-password", json={"email": "user@example.com"})
    first = sent_codes[0][1]
    client.post("/api/auth/forgot-password", json={"email": "user@example.com"})
    second = sent_codes[1][1]
    assert _reset(client, "user@example.com", first).status_code == 400
    assert _reset(client, "user@example.com", second).status_code == 200


# --- reset step ---------------------------------------------------------
def test_reset_changes_the_password_and_kills_every_session(client, sent_codes):
    registration = _register(client)
    old_token = registration["token"]
    assert client.get("/api/auth/me", headers=_auth(old_token)).status_code == 200

    client.post("/api/auth/forgot-password", json={"email": "user@example.com"})
    code = sent_codes[0][1]

    assert _reset(client, "user@example.com", code).status_code == 200

    # Old password no longer authenticates…
    assert (
        client.post(
            "/api/auth/login",
            json={"email": "user@example.com", "password": PASSWORD},
        ).status_code
        == 401
    )
    # …and neither does the session that existed before the reset.
    assert client.get("/api/auth/me", headers=_auth(old_token)).status_code == 401

    # New password works.
    login = client.post(
        "/api/auth/login",
        json={"email": "user@example.com", "password": NEW_PASSWORD},
    )
    assert login.status_code == 200
    assert login.json()["token"]


def test_a_wrong_code_is_rejected_and_costs_an_attempt(client, sent_codes, isolated_users_db):
    _register(client)
    client.post("/api/auth/forgot-password", json={"email": "user@example.com"})
    good = sent_codes[0][1]
    wrong = "000000" if good != "000000" else "111111"

    assert _reset(client, "user@example.com", wrong).status_code == 400

    with sqlite3.connect(isolated_users_db["db"]) as conn:
        attempts = conn.execute("SELECT attempts FROM password_resets").fetchone()[0]
    assert attempts == 1
    # The real code still works while attempts remain.
    assert _reset(client, "user@example.com", good).status_code == 200


def test_code_is_destroyed_after_too_many_wrong_attempts(client, sent_codes):
    _register(client)
    client.post("/api/auth/forgot-password", json={"email": "user@example.com"})
    good = sent_codes[0][1]
    wrong = "000001" if good != "000001" else "000002"

    for _ in range(RESET_MAX_ATTEMPTS):
        assert _reset(client, "user@example.com", wrong).status_code == 400

    # Even the correct code is refused once the budget is spent.
    assert _reset(client, "user@example.com", good).status_code == 400


def test_a_code_cannot_be_reused(client, sent_codes):
    _register(client)
    client.post("/api/auth/forgot-password", json={"email": "user@example.com"})
    code = sent_codes[0][1]
    assert _reset(client, "user@example.com", code).status_code == 200
    assert _reset(client, "user@example.com", code, password="another-pass").status_code == 400


def test_an_expired_code_is_refused(client, sent_codes, isolated_users_db):
    _register(client)
    client.post("/api/auth/forgot-password", json={"email": "user@example.com"})
    code = sent_codes[0][1]

    with sqlite3.connect(isolated_users_db["db"]) as conn:
        conn.execute("UPDATE password_resets SET expires_at = '2000-01-01T00:00:00+00:00'")
        conn.commit()

    assert _reset(client, "user@example.com", code).status_code == 400


def test_reset_does_not_weaken_the_password_policy(client, sent_codes):
    _register(client)
    client.post("/api/auth/forgot-password", json={"email": "user@example.com"})
    code = sent_codes[0][1]
    assert _reset(client, "user@example.com", code, password="short").status_code == 422


def test_reset_rejects_a_non_numeric_code(client, sent_codes):
    _register(client)
    client.post("/api/auth/forgot-password", json={"email": "user@example.com"})
    assert _reset(client, "user@example.com", "abcdef").status_code == 422


def test_reset_for_an_unknown_email_fails_generically(client):
    r = _reset(client, "nobody@example.com", "123456")
    assert r.status_code == 400
    assert r.json()["detail"] == "Invalid or expired reset code"


def test_no_enumeration_difference_between_known_and_unknown_email(client, sent_codes):
    _register(client)
    known = client.post("/api/auth/forgot-password", json={"email": "user@example.com"})
    unknown = client.post("/api/auth/forgot-password", json={"email": "nobody@example.com"})
    assert known.status_code == unknown.status_code == 200
    assert known.json() == unknown.json() == {"ok": True}


# --- regressions: the shared mailer refactor ---------------------------
def test_register_still_issues_a_verification_token(client, sent_codes, isolated_users_db):
    _register(client)
    with sqlite3.connect(isolated_users_db["db"]) as conn:
        n = conn.execute("SELECT COUNT(*) FROM email_verifications").fetchone()[0]
    assert n == 1


def test_verify_email_still_works(client, monkeypatch):
    _register(client)
    token = UserStore.from_env().create_verification_token(1)
    r = client.post("/api/auth/verify-email", json={"user_id": 1, "token": token})
    assert r.status_code == 200
    assert r.json() == {"ok": True}