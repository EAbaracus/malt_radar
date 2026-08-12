"""Task AL-A tests — anonymous allowlist build script determinism + contract.

Spec: Anonymous Read Layer, Task 1. The artifact is the runtime contract;
the API never re-derives it, so the build must be byte-deterministic.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # project root
SCRIPTS = ROOT / "scripts"
DB = ROOT / "output/import/production.db"

# Tests run from backend/ (cwd on sys.path via `python -m pytest`), so the
# repo-root `seo` package is not importable without this insert.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _build(out: Path, limit: int = 50) -> dict:
    r = subprocess.run(
        [sys.executable, str(SCRIPTS / "build_anonymous_allowlist.py"),
         "--db", str(DB), "--out", str(out), "--limit", str(limit)],
        capture_output=True, text=True, cwd=str(ROOT))
    assert r.returncode == 0, r.stderr
    return json.loads(out.read_text(encoding="utf-8"))


def test_allowlist_determinism():
    a, b = ROOT / "artifacts" / "_t1_a.json", ROOT / "artifacts" / "_t1_b.json"
    _build(a)
    _build(b)
    assert a.read_bytes() == b.read_bytes()
    a.unlink()
    b.unlink()


def test_allowlist_contained_in_tier_a_sitemap():
    out = ROOT / "artifacts" / "_t1_c.json"
    art = _build(out)
    import sqlite3
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    from seo.tiers import tier_map
    tiers = tier_map(conn)
    conn.close()
    assert all(tiers.get(wid) == "A" for wid in art["ids"])
    assert len(art["ids"]) == art["n"]
    out.unlink()


def test_allowlist_n_is_respected():
    out = ROOT / "artifacts" / "_t1_d.json"
    art = _build(out, limit=7)
    assert art["n"] == 7 and len(art["ids"]) == 7
    out.unlink()


def test_artifact_has_sha256_and_version():
    out = ROOT / "artifacts" / "_t1_e.json"
    art = _build(out)
    assert art["version"] == 1
    assert len(art["db_sha256"]) == 64
    out.unlink()


def test_allowlist_sorted_by_evidence_count_desc():
    """I3: ids must follow the stable sort contract (evidence_count DESC,
    name, whisky_id). Re-derive the expected ordering from the DB
    independently and compare."""
    out = ROOT / "artifacts" / "_t1_f.json"
    art = _build(out)
    import sqlite3
    from seo.tiers import tier_map
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    tiers = tier_map(conn)
    rows = conn.execute(
        "SELECT whisky_id, name FROM whiskies WHERE superseded_by IS NULL"
    ).fetchall()
    counts: dict[str, int] = {}
    for w in rows:
        wid = w["whisky_id"]
        if tiers.get(wid) == "A":
            counts[wid] = conn.execute(
                "SELECT COUNT(*) FROM flavor_evidence WHERE whisky_id=?",
                (wid,)).fetchone()[0]
    conn.close()

    eligible = [w["whisky_id"] for w in rows if tiers.get(w["whisky_id"]) == "A"]
    name_of = {w["whisky_id"]: (w["name"] or "").lower() for w in rows}
    expected = sorted(
        eligible,
        key=lambda wid: (-counts.get(wid, 0), name_of.get(wid, ""), wid),
    )[:len(art["ids"])]
    assert art["ids"] == expected
    out.unlink()


def test_allowlist_ids_unique():
    """I3: every id in the allowlist must be unique."""
    out = ROOT / "artifacts" / "_t1_g.json"
    art = _build(out)
    ids = art["ids"]
    assert len(ids) == len(set(ids)), "allowlist contains duplicate ids"
    out.unlink()


def test_allowlist_excludes_superseded():
    """I3: no superseded whisky may appear in the allowlist."""
    out = ROOT / "artifacts" / "_t1_h.json"
    art = _build(out)
    import sqlite3
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    superseded = {r[0] for r in conn.execute(
        "SELECT whisky_id FROM whiskies WHERE superseded_by IS NOT NULL"
    ).fetchall()}
    conn.close()
    overlap = set(art["ids"]) & superseded
    assert not overlap, f"allowlist contains superseded ids: {overlap}"
    out.unlink()
