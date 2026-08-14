"""P136 migrate.py — idempotent schema bootstrap for knowledge.db.

Applies migration/schema.sql then migration/migration.sql, recording each in
schema_version. Replay-safe: every statement is IF NOT EXISTS / guarded.
Does NOT touch production.db.
"""
from __future__ import annotations
import os, sqlite3, hashlib, datetime, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
MIG_DIR = os.path.join(HERE, "..", "migration")
SCHEMA = os.path.join(MIG_DIR, "schema.sql")
MIGRATION = os.path.join(MIG_DIR, "migration.sql")
DEFAULT_KB = os.path.join(os.path.dirname(HERE), "..", "..", "output", "import", "knowledge.db")

def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(65536), b""):
            h.update(b)
    return h.hexdigest()

def migrate(kb_path: str, log=print) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(kb_path)), exist_ok=True)
    conn = sqlite3.connect(kb_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        # schema.sql
        sql = open(SCHEMA, encoding="utf-8").read()
        conn.executescript(sql)
        # migration.sql
        mig = open(MIGRATION, encoding="utf-8").read()
        conn.executescript(mig)
        # record version
        sig = sha256(SCHEMA)[:16] + sha256(MIGRATION)[:16]
        cur = conn.execute("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1")
        row = cur.fetchone()
        version = (row[0] + 1) if row else 1
        conn.execute(
            "INSERT INTO schema_version (version, description, applied_at, baseline_sig) VALUES (?,?,?,?)",
            (version, "P136 initial bootstrap + migration replay", _now(), sig),
        )
        conn.commit()
        log(f"[migrate] knowledge.db ready at {kb_path} (version {version}, sig {sig})")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--kb", default=DEFAULT_KB, help="path to knowledge.db")
    args = ap.parse_args()
    migrate(args.kb)
