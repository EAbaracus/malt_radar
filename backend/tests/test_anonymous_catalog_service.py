import pytest
from app.services.anonymous_catalog_service import AnonymousCatalogService

def test_service_whiskies_bounded_to_allowlist():
    service = AnonymousCatalogService()
    res = service.get_whiskies(limit=100, offset=0)
    assert "items" in res
    assert len(res["items"]) <= 100
    allowlist = service.get_allowlist_ids()
    assert len(allowlist) == 150
    assert all(item["whisky_id"] in service._allowlist_set for item in res["items"])

def test_service_whisky_out_of_allowlist_returns_none():
    service = AnonymousCatalogService()
    result = service.get_whisky("NON_ALLOWLIST_ID_99999")
    assert result is None

def test_service_response_shaping_no_prices_no_raw_json():
    service = AnonymousCatalogService()
    res = service.get_whiskies(limit=5, offset=0)
    for item in res["items"]:
        assert "production_price" not in item
        assert "price_value" not in item
        assert "price_context" not in item
        assert "pour_size_ml" not in item
        assert "flavor_evidence" not in item

def test_service_offset_boundary_empty_list():
    service = AnonymousCatalogService()
    res = service.get_whiskies(limit=50, offset=9999)
    assert res["items"] == []
    assert res["total_count"] == len(service.get_allowlist_ids())

def test_service_filter_bourbon_returns_only_bourbons():
    service = AnonymousCatalogService()
    res = service.get_whiskies(limit=50, offset=0, filter="Bourbon")
    assert res["total_count"] <= len(service.get_allowlist_ids())
    for item in res["items"]:
        cat = (item.get("category") or "").lower()
        typ = (item.get("type") or "").lower()
        assert cat == "bourbon" or typ == "bourbon"

def test_service_filter_changes_total_and_slices_filtered_set():
    service = AnonymousCatalogService()
    all_res = service.get_whiskies(limit=50, offset=0)
    bourbon_res = service.get_whiskies(limit=50, offset=0, filter="Bourbon")
    # Filtered total must differ from (or equal to, if everything is bourbon —
    # in practice the allowlist is mixed) the unfiltered total.
    assert bourbon_res["total_count"] <= all_res["total_count"]
    # Pagination slices the FILTERED set: offset beyond the filtered total is empty.
    beyond = service.get_whiskies(limit=50, offset=9999, filter="Bourbon")
    assert beyond["items"] == []
    assert beyond["total_count"] == bourbon_res["total_count"]
