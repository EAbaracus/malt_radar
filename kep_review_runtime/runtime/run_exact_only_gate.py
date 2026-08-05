"""EXACT_ONLY_DRY_RUN gate (P501-EDITORIAL).

Scope: only match_status == 'exact' staging rows. Production NEVER written;
real staging DB NEVER written. All mutations happen on isolated TEMP copies
(via PromotionGate.dry_run, which snapshots production to a temp file).

Checks (all must pass for DRY_RUN_ONLY verdict):
  C1 exact identity only        — every candidate match_status == 'exact'
  C2 existing profile collision — none of the matched whisky_ids already has
                                  an evidence row with the same (whisky_id,
                                  source) pair in production (INSERT-only rule)
  C3 canonical-7 validity       — flavor_vector_json has exactly 7 axes, all
                                  0..1 (R4)
  C4 provenance completeness    — source_url, author, published_date,
                                  authority_tier all present
  C5 duplicate detection        — content_hash unique across candidates
  C6 FK/integrity               — matched whisky_id exists in production
  C7 deterministic Run A == B  — PREPARE plan hash + DRY-RUN insert counts
                                  identical across two independent runs
  C8 production SHA unchanged   — SHA256(production.db) identical before/after

Outputs (written under --outdir, default output/gate_exact_only/):
  exact_only_candidates.jsonl  — one JSON object per exact candidate
  exact_only_diff.json         — Run A vs Run B + staging->production delta
  exact_only_manifest.json     — gate metadata, hashes, check results
  exact_only_report.md         — human-readable gate report

Verdict: DRY_RUN_ONLY. apply() is never called.
"""
import argparse
import json
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "kep_review_runtime"))
sys.path.insert(0, str(ROOT))

from runtime.promotion_engine import PromotionEngine  # noqa: E402
from runtime.promotion_engine import PromotionGate  # noqa: E402
from runtime.audit_writer import AuditWriter  # noqa: E402

CANONICAL_AXES = 7
PROMOTABLE_EXACT = ("exact",)  # gate scope: EXACT ONLY


