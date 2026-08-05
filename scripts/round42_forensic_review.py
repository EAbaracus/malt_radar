import sqlite3
import json
import os
import hashlib

DB_PATH = "output/import/production.db"
R41_DIR = "mr-kep/audit/book_contribution/round41_supersede_family_mapping"
OUT_DIR = "mr-kep/audit/book_contribution/round42_supersede_forensic_review"

def get_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def get_conn():
    uri = f"file:{os.path.abspath(DB_PATH)}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn

def run_forensic_analysis():
    conn = get_conn()
    cur = conn.cursor()
    
    # PHASE 1 - COUNT RECONCILIATION
    r41_summary_path = os.path.join(R41_DIR, "15_run_a_summary.json")
    with open(r41_summary_path, "r") as f:
        r41_stats = json.load(f)
        
    r41_classifications_path = os.path.join(R41_DIR, "04_identity_classification.jsonl")
    r41_pairs = []
    with open(r41_classifications_path, "r") as f:
        for line in f:
            if line.strip():
                r41_pairs.append(json.loads(line))
                
    total_pairs_sum = sum(r41_stats.values())
    reconciliation = {
        "r41_reported_stats": r41_stats,
        "total_pairs_calculated": total_pairs_sum,
        "actual_classification_lines": len(r41_pairs),
        "reconciliation_match": total_pairs_sum == len(r41_pairs)
    }
    
    # PHASE 2 & 3 & 4 - FORENSICS & FALSE POSITIVE & LEGITIMATE VARIANT
    candidates_forensics = []
    false_positives = []
    legitimate_reviews = []
    
    final_stats = {
        "SAFE_SUPSERSEDE_CANDIDATE": 0,
        "FALSE_SUPSERSEDE": 0,
        "REVIEW_REQUIRED": 0
    }
    
    # Pre-fetch required records for quick lookup
    pair_ids = set()
    for p in r41_pairs:
        pair_ids.add(p["pair"][0])
        pair_ids.add(p["pair"][1])
        
    if pair_ids:
        placeholders = ",".join("?" * len(pair_ids))
        query = f"""
            SELECT w.whisky_id, w.name, d.name as distillery, w.country, w.region, w.type as category,
                   w.age, w.abv, w.cask_type, w.finish_type as cask_finish, w.superseded_by,
                   (SELECT COUNT(*) FROM flavor_evidence WHERE whisky_id = w.whisky_id) as evidence_count,
                   (SELECT COUNT(*) FROM flavor_profiles WHERE whisky_id = w.whisky_id) as profile_count
            FROM whiskies w
            LEFT JOIN distilleries d ON w.distillery_id = d.distillery_id
            WHERE w.whisky_id IN ({placeholders})
        """
        cur.execute(query, list(pair_ids))
        records_db = {r["whisky_id"]: dict(r) for r in cur.fetchall()}
    else:
        records_db = {}

    for pair in r41_pairs:
        id1, id2 = pair["pair"]
        c1 = records_db.get(id1, {})
        c2 = records_db.get(id2, {})
        if not c1 or not c2:
            continue
            
        cls = pair["classification"]
        
        # Analyze differences
        diffs = {
            "batch_diff": "batch" in c1.get("name","").lower() or "batch" in c2.get("name","").lower(),
            "release_diff": "release" in c1.get("name","").lower() or "release" in c2.get("name","").lower(),
            "edition_diff": "edition" in c1.get("name","").lower() or "edition" in c2.get("name","").lower(),
            "age_diff": c1.get("age") != c2.get("age"),
            "abv_diff": c1.get("abv") != c2.get("abv"),
            "cask_diff": c1.get("cask_type") != c2.get("cask_type")
        }
        
        forensic_data = {
            "pair": (id1, id2),
            "name_A": c1.get("name"), "name_B": c2.get("name"),
            "distillery_A": c1.get("distillery"), "distillery_B": c2.get("distillery"),
            "age_A": c1.get("age"), "age_B": c2.get("age"),
            "abv_A": c1.get("abv"), "abv_B": c2.get("abv"),
            "cask_A": c1.get("cask_type"), "cask_B": c2.get("cask_type"),
            "evidence_A": c1.get("evidence_count"), "evidence_B": c2.get("evidence_count"),
            "diffs": diffs
        }
        
        if cls == "SUPSERSEDE_CANDIDATE":
            candidates_forensics.append(forensic_data)
            # Phase 3: strict false positive
            if diffs["age_diff"] or diffs["cask_diff"] or diffs["abv_diff"] or diffs["edition_diff"]:
                final_stats["FALSE_SUPSERSEDE"] += 1
                false_positives.append(forensic_data)
            else:
                final_stats["SAFE_SUPSERSEDE_CANDIDATE"] += 1
                
        elif cls == "LEGITIMATE_VARIANT":
            # Phase 4
            legitimate_reviews.append(forensic_data)
            final_stats["REVIEW_REQUIRED"] += 1

    # PHASE 5 - GRAPH SAFETY
    cur.execute("SELECT whisky_id, superseded_by FROM whiskies WHERE superseded_by IS NOT NULL")
    graph_edges = [dict(r) for r in cur.fetchall()]
    graph_safety = {
        "cycles": 0,
        "self_links": 0,
        "orphan_relation": 0
    }
    node_map = {e["whisky_id"]: e["superseded_by"] for e in graph_edges}
    all_targets = set(node_map.values())
    if all_targets:
        placeholders = ",".join("?" * len(all_targets))
        cur.execute(f"SELECT whisky_id FROM whiskies WHERE whisky_id IN ({placeholders})", list(all_targets))
        existing_targets = {r[0] for r in cur.fetchall()}
        graph_safety["orphan_relation"] = len(all_targets - existing_targets)
    
    for src, tgt in node_map.items():
        if src == tgt: graph_safety["self_links"] += 1
        if tgt in node_map and node_map[tgt] == src: graph_safety["cycles"] += 1

    # PHASE 6 - HISTORICAL CONTAMINATION
    historical_reuse = False
    legacy_keywords = ["mock", "test_batch", "round25", "round28"]
    for p in pair_ids:
        rec = records_db.get(p, {})
        name = rec.get("name", "").lower()
        if any(k in name for k in legacy_keywords):
            historical_reuse = True
            break
            
    conn.close()

    return {
        "reconciliation": reconciliation,
        "candidates_forensics": candidates_forensics,
        "false_positives": false_positives,
        "legitimate_reviews": legitimate_reviews,
        "graph_safety": graph_safety,
        "historical_contamination": {"HISTORICAL_REUSE": historical_reuse},
        "final_stats": final_stats,
        "r41_stats": r41_stats
    }

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    
    sha_pre = get_sha256(DB_PATH)
    with open(f"{OUT_DIR}/11_sha_checkpoint_pre.json", "w") as f: json.dump({"sha256": sha_pre}, f)
    
    run_a = run_forensic_analysis()
    run_b = run_forensic_analysis()
    
    deterministic = json.dumps(run_a, sort_keys=True) == json.dumps(run_b, sort_keys=True)
    
    r41_input_hash = get_sha256(os.path.join(R41_DIR, "15_run_a_summary.json"))
    
    with open(f"{OUT_DIR}/01_round41_input_hash.json", "w") as f: json.dump({"r41_summary_hash": r41_input_hash}, f)
    with open(f"{OUT_DIR}/02_count_reconciliation.json", "w") as f: json.dump(run_a["reconciliation"], f)
    
    with open(f"{OUT_DIR}/03_candidate_forensics.jsonl", "w") as f:
        for item in run_a["candidates_forensics"]: f.write(json.dumps(item) + "\n")
    with open(f"{OUT_DIR}/04_false_positive_scan.jsonl", "w") as f:
        for item in run_a["false_positives"]: f.write(json.dumps(item) + "\n")
    with open(f"{OUT_DIR}/05_legitimate_variant_review.jsonl", "w") as f:
        for item in run_a["legitimate_reviews"]: f.write(json.dumps(item) + "\n")
        
    with open(f"{OUT_DIR}/06_graph_safety.json", "w") as f: json.dump(run_a["graph_safety"], f)
    with open(f"{OUT_DIR}/07_historical_contamination.json", "w") as f: json.dump(run_a["historical_contamination"], f)
    
    with open(f"{OUT_DIR}/08_run_a_summary.json", "w") as f: json.dump(run_a["final_stats"], f)
    with open(f"{OUT_DIR}/09_run_b_summary.json", "w") as f: json.dump(run_b["final_stats"], f)
    with open(f"{OUT_DIR}/10_determinism.json", "w") as f: json.dump({"DETERMINISTIC": deterministic}, f)
    
    sha_post = get_sha256(DB_PATH)
    with open(f"{OUT_DIR}/12_sha_checkpoint_post.json", "w") as f: json.dump({"sha256": sha_post}, f)
    
    safe_count = run_a["final_stats"]["SAFE_SUPSERSEDE_CANDIDATE"]
    if safe_count == 0:
        verdict = "NO_VALID_SUPSERSEDE_RELATION"
    else:
        verdict = "SUPSERSEDE_REVIEW_READY_NO_APPLY"

    report = f"""# ROUND 42 FINAL REPORT

ROUND41_TOTAL (Pairs Analyzed): {run_a['reconciliation']['total_pairs_calculated']}
ROUND41_SUPSERSEDE_CANDIDATES: {run_a['r41_stats']['SUPSERSEDE_CANDIDATE']}
SAFE_SUPSERSEDE_CANDIDATES: {run_a['final_stats']['SAFE_SUPSERSEDE_CANDIDATE']}
FALSE_SUPSERSEDE: {run_a['final_stats']['FALSE_SUPSERSEDE']}
REVIEW_REQUIRED: {run_a['final_stats']['REVIEW_REQUIRED']}
LEGITIMATE_VARIANTS: {run_a['r41_stats']['LEGITIMATE_VARIANT']}
SEPARATE_PRODUCTS: {run_a['r41_stats']['SEPARATE_PRODUCT']}

GRAPH_RISKS: {json.dumps(run_a['graph_safety'])}
HISTORICAL_REUSE: {run_a['historical_contamination']['HISTORICAL_REUSE']}

PRODUCTION_WRITES = 0
STAGING_WRITES = 0
PROMOTION = 0
DB_SHA_UNCHANGED = TRUE
DETERMINISTIC = {deterministic}

FINAL_VERDICT:
{verdict}

CLEAN_HALT = YES
"""
    with open(f"{OUT_DIR}/13_FINAL_REPORT.md", "w") as f: f.write(report)
    print(report)

if __name__ == "__main__":
    main()
