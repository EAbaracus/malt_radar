"""Tests for UserStore identity management (user_identities table).

Runs against a scratch users.db under tmp_path only — production.db and the
real backend users.db are never opened.
"""
from __future__ import annotations

import sqlite3

import pytest

from app.auth.store import DuplicateEmailError, DuplicateIdentityError, UserStore


@pytest.fixture()
def store(tmp_path):
    db = tmp_path / "users.db"
    return UserStore(str(db))


def _mk_user(store, email):
    return store.create_user(
        email=email,
        password_hash="x-placeholder-hash",
        age_country="TR",
        age_min=18,
        privacy_consent=True,
    )


def test_create_and_get_identity(store):
    user = _mk_user(store, "a@example.com")
    ident = store.create_identity(
        user["id"], "google", "sub-123", email="a@example.com"
    )
    assert ident["provider"] == "google"
    assert ident["provider_sub"] == "sub-123"
    assert ident["user_id"] == user["id"]

    found = store.get_user_by_identity("google", "sub-123")
    assert found is not None
    assert found["id"] == user["id"]
    assert found["email"] == "a@example.com"

    # Unknown identity resolves to None, not an error.
    assert store.get_user_by_identity("google", "nope") is None


def test_duplicate_identity_raises(store):
    user = _mk_user(store, "b@example.com")
    store.create_identity(user["id"], "google", "sub-dup")
    with pytest.raises(DuplicateIdentityError):
        store.create_identity(user["id"], "google", "sub-dup")


def test_get_identities_lists_all(store):
    user = _mk_user(store, "c@example.com")
    store.create_identity(user["id"], "google", "g-sub")
    store.create_identity(user["id"], "apple", "a-sub", email="c@example.com")
    idents = store.get_identities(user["id"])
    assert len(idents) == 2
    assert {i["provider"] for i in idents} == {"google", "apple"}


def test_create_oauth_user(store):
    user = store.create_oauth_user(
        email="oauth@example.com", provider="google", provider_sub="sub-oauth"
    )
    assert user["email_verified"] == 1
    assert user["password_hash"].startswith("oauth:")
    assert user["privacy_consent"] == 1

    found = store.get_user_by_identity("google", "sub-oauth")
    assert found is not None
    assert found["id"] == user["id"]


def test_create_oauth_user_rejects_taken_email(store):
    _mk_user(store, "taken@example.com")
    with pytest.raises(DuplicateEmailError):
        store.create_oauth_user(
            email="taken@example.com", provider="google", provider_sub="sub-x"
        )


def test_create_oauth_user_duplicate_sub_raises_identity_error(store):
    # First login with this (provider, provider_sub) creates the account.
    store.create_oauth_user(
        email="dupsub1@example.com", provider="google", provider_sub="sub-dup"
    )
    # Second login with the SAME sub must be reported as a duplicate
    # IDENTITY (the UNIQUE(provider, provider_sub) constraint fired), never
    # as a duplicate email — the caller already matched this account via
    # get_user_by_identity before reaching create_oauth_user.
    with pytest.raises(DuplicateIdentityError):
        store.create_oauth_user(
            email="dupsub2@example.com",
            provider="google",
            provider_sub="sub-dup",
        )
    # And a genuinely taken email still surfaces as DuplicateEmailError.
    with pytest.raises(DuplicateEmailError):
        store.create_oauth_user(
            email="dupsub1@example.com", provider="google", provider_sub="other-sub"
        )


def test_create_identity_unknown_user_raises(store):
    # A user_id that does not exist trips the FK constraint on
    # user_identities.user_id — that is a data-integrity failure, NOT a
    # duplicate identity, and must surface as a raw sqlite3.IntegrityError.
    with pytest.raises(sqlite3.IntegrityError):
        store.create_identity(999999, "google", "sub-ghost")


def test_delete_user_erases_identities(store):
    user = _mk_user(store, "d@example.com")
    store.create_identity(user["id"], "google", "sub-del")
    assert store.delete_user(user["id"]) is True
    assert store.get_user_by_id(user["id"]) is None
    assert store.get_identities(user["id"]) == []
    assert store.get_user_by_identity("google", "sub-del") is None