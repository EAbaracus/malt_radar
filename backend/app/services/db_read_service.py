import json
import os
import sqlite3
from typing import Any, ClassVar

from app.db.production_read_adapter import (
    ProductionReadAdapter,  # Faz B2: tek read seam
)
from app.services.name_casing import title_case_name  # B1: serve-time isim casing
from app.utils.source_guard import SourceGuard

# Certified pilot whiskies use the 'GSD-CAND-XXXX' whisky_id prefix and are
# flagged with data_confidence = 'certified'. The staging DB is the single
# source of truth for them; production.db is the default datasource.

CERTIFIED_PREFIX = "GSD-CAND-"

# Anti-scrape bounds (configurable via env; bulk-dump / deep-paging ceiling).
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
        # Faz B2: path resolution ProductionReadAdapter'a (shared_paths.resolve_db_path)
        # migrate edildi. copy-paste 3-level-up kalıbı kaldırıldı.
        self._adapter = ProductionReadAdapter()
        self.db_path = self._adapter.db_path
        self._ro_uri = self._adapter._ro_uri  # backward-compat (some callers read .db_path)

    def _get_connection(self):
        """Faz B2: adapter._get_connection (mode=ro + query_only + canonical tablo check).

        read-only connect burada kalır ama sqlite3.connect sadece adapter'dan.
        """
        return self._adapter._get_connection()

    def get_health(self) -> dict[str, Any]:
        exists = os.path.exists(self.db_path)
        tables = ["distilleries", "whiskies", "tasting_notes", "flavor_profiles", "price_history"]
        VALID_TABLES = set(tables)
        counts = {}

        if exists:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()

                    # Filter valid tables
                    valid_list = [t for t in tables if t in VALID_TABLES]

                    if valid_list:
                        try:
                            # Single query with subqueries to avoid N+1 problem
                            query = "SELECT " + ", ".join([f"(SELECT COUNT(*) FROM {t}) as {t}" for t in valid_list])
                            cursor.execute(query)
                            row = cursor.fetchone()
                            for t in valid_list:
                                counts[t] = row[t]
                        except sqlite3.OperationalError:
                            # Fallback if a table is missing or query fails
                            for t in valid_list:
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
    APP_AXES: ClassVar = ["fruity", "sweet", "spicy", "smoky_peaty", "oak_cask", "malty_cereal", "floral_herbal", "maritime"]

    @staticmethod
    def _normalize_flavor_profile(raw: Any) -> str | None:
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
        axes: dict[str, float] = {}
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
    def _map_canonical_to_app_axes(axes: dict[str, float]) -> str:
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

    def _flavor_profile_for(self, whisky_id: str) -> str | None:
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

    def get_whiskies(self, limit: int = 50, offset: int = 0, q: str | None = None, distillery_id: str | None = None, filter: str | None = None) -> dict[str, Any]:
        limit = _clamp_page(limit)
        offset = _check_offset(offset, limit)

        query = """
            SELECT w.*, d.name as distillery_name, fp.flavor_profile as flavor_profile
            FROM whiskies w
            LEFT JOIN distilleries d ON w.distillery_id = d.distillery_id
            LEFT JOIN flavor_profiles fp ON w.whisky_id = fp.whisky_id
            WHERE LOWER(w.name) NOT LIKE '%smws%' AND LOWER(COALESCE(w.brand,'')) NOT LIKE '%smws%'
              AND w.superseded_by IS NULL
        """
        params = []

        if q and len(q.strip()) >= 2:
            # Case-insensitive search across name and original_name (if present)
            query += " AND (LOWER(w.name) LIKE LOWER(?) OR LOWER(COALESCE(w.original_name, '')) LIKE LOWER(?))"
            term = f"%{q.strip()}%"
            params.extend([term, term])
        else:
            query += " AND 1=1"

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
        params: list[Any] = []
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

        static_conds = {
            "single malt": (
                "(LOWER(w.type) IN ('malt','single malt')"
                " OR LOWER(w.name) LIKE '%single malt%'"
                " OR LOWER(COALESCE(w.region,'')) IN ('islay','speyside','highland','campbeltown','lowland','islands'))"
            ),
            "blended": "(LOWER(w.type) IN ('blend','blended'))",
            "bourbon": "(LOWER(w.type) = 'bourbon')",
            "rye": "(LOWER(w.type) = 'rye')"
        }
        regions = {"speyside", "islay", "highland", "campbeltown", "lowland", "islands"}
        flavors = {
            "peated": ("smoky", "peaty", "peat", "smoky_peaty"),
            "smoky": ("smoky", "peaty", "peat", "smoky_peaty"),
            "sherry": ("sherry", "oak", "cask", "woody", "oak_cask"),
            "sweet": ("sweet",),
            "fruity": ("fruity", "fruit"),
        }

        for f in wanted:
            fl = f.lower()
            if fl in static_conds:
                conds.append(static_conds[fl])
                recognized = True
            elif fl in regions:
                conds.append("(LOWER(COALESCE(w.region,'')) = ?)")
                params.append(fl)
                recognized = True
            elif fl in flavors:
                conds.append(f"({json_axis(*flavors[fl])} > 1.0)")
                recognized = True

        if not recognized:
            # Unknown chip: match nothing (consistent with an empty result set).
            return "0", []
        return " AND ".join(conds), params

    def _prepare_whisky(self, row: dict[str, Any]) -> dict[str, Any]:
        """Post-process a whisky row for the app.

        * Normalize the flavor profile into the 7-axis JSON the Flutter radar
          expects (JSON is passed through; key=val is mapped).
        * Normalize name/original_name casing (B1: serve-time title-case so the
          frontend never renders a lowercase `original_name` twin).
        * Surface certification state (read-only, no transformation of the
          stored value).
        """
        if "flavor_profile" in row and row.get("flavor_profile"):
            row["flavor_profile"] = self._normalize_flavor_profile(row["flavor_profile"])
        # B1: title-case name + original_name. Stored values never mutated; this
        # is a presentation-format normalization only (read-only).
        # KOŞULLU GATE (korpus kanıtı, review REQUEST_CHANGES): production'da
        # name ZATEN kanonik (B1). Yalnızca TAMAMEN küçük harfli isimleri
        # title-case yap (143 hedef satır); büyük harf içeren kanonik isimlere
        # dokunma — aksi halde "(batch 1)"→"(Batch 1)", "(ob)"→"(Ob)" gibi
        # 869 regresyon üretir. original_name ham ikizdir, daima normalize.
        name = row.get("name")
        if name:
            row["name"] = title_case_name(name) if name == name.lower() else name
        orig = row.get("original_name")
        if orig:
            row["original_name"] = title_case_name(orig)
        # Read-only passthrough of the stored certification flag.
        row["data_confidence"] = row.get("data_confidence")
        return row

    def get_whisky(self, whisky_id: str) -> dict[str, Any] | None:
        query = """
            SELECT w.*, d.name as distillery_name, fp.flavor_profile as flavor_profile
            FROM whiskies w
            LEFT JOIN distilleries d ON w.distillery_id = d.distillery_id
            LEFT JOIN flavor_profiles fp ON w.whisky_id = fp.whisky_id
            WHERE w.whisky_id = ?
              AND w.superseded_by IS NULL
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (whisky_id,))
            row = cursor.fetchone()
            return self._prepare_whisky(dict(row)) if row else None

    def get_official_source_references(self, whisky_id: str) -> list[dict[str, Any]]:
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

    def get_distilleries(self, limit: int = 50, offset: int = 0) -> dict[str, Any]:
        limit = _clamp_page(limit)
        offset = _check_offset(offset, limit)

        query = """
            SELECT d.distillery_id, d.name, COUNT(w.whisky_id) as whisky_count
            FROM distilleries d
            LEFT JOIN whiskies w ON d.distillery_id = w.distillery_id
                               AND w.superseded_by IS NULL
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

    def search(self, q: str) -> list[dict[str, Any]]:
        if not q or len(q.strip()) < 2:
            return []

        query = """
            SELECT w.*, d.name as distillery_name, fp.flavor_profile as flavor_profile
            FROM whiskies w
            LEFT JOIN distilleries d ON w.distillery_id = d.distillery_id
            LEFT JOIN flavor_profiles fp ON w.whisky_id = fp.whisky_id
            WHERE (LOWER(w.name) LIKE LOWER(?) OR LOWER(COALESCE(w.original_name, '')) LIKE LOWER(?)
                   OR d.name LIKE ?)
              AND LOWER(w.name) NOT LIKE '%smws%' AND LOWER(COALESCE(w.brand,'')) NOT LIKE '%smws%'
              AND w.superseded_by IS NULL
            GROUP BY w.whisky_id
            ORDER BY CASE WHEN w.whisky_id LIKE 'GSD-CAND-%' THEN 0 ELSE 1 END, w.name ASC
            LIMIT 50
        """
        term = f"%{q.strip()}%"
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (term, term, term))
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

    def get_filters(self) -> dict[str, Any]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Only distilleries that still have active (non-superseded) whiskies
            # are offered as filters; otherwise quarantined/SMWS rows would
            # surface via the distillery facet (SMWS/SYNTH mark-and-hide).
            cursor.execute(
                """
                SELECT DISTINCT d.distillery_id, d.name
                FROM distilleries d
                JOIN whiskies w ON d.distillery_id = w.distillery_id
                               AND w.superseded_by IS NULL
                ORDER BY d.name ASC
                """
            )
            distilleries = [dict(row) for row in cursor.fetchall()]

            return {
                "distilleries": distilleries,
                "regions": "not_available",
                "countries": "not_available",
                "categories": "not_available",
            }

    def get_flavor_profile(self, whisky_id: str) -> dict[str, Any] | None:
        # Faz B2: read seamsiz; ama DbReadService._prepare_whisky üzerinden
        # normalize uygulanmalı (adapter sadece raw çeker). Açık kolon listesi
        # (SELECT * DEĞİL) → flavor_profiles.production_price dahil değil.
        # test_flavor_profile_keeps_radar_fields: flavor_profile / flavor_tags /
        # flavor_source / production_rating vs. radar/zorunlu alanlar korunur.
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT whisky_id, whisky_name, production_bottle_name, match_score,
                       match_method, flavor_vector, flavor_profile, flavor_tags,
                       flavor_source, flavor_data_confidence, production_rating,
                       production_region, notes_for_review, source_count,
                       evidence_count, enrichment_version
                FROM flavor_profiles WHERE whisky_id = ?
                """,
                (whisky_id,),
            )
            row = cursor.fetchone()
        if not row:
            return None
        result = dict(row)
        # Normalize the stored flavor_profile string to the app's 7-axis JSON
        # so the Flutter radar renders correctly (presentation format only).
        if result.get("flavor_profile"):
            result["flavor_profile"] = self._normalize_flavor_profile(result["flavor_profile"])
        return result

    def get_tasting_notes(self, whisky_id: str) -> list[dict[str, Any]]:
        # Faz B2: adapter.query → universal price redaction (tasting_notes'de yok ama defans)
        # Note: production tasting_notes schema has no created_at column.
        return self._adapter.query(
            "tasting_notes",
            where="whisky_id = ?",
            params=(whisky_id,),
            order_by="whisky_id ASC",
        )

    def get_price_history(self, whisky_id: str) -> list[dict[str, Any]]:
        # Faz B2: adapter.get_price_history → universal fiyat kolon redaction.
        # Product Rule: production_price/price_value ASLA API yanıtına girmez.
        return self._adapter.get_price_history(whisky_id)
