"""Password hashing with the standard library (PBKDF2-HMAC-SHA256).

Chosen over bcrypt/argon2 to keep the auth module dependency-free: the project
runtime has no vendored password hashing lib. NIST guidance for PBKDF2-HMAC:
>= 600k iterations is recommended for new deployments; 240k is a reasonable
default for a dev/local service and is configurable.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os

_ALGO = "pbkdf2_sha256"
_DEFAULT_ITERATIONS = 240_000
_SALT_BYTES = 16

_SCHEME_FORMAT = "{algo}${iterations}${salt}${digest}"


def hash_password(password: str, iterations: int = _DEFAULT_ITERATIONS) -> str:
    """Return a self-describing hash string for a password."""
    if not isinstance(password, str) or not password:
        raise ValueError("password must be a non-empty string")
    salt = os.urandom(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, iterations
    )
    return _SCHEME_FORMAT.format(
        algo=_ALGO,
        iterations=iterations,
        salt=base64.b64encode(salt).decode("ascii"),
        digest=base64.b64encode(digest).decode("ascii"),
    )


def verify_password(password: str, stored: str) -> bool:
    """Constant-time comparison against a stored hash string."""
    if not stored:
        return False
    try:
        algo, it_s, salt_b64, digest_b64 = stored.split("$")
        if algo != _ALGO:
            return False
        iterations = int(it_s)
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(digest_b64)
        candidate = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, iterations
        )
        return hmac.compare_digest(candidate, expected)
    except (ValueError, TypeError):
        return False
