"""End-to-end: /api/db/public/whiskies/{id}/similar."""
import json
import os
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
ALLOWLIST = json.load(open("artifacts/anonymous_allowlist.json", encoding="utf-8"))["ids"]


def _pick_target():
    for wid in ALLOWLIST:
        r = client.get(f"/api/db/public/whiskies/{wid}/flavor-profile")
        if r.status_code == 200:
            return wid
    raise AssertionError("allowlist'te profilli hedef yok")


def test_similar_200_shaped_and_limited():
    os.environ["DB_API_ENABLED"] = "true"
    target = _pick_target()
    res = client.get(f"/api/db/public/whiskies/{target}/similar?limit=5")
    assert res.status_code == 200
    body = res.json()
    assert body["whisky_id"] == target
    assert len(body["similar"]) <= 5
    for item in body["similar"]:
        assert item["whisky_id"] != target
        assert "distance" in item and "similarity" in item
        assert "production_price" not in item and "price_value" not in item
        assert "flavor_profile" not in item


def test_similar_anon_no_auth():
    os.environ["DB_API_ENABLED"] = "true"
    target = _pick_target()
    res = client.get(f"/api/db/public/whiskies/{target}/similar")
    assert res.status_code == 200


def test_similar_non_allowlist_target_404():
    os.environ["DB_API_ENABLED"] = "true"
    res = client.get("/api/db/public/whiskies/NOT-IN-ALLOWLIST-1/similar")
    assert res.status_code == 404


def test_similar_regression_full_pool():
    os.environ["DB_API_ENABLED"] = "true"
    target = _pick_target()
    res = client.get(f"/api/db/public/whiskies/{target}/similar?limit=5")
    similar_ids = {i["whisky_id"] for i in res.json()["similar"]}
    first250 = set()
    for p in range(5):
        page = client.get(f"/api/db/public/whiskies?limit=50&offset={p*50}").json()
        first250 |= {i["whisky_id"] for i in page["items"]}
    assert similar_ids - first250, "benzerlik yalnızca alfabetik ilk 250 havuzu (bug)"


def test_similar_limit_bounds():
    os.environ["DB_API_ENABLED"] = "true"
    target = _pick_target()
    assert client.get(f"/api/db/public/whiskies/{target}/similar?limit=0").status_code == 422
    assert client.get(f"/api/db/public/whiskies/{target}/similar?limit=21").status_code == 422
