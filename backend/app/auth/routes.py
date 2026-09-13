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
import os
import smtplib
from email.message import EmailMessage
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request

from app.security import limiter
from app.auth.passwords import hash_password, verify_password
from app.auth.schemas import (
    AuthForgotPasswordRequest,
    AuthGoogleRequest,
    AuthLoginRequest,
    AuthRegisterRequest,
    AuthResetPasswordRequest,
    AuthUpdateProfileRequest,
    AuthVerifyEmailRequest,
    SyncRequest,
)
from app.auth.store import DuplicateEmailError, DuplicateIdentityError, UserStore
from app.auth.providers import (
    InvalidTokenError,
    OAuthIdentityVerifier,
    PROVIDER_VERIFIERS,
    TokenVerificationUnavailableError,
)

logger = logging.getLogger("malt_radar.auth")
router = APIRouter(prefix="/api/auth", tags=["auth"])


# --- dependencies -----------------------------------------------------
def get_store(request: Request) -> UserStore:
    store: Optional[UserStore] = getattr(request.app.state, "user_store", None)
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


def _send_email(email: str, subject: str, body: str, stub_tag: str) -> None:
    """Send one plain-text mail via SMTP when configured, else log a stub.

    Env (all optional; absent -> stub):
      MALT_RADAR_SMTP_HOST / _PORT / _USER / _PASS / _FROM
    A mail failure is logged and swallowed: it must never break the account
    flow that triggered it.
    """
    host = os.getenv("MALT_RADAR_SMTP_HOST", "").strip()
    user = os.getenv("MALT_RADAR_SMTP_USER", "").strip()
    pw = os.getenv("MALT_RADAR_SMTP_PASS", "").strip()
    fr = os.getenv("MALT_RADAR_SMTP_FROM", user or "maltradar@gmail.com")
    port = int(os.getenv("MALT_RADAR_SMTP_PORT", "587") or "587")

    if not (host and user and pw):
        # Dev stub: the payload is logged so the flow is testable without SMTP.
        logger.info("EMAIL-STUB %s for %s: %s", stub_tag, email, body)
        return

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = fr
    msg["To"] = email
    msg.set_content(body)

    try:
        with smtplib.SMTP(host, port, timeout=20) as s:
            s.starttls()
            s.login(user, pw)
            s.send_message(msg)
        logger.info("EMAIL sent (%s) to %s", stub_tag, email)
    except Exception as e:  # noqa: BLE001 — never break the caller on mail failure
        logger.warning("EMAIL send failed for %s: %s", email, e)


def _send_verification_email(email: str, verify_url: str) -> None:
    """Email the address-verification link (24h validity)."""
    # A relative verify path ("/verify-email?…") is resolved against the app
    # origin so the email carries a clickable absolute link.
    if verify_url.startswith("/"):
        origin = os.getenv("MALT_RADAR_APP_URL", "").rstrip("/")
        if origin:
            verify_url = f"{origin}{verify_url}"

    subject = "Malt Radar – E-posta adresinizi doğrulayın"
    body = (
        "Merhaba,\n\n"
        "Malt Radar hesabınız için e-posta adresinizi doğrulamak üzere "
        "aşağıdaki bağlantıya tıklayın (24 saat geçerlidir):\n\n"
        f"{verify_url}\n\n"
        "Bu isteği siz yapmadıysanız bu e-postayı yok sayın.\n"
        "Saygılar,\nMalt Radar"
    )
    _send_email(email, subject, body, "verify url")


def _send_reset_code_email(email: str, code: str) -> None:
    """Email a 6-digit password-reset code (15 min validity).

    The code is sent in the body only; it is never put in a URL, so it cannot
    leak through referrers, browser history, or server access logs.
    """
    subject = "Malt Radar – Şifre sıfırlama kodunuz"
    body = (
        "Merhaba,\n\n"
        "Malt Radar hesabınız için şifre sıfırlama kodunuz:\n\n"
        f"    {code}\n\n"
        "Kod 15 dakika geçerlidir ve yalnızca bir kez kullanılabilir.\n"
        "Kodu uygulamadaki 'Şifremi unuttum' ekranına girin.\n\n"
        "Bu isteği siz yapmadıysanız bu e-postayı yok sayın; şifreniz "
        "değişmez.\n"
        "Saygılar,\nMalt Radar"
    )
    _send_email(email, subject, body, "reset code")


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


# --- social login -------------------------------------------------------
def _get_verifier(request: Request) -> OAuthIdentityVerifier:
    """Resolve the provider verifier with DI override support.

    Tests set ``app.state.google_verifier`` to a fake; production falls back
    to the registered provider verifier. The registry holds verifier CLASSES
    (importing them is free); instantiate on demand so google-auth is only
    imported when a token is actually verified.
    """
    override = getattr(request.app.state, "google_verifier", None)
    if override is not None:
        return override
    return PROVIDER_VERIFIERS["google"]()


