"""Authentication and per-user sync for the Malt Radar API.

Scope notes:
- User data lives in a NEW database separate from `output/import/production.db`
  (which stays immutable / PromotionGate-only). The governed whisky data is
  never touched by auth.
- Passwords: PBKDF2-HMAC-SHA256 (stdlib only, no extra dependency).
- Sessions: opaque random bearer tokens, stored hashed (SHA-256).
- Transactional email is NOT wired here (no SMTP configured); email-verification
  tokens are printed to the server log for the receiver. Connecting an actual
  mail provider is a deploy-time step.
"""
