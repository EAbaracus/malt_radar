# p95b_phase12_execute.py  (AUTHORIZED — Phase B schema + Phase C promotion, gated, rollback-on-fail)
import os, sys, json, sqlite3, hashlib, datetime, uuid
ROOT = r"C:\Users\eltun\Documents\malt radar CLEAN"
PROD = os.path.join(ROOT, "output", "import", "production.db")
BAK  = os.path.join(ROOT, "mr-kep", "p95b_phase12", "backups",
                       "production.db.pre_p95b_phase12.20260718_101917.bak")
AUDIT = {"errors": []}
CANON = ["smoky", "peaty", "fruity", "sweet", "spicy", "maritime", "sherry"]

def sha(p):
    b = open(p, "rb").read(); return hashlib.sha256(b).hexdigest(), len(b)

PRE_SHA, PRE_SZ = sha(PROD)
AUDIT["pre_sha256"] = PRE_SHA; AUDIT["pre_size"] = PRE_SZ
print("PRE_SHA256", PRE_SHA, "size", PRE_SZ)

conn = sqlite3.connect(PROD)
conn.execute("PRAGMA foreign_keys=ON;")
cur = conn.cursor()

# ===================== PHASE B — SCHEMA MIGRATION (single transaction) =====================
try:
    cur.execute("BEGIN")
    cols = [r[1] for r in cur.execute("PRAGMA table_info(flavor_evidence)")]
    if "vector_maritime" not in cols:
        cur.execute("ALTER TABLE flavor_evidence ADD COLUMN vector_maritime REAL")
    conn.commit()
    AUDIT["phase"] = {"B": {"status": "committed", "vector_maritime_added": True,
                                  "vector_rich_retained": True}}
    print("PHASE B: committed (vector_maritime added; vector_rich retained)")
except Exception as e:
    conn.rollback()
    AUDIT["errors"].append(f"PHASE B FAILED: {e}")
    conn.close()
    AUDIT["post_sha256"] = sha(PROD)[0]
    json.dump(AUDIT, open(os.path.join(ROOT, "mr-kep", "p95b_phase12", "promotion_audit_log.json"), "w"), indent=2)
    raise SystemExit("FAIL — Rollback executed (Phase B)")

