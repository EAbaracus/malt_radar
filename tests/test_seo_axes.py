"""seo/axes.py birim testleri — canonical→app MAX-map (REVİZYON R1)."""
from seo.axes import parse_profile, map_to_app, active_axes, APP_AXES

def test_parse_json_and_keyval():
    assert parse_profile('{"fruity": 0.5}') == {"fruity": 0.5}
    assert parse_profile("fruity=0.5, sherry=0.8") == {"fruity": 0.5, "sherry": 0.8}
    assert parse_profile(None) == {}
    assert parse_profile("bozuk") == {}

def test_map_canonical_to_app_max():
    m = map_to_app({"smoky": 0.9, "peaty": 0.4, "peat": 0.2})
    assert m["smoky_peaty"] == 0.9  # MAX birleşimi
    m2 = map_to_app({"sherry": 1.5, "oak": 0.3, "woody": 0.2})
    assert m2["oak_cask"] == 1.5
    m3 = map_to_app({"fruit": 0.6, "spice": 0.7, "floral": 0.2, "malty": 0.8})
    assert m3["fruity"] == 0.6 and m3["spicy"] == 0.7
    assert m3["floral_herbal"] == 0.2 and m3["malty_cereal"] == 0.8

def test_maritime_passthrough_and_app_keys():
    m = map_to_app({"maritime": 0.9})
    assert m["maritime"] == 0.9
    m2 = map_to_app({"fruity": 0.8, "sweet": 0.6, "oak_cask": 0.5})
    assert m2["fruity"] == 0.8 and m2["sweet"] == 0.6 and m2["oak_cask"] == 0.5

def test_component_projection():
    m = map_to_app({"component_1": 0.5, "component_2": 0.5, "component_3": 0.5})
    assert m["fruity"] == 5.0 and m["spicy"] == 5.0 and m["smoky_peaty"] == 5.0
    assert m["maritime"] == 0.0  # R3: 8 eksen şeması

def test_active_axes_counts_mapped():
    # canonical keys: smoky+peaty->1 app ekseni, sherry->1, fruity->1 => 3 aktif
    assert active_axes('{"smoky": 0.9, "peaty": 0.3, "sherry": 0.7, "fruity": 0.4}') == 3
    assert active_axes('{"fruity": 0.0, "sweet": 0.0}') == 0
    assert active_axes("fruity=0.5, spice=0.6") == 2
    assert set(APP_AXES) == {"fruity", "sweet", "spicy", "smoky_peaty",
                              "oak_cask", "malty_cereal", "floral_herbal", "maritime"}
