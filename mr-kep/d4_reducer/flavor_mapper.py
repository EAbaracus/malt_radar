"""FlavorMapper — canonical 7-axis staging->production promotion mapper.

Canonical contract (canonical_flavor_standard.md, frozen):
    smoky, peaty, fruity, sweet, spicy, maritime, sherry   (0-100 scale)

This mapper is the SINGLE authoritative descriptor->axis lexicon used by the
d4 reducer / promotion path. It MUST emit only the 7 canonical axis names.
Legacy/ambiguous descriptors (rich, complex, smooth, balanced, intense) are
handled upstream by AmbiguityHandler and are intentionally absent here.

P95B-FIX-02: added `maritime` (previously missing from this mapper) so the
promotion path preserves maritime evidence instead of dropping it.
"""
from __future__ import annotations


class FlavorMapper:
    def __init__(self):
        # 7-axis canonical mapping dictionary (descriptor -> canonical axis).
        self.mapping = {
            # smoky
            "smoke": "smoky", "smoky": "smoky", "bonfire": "smoky",
            "charred": "smoky", "ash": "smoky", "campfire": "smoky", "smolder": "smoky",
            # peaty
            "peat": "peaty", "peaty": "peaty", "medicinal": "peaty",
            "iodine": "peaty", "phenolic": "peaty", "earthy": "peaty", "moss": "peaty",
            # fruity
            "apple": "fruity", "pear": "fruity", "citrus": "fruity", "lemon": "fruity",
            "orange": "fruity", "tropical": "fruity", "berry": "fruity", "cherry": "fruity",
            "raisin": "fruity", "banana": "fruity",
            # sweet
            "honey": "sweet", "vanilla": "sweet", "caramel": "sweet", "toffee": "sweet",
            "sugar": "sweet", "syrup": "sweet", "cake": "sweet", "chocolate": "sweet",
            # spicy
            "cinnamon": "spicy", "pepper": "spicy", "clove": "spicy", "ginger": "spicy",
            "nutmeg": "spicy", "chili": "spicy", "spice": "spicy",
            # maritime  (P95B-FIX-02: added)
            "salt": "maritime", "brine": "maritime", "seaweed": "maritime",
            "coastal": "maritime", "sea": "maritime", "sea spray": "maritime",
            "marine": "maritime", "salty": "maritime", "ocean": "maritime",
            # sherry
            "sherry": "sherry", "oloroso": "sherry", "px": "sherry", "nutty": "sherry",
            "fig": "sherry", "dried fruit": "sherry", "port": "sherry",
        }

    def get_axis(self, descriptor):
        return self.mapping.get((descriptor or "").lower().strip())

    # Canonical axis set (kept in sync with canonical_flavor_standard.md).
    CANONICAL_AXES = ["smoky", "peaty", "fruity", "sweet", "spicy", "maritime", "sherry"]