# ===================== PHASE C — PROMOTION (INSERT-only, no overwrite) =====================
try:
    cur.execute("BEGIN")
    exist_ev = set(r[0] for r in cur.execute("SELECT whisky_id FROM flavor_evidence"))
    exist_fp = set(r[0] for r in cur.execute("SELECT whisky_id FROM flavor_profiles"))

    promoted_ev = 0; promoted_fp = 0; skipped = []; promoted_wids = set()
    promoted_fp_wids = set()  # ONLY whisky_ids that received a NEW flavor_profiles row

    # C1: validated BOOK rows (7-axis complete, has whisky_id, NOT already in flavor_evidence)
    book_rows = cur.execute(
        "SELECT whisky_id, whisky_name, smoky, peaty, fruity, sweet, spicy, maritime, sherry "
        "FROM staging_book_flavor_profiles "
        "WHERE whisky_id IS NOT NULL AND smoky>0 AND peaty>0 AND fruity>0 AND sweet>0 "
        "AND spicy>0 AND maritime>0 AND sherry>0").fetchall()
    for r in book_rows:
        wid = r[0]
        if wid in exist_ev:
            skipped.append({"whisky_id": wid, "reason": "already_in_flavor_evidence (authority preserved)"})
            continue
        smoky, peaty, fruity, sweet, spicy, maritime, sherry = [float(x or 0) for x in r[2:9]]
        eid = "P95B_" + uuid.uuid4().hex[:20]
        cur.execute(
            "INSERT INTO flavor_evidence (evidence_id, whisky_id, source, vector_smoky, vector_peaty, "
            "vector_fruity, vector_sweet, vector_spicy, vector_maritime, vector_sherry, vector_rich) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (eid, wid, "book", smoky, peaty, fruity, sweet, spicy, maritime, sherry, None))
        promoted_ev += 1; promoted_wids.add(wid)
        if wid not in exist_fp:
            prof = json.dumps({ax: [smoky, peaty, fruity, sweet, spicy, maritime, sherry][i] for i, ax in enumerate(CANON)})
            cur.execute("INSERT INTO flavor_profiles (whisky_id, flavor_profile) VALUES (?,?)", (wid, prof))
            promoted_fp += 1; promoted_fp_wids.add(wid)
    AUDIT["phase"]["C_book"] = {"candidates": len(book_rows), "promoted_evidence": promoted_ev,
                                   "promoted_profiles": promoted_fp}

    # C2: TASTING NOTES resolved via crosswalk (matched_master_whisky_id), not rejected
    note_rows = cur.execute(
        "SELECT staging_note_id, matched_master_whisky_id, nose, palate, finish FROM staging_tasting_notes "
        "WHERE matched_master_whisky_id IS NOT NULL AND approval_status NOT IN ('staging_quality_rejected')"
        ).fetchall()
    sys.path.insert(0, os.path.join(ROOT, "mr-kep", "d4_reducer"))
    from flavor_mapper import FlavorMapper
    from axis_reducer import AxisReducer
    from ambiguity_handler import AmbiguityHandler
    mapper = FlavorMapper(); ah = AmbiguityHandler(); reducer = AxisReducer(mapper, ah)
    import re
    KW = re.compile(r"\b(sea|salt|brine|maritime|coastal|ocean|kelp|iodine|seaweed|medicinal|peat|smoke|smoky|apple|citrus|honey|vanilla|cinnamon|pepper|oak|sherry|raisin)\w*", re.I)
    note_promoted = 0
    for r in note_rows:
        snid, wid, nose, palate, finish = r
        if wid in exist_ev:
            skipped.append({"whisky_id": wid, "staging_note_id": snid,
                           "reason": "tasting note whisky_id already_in_flavor_evidence (authority preserved)"})
            continue
        txt = " ".join(str(x) for x in (nose, palate, finish) if x)
        words = set(w.lower() for w in KW.findall(txt))
        if not words:
            skipped.append({"whisky_id": wid, "staging_note_id": snid,
                           "reason": "no canonical descriptor tokens extracted"})
            continue
        descs = [{"descriptor": w, "intensity": 3, "fact_id": f"note:{snid}:{w}"} for w in words]
        result, _ = reducer.reduce_entity_flavor(str(wid), descs)
        canon = result["canonical_vectors"]  # 7 axes, 0-100
        eid = "P95B_" + uuid.uuid4().hex[:20]
        cur.execute(
            "INSERT INTO flavor_evidence (evidence_id, whisky_id, source, vector_smoky, vector_peaty, "
            "vector_fruity, vector_sweet, vector_spicy, vector_maritime, vector_sherry, vector_rich) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (eid, wid, "tasting_note", canon["smoky"], canon["peaty"], canon["fruity"], canon["sweet"],
             canon["spicy"], canon["maritime"], canon["sherry"], None))
        note_promoted += 1; promoted_wids.add(wid)
        if wid not in exist_fp:
            prof = json.dumps(canon)
            cur.execute("INSERT INTO flavor_profiles (whisky_id, flavor_profile) VALUES (?,?)", (wid, prof))
            promoted_fp += 1; promoted_fp_wids.add(wid)
    AUDIT["phase"]["C_tasting"] = {"candidates": len(note_rows), "promoted_evidence": note_promoted}
    AUDIT["skipped"] = skipped
    conn.commit()
    AUDIT["phase"]["C"] = {"status": "committed", "promoted_evidence_total": promoted_ev + note_promoted,
                              "promoted_profiles_total": promoted_fp, "skipped_count": len(skipped)}
    print(f"PHASE C: committed (book_ev={promoted_ev}, note_ev={note_promoted}, profiles={promoted_fp}, skipped={len(skipped)})")
except Exception as e:
    conn.rollback()
    AUDIT["errors"].append(f"PHASE C FAILED: {e}")
    conn.close()
    json.dump(AUDIT, open(os.path.join(ROOT, "mr-kep", "p95b_phase12", "promotion_audit_log.json"), "w"), indent=2)
    raise SystemExit("FAIL — Rollback executed (Phase C)")

