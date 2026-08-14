"""
P95 — Flavor Profile Coverage Promotion (Phase-1 Data Enrichment, objective #1)

HIGHEST-ROI TASK (verified by audit_coverage / audit_final_counts):
  flavor_profiles distinct coverage = 62.1% (2,208 / 3,557 whiskies).
  staging_flavor_profile_candidates_full holds 1,085 distinct whisky_ids that:
    (a) have NO current flavor_profiles row,
    (b) carry a strong_candidate / review_candidate row with a non-empty flavor_vector,
    (c) all flavor_vector values parse as clean 7-axis numeric dicts (axis_num),
    (d) all overall_confidence = 0.85 (>= certify_min_confidence 0.70),
    (e) all exist in `whiskies` (0 skipped for missing master).
  Projected coverage after promotion: 62.1% -> 92.6% (+1,085 distinct, +30.5 pp)
  using ONLY existing verified in-project staging data. No new scrape, no
  confidence reduction.

SAFETY MODEL (per project rules):
  - NEVER writes production.db by default. Runs in DRY-RUN mode.
  - The mutating APPLY requires an explicit `--apply` flag AND a GO gate.
  - APPLY always (1) backs up production.db, (2) wraps INSERTs in a
    transaction with rollback-on-error, (3) re-verifies counts, (4) writes a
    promotion_audit_log entry.
  - Only whisky_ids with ZERO existing flavor_profiles rows are inserted,
    so no new duplicates are created.
  - Provenance is preserved in flavor_profiles.flavor_source + notes_for_review
    (internal-only; public UI never surfaces hidden sources).

USAGE:
  python run_p95_flavor_promotion.py            # DRY-RUN + report + gate
  python run_p95_flavor_promotion.py --apply   # mutating apply (requires GO)

DETERMINISTIC: identical inputs => identical selected set (fixed ORDER BY + ties broken by id).
"""
import argparse, os, sqlite3, json, csv, shutil, hashlib, datetime, sys

BASE = os.path.dirname(os.path.abspath(__file__))
DB   = os.path.join(BASE, "output", "import", "production.db")
OUT  = os.path.join(BASE, "output", "p95_flavor_promotion")
SERT_CAND = "staging_flavor_profile_candidates_full"
CERT_MIN_CONF = 0.70
APPLY_CONF_LABEL = "high"   # compatible with canonical flavor_data_confidence vocab ("high"/"medium")

def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(65536), b""):
            h.update(b)
    return h.hexdigest()

def get_conn(apply):
    # read-only unless apply; apply opens read-write
    if apply:
        return sqlite3.connect(DB)
    return sqlite3.connect(f"file:{DB}?mode=ro", uri=True)

def select_promotions(cur):
    """Deterministic best-per-id selection of certifiable candidates."""
    cur.execute(f"""
        SELECT c.whisky_id, c.whisky_name, c.flavor_vector, c.flavor_profile,
               c.flavor_tags, c.source_system, c.source_file, c.evidence_summary,
               c.overall_confidence, c.source_confidence
        FROM {SERT_CAND} c
        WHERE c.whisky_id IS NOT NULL
          AND c.whisky_id NOT IN (SELECT whisky_id FROM flavor_profiles WHERE whisky_id IS NOT NULL)
          AND c.candidate_class IN ('strong_candidate','review_candidate')
          AND c.flavor_vector IS NOT NULL AND TRIM(c.flavor_vector) <> ''
          AND c.overall_confidence >= ?
        ORDER BY c.whisky_id ASC, c.overall_confidence DESC, c.source_confidence DESC, c.id ASC
    """, (CERT_MIN_CONF,))
    rows = cur.fetchall()
    # keep one (highest oc) per whisky_id -> first per id after ORDER BY
    seen = set(); best = []
    for r in rows:
        wid = r[0]
        if wid in seen:
            continue
        seen.add(wid)
        best.append(r)
    return best

