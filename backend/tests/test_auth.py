"""Tests for the auth + per-user sync API (separate users.db)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.auth.store import UserStore


@pytest.fixture(autouse=True)
def isolated_users_db(tmp_path, monkeypatch):
    db = tmp_path / "users.db"
    monkeypatch.setenv("MALT_RADAR_USERS_DB_PATH", str(db))
    # Ensure get_store exercises its LAZY init (attribute absent), mirroring a
    # fresh app process — a pre-set .user_store masked the AttributeError bug.
    if hasattr(app.state, "user_store"):
        del app.state.user_store
    # Disable slowapi global rate limits so tests can make many same-IP calls
    # deterministically (rate limiting is exercised separately / in prod).
    app.state.limiter.enabled = False
    yield
    if hasattr(app.state, "user_store"):
        del app.state.user_store
    app.state.limiter.enabled = True


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def _auth(token: str):
    return {"Authorization": f"Bearer {token}"}


def test_register_login_me(client):
    r = client.post(
        "/api/auth/register",
        json={
            "email": "User@Example.com",
            "password": "s3curePass",
            "age_country": "TR",
            "age_min": 18,
            "privacy_consent": True,
        },
    )
    assert r.status_code == 201, r.text
    data = r.json()
    token = data["token"]
    user = data["user"]
    assert user["email"] == "user@example.com"
    assert user["email_verified"] == 0
    assert "password_hash" not in user

    me = client.get("/api/auth/me", headers=_auth(token))
    assert me.status_code == 200
    assert me.json()["email"] == "user@example.com"

    login = client.post(
        "/api/auth/login",
        json={"email": "user@example.com", "password": "s3curePass"},
    )
    assert login.status_code == 200
    assert login.json()["token"]


def test_register_rejects_without_consent(client):
    r = client.post(
        "/api/auth/register",
        json={
            "email": "a@b.com",
            "password": "s3curePass",
            "privacy_consent": False,
        },
    )
    assert r.status_code == 422


def test_register_rejects_omitted_consent(client):
    r = client.post(
        "/api/auth/register",
        json={
            "email": "omitted@b.com",
            "password": "s3curePass",
            "age_country": "US",
            "age_min": 21,
        },
    )
    assert r.status_code == 422


def test_register_rejects_missing_age_gate(client):
    r1 = client.post(
        "/api/auth/register",
        json={
            "email": "age1@b.com",
            "password": "s3curePass",
            "privacy_consent": True,
            "age_min": 21,
        },
    )
    assert r1.status_code == 422

    r2 = client.post(
        "/api/auth/register",
        json={
            "email": "age2@b.com",
            "password": "s3curePass",
            "privacy_consent": True,
            "age_country": "",
            "age_min": 21,
        },
    )
    assert r2.status_code == 422

    r3 = client.post(
        "/api/auth/register",
        json={
            "email": "age3@b.com",
            "password": "s3curePass",
            "privacy_consent": True,
            "age_country": "US",
        },
    )
    assert r3.status_code == 422


def test_register_duplicate_email(client):
    payload = {
        "email": "dup@example.com",
        "password": "s3curePass",
        "age_country": "US",
        "age_min": 21,
        "privacy_consent": True,
    }
    assert client.post("/api/auth/register", json=payload).status_code == 201
    assert client.post("/api/auth/register", json=payload).status_code == 409


def test_login_rejects_bad_password_and_unknown_email(client):
    client.post(
        "/api/auth/register",
        json={
            "email": "b@example.com",
            "password": "s3curePass",
            "age_country": "US",
            "age_min": 21,
            "privacy_consent": True,
        },
    )
    r1 = client.post(
        "/api/auth/login",
        json={"email": "b@example.com", "password": "wrongPass"},
    )
    r2 = client.post(
        "/api/auth/login",
        json={"email": "nope@example.com", "password": "whatever99"},
    )
    assert r1.status_code == 401
    assert r2.status_code == 401
    assert r1.json()["detail"] == r2.json()["detail"]  # no user enumeration


def test_logout_invalidates_session(client):
    reg = client.post(
        "/api/auth/register",
        json={
            "email": "lo@example.com",
            "password": "s3curePass",
            "age_country": "TR",
            "age_min": 18,
            "privacy_consent": True,
        },
    ).json()
    token = reg["token"]
    assert client.get("/api/auth/me", headers=_auth(token)).status_code == 200
    assert client.post("/api/auth/logout", headers=_auth(token)).status_code == 200
    assert client.get("/api/auth/me", headers=_auth(token)).status_code == 401


def test_update_profile(client):
    reg = client.post(
        "/api/auth/register",
        json={
            "email": "prof@example.com",
            "password": "s3curePass",
            "age_country": "TR",
            "age_min": 18,
            "privacy_consent": True,
        },
    ).json()
    token = reg["token"]
    up = client.patch(
        "/api/auth/me",
        headers=_auth(token),
        json={"display_name": "Viski Avcısı"},
    )
    assert up.status_code == 200
    assert up.json()["display_name"] == "Viski Avcısı"


def test_email_verification(client):
    reg = client.post(
        "/api/auth/register",
        json={
            "email": "v@example.com",
            "password": "s3curePass",
            "age_country": "TR",
            "age_min": 18,
            "privacy_consent": True,
        },
    ).json()
    uid = reg["user"]["id"]

    store = UserStore.from_env()
    vtoken = store.create_verification_token(uid)

    bad = client.post(
        "/api/auth/verify-email", json={"user_id": uid, "token": "wrongtoken1"}
    )
    assert bad.status_code == 400

    ok = client.post(
        "/api/auth/verify-email", json={"user_id": uid, "token": vtoken}
    )
    assert ok.status_code == 200
    assert ok.json()["ok"] is True


def test_me_requires_token(client):
    assert client.get("/api/auth/me").status_code == 401


def test_sync_pull_mocked(client, monkeypatch):
    reg = client.post(
        "/api/auth/register",
        json={
            "email": "mockpull@example.com",
            "password": "s3curePass",
            "age_country": "TR",
            "age_min": 18,
            "privacy_consent": True,
        },
    ).json()
    token = reg["token"]

    mocked_data = {
        "favorites": [{"whisky_id": "w_mock", "updated_at": "2026-01-02T00:00:00Z"}],
        "scores": [{"whisky_id": "w_mock", "score": 90, "updated_at": "2026-01-02T00:00:00Z"}],
        "lists": [],
        "items": []
    }

    def mock_sync_pull_all(self, uid):
        return mocked_data

    monkeypatch.setattr(UserStore, "sync_pull_all", mock_sync_pull_all)

    pull = client.get("/api/auth/sync/pull", headers=_auth(token))
    assert pull.status_code == 200
    assert pull.json() == mocked_data


def test_sync_push_pull(client):
    reg = client.post(
        "/api/auth/register",
        json={
            "email": "s@example.com",
            "password": "s3curePass",
            "age_country": "TR",
            "age_min": 18,
            "privacy_consent": True,
        },
    ).json()
    token = reg["token"]

    push = client.post(
        "/api/auth/sync/push",
        headers=_auth(token),
        json={
            "favorites": [{"whisky_id": "w1", "updated_at": "2026-01-02T00:00:00Z"}],
            "scores": [
                {"whisky_id": "w1", "score": 85, "updated_at": "2026-01-02T00:00:00Z"}
            ],
            "lists": [
                {
                    "list_id": "L1",
                    "name": "My Cellar",
                    "sort_order": 0,
                    "updated_at": "2026-01-02T00:00:00Z",
                }
            ],
            "items": [
                {
                    "list_id": "L1",
                    "whisky_id": "w1",
                    "sort_order": 1,
                    "updated_at": "2026-01-02T00:00:00Z",
                }
            ],
        },
    )
    assert push.status_code == 200, push.text
    assert push.json()["counts"]["favorites"] == 1

    pull = client.get("/api/auth/sync/pull", headers=_auth(token))
    assert pull.status_code == 200
    body = pull.json()
    assert len(body["favorites"]) == 1
    assert body["favorites"][0]["whisky_id"] == "w1"
    assert len(body["lists"]) == 1
    assert len(body["items"]) == 1

    # Newer server copy should win over an older push.
    push_older = client.post(
        "/api/auth/sync/push",
        headers=_auth(token),
        json={
            "scores": [
                {"whisky_id": "w1", "score": 10, "updated_at": "2000-01-01T00:00:00Z"}
            ]
        },
    )
    assert push_older.json()["counts"]["scores"] == 0
    pull2 = client.get("/api/auth/sync/pull", headers=_auth(token)).json()
    assert pull2["scores"][0]["score"] == 85


def test_delete_account_erases_user_and_sync(client):
    creds = {
        "email": "erase@example.com",
        "password": "s3curePass",
        "age_country": "TR",
        "age_min": 18,
        "privacy_consent": True,
    }
    reg = client.post("/api/auth/register", json=creds).json()
    token = reg["token"]
    assert client.post(
        "/api/auth/sync/push",
        headers=_auth(token),
        json={
            "favorites": [{"whisky_id": "w1", "updated_at": "2026-01-01T00:00:00Z"}]
        },
    ).status_code == 200

    second_login = client.post(
        "/api/auth/login",
        json={"email": creds["email"], "password": creds["password"]},
    ).json()["token"]

    assert client.delete("/api/auth/me", headers=_auth(token)).status_code == 200

    # Both sessions are dead and the account no longer exists.
    for t in (token, second_login):
        assert client.get("/api/auth/me", headers=_auth(t)).status_code == 401
    assert client.post(
        "/api/auth/login",
        json={"email": creds["email"], "password": creds["password"]},
    ).status_code == 401

    # Re-registering the same email starts with an empty sync store.
    reg2 = client.post("/api/auth/register", json=creds).json()
    pull = client.get(
        "/api/auth/sync/pull", headers=_auth(reg2["token"])
    ).json()
    assert pull.get("favorites", []) == []

