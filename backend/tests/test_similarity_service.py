import json
import pytest
from app.services.similarity_service import SimilarityService


@pytest.fixture
def service():
    return SimilarityService()


def test_unknown_target_returns_none(service):
    assert service.get_similar("DOES-NOT-EXIST-999", limit=5) is None


def test_self_excluded_and_ordered(service):
    ids = service._candidate_profiles()
    assert len(ids) > 100, "full-pool bekleniyor, bounded havuz değil"
    target = next(iter(ids))
    result = service.get_similar(target, limit=5)
    assert result, "en az 1 benzer olmalı"
    assert len(result) <= 5
    assert all(r["whisky_id"] != target for r in result)
    distances = [r["distance"] for r in result]
    assert distances == sorted(distances)
    assert all(0.0 <= r["similarity"] <= 1.0 for r in result)


def test_full_pool_not_alphabetical_first_250(service):
    rows = service._all_active_whiskies()
    name_ordered = sorted(rows, key=lambda r: (r.get("name") or "").lower())
    first250 = {r["whisky_id"] for r in name_ordered[:250]}
    target = next(iter(service._candidate_profiles()))
    result = service.get_similar(target, limit=5)
    assert any(r["whisky_id"] not in first250 for r in result), \
        "benzerlik yalnızca alfabetik ilk 250 havuzundan geldi (bug)"


def test_no_profile_target_returns_empty(service):
    rows = service._all_active_whiskies()
    no_profile = [r for r in rows if not r.get("flavor_profile")]
    if no_profile:
        assert service.get_similar(no_profile[0]["whisky_id"], limit=5) == []
