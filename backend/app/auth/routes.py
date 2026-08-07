"""HTTP routes for authentication and per-user sync.

- `/api/auth/*` endpoints are anonymous where required (register/login/verify)
  and are heavily rate-limited. Authenticated endpoints rely on a bearer token.
- These routes do NOT require the global `x-api-key`; they validate their own
  user token instead.
- Transactional email is stubbed: the verification link is written to the
  server log. Wire an SMTP/transactional provider at deploy time.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request

from app.security import limiter
from app.auth.passwords import hash_password, verify_password
from app.auth.schemas import (
    AuthLoginRequest,
    AuthRegisterRequest,
    AuthUpdateProfileRequest,
    AuthVerifyEmailRequest,
    SyncRequest,
)
from app.auth.store import DuplicateEmailError, UserStore

logger = logging.getLogger("malt_radar.auth")
router = APIRouter(prefix="/api/auth", tags=["auth"])


# --- dependencies -----------------------------------------------------
def get_store(request: Request) -> UserStore:
    store: Optional[UserStore] = request.app.state.user_store
    if store is None:
        store = UserStore.from_env()
        request.app.state.user_store = store
    return store


def get_bearer_token(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if not auth.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return auth.split(" ", 1)[1].strip()


async def get_current_user(
    request: Request, store: UserStore = Depends(get_store)
) -> Dict[str, Any]:
    token = get_bearer_token(request)
    user = store.get_user_by_token(token)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    return _public_user(user)


def _public_user(user: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(user)
    out.pop("password_hash", None)
    return out


def _send_verification_email(email: str, verify_url: str) -> None:
    # Stub (no SMTP configured): log the link so the receiver can verify.
    logger.info(
        "EMAIL-STUB verify url for %s: %s", email, verify_url
    )


# --- account lifecycle ------------------------------------------------
@router.post("/register", status_code=201)
@limiter.limit("5/minute")
async def register(
    request: Request,
    body: AuthRegisterRequest,
    store: UserStore = Depends(get_store),
):
    if not body.privacy_consent:
        raise HTTPException(
            status_code=422,
            detail="Privacy consent (KVKK) is required to create an account",
        )
    if not body.age_country or body.age_min is None:
        raise HTTPException(
            status_code=422,
            detail="Age gate country/minimum age are required",
        )
    password_hash = hash_password(body.password)
    try:
        user = store.create_user(
            email=body.email,
            password_hash=password_hash,
            display_name=body.display_name,
            age_country=body.age_country,
            age_min=body.age_min,
            privacy_consent=body.privacy_consent,
        )
    except DuplicateEmailError:
        raise HTTPException(status_code=409, detail="Email already registered")

    vtoken = store.create_verification_token(user["id"])
    _send_verification_email(
        user["email"],
        f"/verify-email?user_id={user['id']}&token={vtoken}",
    )
    token = store.create_session(user["id"])
    return {"token": token, "user": _public_user(user)}


@router.post("/login")
@limiter.limit("8/minute")
async def login(
    request: Request,
    body: AuthLoginRequest,
    store: UserStore = Depends(get_store),
):
    user = store.get_user_by_email(body.email.strip().lower())
    # Identical response for unknown email vs wrong password (no enumeration).
    if user is None or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(
            status_code=401, detail="Invalid email or password"
        )
    token = store.create_session(user["id"])
    return {"token": token, "user": _public_user(user)}


@router.post("/logout")
async def logout(request: Request, store: UserStore = Depends(get_store)):
    token = get_bearer_token(request)
    user = store.get_user_by_token(token)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    store.delete_session(token)
    return {"ok": True}


@router.get("/me")
async def me(request: Request, user: Dict[str, Any] = Depends(get_current_user)):
    return user


@router.delete("/me")
async def delete_account(
    request: Request,
    user: Dict[str, Any] = Depends(get_current_user),
    store: UserStore = Depends(get_store),
):
    """Permanently delete an account and all associated data (KVKK erasure)."""
    token = get_bearer_token(request)
    store.delete_user(user["id"])
    store.delete_session(token)
    return {"ok": True}


@router.patch("/me")
async def update_profile(
    request: Request,
    body: AuthUpdateProfileRequest,
    user: Dict[str, Any] = Depends(get_current_user),
    store: UserStore = Depends(get_store),
):
    store.update_profile(user["id"], display_name=body.display_name)
    refreshed = store.get_user_by_id(user["id"])
    return _public_user(refreshed) if refreshed else user


@router.post("/verify-email")
@limiter.limit("10/minute")
async def verify_email(
    request: Request,
    body: AuthVerifyEmailRequest,
    store: UserStore = Depends(get_store),
):
    ok = store.consume_verification_token(body.user_id, body.token)
    if not ok:
        raise HTTPException(
            status_code=400, detail="Invalid or expired verification token"
        )
    return {"ok": True}


# --- cross-device sync (bearer-authenticated) --------------------------
@router.post("/sync/push")
async def sync_push(
    request: Request,
    body: SyncRequest,
    user: Dict[str, Any] = Depends(get_current_user),
    store: UserStore = Depends(get_store),
):
    counts: Dict[str, int] = {}
    payload: Dict[str, List[Dict[str, Any]]] = {
        "favorites": body.favorites,
        "scores": body.scores,
        "notes": body.notes,
        "lists": body.lists,
        "items": body.items,
    }
    for kind, rows in payload.items():
        if not rows:
            counts[kind] = 0
            continue
        counts[kind] = store.sync_push(user["id"], kind, rows)
    return {"counts": counts}


@router.get("/sync/pull")
async def sync_pull(
    request: Request,
    user: Dict[str, Any] = Depends(get_current_user),
    store: UserStore = Depends(get_store),
):
    return store.sync_pull_all(user["id"])
