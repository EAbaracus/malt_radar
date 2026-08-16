import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from app.db.production_read_adapter import ProductionReadAdapter
from app.services.db_read_service import DbReadService

ROOT = Path(__file__).resolve().parents[3]
ARTIFACT_PATH = ROOT / "artifacts" / "anonymous_allowlist.json"

class AnonymousCatalogService:
    def __init__(self, artifact_path: Optional[Path] = None):
        self._adapter = ProductionReadAdapter()
        self._db_service = DbReadService()
        path = artifact_path or ARTIFACT_PATH
        if not path.exists():
            raise FileNotFoundError(f"Anonymous allowlist artifact missing: {path}")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self._allowlist_ids: List[str] = data.get("ids", [])
        self._allowlist_set = set(self._allowlist_ids)

    def get_allowlist_ids(self) -> List[str]:
        return self._allowlist_ids

    def get_whiskies(self, limit: int = 50, offset: int = 0, q: Optional[str] = None, filter: Optional[str] = None) -> Dict[str, Any]:
        offset = max(0, offset)
        limit = min(max(1, limit), 50)

        ids = self._allowlist_ids
        if not ids:
            return {"items": [], "total_count": 0, "limit": limit, "offset": offset}

        placeholders = ",".join(["?"] * len(ids))
        # Allowlist build (build_anonymous_allowlist.py) explicitly filters out
        # superseded whiskies at build time. Runtime queries are bounded strictly
        # to allowlist_ids, making runtime supersession filtering redundant.
        where = [f"w.whisky_id IN ({placeholders})"]
        params: list[Any] = list(ids)

        if q and len(q.strip()) >= 2:
            where.append("w.name LIKE ?")
            params.append(f"%{q.strip()}%")

        # Chip filters (Bourbon/Single Malt/Blended/region/flavor) — reuse the
        # governed auth-path vocabulary so anonymous and per-user catalogs
        # filter identically. Unknown chips match nothing ("0").
        if filter:
            cond, fparams = self._db_service._prepare_chip_filter(filter)
            where.append(cond)
            params.extend(fparams)

        where_sql = " AND ".join(where)

        with self._adapter.raw_connection() as conn:
            cursor = conn.cursor()
            # Total over the FILTERED set (BEFORE limit/offset) so pagination
            # slices the filtered result, mirroring db_read_service.
            count_sql = (
                "SELECT COUNT(DISTINCT w.whisky_id) FROM whiskies w "
                "LEFT JOIN flavor_profiles fp ON w.whisky_id = fp.whisky_id "
                f"WHERE {where_sql}"
            )
            total = cursor.execute(count_sql, params).fetchone()[0]

            query = f"""
                SELECT w.*, d.name as distillery_name, fp.flavor_profile as flavor_profile
                FROM whiskies w
                LEFT JOIN distilleries d ON w.distillery_id = d.distillery_id
                LEFT JOIN flavor_profiles fp ON w.whisky_id = fp.whisky_id
                WHERE {where_sql}
                GROUP BY w.whisky_id ORDER BY w.name ASC LIMIT ? OFFSET ?
            """
            rows = [
                self._shape_whisky(dict(row))
                for row in cursor.execute(query, params + [limit, offset]).fetchall()
            ]

        return {
            "items": rows,
            "total_count": total,
            "limit": limit,
            "offset": offset,
        }

    def get_whisky(self, whisky_id: str) -> Optional[Dict[str, Any]]:
        if whisky_id not in self._allowlist_set:
            return None
        raw = self._db_service.get_whisky(whisky_id)
        return self._shape_whisky(raw) if raw else None

    def get_flavor_profile(self, whisky_id: str) -> Optional[Dict[str, Any]]:
        if whisky_id not in self._allowlist_set:
            return None
        return self._db_service.get_flavor_profile(whisky_id)

    def search(self, q: str) -> List[Dict[str, Any]]:
        raw_results = self._db_service.search(q)
        return [self._shape_whisky(r) for r in raw_results if r.get("whisky_id") in self._allowlist_set]

    def get_distilleries(self, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        return self._db_service.get_distilleries(limit, offset)

    def get_filters(self) -> Dict[str, Any]:
        return self._db_service.get_filters()

    def _shape_whisky(self, item: Dict[str, Any]) -> Dict[str, Any]:
        item.pop("production_price", None)
        item.pop("price_value", None)
        item.pop("price_context", None)
        item.pop("pour_size_ml", None)
        raw_fp = item.get("flavor_profile")
        if raw_fp:
            norm_json = DbReadService._normalize_flavor_profile(raw_fp)
            item["flavor_profile"] = json.loads(norm_json) if norm_json else None
        return item

    def get_similar_whiskies(self, whisky_id: str, limit: int = 5) -> Optional[Dict[str, Any]]:
        """G1 REV (2026-08-16): hedef allowlist gate'i KALDIRILDI.

        Gerekçe: sonuçlar zaten tam havuz (onaylı G1 istisnası) — gate hiçbir
        koruma sağlamıyordu; yalnızca allowlist dışı 4.400+ viskide "Benzer
        Lezzetler"i boş döndürüyordu (ürün regresyonu). 404 artık YALNIZCA
        hedef yoksa/superseded ise (SimilarityService._all_active_whiskies).
        """
        from app.services.similarity_service import SimilarityService
        similar = SimilarityService(self._adapter).get_similar(whisky_id, limit)
        if similar is None:
            return None
        return {"similar": similar}
