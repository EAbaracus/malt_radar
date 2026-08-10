"""seo/axes.py — canonical→app eksen haritalaması (REVİZYON R1).

Backend DbReadService._map_canonical_to_app_axes aynası (db_read_service.py:156-201).
stdlib-only; backend ile senkron tutulur (parity riski: backend güncellenirse buraya da işlenmeli).
8 app ekseni: fruity, sweet, spicy, smoky_peaty, oak_cask, malty_cereal, floral_herbal, maritime.
"""
import json

APP_AXES = ["fruity", "sweet", "spicy", "smoky_peaty", "oak_cask",
            "malty_cereal", "floral_herbal", "maritime"]


def parse_profile(raw) -> dict:
    """JSON dict veya key=val string formunu dict'e çevirir (backend aynası)."""
    if not raw:
        return {}
    text = raw.strip() if isinstance(raw, str) else str(raw)
    if text.startswith("{"):
        try:
            obj = json.loads(text)
            return obj if isinstance(obj, dict) else {}
        except (json.JSONDecodeError, ValueError):
            return {}
    axes: dict = {}
    for part in text.split(","):
        if "=" not in part:
            continue
        key, _, val = part.partition("=")
        try:
            axes[key.strip().lower()] = float(val.strip())
        except ValueError:
            pass
    return axes


def map_to_app(axes: dict) -> dict:
    """Canonical/raw dict'i 8 app eksenine MAX-map'ler (backend aynası)."""
    def g(k: str) -> float:
        try:
            return float(axes.get(k, 0.0) or 0.0)
        except (TypeError, ValueError):
            return 0.0

    # Whiskey-Mapper component formu — kendi projeksiyonu (backend ile aynı)
    if "component_1" in axes and "component_2" in axes and "component_3" in axes:
        c1, c2, c3 = g("component_1"), g("component_2"), g("component_3")

        def scale(v: float) -> float:
            if v <= 0:
                return 0.0
            return v * 10 if v <= 1 else v

        return {
            "fruity": scale(c1),
            "sweet": scale((c1 + c2) / 2),
            "spicy": scale(c2),
            "smoky_peaty": scale(c3),
            "oak_cask": scale((c2 + c3) / 2),
            "malty_cereal": scale((c1 + c3) / 2),
            "floral_herbal": scale(c1 * 0.5),
        }

    return {
        "fruity": max(g("fruity"), g("fruit")),
        "sweet": g("sweet"),
        "spicy": max(g("spicy"), g("spice")),
        "smoky_peaty": max(g("smoky_peaty"), g("smoky"), g("peaty"), g("peat")),
        "oak_cask": max(g("oak_cask"), g("sherry"), g("oak"), g("cask"), g("woody")),
        "malty_cereal": max(g("malty_cereal"), g("malty")),
        "floral_herbal": max(g("floral_herbal"), g("floral")),
        "maritime": g("maritime"),
    }


def active_axes(raw) -> int:
    """Map'lenmiş profilde değeri >0 olan app ekseni sayısı."""
    return sum(1 for v in map_to_app(parse_profile(raw)).values() if v > 0)
