"""SimilarityService — tam katalog benzerlik (read-only).

Spec: docs/superpowers/specs/2026-08-16-similar-flavors-server-side-design.md
Normalize parity (G4): raw JSON -> DbReadService._normalize_flavor_profile
(canonical->app axes) -> Dart flavor_profile_normalizer.dart portu.
"""
import json
from typing import Any, Dict, List, Optional

from app.db.production_read_adapter import ProductionReadAdapter
from app.services.db_read_service import DbReadService

MALT_RADAR_AXES = ["fruity", "sweet", "spicy", "smoky_peaty",
                   "oak_cask", "malty_cereal", "floral_herbal"]


def _num_value(v: Any) -> float:
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v.strip())
        except ValueError:
            return 0.0
    return 0.0


def _scale(v: float) -> float:
    if v <= 0:
        return 0.0
    if v <= 1:
        return v * 10
    return v


def _has_whiskey_mapper_components(profile: Dict[str, Any]) -> bool:
    return all(f"component_{i}" in profile for i in (1, 2, 3))


def _dart_normalize(profile: Dict[str, Any]) -> Dict[str, float]:
    axis_profile: Dict[str, float] = {}
    has_axis_value = False
    for axis in MALT_RADAR_AXES:
        value = _num_value(profile.get(axis))
        axis_profile[axis] = value
        has_axis_value = has_axis_value or value > 0
    if has_axis_value:
        return axis_profile
    if _has_whiskey_mapper_components(profile):
        c1 = _num_value(profile.get("component_1"))
        c2 = _num_value(profile.get("component_2"))
        c3 = _num_value(profile.get("component_3"))
        return {
            "fruity": _scale(c1),
            "sweet": _scale((c1 + c2) / 2),
            "spicy": _scale(c2),
            "smoky_peaty": _scale(c3),
            "oak_cask": _scale((c2 + c3) / 2),
            "malty_cereal": _scale((c1 + c3) / 2),
            "floral_herbal": _scale(c1 * 0.5),
        }
    return axis_profile


class SimilarityService:
    def __init__(self, adapter: Optional[ProductionReadAdapter] = None):
        self._adapter = adapter or ProductionReadAdapter()

    def _all_active_whiskies(self) -> List[Dict[str, Any]]:
        sql = """
            SELECT w.whisky_id, w.name, w.original_name, w.distillery_id,
                   d.name AS distillery_name, w.region, w.type, w.country,
                   w.meta_critic_score, w.user_score, fp.flavor_profile
            FROM whiskies w
            LEFT JOIN distilleries d ON w.distillery_id = d.distillery_id
            LEFT JOIN flavor_profiles fp ON w.whisky_id = fp.whisky_id
            WHERE w.superseded_by IS NULL
              AND LOWER(w.name) NOT LIKE '%smws%'
              AND LOWER(COALESCE(w.brand, '')) NOT LIKE '%smws%'
        """
        with self._adapter.raw_connection() as conn:
            conn.row_factory = __import__("sqlite3").Row
            rows = [dict(r) for r in conn.execute(sql).fetchall()]
        return rows

    def _candidate_profiles(self) -> Dict[str, Dict[str, float]]:
        profiles = {}
        for row in self._all_active_whiskies():
            raw = row.get("flavor_profile")
            if not raw:
                continue
            try:
                app_axes = json.loads(
                    DbReadService._normalize_flavor_profile(raw) or "{}")
            except (json.JSONDecodeError, TypeError):
                continue
            if not isinstance(app_axes, dict):
                continue
            norm = _dart_normalize(app_axes)
            if any(v > 0 for v in norm.values()):
                profiles[row["whisky_id"]] = norm
        return profiles

    def get_similar(self, whisky_id: str, limit: int = 5) -> Optional[List[Dict[str, Any]]]:
        rows = self._all_active_whiskies()
        target_row = next((r for r in rows if r["whisky_id"] == whisky_id), None)
        if target_row is None:
            return None
        raw = target_row.get("flavor_profile")
        if not raw:
            return []
        try:
            target_norm = _dart_normalize(json.loads(
                DbReadService._normalize_flavor_profile(raw) or "{}"))
        except (json.JSONDecodeError, TypeError):
            return []
        if not any(v > 0 for v in target_norm.values()):
            return []
        scored = []
        for row in rows:
            wid = row["whisky_id"]
            if wid == whisky_id:
                continue
            raw_other = row.get("flavor_profile")
            if not raw_other:
                continue
            try:
                other_norm = _dart_normalize(json.loads(
                    DbReadService._normalize_flavor_profile(raw_other) or "{}"))
            except (json.JSONDecodeError, TypeError):
                continue
            if not any(v > 0 for v in other_norm.values()):
                continue
            dist = sum((target_norm[k] - other_norm[k]) ** 2
                       for k in target_norm if k in other_norm)
            item = {k: row[k] for k in (
                "whisky_id", "name", "original_name", "distillery_name",
                "region", "type", "country", "meta_critic_score", "user_score")}
            item["distance"] = round(dist, 6)
            item["similarity"] = round(1.0 / (1.0 + (dist ** 0.5)), 6)
            scored.append(item)
        scored.sort(key=lambda r: r["distance"])
        return scored[:limit]
