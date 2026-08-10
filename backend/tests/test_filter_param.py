"""Test server-side catalog filtering via the `filter` query param.

Regression for the live bug where client-side `&filter=` was silently
swallowed by the backend: three requests with different filter values
returned the SAME result set (filter=peated == filter=bourbon == no filter).
With server-side filtering, different filters must return different sets,
and the flavor filters (Peated/Smoky/Sherry) must match against the
normalized app-axis profile (canonical keys mapped by A).
"""
import os

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(autouse=True)
def enable_db_api():
    old_val = os.environ.get("DB_API_ENABLED")
    os.environ["DB_API_ENABLED"] = "true"
    yield
    if old_val is None:
        os.environ.pop("DB_API_ENABLED", None)
    else:
        os.environ["DB_API_ENABLED"] = old_val


@pytest.fixture
def client():
    return TestClient(app)


def _names(items):
    return [i["name"] for i in items]


def test_filter_param_is_not_silently_swallowed(client):
    """Different filter values must return different result sets."""
    base = client.get("/api/db/whiskies?limit=50&offset=0").json()["items"]
    peated = client.get("/api/db/whiskies?limit=50&offset=0&filter=peated").json()["items"]
    sweet = client.get("/api/db/whiskies?limit=50&offset=0&filter=sweet").json()["items"]

    # All three return 200 with data
    assert len(base) > 0
    assert len(peated) > 0
    assert len(sweet) > 0

    # Filtered sets must differ from the unfiltered base (not identical replay)
    assert set(_names(peated)) != set(_names(base))
    assert set(_names(sweet)) != set(_names(base))
    # And from each other (a 'peated' vs 'sweet' set is expected to differ;
    # overlap is fine, exact equality is the bug being prevented)
    assert set(_names(peated)) != set(_names(sweet))


def test_filter_peated_matches_normalized_smoky_peaty(client):
    """Peated filter must return whiskies whose normalized profile has
    smoky_peaty > 1.0 — including canonical-key rows (smoky/peaty) that used
    to map to 0 and therefore matched nothing."""
    items = client.get("/api/db/whiskies?limit=50&offset=0&filter=peated").json()["items"]
    assert len(items) > 0
    for item in items:
        fp = item.get("flavor_profile")
        assert fp, "every filtered item must carry a flavor_profile"
        # The profile served by the API is already normalized to app axes
        import json
        prof = json.loads(fp)
        assert prof.get("smoky_peaty", 0) > 1.0


def test_filter_sherry_matches_normalized_oak_cask(client):
    """Sherry filter must match canonical sherry rows mapped to oak_cask."""
    items = client.get("/api/db/whiskies?limit=50&offset=0&filter=sherry").json()["items"]
    assert len(items) > 0
    import json
    for item in items:
        fp = item.get("flavor_profile")
        assert fp
        prof = json.loads(fp)
        assert prof.get("oak_cask", 0) > 1.0


def test_unknown_filter_returns_empty_not_error(client):
    """An unrecognized filter value is a no-match, not a 500."""
    resp = client.get("/api/db/whiskies?limit=50&offset=0&filter=doesnotexist")
    assert resp.status_code == 200
    assert resp.json()["items"] == []
