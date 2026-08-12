"""social/metrics.py — READ-ONLY veri istatistiği çıkarıcı (Malt Radar).

Production DB'ye ASLA yazmaz. Sadece paylaşılabilir, yasal-clean içerik
matesneli sayıları okur. AGENTS.md canon: read-only, kanıt kayıtlı.

Yasal sınır (4250/m.20-21): içki tanıtımı yasak — bu modül üretilen
istatistikler app'in BİLGİ/VERİ aracı olmasını vurgular, içki satış/skor/
teşvik içermez. Fiyat (price) hiçbir çıktıda yer almaz (product rule).
"""

from __future__ import annotations

import datetime as _dt
import hashlib as _hl
import sqlite3 as _sq
from pathlib import Path as _P

DEFAULT_DB = _P(__file__).resolve().parents[1] / "output" / "import" / "production.db"


class MetricsError(RuntimeError):
    pass


def _connect(db_path: str) -> _sq.Connection:
    p = _P(db_path)
    if not p.exists():
        raise MetricsError(f"DB bulunamadi: {p}")
    c = _sq.connect(f"file:{p.as_posix()}?mode=ro", uri=True)
    c.row_factory = _sq.Row
    return c


def _sha256(path: str) -> str:
    h = _hl.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def collect(db_path: str = str(DEFAULT_DB)) -> dict:
    """Production DB'den yasal-clean içerik matesnelerini toplar."""
    c = _connect(db_path)
    cur = c.cursor()

    def one(sql: str, *args):
        r = cur.execute(sql, args).fetchone()
        return r[0] if r else None

    def _distinct(column: str, table: str = "whiskies"):
        r = cur.execute(
            f"SELECT DISTINCT {column} FROM {table} "
            f"WHERE {column} IS NOT NULL AND length({column})>0"
        ).fetchall()
        return [row[0] for row in r]

    total_whiskies = one("SELECT COUNT(*) FROM whiskies") or 0
    total_distilleries = one("SELECT COUNT(*) FROM distilleries") or 0
    total_brands = one("SELECT COUNT(*) FROM brands") or 0
    total_flavor_evidence = one("SELECT COUNT(*) FROM flavor_evidence") or 0
    total_flavor_profiles = one(
        "SELECT COUNT(*) FROM flavor_profiles WHERE flavor_profile IS NOT NULL"
    ) or 0

    # Coğrafi yayılım (içki değil, veri seti kapsamı hikayesi = app'i tanıtır)
    countries = cur.execute(
        "SELECT country, COUNT(*) n FROM whiskies "
        "WHERE country IS NOT NULL AND length(country)>0 "
        "GROUP BY country ORDER BY n DESC"
    ).fetchall()

    # Kanıt kaynakları (OCR / editorial / book — veri üretim süreci hikayesi)
    evidence_sources = cur.execute(
        "SELECT source, COUNT(*) n FROM flavor_evidence "
        "WHERE source IS NOT NULL GROUP BY source ORDER BY n DESC"
    ).fetchall()

    # En çok kataloglanan bölge (veri kapsamı hikayesi)
    regions = cur.execute(
        "SELECT region, COUNT(*) n FROM distilleries "
        "WHERE region IS NOT NULL AND length(region)>0 "
        "GROUP BY region ORDER BY n DESC LIMIT 5"
    ).fetchall()

    # Beş ana whisky tipi (katalog çeşitliliği hikayesi)
    types = cur.execute(
        "SELECT type, COUNT(*) n FROM whiskies "
        "WHERE type IS NOT NULL AND length(type)>0 "
        "GROUP BY type ORDER BY n DESC LIMIT 6"
    ).fetchall()

    m = {
        "generated_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "db_file": _P(db_path).name,
        "db_sha256": _sha256(db_path),
        "totals": {
            "whiskies": total_whiskies,
            "distilleries": total_distilleries,
            "brands": total_brands,
            "flavor_evidence": total_flavor_evidence,
            "flavor_profiles": total_flavor_profiles,
        },
        "countries": [{"name": r["country"], "count": r["n"]} for r in countries],
        "evidence_sources": [
            {"name": r["source"], "count": r["n"]} for r in evidence_sources
        ],
        "regions": [{"name": r["region"], "count": r["n"]} for r in regions],
        "types": [{"name": r["type"], "count": r["n"]} for r in types],
    }
    c.close()
    return m


def summary(m: dict) -> dict:
    """Sadece paylaşılabilir, legal-clean özet (içki/teşvik yok)."""
    t = m["totals"]
    top_country = ", ".join(f"{x['name']} ({x['count']})" for x in m["countries"][:3])
    top_src = ", ".join(f"{x['name']} ({x['count']})" for x in m["evidence_sources"][:3])
    top_region = ", ".join(f"{x['name']} ({x['count']})" for x in m["regions"][:3])
    return {
        "katalog": f"{t['whiskies']} viski, {t['distilleries']} damıtım evi, {t['brands']} marka",
        "kanit": f"{t['flavor_evidence']} flavor kanıtı, {t['flavor_profiles']} flavor profili",
        "ulkeler": top_country,
        "kaynaklar": top_src,
        "bolgeler": top_region,
    }


if __name__ == "__main__":
    import json
    import sys

    db = sys.argv[1] if len(sys.argv) > 1 else str(DEFAULT_DB)
    try:
        m = collect(db)
        print("=== ----")
        print(json.dumps(summary(m), ensure_ascii=False, indent=2))
        print("=== ----")
        print("db_sha256:", m["db_sha256"])
    except MetricsError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
