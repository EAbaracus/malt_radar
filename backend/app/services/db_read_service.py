import os
import sqlite3
import json
from typing import List, Dict, Any, Optional

from app.utils.source_guard import SourceGuard

# Certified pilot whiskies use the 'GSD-CAND-XXXX' whisky_id prefix and are
# flagged with data_confidence = 'certified'. The staging DB is the single
# source of truth for them; production.db is the default datasource.

CERTIFIED_PREFIX = "GSD-CAND-"

# Anti-scrape bounds (configurable via env; bulk-dump / deep-paging ceiling).
# The API never returns more than CATALOG_MAX_PAGE rows per page nor lets a
# client offset past CATALOG_MAX_OFFSET rows (blocks unbounded full-catalog
# replay through pagination).
CATALOG_MAX_PAGE = int(os.getenv("CATALOG_MAX_PAGE", "50"))
CATALOG_MAX_OFFSET = int(os.getenv("CATALOG_MAX_OFFSET", "10000"))


class CatalogBoundsError(ValueError):
    """Raised when a read would exceed the catalog browse bounds."""


def _clamp_page(limit: int) -> int:
    return min(max(1, int(limit)), CATALOG_MAX_PAGE)


def _check_offset(offset: int, limit: int) -> int:
    offset = max(0, int(offset))
    if offset > CATALOG_MAX_OFFSET or offset + limit > CATALOG_MAX_OFFSET + CATALOG_MAX_PAGE:
        raise CatalogBoundsError(
            f"offset beyond catalog browse limit (max {CATALOG_MAX_OFFSET})"
        )
    return offset