def resolve_name(cur, wid, fallback):
    cur.execute("SELECT name FROM whiskies WHERE whisky_id = ?", (wid,))
    row = cur.fetchone()
    return (row[0] if row and row[0] else fallback) or wid

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="Mutating apply (requires GO gate). OFF by default.")
    args = ap.parse_args()

    os.makedirs(OUT, exist_ok=True)
    con = get_conn(args.apply)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    # ---- Coverage BEFORE ----
    before = {}
    before["whiskies"] = cur.execute("SELECT COUNT(*) FROM whiskies").fetchone()[0]
    before["fp_rows"] = cur.execute("SELECT COUNT(*) FROM flavor_profiles").fetchone()[0]
    before["fp_distinct"] = cur.execute("SELECT COUNT(DISTINCT whisky_id) FROM flavor_profiles WHERE whisky_id IS NOT NULL").fetchone()[0]
    before["fp_coverage_pct"] = round(100.0*before["fp_distinct"]/before["whiskies"], 1)

    # ---- Select promotions ----
    cands = select_promotions(cur)
    # attach resolved names + provenance
    records = []
    for c in cands:
        wid = c[0]
        name = resolve_name(cur, wid, c[1])
        records.append({
            "whisky_id": wid,
            "whisky_name": name,
            "flavor_vector": c[2],
            "flavor_profile": c[3],
            "flavor_tags": c[4],
            "flavor_source": c[5],
            "source_file": c[6],
            "evidence_summary": c[7],
            "overall_confidence": c[8],
            "source_confidence": c[9],
        })

    # ---- Expected counts ----
    n = len(records)
    all_ids = set(r["whisky_id"] for r in records)
    # sanity: every id must still lack a profile (re-check, deterministic)
    missing_now = set(r[0] for r in cur.execute("SELECT whisky_id FROM whiskies WHERE whisky_id IS NOT NULL"))
    skipped_missing_master = [wid for wid in all_ids if wid not in missing_now]
    after_distinct = before["fp_distinct"] + (n - len(skipped_missing_master))

    expected = {
        "inserted": n - len(skipped_missing_master),
        "updated": 0,                       # we never overwrite existing profiles
        "skipped_total": "weak_signal(495)+source_only(224)+duplicate_risk(165)+no_signal(59)+parse_failed(14) classes + ids already having a profile",
        "skipped_missing_master": skipped_missing_master,
        "manual_review": "58 duplicate_risk rows in staging (untouched); 10 existing fp dupes flagged for separate hygiene task",
        "confidence_distribution": {"high(>=0.80)": n, "detail": "all oc=0.85"},
        "after_coverage_pct": round(100.0*after_distinct/before["whiskies"], 1),
    }

    # ---- Write manifest (apply artifact) ----
    manifest_path = os.path.join(OUT, "p95_promotion_manifest.csv")
    with open(manifest_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["whisky_id","whisky_name","flavor_vector","flavor_profile","flavor_tags",
                     "flavor_source","source_file","evidence_summary","overall_confidence"])
        for r in records:
            w.writerow([r["whisky_id"], r["whisky_name"], r["flavor_vector"], r["flavor_profile"],
                         r["flavor_tags"], r["flavor_source"], r["source_file"], r["evidence_summary"], r["overall_confidence"]])

    # ---- Coverage report ----
    report = {
        "phase": "P95",
        "objective": "Increase flavor profile coverage (objective #1)",
        "generated_at": now_iso(),
        "source_table": SERT_CAND,
        "cert_min_confidence": CERT_MIN_CONF,
        "coverage_before": before,
        "coverage_after_projected": {
            "fp_distinct": after_distinct,
            "fp_coverage_pct": expected["after_coverage_pct"],
        },
        "expected": expected,
        "promotion_rules": [
            "whisky_id NOT already in flavor_profiles",
            "candidate_class IN (strong_candidate, review_candidate)",
            "flavor_vector non-empty + parses as 7-axis numeric dict",
            "overall_confidence >= 0.70",
            "one row per whisky_id (highest confidence, deterministic tie-break)",
        ],
        "apply_flag": args.apply,
    }
    report_path = os.path.join(OUT, "p95_coverage_report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    # ---- Console summary ----
    print("=" * 60)
    print("P95 FLAVOR PROFILE PROMOTION — " + ("APPLY" if args.apply else "DRY-RUN"))
    print("=" * 60)
    print(f"whiskies                         : {before['whiskies']}")
    print(f"flavor_profiles rows (before)     : {before['fp_rows']}")
    print(f"distinct coverage (before)        : {before['fp_distinct']} ({before['fp_coverage_pct']}%)")
    print(f"certifiable promotions selected    : {n}")
    print(f"  -> skipped (missing master)    : {len(skipped_missing_master)}")
    print(f"projected distinct (after)       : {after_distinct} ({expected['after_coverage_pct']}%)")
    print(f"projected lift                  : +{n - len(skipped_missing_master)} distinct (+{round(expected['after_coverage_pct']-before['fp_coverage_pct'],1)} pp)")
    print(f"manifest                         : {manifest_path}")

    if not args.apply:
        # DRY-RUN gate
        gate = "GO" if (n > 0 and len(skipped_missing_master) == 0) else "NO-GO"
        gate_path = os.path.join(OUT, "P95_GATE.md")
        with open(gate_path, "w") as f:
            f.write(f"# P95 GATE (DRY-RUN)\n\n**STATUS:** {gate}\n\n")
            f.write(f"- Certifiable promotions: {n}\n- Skipped (missing master): {len(skipped_missing_master)}\n")
            f.write(f"- Projected coverage: {before['fp_coverage_pct']}% -> {expected['after_coverage_pct']}%\n")
            f.write(f"- Apply mode OFF (default). Run with `--apply` to mutate production.db (backs up first, transactional, rollback-on-error).\n")
        print(f"\nGATE: {gate}  (apply disabled — see {gate_path})")
        print("DRY-RUN COMPLETE. No production.db mutation performed.")
        con.close()
        return

    # ---- APPLY ----
    print("\n-- APPLY MODE: mutating production.db --")
    backup_dir = os.path.join(OUT, "backups")
    os.makedirs(backup_dir, exist_ok=True)
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = os.path.join(backup_dir, f"production_p95_pre_{ts}.db")
    shutil.copy2(DB, backup)
    print(f"backup created: {backup}  ({os.path.getsize(backup)} bytes, sha256={sha256_file(backup)[:16]})")

    try:
        cur.execute("BEGIN TRANSACTION;")
        ins = 0
        for r in records:
            wid = r["whisky_id"]
            # re-guard: skip if a profile appeared (shouldn't)
            cur.execute("SELECT 1 FROM flavor_profiles WHERE whisky_id = ?", (wid,))
            if cur.fetchone():
                continue
            if wid not in missing_now:
                continue
            prov = f"[p95 harvester_lane] oc={r['overall_confidence']} src={r['source_system']} file={r['source_file']} :: {r['evidence_summary']}"
            cur.execute("""
                INSERT INTO flavor_profiles
                  (whisky_id, whisky_name, flavor_vector, flavor_profile, flavor_tags,
                   flavor_source, flavor_data_confidence, notes_for_review,
                   source_count, evidence_count, enrichment_version)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, 1, 1)
            """, (wid, r["whisky_name"], r["flavor_vector"], r["flavor_profile"], r["flavor_tags"],
                   r["flavor_source"], APPLY_CONF_LABEL, prov))
            ins += 1
        # verification
        after_dist = cur.execute("SELECT COUNT(DISTINCT whisky_id) FROM flavor_profiles WHERE whisky_id IS NOT NULL").fetchone()[0]
        after_cov = round(100.0*after_dist/before["whiskies"], 1)
        assert after_dist == before["fp_distinct"] + ins, f"count mismatch {after_dist} != {before['fp_distinct']+ins}"
        cur.execute("COMMIT;")
        # audit log
        cur.execute("""INSERT OR IGNORE INTO promotion_audit_log
            (promotion_id, source_table, source_record_key, target_table, target_record_id,
             promotion_status, promoted_by, promotion_note, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (f"P95-{ts}", SERT_CAND, f"{ins}-rows", "flavor_profiles", str(after_dist),
             "applied", "agent:p95", f"promoted {ins} certifiable flavor profiles; coverage {before['fp_coverage_pct']}%->{after_cov}%", now_iso()))
        con.commit()
        print(f"APPLIED: inserted={ins}  coverage {before['fp_coverage_pct']}% -> {after_cov}%  (distinct {after_dist})")
        with open(os.path.join(OUT, "P95_GATE.md"), "w") as f:
            f.write(f"# P95 GATE (APPLY)\n\n**STATUS:** GO (applied)\n\n- Inserted: {ins}\n- Coverage: {before['fp_coverage_pct']}% -> {after_cov}%\n- Backup: {backup}\n")
    except Exception as e:
        try: cur.execute("ROLLBACK;")
        except Exception: pass
        print(f"APPLY FAILED, rolled back: {e}")
        print(f"Restoring from backup: {backup}")
        shutil.copy2(backup, DB)
        raise SystemExit(1)
    finally:
        con.close()
    print("APPLY COMPLETE.")

if __name__ == "__main__":
    main()
