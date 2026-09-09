"""Whiskey-Mapper component rows must not render as radar profiles.

`component_1/2/3` are scatter-plot coordinates from `whiskey_scatter.json`,
not axis intensities. Projecting them onto the 7 display axes makes four of
the seven axes linear combinations of the other three, so neighbouring
whiskies get visually identical radars and unpeated bottlings get high
smoky_peaty values.

Display callers must therefore receive None. The similarity path keeps the
projection (the coordinates are the correct input for a distance metric) and
its output must not change.
"""

import json

from app.services.db_read_service import DbReadService

# Real production row (Aberlour 12yo Double Cask Matured, W000352).
COMPONENT_ROW = json.dumps(
    {
        "component_1": "0.4514262490991952",
        "component_2": "0.14099178775965848",
        "component_3": "0.4711033245498027",
    }
)

# Real production row (Aberlour 18yo, W000195) in canonical axis form.
CANONICAL_ROW = json.dumps(
    {
        "fruity": 1.29,
        "sweet": 3.15,
        "spicy": 1.33,
        "smoky": 1.46,
        "peaty": 0.9,
        "sherry": 3.31,
        "malty": 4.31,
        "floral": 0.38,
        "maritime": 0.08,
    }
)


def test_component_row_is_suppressed_on_display_path():
    assert DbReadService._normalize_flavor_profile(COMPONENT_ROW) is None


def test_component_row_still_projects_for_similarity():
    out = DbReadService._normalize_flavor_profile(
        COMPONENT_ROW, allow_component_projection=True
    )
    assert out is not None
    axes = json.loads(out)
    # Historical projection preserved byte-for-byte: four axes stay linear
    # combinations of the three components.
    assert axes["fruity"] == 4.514262490991952
    assert axes["spicy"] == 1.4099178775965848
    assert axes["smoky_peaty"] == 4.711033245498027
    assert axes["floral_herbal"] == axes["fruity"] / 2


def test_canonical_row_is_unaffected():
    axes = json.loads(DbReadService._normalize_flavor_profile(CANONICAL_ROW))
    assert axes["fruity"] == 1.29
    assert axes["smoky_peaty"] == 1.46  # max(smoky, peaty)
    assert axes["oak_cask"] == 3.31  # sherry -> oak_cask
    assert axes["malty_cereal"] == 4.31
    assert axes["floral_herbal"] == 0.38
    assert axes["maritime"] == 0.08


def test_canonical_row_floral_is_not_half_of_fruity():
    """The component-projection signature must not appear on real rows."""
    axes = json.loads(DbReadService._normalize_flavor_profile(CANONICAL_ROW))
    assert axes["floral_herbal"] != axes["fruity"] / 2


def test_empty_and_all_zero_profiles_are_suppressed():
    """`{}` / `[]` / all-zero rows must not render as a flat radar.

    Production holds 791 `{}` rows, 25 `[]` rows and 72 stored all-zero rows.
    Before this guard each of them mapped to a full zero vector, which is
    non-null and therefore drew an identical empty heptagon for ~888 whiskies.
    """
    for raw in ("{}", "[]", '{"smoky_peaty":0.0,"fruity":0.0,"sweet":0.0}'):
        assert DbReadService._normalize_flavor_profile(raw) is None, raw


def test_single_axis_profile_still_renders():
    """Suppression must not swallow a sparse but real profile."""
    out = DbReadService._normalize_flavor_profile('{"smoky":0,"peaty":100,"fruity":0}')
    assert out is not None
    assert json.loads(out)["smoky_peaty"] == 100.0
