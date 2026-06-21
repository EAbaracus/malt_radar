import os
import csv
import re
import glob
import hashlib

base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
output_dir = os.path.join(base_dir, "data", "output")
snapshots_dir = os.path.join(output_dir, "tasting_note_snapshots")
reports_dir = os.path.join(base_dir, "output", "reports")

os.makedirs(snapshots_dir, exist_ok=True)
os.makedirs(reports_dir, exist_ok=True)

rejected_csv_in = os.path.join(output_dir, "web_tasting_note_resolved_snapshot_rejected.csv")
resolved_candidates_csv = os.path.join(output_dir, "web_tasting_note_resolved_url_candidates.csv")

index_csv_out = os.path.join(output_dir, "web_tasting_note_recovered_text_snapshots_index.csv")
extractable_csv_out = os.path.join(output_dir, "web_tasting_note_recovered_extractable_candidates.csv")
rejected_csv_out = os.path.join(output_dir, "web_tasting_note_recovered_snapshot_rejected.csv")
report_md = os.path.join(reports_dir, "220_web_tasting_note_recovered_text_snapshot_report.md")
gate_txt = os.path.join(reports_dir, "221_web_tasting_note_recovered_text_snapshot_gate.txt")

OUT_FIELDS = [
    "whisky_id", "whisky_name", "source_file", "candidate_url", "snapshot_text_path",
    "text_length", "name_match", "review_signal", "age_conflict", "ordinal_conflict",
    "extractability_status", "reject_reason"
]

def normalize(text):
    return re.sub(r'[^a-z0-9]', '', str(text).lower())

def get_age_from_name(name):
    match = re.search(r'\b(\d{1,2})\s*(year|yo|y\.o)\b', name, re.IGNORECASE)
    if match: return match.group(1)
    match2 = re.search(r'\b(\d{1,2})\b', name)
    if match2 and 10 <= int(match2.group(1)) <= 50:
        return match2.group(1)
    return None

def check_age_conflict(name, text):
    age_in_name = get_age_from_name(name)
    if not age_in_name: return False
    
    ages_to_check = ['10', '12', '14', '15', '16', '18', '21', '25', '30']
    text_lower = text.lower()
    age_in_name_found = re.search(r'\b' + age_in_name + r'\b', text_lower)
    
    if not age_in_name_found:
        for a in ages_to_check:
            if a != age_in_name and re.search(r'\b' + a + r'\b', text_lower):
                return True 
    return False

def check_ordinal_conflict(name, text):
    match = re.search(r'\b(\d+)(st|nd|rd|th)\b', name, re.IGNORECASE)
    if not match: return False
    ordinal_in_name = match.group(1)
    text_lower = text.lower()
    if not re.search(r'\b' + ordinal_in_name + r'(st|nd|rd|th)\b', text_lower):
        if re.search(r'\b(\d+)(st|nd|rd|th)\b', text_lower):
            return True
    return False

def token_overlap(name1, name2):
    t1 = set(normalize(t) for t in name1.split() if len(t)>2)
    t2 = set(normalize(t) for t in name2.split() if len(t)>2)
    if not t1 or not t2:
        return 0.0
    return len(t1.intersection(t2)) / float(max(len(t1), len(t2)))

def get_db_hash(db_path):
    if os.path.exists(db_path):
        with open(db_path, "rb") as df:
            return hashlib.sha256(df.read()).hexdigest()
    return "N/A"

