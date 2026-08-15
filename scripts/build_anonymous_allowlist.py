"""Build-time deterministic anonymous allowlist (spec: Anonymous Read Layer, AL-A).

Pipeline: live production.db (read-only) -> seo.tiers.tier_map -> Tier A
-> sitemap-eligible (tier != 'C_no') -> stable sort -> first N.

Determinism contract: same DB + same N -> byte-identical artifact.
The artifact is the runtime contract; the API never re-derives it.
"""
import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))                # for `seo` package
sys.path.insert(0, str(ROOT / "backend"))    # for `app` package

from seo.tiers import tier_map  # noqa: E402
from app.db.production_read_adapter import ProductionReadAdapter  # noqa: E402

DEFAULT_LIMIT = int(os.getenv("ANONYMOUS_CATALOG_LIMIT", "150"))


def db_sha256(db_path: str) -> str:
    return hashlib.sha256(Path(db_path).read_bytes()).hexdigest()


def build_allowlist(db_path: str, limit: int) -> list[str]:
    adapter = ProductionReadAdapter(db_path=db_path)
    # I1: use the adapter's public read seam (raw_connection) instead of the
    # private _get_connection. I2: keep all DB reads AND the dependent
    # computation inside the `with` block before the connection is closed.
    with adapter.raw_connection() as conn:
        tiers = tier_map(conn)
        # evidence_count per whisky (only needed for Tier A; matches seo.generator)
        counts: dict[str, int] = {}
        for wid, tier in tiers.items():
            if tier == "A":
                counts[wid] = conn.execute(
                    "SELECT COUNT(*) FROM flavor_evidence WHERE whisky_id=?",
                    (wid,)).fetchone()[0]
        rows = conn.execute(
            "SELECT whisky_id, name FROM whiskies WHERE superseded_by IS NULL").fetchall()
        # Tier A is by construction sitemap-eligible (C_no can never be 'A').
        eligible = [w["whisky_id"] for w in rows if tiers.get(w["whisky_id"]) == "A" and "smws" not in (w["name"] or "").lower()]
        # Stable sort: evidence_count DESC, name (case-insensitive), whisky_id tie-break
        name_of = {w["whisky_id"]: (w["name"] or "").lower() for w in rows}
        eligible.sort(key=lambda wid: (-counts.get(wid, 0), name_of.get(wid, ""), wid))
        return eligible[:limit]


def main() -> int:
    ap = argparse.ArgumentParser(description="Build anonymous allowlist artifact")
    ap.add_argument("--db", default=str(ROOT / "output/import/production.db"))
    ap.add_argument("--out", default=str(ROOT / "artifacts" / "anonymous_allowlist.json"))
    ap.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    args = ap.parse_args()

    ids = build_allowlist(args.db, args.limit)
    # C1: `build_date` (date.today()) broke byte-determinism across runs on the
    # same DB state. It is excluded from the artifact; db_sha256 already pins the
    # DB state, so byte-identical output holds for identical inputs.
    artifact = {
        "version": 1,
        "db_sha256": db_sha256(args.db),
        "limit_source": "ANONYMOUS_CATALOG_LIMIT",
        "n": len(ids),
        "sort_key": "evidence_count DESC, name, whisky_id",
        "ids": ids,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(artifact, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"allowlist: n={len(ids)} -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
