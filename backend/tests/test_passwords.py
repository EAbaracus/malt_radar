import pytest
import base64
from app.auth.passwords import hash_password, verify_password

def test_password_hash_and_verify():
    password = "supersecretpassword"
    hashed = hash_password(password)

    # It should verify correctly
    assert verify_password(password, hashed) is True

    # Wrong password should fail
    assert verify_password("wrongpassword", hashed) is False

def test_hash_password_invalid_input():
    with pytest.raises(ValueError, match="password must be a non-empty string"):
        hash_password("")

    with pytest.raises(ValueError, match="password must be a non-empty string"):
        hash_password(None)

def test_verify_password_invalid_stored_format():
    # Doesn't split into 4 parts
    assert verify_password("password", "invalid$format") is False

    # Algo mismatch
    assert verify_password("password", "wrongalgo$1000$salt$hash") is False

    # Invalid iterations (not an int) (Triggers ValueError)
    assert verify_password("password", "pbkdf2_sha256$notanint$salt$hash") is False

def test_verify_password_invalid_base64():
    # Base64 decode will fail if it's not valid base64 (binascii.Error which is a subclass of ValueError)
    # Using invalid base64 characters
    assert verify_password("password", "pbkdf2_sha256$1000$salt!$hash") is False
    assert verify_password("password", "pbkdf2_sha256$1000$salt$hash!") is False

def test_verify_password_none_or_empty():
    assert verify_password("password", "") is False
    assert verify_password("password", None) is False

def test_verify_password_unpacking_value_error():
    # We can trigger ValueError when we unpack too many or too few values.
    assert verify_password("password", "pbkdf2_sha256$1000$salt") is False
    assert verify_password("password", "pbkdf2_sha256$1000$salt$hash$extra") is False


def test_verify_password_type_error_in_compare_digest(monkeypatch):
    hashed = hash_password("password")

    # We can mock compare_digest to raise TypeError
    import hmac
    def mock_compare_digest(a, b):
        raise TypeError("Mock TypeError")

    monkeypatch.setattr(hmac, "compare_digest", mock_compare_digest)

    assert verify_password("password", hashed) is False
