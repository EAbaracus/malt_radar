"""ROLLBACK P501-EXACT-ONLY — restore production.db from pre-apply backup.

User instruction: restore from backup, verify SHA == 17d64bf..., verify
row counts / integrity, verify the 6 conflicting (whisky_id,'whiskysaga')
pairs are absent. NO re-promotion.

Uses the governed rollback path: db_write_guard.authorized_file_replacement
(same ACL-lift mechanism the PromotionGate commit uses, in reverse).
Production.db goes from b4c9426a... back to 17d64bf...
"""
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "kep_review_runtime"))
sys.path.insert(0, str(ROOT))

from runtime import db_write_guard  # noqa: E402

PROD = ROOT / "output/import/production.db"
BACKUP = ROOT / "output/import/backups/production_prepromote_20260805_110742.db"
EXPECTED_SHA = "17d64bf5fea2e84840b71ebbf0fa27d00ae310ddd97fc9c40d60bcf0c25bd499"
CONFLICT_PAIRS = [("W002329", "W000045", "W000397", "W003687", "W003827", "W3298")]


def sha256(path) -> str:
    import hashlib
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main() -> int:
    print("=== ROLLBACK P501-EXACT-ONLY ===")
    failures = []

    # 1. Backup integrity before touching anything
    bak_sha = sha256(BACKUP)
    ok_backup = bak_sha == EXPECTED_SHA
    print(f"  [{'PASS' if ok_backup else 'FAIL'}] backup SHA: {bak_sha[:16]}…")
    if not ok_backup:
        failures.append("backup_sha")

    # 2. Sanity: current production evidences the promoted state
    pre_sha = sha256(PROD)
    print(f"  production SHA (before): {pre_sha[:16]}… (b4c9426a… bekleniyor)")

    # 3. Restore via governed file replacement
    try:
        db_write_guard.authorized_file_replacement(
            temp_copy_path=str(BACKUP),
            production_db_path=str(PROD),
            authorized_context="rollback:P501-EXACT-ONLY:human-gate",
        )
        print("  [PASS] restore executed (authorized_file_replacement)")
    except Exception as e:
        print(f"  [FAIL] restore failed: {e}")
        failures.append("restore")
        return 3

    # 4. Verify restored SHA == expected pre-apply
    post_sha = sha256(PROD)
    ok_sha = post_sha == EXPECTED_SHA
    print(f"  [{'PASS' if ok_sha else 'FAIL'}] production SHA after: {post_sha[:16]}…")
    if not ok_sha:
        failures.append("post_sha")

    # 5. Row counts + integrity
    conn = sqlite3.connect(f"file:{PROD}?mode=ro", uri=True)
    n_ev = conn.execute("SELECT COUNT(*) FROM flavor_evidence").fetchone()[0]
    n_fp = conn.execute("SELECT COUNT(*) FROM flavor_profiles").fetchone()[0]
    integ = conn.execute("PRAGMA integrity_check").fetchone()[0]
    r4 = conn.execute(
        "SELECT COUNT(*) FROM flavor_evidence WHERE "
        "NOT (vector_smoky BETWEEN 0 AND 1 AND vector_peaty BETWEEN 0 AND 1 "
        "AND vector_sherry BETWEEN 0 AND 1 AND vector_fruity BETWEEN 0 AND 1 "
        "AND vector_spicy BETWEEN 0 AND 1 AND vector_sweet BETWEEN 0 AND 1 "
        "AND vector_rich BETWEEN 0 AND 1 AND vector_maritime BETWEEN 0 AND 1)"
    ).fetchone()[0]
    ok_ev = n_ev == 5805
    ok_fp = n_fp == 4285
    ok_integ = integ == "ok"
    ok_r4 = r4 == 0
    print(f"  [{'PASS' if ok_ev else 'FAIL'}] evidence rows: {n_ev} (5805 beklenen)")
    print(f"  [{'PASS' if ok_fp else 'FAIL'}] flavor profiles: {n_fp} (4285 beklenen)")
    print(f"  [{'PASS' if ok_integ else 'FAIL'}] integrity: {integ}")
    print(f"  [{'PASS' if ok_r4 else 'FAIL'}] R4 violations: {r4}")
    for c in (ok_ev, ok_fp, ok_integ, ok_r4):
        if not c:
            failures.append("rows")

    # 6. Verify the 6 conflicting pairs are ABSENT (source='whiskysaga' total)
    ws_total = conn.execute(
        "SELECT COUNT(*) FROM flavor_evidence WHERE source='whiskysaga'").fetchone()[0]
    hit = 0
    for wid in CONFLICT_PAIRS[0]:
        r = conn.execute(
            "SELECT COUNT(*) FROM flavor_evidence WHERE whisky_id=? AND source='whiskysaga'",
            (wid,)).fetchone()[0]
        hit += r
    ok_absent = ws_total == 0 and hit == 0
    print(f"  [{'PASS' if ok_absent else 'FAIL'}] whiskysaga rows total={ws_total}, "
          f"conflict-pair rows={hit} (0 beklenen)")
    if not ok_absent:
        failures.append("conflicts_present")
    conn.close()

    # 7. Closure
    ts = datetime.now(timezone.utc).isoformat()
    doc = {
        "phase_id": "P501-EXACT-ONLY", "action": "ROLLBACK", "generated_at": ts,
        "approved_by": "human", "rationale": "Kural-9: 6 yeni (whisky_id,source) dupe"
        " (W003827 Port Askaig 28→8, W3298 Akashi Blended→Single Malt vb.) — "
        "matcher hard-block eksikliği; kabul seçilmedi (zero-trust)",
        "sha_before_rollback": pre_sha, "sha_after_rollback": post_sha,
        "expected_sha": EXPECTED_SHA,
        "row_counts": {"evidence": n_ev, "profiles": n_fp},
        "integrity": integ, "r4": r4,
        "whiskysaga_conflict_pairs_absent": ok_absent,
        "verification_status": "PASS" if not failures else "FAIL",
    }
    out = ROOT / "output/gate_exact_only/rollback_closure.json"
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  closure: {out}")
    print(f"\n  RESULT: {'ROLLBACK VERIFIED' if not failures else 'FAILED: ' + ','.join(failures)}")
    return 0 if not failures else 4


if __name__ == "__main__":
    sys.exit(main())
