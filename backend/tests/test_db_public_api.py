from fastapi.testclient import TestClient
import os
from app.main import app

client = TestClient(app)

def test_public_whiskies_unauthenticated_200():
    os.environ["DB_API_ENABLED"] = "true"
    res = client.get("/api/db/public/whiskies")
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert len(data["items"]) <= 150

def test_public_evidence_route_not_found_404():
    # Route does not exist in public router (G4 Option A isolation)
    res = client.get("/api/db/public/whiskies/GSD-CAND-0001/evidence")
    assert res.status_code == 404

def test_public_price_history_route_not_found_404():
    res = client.get("/api/db/public/whiskies/GSD-CAND-0001/price-history")
    assert res.status_code == 404

def test_authenticated_router_requires_auth():
    # /api/db/whiskies remains protected when enabled
    os.environ["DB_API_ENABLED"] = "true"
    res = client.get("/api/db/whiskies")
    assert res.status_code == 401
