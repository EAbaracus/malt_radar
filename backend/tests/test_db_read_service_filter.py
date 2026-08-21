import pytest
from app.services.db_read_service import DbReadService

@pytest.fixture
def service():
    # DbReadService relies on a sqlite connection in its real methods,
    # but _prepare_chip_filter is a pure string-building method that doesn't
    # touch the DB connection or its state, so we can test it directly.
    return DbReadService()

def test_prepare_chip_filter_empty_string(service):
    cond, params = service._prepare_chip_filter("")
    assert cond == "0"
    assert params == []

def test_prepare_chip_filter_whitespace(service):
    cond, params = service._prepare_chip_filter("   ,  ")
    assert cond == "0"
    assert params == []

def test_prepare_chip_filter_unknown_filter(service):
    cond, params = service._prepare_chip_filter("unknown_filter")
    assert cond == "0"
    assert params == []

def test_prepare_chip_filter_single_malt(service):
    cond, params = service._prepare_chip_filter("single malt")
    assert "LOWER(w.type) IN ('malt','single malt')" in cond
    assert "LOWER(w.name) LIKE '%single malt%'" in cond
    assert "LOWER(COALESCE(w.region,'')) IN ('islay','speyside','highland','campbeltown','lowland','islands')" in cond
    assert params == []

def test_prepare_chip_filter_blended(service):
    cond, params = service._prepare_chip_filter("blended")
    assert "LOWER(w.type) IN ('blend','blended')" in cond
    assert params == []

def test_prepare_chip_filter_bourbon(service):
    cond, params = service._prepare_chip_filter("bourbon")
    assert "LOWER(w.type) = 'bourbon'" in cond
    assert params == []

def test_prepare_chip_filter_rye(service):
    cond, params = service._prepare_chip_filter("rye")
    assert "LOWER(w.type) = 'rye'" in cond
    assert params == []

@pytest.mark.parametrize("region", [
    "speyside", "islay", "highland", "campbeltown", "lowland", "islands"
])
def test_prepare_chip_filter_regions(service, region):
    cond, params = service._prepare_chip_filter(region)
    assert "LOWER(COALESCE(w.region,'')) = ?" in cond
    assert params == [region]

@pytest.mark.parametrize("flavor, expected_keys", [
    ("peated", ["smoky", "peaty", "peat", "smoky_peaty"]),
    ("smoky", ["smoky", "peaty", "peat", "smoky_peaty"]),
    ("sherry", ["sherry", "oak", "cask", "woody", "oak_cask"]),
    ("sweet", ["sweet"]),
    ("fruity", ["fruity", "fruit"]),
])
def test_prepare_chip_filter_flavors(service, flavor, expected_keys):
    cond, params = service._prepare_chip_filter(flavor)

    # Check that each expected JSON extraction key is present in the condition
    for key in expected_keys:
        assert f"json_extract(fp.flavor_profile, '$.{key}')" in cond

    assert "> 1.0" in cond
    assert params == []

def test_prepare_chip_filter_case_insensitivity(service):
    cond1, params1 = service._prepare_chip_filter("SINGLE MALT")
    cond2, params2 = service._prepare_chip_filter("single malt")
    assert cond1 == cond2
    assert params1 == params2

    cond3, params3 = service._prepare_chip_filter("IsLaY")
    assert "LOWER(COALESCE(w.region,'')) = ?" in cond3
    assert params3 == ["islay"]

def test_prepare_chip_filter_multiple_filters(service):
    cond, params = service._prepare_chip_filter("single malt, islay, peated")

    # Check that all three conditions are joined by AND
    assert " AND " in cond

    # Check single malt part
    assert "LOWER(w.type) IN ('malt','single malt')" in cond

    # Check islay part
    assert "LOWER(COALESCE(w.region,'')) = ?" in cond
    assert params == ["islay"]

    # Check peated part
    assert "json_extract(fp.flavor_profile, '$.smoky')" in cond

def test_prepare_chip_filter_comma_separated_with_whitespace(service):
    cond, params = service._prepare_chip_filter("  bourbon  ,   rye   ")

    assert " AND " in cond
    assert "LOWER(w.type) = 'bourbon'" in cond
    assert "LOWER(w.type) = 'rye'" in cond
    assert params == []

def test_prepare_chip_filter_unknown_and_known_filter(service):
    # The logic sets recognized=True if ANY filter is recognized.
    # It only returns "0", [] if NO filter is recognized.
    # Let's verify how it behaves with one known and one unknown.
    cond, params = service._prepare_chip_filter("bourbon, unknown_junk")

    # Recognized gets set to True by 'bourbon', but 'unknown_junk' does not
    # add anything to `conds`.
    assert "LOWER(w.type) = 'bourbon'" in cond
    assert params == []
