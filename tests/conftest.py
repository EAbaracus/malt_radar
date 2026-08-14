"""Shared pytest fixtures for the backend security tests.

Two responsibilities:
  1. Set the feature-flag + DB env vars *before* the app is imported, so the
     routers' flag checks see the intended values.
  2. An autouse fixture re-asserts the test API key before every test so that
     key-protected endpoints are reachable regardless of module import order
     or other tests mutating app.security.API_KEY.
"""
import os
import sys

# Ensure the backend package is importable.
_BACKEND = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend")
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

# Feature flags + DB path must be set before `app.main` is first imported.
os.environ.setdefault("DB_API_ENABLED", "true")
os.environ.setdefault("MALT_RADAR_DB_PATH", "output/import/production.db")
os.environ.setdefault("ADMIN_REVIEW_API_ENABLED", "true")
os.environ.setdefault("ADMIN_REVIEW_WRITE_ENABLED", "false")
os.environ.setdefault("ADMIN_REVIEW_PROMOTION_ENABLED", "false")

import app.security as _security

import pytest

TEST_API_KEY = "test-api-key"


@pytest.fixture(autouse=True)
def _configure_test_api_key():
    _security.API_KEY = TEST_API_KEY
    yield
    _security.API_KEY = TEST_API_KEY
