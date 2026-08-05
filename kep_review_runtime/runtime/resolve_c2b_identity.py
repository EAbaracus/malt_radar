"""C2B identity/evidence resolution — 8 held staging records (P501-C2B-01).

USER RULE: NO deletion. The 8 records are resolved at identity level:
  - duplicate-review pairs (Redbreast 21, Jura 18): newer/complete article is
    canonical (stays exact & promotable), the older one is marked
    'duplicate_of' (manual_review, metadata annotation) — stays in staging,
    never promoted
  - wrong bindings (Akashi): rebound to the CORRECT production master
    (W001357 white oak akashi blended / W000888 white oak akashi single malt)
  - GlenAllachie 15 YO stays W003687 (correct); the 15 YO Limited Edition has
    NO matching production master and cannot be auto-bound -> manual_review

Outputs an ISOLATED staging DB (output/staging/c2b_resolved_staging.db) for a
DEDICATED staging->gate->promotion lifecycle. unified_staging.db untouched.
Writes: staging only. Production: read-only.
"""
import json
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC_STAGING = ROOT / "output/staging/unified_staging.db"
OUT_STAGING = ROOT / "output/staging/c2b_resolved_staging.db"
MANIFEST = ROOT / "output/gate_exact_only/c2b_identity_resolution.json"

# evidence_id -> {new_master, new_status, reason}
RESOLUTIONS = {
    "EDR-160e45ebc546775a": {"master": "W000045", "status": "exact",
                             "kind": "canonical",
                             "reason": "Redbreast 21 YO kanonik inceleme (2025-10-30, score 91, tam N/P/F)"},
    "EDR-8ad8f4cb22be8547": {"master": "W000045", "status": "manual_review",
                             "kind": "duplicate_of:EDR-160e45ebc546775a",
                             "reason": "Redbreast 21 YO eski 2. inceleme (2017-01-06, skor yok, finish yok) — "
                                       "aynı (whisky_id,source) çifti; kanonik 2025 kaydı seçildi"},
    "EDR-b6b04a401c3de71a": {"master": "W000397", "status": "exact",
                             "kind": "canonical",
                             "reason": "Jura 18 YO daha yeni inceleme (2018-09-27, abv 44)"},
    "EDR-00e2925b57923209": {"master": "W000397", "status": "manual_review",
                             "kind": "duplicate_of:EDR-b6b04a401c3de71a",
                             "reason": "Jura 18 YO eski inceleme (2017-06-22, abv 42) — aynı "
                                       "(whisky_id,source) çifti; kanonik 2018 kaydı seçildi"},
    "EDR-c3b06120cdf3565b": {"master": "W001357", "status": "exact",
                             "kind": "rebind",
                             "reason": "Akashi Blended Whisky (40%, Blended) -> W001357 'white oak "
                                       "akashi blended' (jenerik W3298 'Akashi' YANLIŞ bağlamaydı)"},
    "EDR-9a9a8742d1a1921f": {"master": "W000888", "status": "exact",
                             "kind": "rebind",
                             "reason": "Akashi Single Malt (46%, Single Malt) -> W000888 'white oak "
                                       "akashi single malt (nas)' (jenerik W3298 YANLIŞ bağlamaydı)"},
    "EDR-e351d627a207d977": {"master": "W003687", "status": "exact",
                             "kind": "canonical",
                             "reason": "GlenAllachie 15 YO (46%, 2021) — W003687 doğru master"},
    "EDR-bb608a438fef0904": {"master": None, "status": "manual_review",
                             "kind": "no_master",
                             "reason": "GlenAllachie 15 YO Limited Edition (54.5%) — production "
                                       "registry'de LE master'ı YOK; otomatik bağlama yapılamaz"},
}
EXPECTED = {
    "canonical_promotable": ["EDR-160e45ebc546775a", "EDR-b6b04a401c3de71a",
                             "EDR-c3b06120cdf3565b", "EDR-9a9a8742d1a1921f",
                             "EDR-e351d627a207d977"],
    "held_not_promotable": ["EDR-8ad8f4cb22be8547", "EDR-00e2925b57923209",
                            "EDR-bb608a438fef0904"],
}

def main() -> int:
    ts = datetime.now(timezone.utc).isoformat()
    shutil.copy2(SRC_STAGING, OUT_STAGING)
    conn = sqlite3.connect(OUT_STAGING)
    conn.execute("BEGIN")
    applied = {}
    for eid, res in RESOLUTIONS.items():
        meta = None
        row = conn.execute(
            "SELECT metadata_json FROM staging_editorial_reviews WHERE evidence_id=?",
            (eid,)).fetchone()
        if row and row[0]:
            meta = json.loads(row[0])
        meta = meta or {}
        meta["c2b_resolution"] = {
            "kind": res["kind"], "reason": res["reason"], "resolved_at": ts,
        }
        conn.execute(
            "UPDATE staging_editorial_reviews SET matched_master_whisky_id=?, "
            "match_status=?, match_confidence=?, metadata_json=? WHERE evidence_id=?",
            (res["master"], res["status"],
             1.0 if res["status"] == "exact" else None,
             json.dumps(meta, ensure_ascii=False), eid))
        applied[eid] = res
    conn.commit()
    conn.close()

    # verify post-update counts
    v = sqlite3.connect(f"file:{OUT_STAGING}?mode=ro", uri=True)
    n_exact = v.execute(
        "SELECT COUNT(*) FROM staging_editorial_reviews WHERE match_status='exact'"
    ).fetchone()[0]
    n_mr = v.execute(
        "SELECT COUNT(*) FROM staging_editorial_reviews WHERE match_status='manual_review'"
    ).fetchone()[0]
    src_unchanged = 0
    u = sqlite3.connect(f"file:{SRC_STAGING}?mode=ro", uri=True)
    for eid in RESOLUTIONS:
        r = u.execute("SELECT match_status FROM staging_editorial_reviews WHERE evidence_id=?",
                      (eid,)).fetchone()
        if r and r[0] == "exact":
            src_unchanged += 1
    u.close()
    v.close()

    doc = {
        "phase": "P501-C2B-01", "generated_at": ts,
        "src_staging": str(SRC_STAGING), "out_staging": str(OUT_STAGING),
        "resolution_count": len(RESOLUTIONS),
        "resolutions": {k: {"master": v["master"], "status": v["status"],
                            "kind": v["kind"], "reason": v["reason"]}
                        for k, v in RESOLUTIONS.items()},
        "expected": EXPECTED,
        "post_update": {"exact": n_exact, "manual_review": n_mr},
        "source_unified_untouched_evidence_ids": RESOLUTIONS.keys().__len__(),
        "user_rule": "NO deletion — all 8 rows remain in staging; held rows are "
                     "manual_review + duplicate_of annotation, not deleted",
        "note": "GlenAllachie 15 YO Limited Edition has no production master -> "
                "manual_review; new master creation is a separate MR-KEP task",
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"c2b_resolved_staging.db: {n_exact} exact, {n_mr} manual_review")
    print(f"unified_staging.db: {src_unchanged}/8 kayıt hâlâ eski durumda (dokunulmadı)")
    print(f"manifest: {MANIFEST}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