class DbReadService:
    def __init__(self):
        # Default to output/import/production.db relative to the project root.
        # Staging (or any other datasource) is selected entirely through the
        # MALT_RADAR_DB_PATH environment variable -- no source code change needed.
        default_db = "output/import/production.db"
        env_db = os.getenv("MALT_RADAR_DB_PATH", default_db)

        # Resolve to absolute path if necessary
        if not os.path.isabs(env_db):
            # Assume project root is 3 levels up from this file
            # (backend/app/services/db_read_service.py)
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            self.db_path = os.path.abspath(os.path.join(base_dir, env_db))
        else:
            self.db_path = env_db

    def _get_connection(self):
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Database not found at {self.db_path}")

        # Read-only explicitly
        uri = f"file:{self.db_path}?mode=ro"
        conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.row_factory = sqlite3.Row
        return conn

    def get_health(self) -> Dict[str, Any]:
        exists = os.path.exists(self.db_path)
        tables = ["distilleries", "whiskies", "tasting_notes", "flavor_profiles", "price_history"]
        VALID_TABLES = set(tables)
        counts = {}

        if exists:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    for t in tables:
                        if t not in VALID_TABLES:
                            continue
                        try:
                            cursor.execute(f"SELECT COUNT(*) as c FROM {t}")
                            counts[t] = cursor.fetchone()["c"]
                        except sqlite3.OperationalError:
                            counts[t] = 0
            except FileNotFoundError:
                exists = False

        return {
            "db_reachable": exists,
            "read_only": True,
            "counts": counts,
        }

    # ------------------------------------------------------------------
    # Flavor profile handling
    #
    # The DB stores flavor profiles in two shapes:
    #   * 7-axis JSON for normal whiskies: {"fruity":0.0, "sweet":9.0, ...}
    #   * "key=val, key=val" string for the 5 certified pilot rows
    #     (e.g. "smoky=70.0, peaty=70.0, ...", where 'maritime' exists but is
    #      not one of the app axes).
    #
    # The Flutter radar only understands the 7-axis vocabulary, so we always
    # emit the 7-axis JSON form. JSON is passed through unchanged; the
    # key=val form is mapped onto the 7 axes (maritime is dropped as it is
    # not an app axis). Stored values are never modified -- this is a
    # presentation-format adaptation only.
    # ------------------------------------------------------------------
    # The app (Flutter radar) receives a fixed 7-axis vocabulary. Maritime is a
    # canonical axis (canonical_flavor_standard.md frozen 7) and MUST be exposed to
    # clients; it is no longer dropped. smoky_peaty / oak_cask / malty_cereal /
    # floral_herbal are presentation merges/projections of canonical axes; maritime
    # is passed through directly. Stored values are never modified.
    APP_AXES = ["fruity", "sweet", "spicy", "smoky_peaty", "oak_cask", "malty_cereal", "floral_herbal", "maritime"]

    @staticmethod
    def _normalize_flavor_profile(raw: Any) -> Optional[str]:
        if not raw:
            return None

        text = raw.strip() if isinstance(raw, str) else str(raw)

        # JSON form: canonical-key dict (smoky/peaty/sherry/woody/...) or
        # already-app-axis dict. Both are mapped onto the app's 7-axis
        # vocabulary so client-side filters (Peated/Smoky/Sherry) match real
        # production data. Canonical -> app mapping table:
        #   smoky, peaty, peat      -> smoky_peaty        (combined via MAX)
        #   sherry, oak, cask, woody -> oak_cask          (combined via MAX)
        #   fruity/fruit            -> fruity; spicy/spice -> spicy
        #   floral                  -> floral_herbal; malty -> malty_cereal
        #   maritime                -> maritime (pass-through)
        # MAX is used (not average) so a strong single-axis signal is not
        # diluted — consistent with the historical key=val mapping below.
        # Unmapped keys (mineral, texture, rich, ...) are dropped.
        if text.startswith("{"):
            try:
                obj = json.loads(text)
            except (json.JSONDecodeError, ValueError):
                return None
            if isinstance(obj, dict):
                return DbReadService._map_canonical_to_app_axes(obj)

        # key=val, key=val, ... form (certified pilot rows).
        axes: Dict[str, float] = {}
        for part in text.split(","):
            if "=" not in part:
                continue
            key, _, val = part.partition("=")
            try:
                axes[key.strip().lower()] = float(val.strip())
            except ValueError:
                pass
        return DbReadService._map_canonical_to_app_axes(axes)

    @staticmethod
    def _map_canonical_to_app_axes(axes: Dict[str, float]) -> str:
        """Map a canonical/raw axis dict onto the app's 7-axis vocabulary.

        Stored values are never modified; this is a presentation-format
        adaptation only. See the mapping table in _normalize_flavor_profile.
        """
        def g(k: str) -> float:
            try:
                return float(axes.get(k, 0.0) or 0.0)
            except (TypeError, ValueError):
                return 0.0

        # Whiskey-Mapper component form (component_1/2/3) — pass through its
        # own projection so those 231 rows keep their radar shape.
        if "component_1" in axes and "component_2" in axes and "component_3" in axes:
            c1, c2, c3 = g("component_1"), g("component_2"), g("component_3")

            def scale(v: float) -> float:
                if v <= 0:
                    return 0.0
                if v <= 1:
                    return v * 10
                return v

            return json.dumps({
                "fruity": scale(c1),
                "sweet": scale((c1 + c2) / 2),
                "spicy": scale(c2),
                "smoky_peaty": scale(c3),
                "oak_cask": scale((c2 + c3) / 2),
                "malty_cereal": scale((c1 + c3) / 2),
                "floral_herbal": scale(c1 * 0.5),
            })

        mapped = {
            "fruity": max(g("fruity"), g("fruit")),
            "sweet": g("sweet"),
            "spicy": max(g("spicy"), g("spice")),
            "smoky_peaty": max(g("smoky_peaty"), g("smoky"), g("peaty"), g("peat")),
            "oak_cask": max(g("oak_cask"), g("sherry"), g("oak"), g("cask"), g("woody")),
            "malty_cereal": max(g("malty_cereal"), g("malty")),
            "floral_herbal": max(g("floral_herbal"), g("floral")),
            # Maritime is a canonical axis; pass it through (do NOT drop).
            "maritime": g("maritime"),
        }
        return json.dumps(mapped)

    def _flavor_profile_for(self, whisky_id: str) -> Optional[str]:
        """Return the normalized 7-axis flavor profile JSON for a whisky, or None."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT flavor_profile FROM flavor_profiles WHERE whisky_id = ?",
                (whisky_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return self._normalize_flavor_profile(row["flavor_profile"])

    def get_whiskies(self, limit: int = 50, offset: int = 0, q: Optional[str] = None, distillery_id: Optional[str] = None, filter: Optional[str] = None) -> Dict[str, Any]:
        limit = _clamp_page(limit)
        offset = _check_offset(offset, limit)

        query = """
            SELECT w.*, d.name as distillery_name, fp.flavor_profile as flavor_profile
            FROM whiskies w
            LEFT JOIN distilleries d ON w.distillery_id = d.distillery_id
            LEFT JOIN flavor_profiles fp ON w.whisky_id = fp.whisky_id
            WHERE w.superseded_by IS NULL
        """
        params = []

        if q and len(q.strip()) >= 2:
            query += " AND w.name LIKE ?"
            params.append(f"%{q.strip()}%")

        if distillery_id:
            query += " AND w.distillery_id = ?"
            params.append(distillery_id)

        # Server-side filter: translate chips into SQL conditions applied
        # BEFORE LIMIT/OFFSET so pagination slices the FILTERED set (filtering
        # after the DB query would scatter matches across page boundaries and
        # the client's short-page/empty-page detection would stop early).
        if filter:
            cond, fparams = self._prepare_chip_filter(filter)
            if cond:
                query += f" AND ({cond})"
                params.extend(fparams)

        query += " GROUP BY w.whisky_id"
        # Certified Gold Dataset rows (whisky_id LIKE 'GSD-CAND-%') are surfaced first.
        query += " ORDER BY CASE WHEN w.whisky_id LIKE 'GSD-CAND-%' THEN 0 ELSE 1 END, w.name ASC"
        query += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = [self._prepare_whisky(dict(row)) for row in cursor.fetchall()]

        return {
            "items": rows,
            "total_count": len(rows),
            "limit": limit,
            "offset": offset,
        }

    def _prepare_chip_filter(self, filter: str):
        """Translate a comma-separated chip list into (sql_cond, params).

        Chips are AND-ed together; the category/region/flavor vocab mirrors
        home_screen.dart. Flavor chips match the CANONICAL axis values via
        json_extract (the same MAX-combination the app-axis mapping uses:
        smoky_peaty=max(smoky,peaty), oak_cask=max(sherry,oak,cask,woody)),
        evaluated against the raw stored profile before normalization.
        Returns ('', []) when no chip is recognized.
        """
        wanted = [f.strip() for f in filter.split(",") if f.strip()]
        conds = []
        params: List[Any] = []
        recognized = False

        def json_axis(*keys: str) -> str:
            # MAX of COALESCE(json_extract(fp.flavor_profile, '$.k'), 0) over keys.
            # NOTE: a single-key MAX() would be parsed as an AGGREGATE by
            # SQLite (misuse of aggregate in WHERE); single key must stay a
            # plain COALESCE, multi-key uses scalar MAX(a, b, ...).
            parts = [f"COALESCE(json_extract(fp.flavor_profile, '$.{k}'), 0)" for k in keys]
            if len(parts) == 1:
                return parts[0]
            return "MAX(" + ", ".join(parts) + ")"

        for f in wanted:
            fl = f.lower()
            if fl == "single malt":
                conds.append(
                    "(LOWER(w.type) IN ('malt','single malt')"
                    " OR LOWER(w.category) = 'single malt'"
                    " OR (LOWER(w.category) = 'scotch' AND LOWER(w.type) = 'malt')"
                    " OR LOWER(w.name) LIKE '%single malt%'"
                    " OR LOWER(COALESCE(w.region,'')) IN ('islay','speyside','highland','campbeltown','lowland','islands'))"
                )
                recognized = True
            elif fl == "blended":
                conds.append("(LOWER(w.type) IN ('blend','blended') OR LOWER(w.category) IN ('blended','blend'))")
                recognized = True
            elif fl == "bourbon":
                conds.append("(LOWER(w.category) = 'bourbon' OR LOWER(w.type) = 'bourbon')")
                recognized = True
            elif fl == "rye":
                conds.append("(LOWER(w.category) = 'rye' OR LOWER(w.type) = 'rye')")
                recognized = True
            elif fl in ("speyside", "islay", "highland", "campbeltown", "lowland", "islands"):
                conds.append("(LOWER(COALESCE(w.region,'')) = ?)")
                params.append(fl)
                recognized = True
            elif fl in ("peated", "smoky"):
                conds.append(f"({json_axis('smoky', 'peaty', 'peat', 'smoky_peaty')} > 1.0)")
                recognized = True
            elif fl == "sherry":
                conds.append(f"({json_axis('sherry', 'oak', 'cask', 'woody', 'oak_cask')} > 1.0)")
                recognized = True
            elif fl == "sweet":
                conds.append(f"({json_axis('sweet')} > 1.0)")
                recognized = True
            elif fl == "fruity":
                conds.append(f"({json_axis('fruity', 'fruit')} > 1.0)")
                recognized = True

        if not recognized:
            # Unknown chip: match nothing (consistent with an empty result set).
            return "0", []
        return " AND ".join(conds), params

    def _prepare_whisky(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Post-process a whisky row for the app.

        * Normalize the flavor profile into the 7-axis JSON the Flutter radar
          expects (JSON is passed through; key=val is mapped).
        * Surface certification state (read-only, no transformation of the
          stored value).
        """
        if "flavor_profile" in row and row.get("flavor_profile"):
            row["flavor_profile"] = self._normalize_flavor_profile(row["flavor_profile"])
        # Read-only passthrough of the stored certification flag.
        row["data_confidence"] = row.get("data_confidence")
        return row

    def get_whisky(self, whisky_id: str) -> Optional[Dict[str, Any]]:
        query = """
            SELECT w.*, d.name as distillery_name, fp.flavor_profile as flavor_profile
            FROM whiskies w
            LEFT JOIN distilleries d ON w.distillery_id = d.distillery_id
            LEFT JOIN flavor_profiles fp ON w.whisky_id = fp.whisky_id
            WHERE w.whisky_id = ?
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (whisky_id,))
            row = cursor.fetchone()
            return self._prepare_whisky(dict(row)) if row else None

    def get_official_source_references(self, whisky_id: str) -> List[Dict[str, Any]]:
        """Return official_source_references for a whisky.

        Read-only. Public responses are passed through SourceGuard so internal
        source fields (source_name, source_url, source_domain, ...) are never
        leaked to untrusted clients. This is the public read path, so
        is_manual defaults to False and the forbidden fields are stripped.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM official_source_references WHERE entity_id = ? ORDER BY field_name ASC",
                (whisky_id,),
            )
            rows = [dict(row) for row in cursor.fetchall()]
        return SourceGuard.sanitize_collection(rows, is_manual=False)

    def get_distilleries(self, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        limit = _clamp_page(limit)
        offset = _check_offset(offset, limit)

        query = """
            SELECT d.distillery_id, d.name, COUNT(w.whisky_id) as whisky_count
            FROM distilleries d
            LEFT JOIN whiskies w ON d.distillery_id = w.distillery_id
            GROUP BY d.distillery_id
            ORDER BY d.name ASC
            LIMIT ? OFFSET ?
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (limit, offset))
            rows = [dict(row) for row in cursor.fetchall()]

        return {
            "items": rows,
            "total_count": len(rows),
            "limit": limit,
            "offset": offset,
        }

    def search(self, q: str) -> List[Dict[str, Any]]:
        if not q or len(q.strip()) < 2:
            return []

        query = """
            SELECT w.*, d.name as distillery_name, fp.flavor_profile as flavor_profile
            FROM whiskies w
            LEFT JOIN distilleries d ON w.distillery_id = d.distillery_id
            LEFT JOIN flavor_profiles fp ON w.whisky_id = fp.whisky_id
            WHERE (w.name LIKE ? OR d.name LIKE ?) AND w.superseded_by IS NULL
            GROUP BY w.whisky_id
            ORDER BY CASE WHEN w.whisky_id LIKE 'GSD-CAND-%' THEN 0 ELSE 1 END, w.name ASC
            LIMIT 50
        """
        term = f"%{q.strip()}%"
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (term, term))
            rows = [self._prepare_whisky(dict(r)) for r in cursor.fetchall()]

        # Deduplicate by canonical name so a certified + legacy duplicate are
        # not both presented. Certified GSD rows are kept preferentially
        # (already sorted first).
        seen = set()
        unique = []
        for r in rows:
            name = (r.get("name") or "").strip().lower()
            if name in seen:
                continue
            seen.add(name)
            unique.append(r)
        return unique

    def get_filters(self) -> Dict[str, Any]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT distillery_id, name FROM distilleries ORDER BY name ASC")
            distilleries = [dict(row) for row in cursor.fetchall()]

            return {
                "distilleries": distilleries,
                "regions": "not_available",
                "countries": "not_available",
                "categories": "not_available",
            }

    def get_flavor_profile(self, whisky_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Product Rule (AGENTS.md): production_price ASLA API yanıtına girmez.
            # Açık kolon listesi — SELECT * DEĞİL (eski sürüm production_price sızdırıyordu).
            cursor.execute("""
                SELECT whisky_id, whisky_name, production_bottle_name, match_score,
                       match_method, flavor_vector, flavor_profile, flavor_tags,
                       flavor_source, flavor_data_confidence, production_rating,
                       production_region, notes_for_review, source_count,
                       evidence_count, enrichment_version
                FROM flavor_profiles WHERE whisky_id = ?
            """, (whisky_id,))
            row = cursor.fetchone()
            if not row:
                return None
            result = dict(row)
            # Normalize the stored flavor_profile string to the app's 7-axis JSON
            # so the Flutter radar renders correctly (presentation format only).
            if result.get("flavor_profile"):
                result["flavor_profile"] = self._normalize_flavor_profile(result["flavor_profile"])
            return result

    def get_tasting_notes(self, whisky_id: str) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tasting_notes WHERE whisky_id = ?", (whisky_id,))
            return [dict(row) for row in cursor.fetchall()]

    def get_price_history(self, whisky_id: str) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM price_history WHERE whisky_id = ?", (whisky_id,))
            return [dict(row) for row in cursor.fetchall()]
