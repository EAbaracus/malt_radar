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
    """Project an app-axis dict onto the 7 Malt Radar axes (Dart-port parity).

    The Whiskey-Mapper `component_1/2/3` branch below looks dead on the current
    path: `DbReadService._normalize_flavor_profile` already projects those rows
    onto app axes before this function runs, so it never fires in production
    today. It is kept deliberately as a byte-for-byte port of
    `flavor_profile_normalizer.dart` (G4 parity contract) and as a guard against
    a future backend-normalize change that would otherwise silently alter
    similarity scores.
    """
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
        """Return all active whiskies (superseded/SMWS filtered) with profiles.

        One full read of the active catalog. `get_similar` and
        `_candidate_profiles` both build on this so a single request never
        re-reads the DB.
        """
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
            GROUP BY w.whisky_id
        """
        with self._adapter.raw_connection() as conn:
            rows = [dict(r) for r in conn.execute(sql).fetchall()]
        return rows

    def _build_profiles(self, rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
        """Normalize + filter rows into ``{whisky_id: 7-axis norm}``.

        Single normalize path shared by ``_candidate_profiles`` (kept for tests)
        and ``get_similar``. Rows without a usable profile — missing raw JSON,
        unparseable JSON, or all-zero axes — are skipped.
        """
        profiles: Dict[str, Dict[str, float]] = {}
        for row in rows:
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

    def _candidate_profiles(self) -> Dict[str, Dict[str, float]]:
        """Compatibility alias: full active-pool profiles (used by tests)."""
        return self._build_profiles(self._all_active_whiskies())

    def get_similar(self, whisky_id: str, limit: int = 5) -> Optional[List[Dict[str, Any]]]:
        """Return the ``limit`` most similar whiskies to ``whisky_id``.

        Full active-pool scan ordered by squared 7-axis Euclidean distance;
        similarity is ``1 / (1 + sqrt(distance))`` (identical to the Flutter
        client). Returns ``None`` when ``whisky_id`` is not in the active pool
        (superseded or SMWS-filtered), and ``[]`` when it has no usable profile.
        """
        # Clamp: negative/zero limits previously produced a buggy slice (e.g.
        # rows[:-1] when limit was negative); cap at 20 to bound response size.
        limit = max(1, min(int(limit), 20))
        rows = self._all_active_whiskies()
        row_by_id = {r["whisky_id"]: r for r in rows}
        if whisky_id not in row_by_id:
            return None
        profiles = self._build_profiles(rows)
        target_norm = profiles.get(whisky_id)
        if target_norm is None:
            return []
        scored = []
        for wid, other_norm in profiles.items():
            if wid == whisky_id:
                continue
            dist = sum((target_norm[k] - other_norm[k]) ** 2
                       for k in target_norm if k in other_norm)
            row = row_by_id[wid]
            item = {k: row[k] for k in (
                "whisky_id", "name", "original_name", "distillery_name",
                "region", "type", "country", "meta_critic_score", "user_score")}
            item["distance"] = round(dist, 6)
            item["similarity"] = round(1.0 / (1.0 + (dist ** 0.5)), 6)
            scored.append(item)
        scored.sort(key=lambda r: r["distance"])
        return scored[:limit]
