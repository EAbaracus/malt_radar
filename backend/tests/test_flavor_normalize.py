"""Test canonical → app-axes flavor profile normalization.

Canonical pipeline keys (smoky, peaty, sherry, woody, maritime) must map onto
the Flutter app's 7-axis vocabulary (smoky_peaty, oak_cask, malty_cereal,
floral_herbal, fruity, sweet, spicy) so client-side filters (Peated, Smoky,
Sherry) match real production data. Regression for the live bug where those
filters returned 0 matches because the backend passed canonical-key JSON
through unchanged while the frontend only reads app axes.
"""
import json

import pytest

from app.services.db_read_service import DbReadService


@pytest.fixture
def service():
    return DbReadService()


# --- Real production values as fixtures (canonical-key JSON) ----------------

def test_canonical_smoky_and_peaty_map_to_smoky_peaty(service):
    # W001097-style canonical profile: smoky + peaty present, no smoky_peaty.
    raw = json.dumps({
        "smoky": 10.0, "peaty": 10.0, "sherry": 10.0,
        "fruity": 10.0, "spicy": 10.0, "sweet": 10.0, "rich": 10.0,
    })
    normalized = json.loads(service._normalize_flavor_profile(raw))

    assert normalized["smoky_peaty"] == pytest.approx(10.0)
    # Peated filter uses `smoky_peaty > 1.0`
    assert normalized["smoky_peaty"] > 1.0


def test_canonical_smoky_only_maps_to_smoky_peaty(service):
    # W000559-style: smoky present (low value), no peaty, no smoky_peaty.
    raw = json.dumps({
        "sherry": 1.5, "spicy": 0.5, "oak_cask": 0.5,
        "fruity": 0.34, "smoky": 0.25, "sweet": 1.98, "malty_cereal": 0.5,
    })
    normalized = json.loads(service._normalize_flavor_profile(raw))

    assert normalized["smoky_peaty"] == pytest.approx(0.25)


def test_canonical_sherry_maps_to_oak_cask(service):
    # W000318-style: sherry present, no oak_cask key.
    raw = json.dumps({
        "sherry": 0.25, "fruity": 0.62, "maritime": 0.12,
        "sweet": 0.88, "malty_cereal": 1.0,
    })
    normalized = json.loads(service._normalize_flavor_profile(raw))

    assert normalized["oak_cask"] == pytest.approx(0.25)


def test_canonical_sherry_merges_with_existing_oak_cask(service):
    # sherry AND oak_cask both present -> take the max (matches key=val rule).
    raw = json.dumps({
        "sherry": 1.5, "oak_cask": 2.0, "spicy": 0.5,
        "fruity": 0.34, "sweet": 1.98,
    })
    normalized = json.loads(service._normalize_flavor_profile(raw))

    assert normalized["oak_cask"] == pytest.approx(2.0)


def test_app_axes_profile_passes_through_unchanged(service):
    # W000441-style: already app-axis JSON must NOT be zeroed by the mapping.
    raw = json.dumps({
        "fruity": 0.0, "sweet": 9.0, "spicy": 0.0, "smoky_peaty": 2.0,
        "oak_cask": 1.0, "floral_herbal": 0.0, "malty_cereal": 7.0,
    })
    normalized = json.loads(service._normalize_flavor_profile(raw))

    assert normalized["smoky_peaty"] == pytest.approx(2.0)
    assert normalized["oak_cask"] == pytest.approx(1.0)
    assert normalized["sweet"] == pytest.approx(9.0)


def test_canonical_woody_maps_to_oak_cask(service):
    # W000080-style: woody present, no oak_cask, no sherry.
    raw = json.dumps({
        "smoky": 0.1667, "sherry": 0.0, "fruity": 0.0, "sweet": 0.0,
        "spicy": 0.0, "maritime": 0.0833, "woody": 1.0,
    })
    normalized = json.loads(service._normalize_flavor_profile(raw))

    assert normalized["oak_cask"] == pytest.approx(1.0)


def test_output_always_has_all_app_axes(service):
    raw = json.dumps({"smoky": 1.0, "sherry": 2.0})
    normalized = json.loads(service._normalize_flavor_profile(raw))

    expected = {
        "fruity", "sweet", "spicy", "smoky_peaty",
        "oak_cask", "malty_cereal", "floral_herbal",
    }
    assert expected.issubset(normalized.keys())