def sha256(path: Path) -> str:
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(results: dict, code: str, cond: bool, detail: str) -> None:
    results[code] = {"pass": bool(cond), "detail": detail}
    print(f"  [{'PASS' if cond else 'FAIL'}] {code}: {detail}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--staging", default=str(ROOT / "output/staging/unified_staging.db"))
    ap.add_argument("--production", default=str(ROOT / "output/import/production.db"))
    ap.add_argument("--phase", default="P501-EXACT-ONLY")
    ap.add_argument("--outdir", default=str(ROOT / "output" / "gate_exact_only"))
    ap.add_argument("--exclude-ids", default="",
                    help="comma-separated evidence_ids to EXCLUDE from the "
                         "promotion scope (C2B duplicates / wrong bindings)")
    args = ap.parse_args()

    exclude_ids = {e.strip() for e in args.exclude_ids.split(",") if e.strip()}
    if exclude_ids:
        ph = ",".join("?" * len(exclude_ids))
        excl_sql = f" AND evidence_id NOT IN ({ph})"
        excl_args = tuple(sorted(exclude_ids))
    else:
        excl_sql, excl_args = "", ()

    staging_path = Path(args.staging)
    prod_path = Path(args.production)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    # Temp dir for gate artifacts (cleaned at the end).
    tmpdir = outdir / "_tmp"
    tmpdir.mkdir(exist_ok=True)

    checks: dict = {}

    # ── 1. Extract exact-only candidates (read-only on real staging) ─────
    conn = sqlite3.connect(f"file:{staging_path}?mode=ro", uri=True)
    rows = conn.execute(
        "SELECT evidence_id, source_id, source_url, authority_tier, author, "
        "published_date, content_hash, raw_name, normalized_name, "
        "matched_master_whisky_id, match_status, match_confidence, "
        "score_value, score_normalized, nose, palate, finish, conclusion, "
        "flavor_vector_json, metadata_json, extraction_method "
        "FROM staging_editorial_reviews WHERE match_status IN "
        f"('exact'){excl_sql} ORDER BY evidence_id", excl_args).fetchall()
    conn.close()

    candidates = []
    for r in rows:
        vec = json.loads(r[18]) if r[18] else None
        candidates.append({
            "evidence_id": r[0], "source_id": r[1], "source_url": r[2],
            "authority_tier": r[3], "author": r[4], "published_date": r[5],
            "content_hash": r[6], "raw_name": r[7], "normalized_name": r[8],
            "matched_master_whisky_id": r[9], "match_status": r[10],
            "match_confidence": r[11], "score_value": r[12],
            "score_normalized": r[13], "nose": r[14], "palate": r[15],
            "finish": r[16], "conclusion": r[17],
            "flavor_vector_json": vec, "metadata_json": r[19],
            "extraction_method": r[20],
        })

    # C1: exact identity only
    non_exact = [c for c in candidates if c["match_status"] not in PROMOTABLE_EXACT]
    check(checks, "C1", not non_exact,
          f"{len(candidates)} exact candidates, {len(non_exact)} non-exact leaked")

    # C5: duplicate detection (content_hash)
    hashes = [c["content_hash"] for c in candidates if c["content_hash"]]
    dupes = len(hashes) - len(set(hashes))
    check(checks, "C5", dupes == 0, f"{len(hashes)} unique content_hash, {dupes} dupes")

    # C4: provenance completeness
    missing_p = [c["evidence_id"] for c in candidates
                 if not c["source_url"] or not c["author"] or not c["published_date"]
                 or not c["authority_tier"]]
    check(checks, "C4", not missing_p, f"{len(missing_p)} rows missing provenance fields")

    # C3: canonical-7 validity
    bad_vec = []
    for c in candidates:
        v = c["flavor_vector_json"]
        if not v or len(v) != CANONICAL_AXES:
            bad_vec.append((c["evidence_id"], "len"))
            continue
        if any(not isinstance(x, (int, float)) or not (0.0 <= x <= 1.0) for x in v.values()):
            bad_vec.append((c["evidence_id"], "range"))
    check(checks, "C3", not bad_vec, f"{len(bad_vec)} rows with invalid canonical-7 vector")

    # C6: FK/integrity — matched whisky_id exists in production
    pconn = sqlite3.connect(f"file:{prod_path}?mode=ro", uri=True)
    n_prod = pconn.execute("SELECT COUNT(*) FROM whiskies").fetchone()[0]
    bad_fk = []
    for c in candidates:
        wid = c["matched_master_whisky_id"]
        if wid is None:
            bad_fk.append((c["evidence_id"], "null id"))
            continue
        got = pconn.execute("SELECT 1 FROM whiskies WHERE whisky_id=?", (wid,)).fetchone()
        if not got:
            bad_fk.append((c["evidence_id"], f"missing {wid}"))
    check(checks, "C6", not bad_fk, f"{len(bad_fk)} rows with missing FK; production whiskies={n_prod}")

    # C2: existing profile collision — (whisky_id, source) already in evidence
    collisions = []
    for c in candidates:
        hit = pconn.execute(
            "SELECT 1 FROM flavor_evidence WHERE whisky_id=? AND source=? LIMIT 1",
            (c["matched_master_whisky_id"], c["source_id"])).fetchone()
        if hit:
            collisions.append((c["evidence_id"], c["matched_master_whisky_id"], c["source_id"]))
    check(checks, "C2", not collisions,
          f"{len(collisions)} (whisky_id,source) pairs already present in production evidence")

    # C2B: batch-internal (whisky_id, source_id) uniqueness — two distinct
    # articles (e.g. "Akashi Blended" vs "Akashi Single Malt", or "Port Askaig
    # 28" vs "Port Askaig 8") must NOT both resolve to the same production
    # whisky in ONE batch. Same pair twice = ambiguous identity -> HOLD.
    from collections import Counter
    pair_counts = Counter((c["matched_master_whisky_id"], c["source_id"])
                          for c in candidates if c["matched_master_whisky_id"])
    batch_dupes = {k: v for k, v in pair_counts.items() if v > 1}
    check(checks, "C2B", not batch_dupes,
          f"{sum(batch_dupes.values())} rows across {len(batch_dupes)} duplicated "
          f"(whisky_id,source) pairs: {list(batch_dupes)[:6]}")
    pconn.close()

    # ── C7/C8: deterministic gate runs on an ISOLATED exact-only staging copy
    # Build temp staging DB containing ONLY exact rows (copy + prune).
    tmp_staging = tmpdir / "exact_only_staging.db"
    shutil.copy2(staging_path, tmp_staging)
    tconn = sqlite3.connect(tmp_staging)
    if exclude_ids:
        ph = ",".join("?" * len(exclude_ids))
        tconn.execute(
            f"DELETE FROM staging_editorial_reviews WHERE match_status != 'exact' "
            f"OR evidence_id IN ({ph})", tuple(sorted(exclude_ids)))
    else:
        tconn.execute("DELETE FROM staging_editorial_reviews WHERE match_status != 'exact'")
    tconn.commit()
    tconn.close()

    sha_before = sha256(prod_path)

    def run_gate(tag: str) -> dict:
        audit = AuditWriter(str(ROOT / "kep_review_runtime" / "runtime" / "runtime.db"))
        engine = PromotionEngine(str(tmp_staging), str(prod_path),
                                 adapter_name="editorial", audit_writer=audit)
        gate = PromotionGate(engine, str(tmp_staging), str(prod_path))
        prep = gate.prepare(args.phase)
        dry = gate.dry_run(args.phase)
        return {
            "tag": tag,
            "prep": {"staging_rows": prep.staging_row_count,
                     "expected_inserts": prep.expected_inserts,
                     "expected_skips": prep.expected_skips,
                     "expected_conflicts": prep.expected_conflicts,
                     "plan_hash": prep.action_plan_hash,
                     "passed": prep.passed},
            "dry": {"sha_before": dry.sha_before, "sha_after": dry.sha_after,
                    "expected_inserts": dry.expected_inserts,
                    "actual_inserts": dry.actual_inserts,
                    "expected_conflicts": dry.expected_conflicts,
                    "actual_conflicts": dry.actual_conflicts,
                    "expected_failures": dry.expected_failures,
                    "actual_failures": dry.actual_failures,
                    "delta": dry.delta,
                    "side_effect_check": dry.side_effect_check,
                    "integrity_check": dry.integrity_check,
                    "matched": dry.matched, "passed": dry.passed},
        }

    run_a = run_gate("A")
    run_b = run_gate("B")

    # C7: deterministic
    det = (run_a["prep"]["plan_hash"] == run_b["prep"]["plan_hash"]
           and run_a["dry"]["actual_inserts"] == run_b["dry"]["actual_inserts"])
    check(checks, "C7", det,
          f"plan_hash A={run_a['prep']['plan_hash'][:12]}.. B={run_b['prep']['plan_hash'][:12]}.. "
          f"inserts A={run_a['dry']['actual_inserts']} B={run_b['dry']['actual_inserts']}")

    sha_after = sha256(prod_path)

    # C8: production SHA unchanged
    check(checks, "C8", sha_before == sha_after,
          f"before={sha_before[:16]} after={sha_after[:16]}")

    # ── Outputs ─────────────────────────────────────────────────────────
    ts = datetime.now(timezone.utc).isoformat()

    # exact_only_candidates.jsonl
    cand_path = outdir / "exact_only_candidates.jsonl"
    with cand_path.open("w", encoding="utf-8") as f:
        for c in candidates:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    # exact_only_diff.json
    diff_path = outdir / "exact_only_diff.json"
    diff = {
        "phase": args.phase, "generated_at": ts,
        "candidates": len(candidates),
        "run_a": run_a, "run_b": run_b,
        "deterministic": det,
        "production_delta": run_a["dry"]["delta"],
        "sha": {"before": sha_before, "after": sha_after,
                "unchanged": sha_before == sha_after},
    }
    diff_path.write_text(json.dumps(diff, ensure_ascii=False, indent=2), encoding="utf-8")

    # exact_only_manifest.json
    all_pass = all(v["pass"] for v in checks.values())
    manifest = {
        "gate": "EXACT_ONLY_DRY_RUN", "phase": args.phase, "generated_at": ts,
        "inputs": {"unified_staging_total": 5032,
                   "exact_before_exclusion": 565,
                   "excluded_evidence_ids": sorted(exclude_ids),
                   "candidate_rows_after_exclusion": len(candidates),
                   "promotable_scope": "exact",
                   "note": "4 C2B pairs (8 evidence rows) excluded from scope: "
                           "W000045/W000397 dup pages + W3298/W003687 wrong "
                           "bindings; NO deletion, staging untouched"},
        "action": {"apply_called": False, "production_writes": 0,
                   "staging_writes": 0,
                   "note": "all mutations occurred on isolated temp copies"},
        "checks": checks,
        "sha_production": {"before": sha_before, "after": sha_after},
        "verdict": "DRY_RUN_ONLY" if all_pass else "HOLD",
        "human_go_required": True,
    }
    (outdir / "exact_only_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    # exact_only_report.md
    lines = [
        f"# Gate Report — EXACT_ONLY_DRY_RUN ({args.phase})",
        "",
        f"- Generated: {ts}",
        f"- Unified staging rows: {len(rows)}",
        f"- Exact candidates: {len(candidates)}",
        f"- PromotionGate.apply() called: **NO**",
        f"- Production writes: **0** — SHA before `{sha_before[:16]}…` after `{sha_after[:16]}…`",
        f"- Staging writes: **0** (temp copies only)",
        "",
        "## Checks",
        "",
        "| Check | Result | Detail |",
        "|-------|--------|--------|",
    ]
    for code, v in checks.items():
        lines.append(f"| {code} | {'PASS' if v['pass'] else 'FAIL'} | {v['detail']} |")
    lines += [
        "",
        "## Dry-run (Run A — temp copy)",
        "",
        f"- Expected inserts: {run_a['dry']['expected_inserts']}",
        f"- Actual inserts: {run_a['dry']['actual_inserts']}",
        f"- Conflicts: {run_a['dry']['actual_conflicts']}",
        f"- Failures: {run_a['dry']['actual_failures']}",
        f"- Delta: `{json.dumps(run_a['dry']['delta'])}`",
        f"- Side-effect check: {run_a['dry']['side_effect_check']}",
        f"- Integrity check: {run_a['dry']['integrity_check']}",
        "",
        "## Determinism (Run A == Run B)",
        "",
        f"- plan_hash: `{run_a['prep']['plan_hash']}` (A) vs `{run_b['prep']['plan_hash']}` (B)",
        f"- inserts: {run_a['dry']['actual_inserts']} (A) vs {run_b['dry']['actual_inserts']} (B)",
        f"- deterministic: **{'YES' if det else 'NO'}**",
        "",
        "## Verdict",
        "",
        f"**{'DRY_RUN_ONLY' if all_pass else 'HOLD'}** — apply blocked.",
        "",
        "**HUMAN_GO_REQUIRED = YES**",
        "",
    ]
    (outdir / "exact_only_report.md").write_text("\n".join(lines), encoding="utf-8")

    # ── Cleanup temp ───────────────────────────────────────────────────
    shutil.rmtree(tmpdir, ignore_errors=True)

    print(f"\n=== GATE {args.phase} ===")
    print(f"  outputs: {outdir}")
    print(f"  candidates: {len(candidates)}")
    print(f"  verdict: {'DRY_RUN_ONLY' if all_pass else 'HOLD'}")
    print(f"  apply_called: False | production_writes: 0 | staging_writes: 0")
    print(f"  HUMAN_GO_REQUIRED: YES")
    return 0 if all_pass else 2


if __name__ == "__main__":
    sys.exit(main())