def main():
    db_path = os.path.join(base_dir, "output", "import", "production.db")
    expected_hash = "fdad80458436f13dff5e70955bd6c887980cddba6c253d6f28042b7ceba432c1"
    hash_before = get_db_hash(db_path)

    if not os.path.exists(rejected_csv_in):
        print(f"File not found: {rejected_csv_in}")
        return

    resolved_info = {}
    if os.path.exists(resolved_candidates_csv):
        with open(resolved_candidates_csv, 'r', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                resolved_info[row.get("whisky_id")] = row

    candidates = []
    with open(rejected_csv_in, 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            w_id = row.get("whisky_id", "")
            res_row = resolved_info.get(w_id, {})
            sys = res_row.get("source_system", "").lower()
            dom = res_row.get("candidate_domain", "").lower()
            sf = res_row.get("source_file", "").lower()
            if "scotchgit" in sys or "reddit" in sys or "reddit" in dom or "scotchgit" in sf:
                row["source_file"] = res_row.get("source_file", "unknown")
                row["candidate_url"] = res_row.get("candidate_url", row.get("source_url", ""))
                candidates.append(row)

    patterns = [
        "data/output/scotchgit_candidates_high_confidence.csv",
        "data/output/scotchgit_candidates_medium_confidence.csv",
        "data/output/scotchgit_candidates_quality_review.csv",
        "data/external/scotchgit/scotchfile.csv"
    ]
    
    text_columns = ["tasting_note", "review", "notes", "body", "text", "comment", "description", "nose", "palate"]
    name_columns = ["product_name", "product", "name", "title", "whisky_name", "Whisky Name"]

    source_records = []
    for p in patterns:
        matches = glob.glob(os.path.join(base_dir, p))
        for m in matches:
            if os.path.isfile(m):
                try:
                    with open(m, 'r', encoding='utf-8', errors='ignore') as f:
                        reader = csv.DictReader(f)
                        col_names = reader.fieldnames or []
                        found_text_cols = [c for c in col_names if any(t in c.lower() for t in text_columns)]
                        found_name_cols = [c for c in col_names if c in name_columns]
                        
                        if not found_name_cols:
                            continue
                            
                        for row in reader:
                            name = next((row.get(c) for c in found_name_cols if row.get(c)), "")
                            if not name: continue
                            text = next((row.get(c) for c in found_text_cols if row.get(c)), "")
                            source_records.append({
                                "name": name,
                                "text": text
                            })
                except Exception:
                    pass

    results = []
    extractable = []
    rejected = []
    
    counts = {"total": len(candidates), "extractable": 0, "rejected_no_text": 0, "rejected_quality": 0}

    for cand in candidates:
        w_id = cand["whisky_id"]
        w_name = cand["whisky_name"]
        
        out = {
            "whisky_id": w_id,
            "whisky_name": w_name,
            "source_file": cand["source_file"],
            "candidate_url": cand["candidate_url"],
            "snapshot_text_path": "",
            "text_length": 0,
            "name_match": False,
            "review_signal": False,
            "age_conflict": False,
            "ordinal_conflict": False,
            "extractability_status": "no_existing_text",
            "reject_reason": ""
        }
        
        best_sr = None
        best_score = 0.0
        
        for sr in source_records:
            n1 = normalize(w_name)
            n2 = normalize(sr["name"])
            if not n1 or not n2: continue
            
            if n1 == n2:
                score = 0.95
            else:
                score = token_overlap(w_name, sr["name"])
                
            if score > best_score and score >= 0.75:
                if not check_age_conflict(w_name, sr["name"]) and not check_ordinal_conflict(w_name, sr["name"]):
                    best_score = score
                    best_sr = sr

        if best_sr and best_sr["text"]:
            text = best_sr["text"]
            text_path = os.path.join(snapshots_dir, f"recovered_scotchgit_{w_id}.txt")
            with open(text_path, 'w', encoding='utf-8') as f:
                f.write(text)
                
            out["snapshot_text_path"] = os.path.relpath(text_path, base_dir)
            out["text_length"] = len(text)
            
            text_lower = text.lower()
            text_normalized = normalize(text)
            name_tokens = set(normalize(t) for t in w_name.split() if len(t)>2)
            
            if normalize(w_name) in text_normalized or all(t in text_normalized for t in name_tokens):
                out["name_match"] = True
            
            review_tokens = ["nose", "palate", "finish", "tasting", "review", "aroma", "flavour", "flavor", "sweet", "smoke", "peat", "oak", "fruit", "vanilla"]
            if any(t in text_lower for t in review_tokens):
                out["review_signal"] = True
                
            out["age_conflict"] = check_age_conflict(w_name, text)
            out["ordinal_conflict"] = check_ordinal_conflict(w_name, text)
            
            rejects = []
            if out["text_length"] < 300: rejects.append("text_too_short")
            if not out["name_match"]: rejects.append("no_name_match")
            if not out["review_signal"]: rejects.append("no_review_signals")
            if out["age_conflict"]: rejects.append("age_conflict")
            if out["ordinal_conflict"]: rejects.append("ordinal_conflict")
            
            if rejects:
                out["extractability_status"] = "rejected"
                out["reject_reason"] = "|".join(rejects)
                counts["rejected_quality"] += 1
            else:
                out["extractability_status"] = "extractable"
                counts["extractable"] += 1
        else:
            out["extractability_status"] = "no_existing_text"
            out["reject_reason"] = "no_text_found_in_csv"
            counts["rejected_no_text"] += 1
            
        results.append(out)

    for r in results:
        if r["extractability_status"] == "extractable":
            extractable.append(r)
        else:
            rejected.append(r)
            
    with open(index_csv_out, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=OUT_FIELDS)
        w.writeheader()
        w.writerows(results)
        
    with open(extractable_csv_out, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=OUT_FIELDS)
        w.writeheader()
        w.writerows(extractable)
        
    with open(rejected_csv_out, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=OUT_FIELDS)
        w.writeheader()
        w.writerows(rejected)
        
    with open(report_md, 'w', encoding='utf-8') as f:
        f.write("# 220 Web Tasting Note Recovered Text Snapshot Report\n\n")
        f.write(f"- Total rejected Reddit/ScotchGit candidates processed: {counts['total']}\n")
        f.write(f"- Extractable (Text recovered & passed checks): {counts['extractable']}\n")
        f.write(f"- Rejected (Quality checks failed): {counts['rejected_quality']}\n")
        f.write(f"- No Existing Text (Text not found in CSV): {counts['rejected_no_text']}\n")
        
    hash_after = get_db_hash(db_path)
    hash_ok = (hash_before == expected_hash) and (hash_after == expected_hash)
    gate_status = "GO" if (hash_ok and counts['total'] > 0 and (counts['extractable'] > 0 or counts['rejected_no_text'] > 0 or counts['rejected_quality'] > 0)) else "NO-GO"
    
    with open(gate_txt, 'w', encoding='utf-8') as f:
        f.write(f"GATE_STATUS: {gate_status}\n")
        f.write(f"REASON: Processed {counts['total']} candidates.\n")
        f.write(f"DB_HASH_BEFORE: {hash_before}\n")
        f.write(f"DB_HASH_AFTER: {hash_after}\n")
        f.write(f"EXPECTED_HASH: {expected_hash}\n")

    print(f"Recovery Pipeline finished. Extractable: {counts['extractable']}, NoText: {counts['rejected_no_text']}")

if __name__ == "__main__":
    main()
