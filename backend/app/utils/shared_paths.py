"""Shared constants + helpers for the db/ write/guard + adapter seams (Faz 0–1).

- _sha256_file: G2 pre/post write SHA audit helper (boşuna duplicated copy'lardan
  kaçın).
- ALLOWED_TABLES: ReviewQueryService.execute_action içinde tanımlı idi, tekrar
  tanımlamak yerine shared; hem ReviewActionWriter (write) hem de
  ProductionReadAdapter (read) canonical tablo listesini burada tutar.

NOT: read için ALL_CANONICAL_TABLES (production_read_adapter.py); write için
ALLOWED_TABLES (bu modül). İki set farklı sektörden: read tüm canonical tabloları
okur, write yalnızca staging_* + knowledge_* + review_actions.
"""
from __future__ import annotations

import hashlib
import os


def _sha256_file(path: str) -> str:
    """SHA-256 of a file's bytes (production.db pre/post write audit, G2)."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


# Tablolar: staging_* + knowledge_* (ReviewQueryService.execute_action /
# ReviewActionWriter tarafından yazılan). read için değil — read
# ProductionReadAdapter.ALL_CANONICAL_TABLES'ı kullanır.
ALLOWED_TABLES: dict[str, str] = {
    "staging_new_products": "staging_new_products",
    "staging_tasting_notes": "staging_tasting_notes",
    "staging_historical_menu_prices": "staging_historical_menu_prices",
    "staging_manual_review_queue": "staging_manual_review_queue",
    "knowledge_regions": "knowledge_regions",
    "knowledge_glossary_terms": "knowledge_glossary_terms",
    "knowledge_guides": "knowledge_guides",
}


DEFAULT_DB = "output/import/production.db"


def resolve_db_path(db_path: str | None = None,
                    env_var: str = "MALT_RADAR_DB_PATH",
                    caller_file: str | None = None) -> str:
    """Canonical production.db path resolution.

    Faz B: bu fonksiyonun amacı, DbReadService'ın (3 level up from
    backend/app/services/) ve ProductionReadAdapter'ın (backend/app/db/)
    ayrı ayrı yazdığı 3-level-up mantığının kopyasını öldürmek. Her read adapter
    bu fonksiyonu çağırır; path çözümlemesi tek yerde (tek copy).

    Priority: explicit db_path arg > env_var > DEFAULT_DB.
    Relative pathler projen root'undan (backend/ün 2 level yukarısından) çözülür.
    caller_file verilirse (örn. __file__), onun 2 level yukarısı root kabul edilir;
    yoksa os.getcwd()'den env çözümleme yapılmaz — her zaman projen içinden.
    """
    source = db_path or os.getenv(env_var, DEFAULT_DB)
    if os.path.isabs(source):
        return source
    # caller_file: backend/app/{services,db,...}/*.py → dirname 3x = project root.
    #   app/db/production_read_adapter.py → dirname=app/db → dirname=app → dirname=backend → dirname=project_root
    #   app/services/review_query_service.py → dirname=app/services → dirname=app → dirname=backend → dirname=project_root
    if caller_file:
        base = os.path.dirname(os.path.abspath(caller_file))
        # app/{services,db,utils,routers} → app → backend → project_root
        for _ in range(3):
            base = os.path.dirname(base)
        return os.path.abspath(os.path.join(base, source))
    # fallback: env cwd'den (pytest backend/ cwd'de çalışıyorsa da 3 dirname up = project root)
    base = os.path.dirname(os.path.dirname(os.path.abspath(os.getcwd())))
    return os.path.abspath(os.path.join(base, source))
