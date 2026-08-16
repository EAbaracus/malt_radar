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
    assert 1 <= len(body["similar"]) <= 5  # vacuous-pass koruması: boş liste fail etmeli
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


def test_similar_unknown_target_404():
    os.environ["DB_API_ENABLED"] = "true"
    res = client.get("/api/db/public/whiskies/DOES-NOT-EXIST-999/similar")
    assert res.status_code == 404


def test_similar_non_allowlist_active_target_200():
    """G1 REV: aktif (non-superseded) her hedef çalışır — allowlist dışı dahil."""
    os.environ["DB_API_ENABLED"] = "true"
    from app.services.similarity_service import SimilarityService
    svc = SimilarityService()
    rows = svc._all_active_whiskies()
    non_allow = [
        r["whisky_id"] for r in rows
        if r["whisky_id"] not in ALLOWLIST and r.get("flavor_profile")
    ]
    assert non_allow, "allowlist dışı aktif profilli hedef bekleniyor (veri kontrolü)"
    res = client.get(f"/api/db/public/whiskies/{non_allow[0]}/similar?limit=5")
    assert res.status_code == 200
    body = res.json()
    assert len(body["similar"]) >= 1
    for item in body["similar"]:
        assert item["whisky_id"] != non_allow[0]


def test_similar_regression_full_pool():
    """Benzer sonuçlar allowlist'e hapsolmamış (G1 tam havuz) — bug regresyonu.

    Public /whiskies allowlist (N=150) ile sınırlıdır; /similar sonuçları
    allowlist dışı viskilerden geliyorsa tam havuz çalışıyor demektir.
    (Eski client bug'ı: benzerlik yalnızca alfabetik ilk dilim/allowlist
    içinde hesaplanıyordu -> yalnızca A/B harfli sonuçlar.)
    """
    os.environ["DB_API_ENABLED"] = "true"
    target = _pick_target()
    res = client.get(f"/api/db/public/whiskies/{target}/similar?limit=5")
    similar_ids = {i["whisky_id"] for i in res.json()["similar"]}
    public_set = set()
    for p in range(5):
        page = client.get(f"/api/db/public/whiskies?limit=50&offset={p*50}").json()
        public_set |= {i["whisky_id"] for i in page["items"]}
    assert similar_ids - public_set, "benzerlik sonuçları allowlist'e hapsolmuş (bug)"


def test_similar_limit_bounds():
    os.environ["DB_API_ENABLED"] = "true"
    target = _pick_target()
    assert client.get(f"/api/db/public/whiskies/{target}/similar?limit=0").status_code == 422
    assert client.get(f"/api/db/public/whiskies/{target}/similar?limit=21").status_code == 422
    # Geçerli sınır: limit=20 -> 200
    res = client.get(f"/api/db/public/whiskies/{target}/similar?limit=20")
    assert res.status_code == 200
    assert len(res.json()["similar"]) <= 20