# ===================== PHASE D — VALIDATION =====================
POST_SHA, POST_SZ = sha(PROD)
AUDIT["post_sha256"] = POST_SHA; AUDIT["post_size"] = POST_SZ
post = conn.cursor()
v = {}
v["migration_committed"] = True
v["vector_maritime_exists"] = any(r[1] == "vector_maritime" for r in post.execute("PRAGMA table_info(flavor_evidence)"))
v["evidence_rows_before"] = 791
v["evidence_rows_after"] = post.execute("SELECT COUNT(*) FROM flavor_evidence").fetchone()[0]
v["evidence_id_unique"] = list(post.execute("SELECT COUNT(*), COUNT(DISTINCT evidence_id) FROM flavor_evidence").fetchone())
v["null_whisky_in_evidence"] = post.execute("SELECT COUNT(*) FROM flavor_evidence WHERE whisky_id IS NULL").fetchone()[0]
# validate ONLY promoted profiles (7 canonical axes exactly)
bad = 0; total_fp = 0
ph = ",".join("?" * len(promoted_fp_wids)) or "NULL"
for wid, fp in post.execute(
        "SELECT whisky_id, flavor_profile FROM flavor_profiles WHERE whisky_id IN ({})".format(ph),
        list(promoted_fp_wids)):
    if not fp: continue
    total_fp += 1
    try:
        d = json.loads(fp)
        if set(d.keys()) != set(CANON): bad += 1
    except Exception:
        bad += 1
v["flavor_profiles_promoted_checked"] = total_fp
v["flavor_profiles_promoted_bad_axis_count"] = bad
mar_nonnull = post.execute("SELECT COUNT(*) FROM flavor_evidence WHERE vector_maritime IS NOT NULL").fetchone()[0]
rich_present = post.execute("SELECT COUNT(*) FROM flavor_evidence WHERE vector_rich IS NOT NULL").fetchone()[0]
v["vector_maritime_nonnull"] = mar_nonnull
v["vector_rich_present"] = rich_present
integ = post.execute("PRAGMA integrity_check").fetchone()[0]
v["integrity_check"] = integ
AUDIT["validation"] = v

gates = (v["vector_maritime_exists"] and v["evidence_id_unique"][0] == v["evidence_id_unique"][1]
          and v["null_whisky_in_evidence"] == 0 and v["flavor_profiles_promoted_bad_axis_count"] == 0
          and integ == "ok")
AUDIT["validation_passed"] = bool(gates)
print("PHASE D validation:", json.dumps(v, indent=2))
conn.close()

# regression (P95B-FIX-02 suite)
import subprocess
r = subprocess.run([sys.executable, "-m", "pytest", "mr-kep/p95b_fix02/test_canonical_axes.py", "-q"],
                   cwd=ROOT, capture_output=True, text=True, timeout=120)
AUDIT["regression"] = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr.strip()[:200]
AUDIT["regression_passed"] = (r.returncode == 0)

ALL_OK = bool(gates and AUDIT["regression_passed"])
AUDIT["all_gates_passed"] = ALL_OK

if not ALL_OK:
    # RULE: if any gate fails, perform FULL rollback and report NO-GO.
    import shutil as _sh
    _sh.copyfile(BAK, PROD)
    rb = hashlib.sha256(open(PROD, "rb").read()).hexdigest()
    AUDIT["rollback_executed"] = True
    AUDIT["post_rollback_sha256"] = rb
    AUDIT["post_rollback_matches_pre"] = (rb == PRE_SHA)
    json.dump(AUDIT, open(os.path.join(ROOT, "mr-kep", "p95b_phase12", "promotion_audit_log.json"), "w"), indent=2)
    print("\nFINAL: FAIL — Rollback executed (gates={}, regression={})".format(ALL_OK, AUDIT["regression_passed"]))
else:
    AUDIT["rollback_executed"] = False
    AUDIT["post_sha256"] = sha(PROD)[0]
    json.dump(AUDIT, open(os.path.join(ROOT, "mr-kep", "p95b_phase12", "promotion_audit_log.json"), "w"), indent=2)
    print("\nFINAL: PASS — Phase 12 completed successfully")