@router.post("/google")
@limiter.limit("8/minute")
async def google_login(
    request: Request,
    body: AuthGoogleRequest,
    store: UserStore = Depends(get_store),
):
    """Sign in (or sign up) with a Google id-token.

    Find-or-create + link:
      1. identity (google, sub) exists            -> reuse that user
      2. else email already registered            -> link identity to it
      3. else                                     -> create OAuth user
    Google only signs accounts with a verified email, but we still refuse
    tokens that claim otherwise. A single 401 (no enumeration) is returned
    for both invalid tokens and unverified emails.
    """
    verifier = _get_verifier(request)
    try:
        claims = verifier.verify_id_token(body.id_token)
    except InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid Google token")
    except TokenVerificationUnavailableError:
        # Provider unreachable (network/JWKS): not the client's fault.
        raise HTTPException(
            status_code=503, detail="verification_unavailable"
        )

    sub: Optional[str] = claims.get("sub")
    email: Optional[str] = claims.get("email")
    email_verified: Optional[Any] = claims.get("email_verified")
    if not sub or not email or not email_verified:
        raise HTTPException(status_code=401, detail="Invalid Google token")
    # Normalize before any lookup/insert so "User@Example.COM" can never
    # create a second account or a mismatched identity row.
    email = email.strip().lower()

    user = store.get_user_by_identity("google", sub)
    if user is None:
        user = store.get_user_by_email(email)
        if user is not None:
            # Merge: link the Google identity to the existing account. The
            # identity insert may itself lose a race (a concurrent request
            # linked this sub first) — then re-resolve by identity.
            try:
                store.create_identity(user["id"], "google", sub, email=email)
            except DuplicateIdentityError:
                logger.info(
                    "google identity %s:%s raced while linking; reusing existing user",
                    "google",
                    sub,
                )
                user = store.get_user_by_identity("google", sub)
                if user is None:
                    raise HTTPException(
                        status_code=409,
                        detail="Identity already exists but its user could not be resolved",
                    )
        else:
            try:
                user = store.create_oauth_user(
                    email=email,
                    provider="google",
                    provider_sub=sub,
                    display_name=claims.get("name"),
                    age_country="",
                    age_min=0,
                    privacy_consent=True,
                )
            except DuplicateIdentityError:
                # Race: a concurrent request with the same brand-new (google,
                # sub) already created the identity+user between our
                # get_user_by_identity check and this insert. That user IS the
                # authenticated principal — log in as them (idempotent), not
                # 409/500.
                logger.info(
                    "google identity %s:%s raced; reusing existing user", "google", sub
                )
                user = store.get_user_by_identity("google", sub)
                if user is None:
                    raise HTTPException(
                        status_code=409,
                        detail="Identity already exists but its user could not be resolved",
                    )
            except DuplicateEmailError:
                # Race: a concurrent request with the same email (but a
                # different sub) created the user between our
                # get_user_by_email check and this insert. That account IS the
                # authenticated principal — link this identity to it and log
                # in as them (idempotent), never 500.
                logger.info(
                    "google email %s raced; linking identity to existing user", email
                )
                existing = store.get_user_by_email(email)
                if existing is None:
                    raise HTTPException(
                        status_code=409,
                        detail="Email already registered but its user could not be resolved",
                    )
                try:
                    store.create_identity(
                        existing["id"], "google", sub, email=email
                    )
                except DuplicateIdentityError:
                    # A third concurrent request linked this sub first —
                    # resolve by identity; the user is the same either way.
                    existing = store.get_user_by_identity("google", sub)
                    if existing is None:
                        raise HTTPException(
                            status_code=409,
                            detail="Identity already exists but its user could not be resolved",
                        )
                user = existing
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


# --- password reset -----------------------------------------------------
# Two steps: request a code by email, then exchange email+code+new password.
# Both endpoints answer identically for known and unknown addresses so the API
# cannot be used to enumerate registered emails.
@router.post("/forgot-password")
@limiter.limit("5/minute")
async def forgot_password(
    request: Request,
    body: AuthForgotPasswordRequest,
    store: UserStore = Depends(get_store),
):
    user = store.get_user_by_email(body.email)
    if user is not None:
        code = store.create_reset_code(user["id"])
        _send_reset_code_email(user["email"], code)
    return {"ok": True}


@router.post("/reset-password")
@limiter.limit("10/minute")
async def reset_password(
    request: Request,
    body: AuthResetPasswordRequest,
    store: UserStore = Depends(get_store),
):
    user = store.get_user_by_email(body.email)
    # One generic failure for unknown email, wrong code, exhausted attempts and
    # expired code — the client learns nothing about which case it hit.
    if user is None or not store.consume_reset_code(user["id"], body.code):
        raise HTTPException(status_code=400, detail="Invalid or expired reset code")

    store.update_password_hash(user["id"], hash_password(body.new_password))
    # Any session minted before this reset may belong to whoever took the
    # account: drop them all so the new password is the only way in.
    store.delete_sessions_for_user(user["id"])
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
