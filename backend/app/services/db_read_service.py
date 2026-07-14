import os
import sqlite3
import json
from typing import List, Dict, Any, Optional

# Certified pilot whiskies use the 'GSD-CAND-XXXX' whisky_id prefix and are
# flagged with data_confidence = 'certified'. The staging DB is the single
# source of truth for them; production.db is the default datasource.

CERTIFIED_PREFIX = "GSD-CAND-"


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
    APP_AXES = ["fruity", "sweet", "spicy", "smoky_peaty", "oak_cask", "malty_cereal", "floral_herbal"]

    @staticmethod
    def _normalize_flavor_profile(raw: Any) -> Optional[str]:
        if not raw:
            return None

        text = raw.strip() if isinstance(raw, str) else str(raw)

        # Already JSON? Validate it is a mapping and pass through unchanged.
        if text.startswith("{"):
            try:
                obj = json.loads(text)
                if isinstance(obj, dict):
                    return text
            except (json.JSONDecodeError, ValueError):
                return None

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

        def g(k: str) -> float:
            return axes.get(k, 0.0)

        mapped = {
            "fruity": g("fruity"),
            "sweet": g("sweet"),
            "spicy": g("spicy"),
            "smoky_peaty": max(g("smoky"), g("peaty")),
            "oak_cask": max(g("sherry"), g("oak"), g("cask")),
            "malty_cereal": g("malty"),
            "floral_herbal": g("floral"),
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

    def get_whiskies(self, limit: int = 50, offset: int = 0, q: Optional[str] = None, distillery_id: Optional[str] = None) -> Dict[str, Any]:
        limit = min(max(1, limit), 100)
        offset = max(0, offset)

        query = """
            SELECT w.*, d.name as distillery_name, fp.flavor_profile as flavor_profile
            FROM whiskies w
            LEFT JOIN distilleries d ON w.distillery_id = d.distillery_id
            LEFT JOIN flavor_profiles fp ON w.whisky_id = fp.whisky_id
            WHERE 1=1
        """
        params = []

        if q and len(q.strip()) >= 2:
            query += " AND w.name LIKE ?"
            params.append(f"%{q.strip()}%")

        if distillery_id:
            query += " AND w.distillery_id = ?"
            params.append(distillery_id)

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
        """Return official_source_references rows exactly as stored (read-only).
        No transformation, summarization, or generated citations."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM official_source_references WHERE entity_id = ? ORDER BY field_name ASC",
                (whisky_id,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_distilleries(self, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        limit = min(max(1, limit), 100)
        offset = max(0, offset)

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
            WHERE w.name LIKE ? OR d.name LIKE ?
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
            cursor.execute("SELECT * FROM flavor_profiles WHERE whisky_id = ?", (whisky_id,))
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
