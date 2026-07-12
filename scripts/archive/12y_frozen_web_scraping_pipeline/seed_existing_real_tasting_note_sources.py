import os
import csv
import re
import glob
import hashlib
import sqlite3

base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
output_dir = os.path.join(base_dir, "data", "output")
reports_dir = os.path.join(base_dir, "output", "reports")

os.makedirs(reports_dir, exist_ok=True)

cand_csv_out = os.path.join(output_dir, "web_tasting_note_source_seed_candidates.csv")
manual_csv_out = os.path.join(output_dir, "web_tasting_note_source_seed_manual_review.csv")
reject_csv_out = os.path.join(output_dir, "web_tasting_note_source_seed_rejected.csv")
report_md = os.path.join(reports_dir, "222_web_tasting_note_source_seed_report.md")
gate_txt = os.path.join(reports_dir, "223_web_tasting_note_source_seed_gate.txt")

OUT_FIELDS = [
    "whisky_id", "whisky_name", "source_file", "source_system", "source_url",
    "text_preview", "text_length", "confidence_score", "match_reason", "seed_status", "reject_reason"
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

def get_whiskies_without_flavor_profile(db_path):
    whiskies = []
    if os.path.exists(db_path):
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        cursor = conn.cursor()
        
        # Check if flavor_profiles table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='flavor_profiles'")
        has_flavor = cursor.fetchone() is not None
        
        if has_flavor:
            cursor.execute("""
                SELECT w.whisky_id, w.name, fp.whisky_id
                FROM whiskies w
                LEFT JOIN flavor_profiles fp ON w.whisky_id = fp.whisky_id
                WHERE fp.whisky_id IS NULL
            """)
            rows = cursor.fetchall()
            for r in rows:
                whiskies.append({"whisky_id": r[0], "name": r[1]})
        else:
            cursor.execute("SELECT whisky_id, name FROM whiskies")
            rows = cursor.fetchall()
            for r in rows:
                whiskies.append({"whisky_id": r[0], "name": r[1]})
        conn.close()
    return whiskies

def main():
    db_path = os.path.join(base_dir, "output", "import", "production.db")
    expected_hash = "fdad80458436f13dff5e70955bd6c887980cddba6c253d6f28042b7ceba432c1"
    hash_before = get_db_hash(db_path)

    target_whiskies = get_whiskies_without_flavor_profile(db_path)
    
    # Exclude web_tasting_note output files
    patterns = [
        "data/output/*tasting*.csv",
        "data/output/*whiskynotes*.csv",
        "data/output/*masterofmalt*.csv",
        "data/output/*whiskybase*.csv",
        "data/output/*whiskyedition*.csv",
        "data/output/real_twe_flavour_categories*.csv"
    ]
    
    source_files = set()
    for p in patterns:
        for m in glob.glob(os.path.join(base_dir, p)):
            basename = os.path.basename(m)
            if not basename.startswith("web_tasting_note") and not basename.startswith("scotchgit"):
                source_files.add(m)
                
    source_records = []
    
    name_cols = ["product_name", "product", "name", "title", "whisky_name"]
    url_cols = ["source_url", "url", "review_url", "page_url"]
    text_cols = ["tasting_note", "note", "notes", "review_text", "description", "flavour", "flavor", "nose", "palate", "finish", "conclusion"]
    sys_cols = ["source_system", "source_type", "source"]

    for fpath in source_files:
        basename = os.path.basename(fpath)
        try:
            with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames or []
                
                c_name = next((c for c in headers if c.lower() in name_cols), None)
                if not c_name: c_name = next((c for c in headers if "name" in c.lower() or "product" in c.lower()), None)
                
                c_url = next((c for c in headers if c.lower() in url_cols), None)
                c_sys = next((c for c in headers if c.lower() in sys_cols), None)
                c_texts = [c for c in headers if any(t in c.lower() for t in text_cols)]
                
                if not c_name:
                    continue
                    
                for row in reader:
                    name_val = row.get(c_name, "").strip()
                    if not name_val: continue
                    
                    url_val = row.get(c_url, "") if c_url else ""
                    sys_val = row.get(c_sys, basename) if c_sys else basename
                    
                    text_parts = []
                    for ct in c_texts:
                        tv = row.get(ct, "").strip()
                        if tv: text_parts.append(tv)
                    text_val = " ".join(text_parts)
                    
                    source_records.append({
                        "name": name_val,
                        "url": url_val,
                        "sys": sys_val,
                        "text": text_val,
                        "file": basename
                    })
        except Exception:
            pass

    results = []
    
    for tw in target_whiskies:
        w_id = tw["whisky_id"]
        w_name = tw["name"]
        
        best_sr = None
        best_score = 0.0
        
        n1 = normalize(w_name)
        if not n1: continue
        
        for sr in source_records:
            n2 = normalize(sr["name"])
            if not n2: continue
            
            if n1 == n2:
                score = 0.95
            else:
                score = token_overlap(w_name, sr["name"])
                
            if score > best_score and score >= 0.60:
                best_score = score
                best_sr = sr
                
        if not best_sr:
            continue
            
        out = {
            "whisky_id": w_id,
            "whisky_name": w_name,
            "source_file": best_sr["file"],
            "source_system": best_sr["sys"],
            "source_url": best_sr["url"],
            "text_preview": (best_sr["text"][:100] + "...") if best_sr["text"] else "",
            "text_length": len(best_sr["text"]),
            "confidence_score": best_score,
            "match_reason": "",
            "seed_status": "",
            "reject_reason": ""
        }
        
        age_conf = check_age_conflict(w_name, best_sr["name"])
        ord_conf = check_ordinal_conflict(w_name, best_sr["name"])
        
        has_url = best_sr["url"] and "example.com" not in best_sr["url"] and "placeholder" not in best_sr["url"]
        has_text = len(best_sr["text"]) >= 120
        
        rejects = []
        if age_conf: rejects.append("age_conflict")
        if ord_conf: rejects.append("ordinal_conflict")
        if not has_url and not has_text: rejects.append("no_valid_url_or_sufficient_text")
        
        if rejects:
            out["seed_status"] = "rejected"
            out["reject_reason"] = "|".join(rejects)
        elif best_score >= 0.95:
            out["seed_status"] = "source_seed_candidate"
            out["match_reason"] = "exact_normalized_match"
        elif best_score >= 0.80:
            out["seed_status"] = "source_seed_candidate"
            out["match_reason"] = "strong_token_match"
        else:
            out["seed_status"] = "manual_review"
            out["match_reason"] = "medium_token_match"
            
        results.append(out)

    candidates = [r for r in results if r["seed_status"] == "source_seed_candidate"]
    manuals = [r for r in results if r["seed_status"] == "manual_review"]
    rejecteds = [r for r in results if r["seed_status"] == "rejected"]
    
    with open(cand_csv_out, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=OUT_FIELDS)
        w.writeheader()
        w.writerows(candidates)
        
    with open(manual_csv_out, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=OUT_FIELDS)
        w.writeheader()
        w.writerows(manuals)
        
    with open(reject_csv_out, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=OUT_FIELDS)
        w.writeheader()
        w.writerows(rejecteds)
        
    with open(report_md, 'w', encoding='utf-8') as f:
        f.write("# 222 Web Tasting Note Source Seed Report\n\n")
        f.write("
Estimated API Cost: $0.00
Actual API Cost: $0.00
Local Compute Used: Yes
Fully Local Execution: Yes
")

        f.write(f"- Flavor profile missing whisky count: {len(target_whiskies)}\n")
        f.write(f"- Scanned source CSV count: {len(source_files)}\n")
        f.write(f"- Total matched whiskies: {len(results)}\n")
        f.write(f"- Source Seed Candidates: {len(candidates)}\n")
        f.write(f"- Manual Review: {len(manuals)}\n")
        f.write(f"- Rejected: {len(rejecteds)}\n")
        
    hash_after = get_db_hash(db_path)
    hash_ok = (hash_before == expected_hash) and (hash_after == expected_hash)
    gate_status = "GO" if (hash_ok and (len(candidates) > 0 or len(rejecteds) > 0 or len(manuals) > 0)) else "NO-GO"
    
    with open(gate_txt, 'w', encoding='utf-8') as f:
        f.write(f"GATE_STATUS: {gate_status}\n")
        f.write(f"REASON: Processed {len(target_whiskies)} whiskies and found {len(results)} matches.\n")
        f.write(f"DB_HASH_BEFORE: {hash_before}\n")
        f.write(f"DB_HASH_AFTER: {hash_after}\n")
        f.write(f"EXPECTED_HASH: {expected_hash}\n")

    print(f"Seed Pipeline finished. Candidates: {len(candidates)}, Manual: {len(manuals)}, Rejected: {len(rejecteds)}")

if __name__ == "__main__":
    main()
