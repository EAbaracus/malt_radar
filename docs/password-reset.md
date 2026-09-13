# Password reset (6-digit code)

Added because the app offered no "forgot password" path: a user who lost the
password had no way back into their own account.

## Flow

```
AuthScreen (login)
  └─ "Şifremi unuttum"  ──►  mode: forgot   (email only, no password field)
        POST /api/auth/forgot-password {email}     rate 5/min
          └─ 200 {ok:true} ALWAYS (registered or not)
              └─  mode: reset   (code + new password + confirm)
                    POST /api/auth/reset-password {email, code, new_password}
                      └─ 200 {ok:true} → mode: login, local session cleared
```

The code is **emailed, never put in a URL** — so it cannot leak through
referrers, browser history, or access logs. This is also why the flow has no
deep-link/landing-page dependency: the existing email-verification link
(`/verify-email?user_id=…&token=…`) has no consumer route in the app, and
copying that pattern would have shipped a reset link nobody could click.

## Security properties (and why each exists)

| Property | Why |
|---|---|
| TTL 15 minutes (`RESET_TTL_MINUTES`) | a 6-digit code is brute-forceable; exposure time is a defence |
| Max 5 wrong tries, then the code is destroyed (`RESET_MAX_ATTEMPTS`) | bounds guessing to 5 tries per 15 min window |
| One active code per user (`user_id` is the PRIMARY KEY) | a new request invalidates the old code instead of leaving several live |
| `secrets.compare_digest` on the hash | constant-time comparison |
| Only the sha256 hash is stored | same posture as sessions/verification tokens |
| Generic `400 Invalid or expired reset code` for unknown email, wrong code, exhausted attempts, expired code | no account enumeration, no oracle for which branch failed |
| `forgot-password` returns `{ok:true}` for unknown addresses too | no account enumeration |
| **All sessions deleted on success** (`delete_sessions_for_user`) | a session minted before the reset may belong to whoever took the account |
| Password policy reused from register (min 8) | a reset must not be a way to weaken the account |
| Client clears its local session after success | the stored token is dead server-side; keeping it would leave the app "logged in" with a dead credential |

Not defended, deliberately: an offline brute force of the code hash from a stolen
`users.db`. That dump already contains password hashes, so it is not the boundary
this feature defends — the live-guessing bound is.

## Mail

Reuses the existing SMTP path (`MALT_RADAR_SMTP_*`) via a shared
`_send_email(to, subject, body, stub_tag)`. When SMTP is unconfigured the code
goes to the server log (`EMAIL-STUB reset code for …`), which is what makes the
flow testable in dev. A mail failure is logged and swallowed — it never breaks
the request (same rule as registration).

## Files

- `backend/app/auth/store.py` — `password_resets` table, `create_reset_code`,
  `consume_reset_code`, `update_password_hash`, `delete_sessions_for_user`
- `backend/app/auth/schemas.py` — `AuthForgotPasswordRequest`,
  `AuthResetPasswordRequest`
- `backend/app/auth/routes.py` — `_send_email` refactor,
  `_send_reset_code_email`, `POST /forgot-password`, `POST /reset-password`
- `frontend/lib/core/api/auth_api.dart` — `forgotPassword`, `resetPassword`
- `frontend/lib/features/auth/presentation/auth_controller.dart` —
  `requestPasswordReset`, `confirmPasswordReset`
- `frontend/lib/features/auth/presentation/auth_screen.dart` —
  `AuthMode.forgot` + `AuthMode.reset`, entry link, per-step fields/labels
- Tests: `backend/tests/test_password_reset.py` (15),
  `frontend/test/features/auth/password_reset_test.dart` (9)

## Known gap (pre-existing, not introduced here)

Email **verification** still emails a link (`/verify-email?user_id&token`) whose
POST endpoint has no in-app consumer route, so clicking it most likely does not
verification. Confirmed by source inspection only (no `verify-email` route in
`frontend/lib`, no page in `frontend/web`); needs a live check before changing.
Left as-is: out of scope for this change, and the reset flow deliberately does
not depend on that mechanism.
