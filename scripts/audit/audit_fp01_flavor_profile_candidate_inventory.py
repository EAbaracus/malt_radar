import sqlite3
import csv
import json
import hashlib
from pathlib import Path

def get_hash(filepath):
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            h.update(chunk)
    return h.hexdigest().upper()

def main():
    root = Path(__file__).resolve().parent.parent.parent
    db_path = root / "output" / "import" / "production.db"
    out_csv = root / "data" / "output" / "fp01_flavor_profile_candidate_inventory.csv"
    report_out = root / "output" / "reports" / "fp01_flavor_profile_candidate_inventory_report.md"
    gate_out = root / "output" / "reports" / "fp01_flavor_profile_candidate_inventory_gate.txt"
    
    hash_before = get_hash(db_path)
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    cur = conn.cursor()
    
    cur.execute("SELECT COUNT(*) FROM whiskies")
    total_whiskies = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM flavor_profiles")
    current_flavor_profiles = cur.fetchone()[0]
    
    current_coverage = current_flavor_profiles / total_whiskies if total_whiskies else 0
    whiskies_without_profile = total_whiskies - current_flavor_profiles
    
    cur.execute("SELECT DISTINCT whisky_id FROM flavor_profiles")
    existing_profile_whisky_ids = set(row[0] for row in cur.fetchall())
    
    sources = []
    
    wm_file = root / "data" / "output" / "whiskeymapper_final_import_candidates_high_only.csv"
    wm_raw = 0
    wm_matched = 0
    wm_already = 0
    if wm_file.exists():
        with open(wm_file, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                wm_raw += 1
                wid = row.get("matched_product_id")
                if wid:
                    wm_matched += 1
                    if wid in existing_profile_whisky_ids:
                        wm_already += 1
    
    wm_net = wm_matched - wm_already
    sources.append({
        "source_name": "WhiskeyMapper",
        "raw_candidate_count": wm_raw,
        "matched_whisky_count": wm_matched,
        "already_has_profile_count": wm_already,
        "net_new_profile_candidate_count": wm_net,
        "high_confidence_count": wm_raw,
        "review_count": 0,
        "blocked_count": 0,
        "estimated_total_profiles_after_source": current_flavor_profiles + wm_net,
        "estimated_coverage_after_source": (current_flavor_profiles + wm_net) / total_whiskies if total_whiskies else 0,
        "notes": ""
    })
    
    ml_file = root / "data" / "output" / "structured_ml_whiskey_source" / "high_match_safe_preview.csv"
    ml_raw = 0
    ml_matched = 0
    ml_already = 0
    ml_high = 0
    ml_blocked = 0
    if ml_file.exists():
        with open(ml_file, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                ml_raw += 1
                wid = row.get("whisky_id")
                if wid:
                    ml_matched += 1
                    if wid in existing_profile_whisky_ids:
                        ml_already += 1
                if row.get("qa_status") == "qa_pass":
                    ml_high += 1
                else:
                    ml_blocked += 1
    
    ml_net = ml_matched - ml_already
    sources.append({
        "source_name": "Structured ML Whiskey",
        "raw_candidate_count": ml_raw,
        "matched_whisky_count": ml_matched,
        "already_has_profile_count": ml_already,
        "net_new_profile_candidate_count": ml_net,
        "high_confidence_count": ml_high,
        "review_count": 0,
        "blocked_count": ml_blocked,
        "estimated_total_profiles_after_source": current_flavor_profiles + ml_net,
        "estimated_coverage_after_source": (current_flavor_profiles + ml_net) / total_whiskies if total_whiskies else 0,
        "notes": ""
    })
    
    sg_file = root / "data" / "output" / "scotchgit_flavor_preview_import.csv"
    sg_raw = 0
    sg_matched = 0
    sg_already = 0
    sg_high = 0
    if sg_file.exists():
        with open(sg_file, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                sg_raw += 1
                wid = row.get("matched_master_whisky_id") or row.get("matched_product_id")
                if wid:
                    sg_matched += 1
                    if wid in existing_profile_whisky_ids:
                        sg_already += 1
                sg_high += 1 
    
    sg_net = sg_matched - sg_already
    sources.append({
        "source_name": "ScotchGit",
        "raw_candidate_count": sg_raw,
        "matched_whisky_count": sg_matched,
        "already_has_profile_count": sg_already,
        "net_new_profile_candidate_count": sg_net,
        "high_confidence_count": sg_high,
        "review_count": 0,
        "blocked_count": 0,
        "estimated_total_profiles_after_source": current_flavor_profiles + sg_net,
        "estimated_coverage_after_source": (current_flavor_profiles + sg_net) / total_whiskies if total_whiskies else 0,
        "notes": ""
    })
    
    cur.execute("SELECT whisky_id, import_recommendation FROM staging_tasting_notes WHERE source_system = 'book_entry_boundary_clean_title'")
    book_rows = cur.fetchall()
    bk_raw = len(book_rows)
    bk_matched = 0
    bk_already = 0
    bk_high = 0
    for row in book_rows:
        wid = row[0]
        imp_rec = row[1]
        
        has_radar = False
        conf = 0
        if imp_rec:
            try:
                j = json.loads(imp_rec)
                radar = j.get("radar_scores_0_100", {})
                conf = float(j.get("confidence", 0))
                if any(v is not None for v in radar.values()):
                    has_radar = True
            except:
                pass
                
        if wid:
            bk_matched += 1
            if wid in existing_profile_whisky_ids:
                bk_already += 1
                
        if has_radar and conf >= 0.5:
            bk_high += 1
            
    bk_net = bk_high - bk_already if bk_matched > 0 else bk_high
    sources.append({
        "source_name": "book_pipeline_validated",
        "raw_candidate_count": bk_raw,
        "matched_whisky_count": bk_matched,
        "already_has_profile_count": bk_already,
        "net_new_profile_candidate_count": bk_net,
        "high_confidence_count": bk_high,
        "review_count": bk_raw - bk_high,
        "blocked_count": 0,
        "estimated_total_profiles_after_source": current_flavor_profiles + bk_net,
        "estimated_coverage_after_source": (current_flavor_profiles + bk_net) / total_whiskies if total_whiskies else 0,
        "notes": "12O status=early_inventory_only, no apply plan, validated count=5"
    })
    
    if sources:
        Path(out_csv).parent.mkdir(parents=True, exist_ok=True)
        with open(out_csv, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=list(sources[0].keys()))
            w.writeheader()
            w.writerows(sources)
            
    best_source = max(sources, key=lambda x: x["net_new_profile_candidate_count"]) if sources else None
    
    gate_decision = "REVIEW"
    
    md = f"""# FP-01 WhiskeyMapper & ML Flavor Candidate Audit Report

## DB Metrics
- **Total Whiskies:** {total_whiskies}
- **Current Flavor Profiles:** {current_flavor_profiles}
- **Current Coverage:** {current_coverage:.2%}
- **Whiskies Without Profile:** {whiskies_without_profile}

## Source Contribution Ranking
"""
    sources.sort(key=lambda x: x["net_new_profile_candidate_count"], reverse=True)
    
    for s in sources:
        md += f"### {s['source_name']}\n"
        md += f"- Raw Candidates: {s['raw_candidate_count']}\n"
        md += f"- Matched Whiskies: {s['matched_whisky_count']}\n"
        md += f"- Already Has Profile: {s['already_has_profile_count']}\n"
        md += f"- Net New Profile Candidates: {s['net_new_profile_candidate_count']}\n"
        md += f"- Estimated Total Profiles: {s['estimated_total_profiles_after_source']}\n"
        md += f"- Estimated Coverage After: {s['estimated_coverage_after_source']:.2%}\n"
        if s["notes"]:
            md += f"- Notes: {s['notes']}\n"
        md += "\n"
        
    md += f"## Best Next Source Recommendation\n"
    if best_source:
        md += f"**{best_source['source_name']}** with {best_source['net_new_profile_candidate_count']} net new candidates.\n\n"
        
    md += f"## Security & Verification\n"
    md += f"- DB Modified: false\n"
    md += f"- Production DB Hash: {hash_before}\n\n"
    md += f"Gate decision: **{gate_decision}**\n"
    
    Path(report_out).parent.mkdir(parents=True, exist_ok=True)
    with open(report_out, "w", encoding="utf-8") as f:
        f.write(md)
        f.write("""\nEstimated API Cost: $0.00\nActual API Cost: $0.00\nLocal Compute Used: Yes\nFully Local Execution: Yes\n""")

        
    with open(gate_out, "w", encoding="utf-8") as f:
        f.write(gate_decision)
        
if __name__ == "__main__":
    main()
