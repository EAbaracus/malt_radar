import os
import json
import sqlite3
import csv
import glob
from datetime import datetime
from collections import Counter
import re
import traceback

DB_PATH = "output/import/production.db"
INPUT_DIR = "data/manual_sources/books/notebooklm_json"
OUTPUT_CSV_DIR = "data/manual_sources/books/review_csv"
REPORT_FILE = "output/reports/12v_notebooklm_book_profile_validator_report.md"
GATE_FILE = "output/reports/12v_notebooklm_book_profile_validator_gate.txt"

EXPECTED_AXES = [
    "smoky", "peaty", "sherry", "fruity", "floral", "spicy", "sweet", "oak",
    "maritime", "winey", "malty", "nutty", "herbal", "waxy", "oily",
    "light_body", "rich_body"
]
VALID_RADAR_VALUES = {0, 20, 40, 60, 80, 100}
PROXY_KEYWORDS = ["proxy", "based on", "yerine", "not exact", "exact expression not found"]

def clean_basic(text):
    if not text: return ""
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9\s]', '', str(text).lower())).strip()

def clean_advanced(text):
    if not text: return ""
    t = str(text).lower()
    t = re.sub(r'[^a-z0-9\s]', ' ', t)
    t = re.sub(r'(?<=\d)(yo|y|year|years)\b', ' ', t)
    t = re.sub(r'\b(the|single|malt|scotch|whisky|whiskey|yo|year|old|years)\b', ' ', t)
    return re.sub(r'\s+', ' ', t).strip()

def extract_age_num(text):
    if not text: return ""
    m = re.search(r'\b(\d+)\b', str(text))
    return m.group(1) if m else ""

def contains_proxy_keywords(text):
    if not text: return False
    text_lower = text.lower()
    for kw in PROXY_KEYWORDS:
        if kw in text_lower: return True
    return False

def setup_directories():
    os.makedirs(OUTPUT_CSV_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(REPORT_FILE), exist_ok=True)

def match_whisky(all_whiskies, name, age, distillery):
    # 1. Exact
    matches = [w for w in all_whiskies if w[1] == name and (w[2] or "") == (age or "")]
    if len(matches) == 1: return matches[0], "exact"

    # 2. Normalized Exact
    b_name = clean_basic(name)
    b_age = clean_basic(age)
    matches = [w for w in all_whiskies if clean_basic(w[1]) == b_name and clean_basic(w[2]) == b_age]
    if len(matches) == 1: return matches[0], "normalized_exact"

    # 3. Age variant
    a_name = clean_advanced(name)
    a_age = extract_age_num(age)
    if not a_name: a_name = "___IMPOSSIBLE___"
    
    matches = []
    for w in all_whiskies:
        w_a_name = clean_advanced(w[1])
        w_a_age = extract_age_num(w[2])
        if w_a_name == a_name or w_a_name == a_name.replace("the ", "") or a_name == w_a_name.replace("the ", ""):
            if a_age and w_a_age == a_age:
                matches.append(w)
            elif not a_age and not w_a_age:
                matches.append(w)
            elif not a_age and w_a_age and w_a_age in a_name.split():
                matches.append(w)
            elif not w_a_age and a_age and a_age in w_a_name.split():
                matches.append(w)
            elif a_age and str(a_age) in clean_basic(w[1]):
                matches.append(w)
    
    if len(matches) == 1: return matches[0], "age_variant"

    # 4. Distillery + Age Fallback
    if distillery and age:
        dist_clean = clean_advanced(distillery)
        age_num = extract_age_num(age)
        if dist_clean and age_num:
            fallback_str = f"{dist_clean} {age_num}"
            matches = []
            for w in all_whiskies:
                w_a_name = clean_advanced(w[1])
                w_a_age = extract_age_num(w[2])
                
                if w_a_name == fallback_str:
                    matches.append(w)
                elif w_a_name == dist_clean and w_a_age == age_num:
                    matches.append(w)
                elif dist_clean in w_a_name and age_num in clean_basic(w[1]):
                    matches.append(w)
                    
            if len(matches) == 1: return matches[0], "distillery_age"
            
    return None, "not_found"

def check_conflicts(cursor, whisky_id, radar):
    conflict_existing_profile = False
    existing_profile_source = ""
    radar_conflict = False
    conflict_existing_note = False
    existing_note_source = ""
    
    cursor.execute("SELECT flavor_vector, flavor_source FROM flavor_profiles WHERE whisky_id = ?", (whisky_id,))
    fp_row = cursor.fetchone()
    if fp_row:
        conflict_existing_profile = True
        existing_profile_source = str(fp_row[1]) if fp_row[1] else ""
        if fp_row[0] and radar:
            try:
                db_radar = json.loads(fp_row[0])
                for k, v in radar.items():
                    if db_radar.get(k) != v:
                        radar_conflict = True
                        break
            except Exception:
                radar_conflict = True

    cursor.execute("SELECT source_system FROM tasting_notes WHERE whisky_id = ? LIMIT 1", (whisky_id,))
    tn_row = cursor.fetchone()
    if tn_row:
        conflict_existing_note = True
        existing_note_source = "tasting_notes"
    else:
        cursor.execute("SELECT source_system FROM staging_tasting_notes WHERE whisky_id = ? LIMIT 1", (whisky_id,))
        stn_row = cursor.fetchone()
        if stn_row:
            conflict_existing_note = True
            existing_note_source = "staging_tasting_notes"
            
    return conflict_existing_profile, existing_profile_source, radar_conflict, conflict_existing_note, existing_note_source

def write_csv(data_list, filepath):
    if not data_list:
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            pass
        return
        
    keys = set()
    for d in data_list:
        keys.update(d.keys())
        if "radar_scores_0_100" in d and isinstance(d["radar_scores_0_100"], dict):
            keys.update([f"radar_{k}" for k in d["radar_scores_0_100"].keys()])
            
    keys = sorted(list(keys))
    if "radar_scores_0_100" in keys: 
        keys.remove("radar_scores_0_100")
    
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        for d in data_list:
            row = {k: v for k, v in d.items() if k != "radar_scores_0_100"}
            if "radar_scores_0_100" in d and isinstance(d["radar_scores_0_100"], dict):
                for rk, rv in d["radar_scores_0_100"].items():
                    row[f"radar_{rk}"] = rv
            writer.writerow(row)

def main():
    setup_directories()
    
    if not os.path.exists(DB_PATH):
        print(f"Error: Database {DB_PATH} not found.")
        return

    json_files = glob.glob(os.path.join(INPUT_DIR, "*.json"))
    
    accept_preview = []
    manual_review = []
    not_found = []
    blocked = []
    
    stats = {
        "input_rows": 0,
        "input_errors": 0,
        "matched_whisky_id_count": 0,
        "unmatched_count": 0,
        "explicit_zero_count": 0,
        "null_radar_count": 0,
        "light_rich_conflict_count": 0,
        "rescued_match_count": 0,
        "confidence_dist": Counter(),
        "source_book_dist": Counter(),
        "match_strategy_dist": Counter(),
        "input_error_files": [],
        "not_found_list": [],
        "manual_review_reasons": Counter(),
        "blocked_reasons": Counter()
    }
    
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    cursor = conn.cursor()
    
    # Cache all whiskies for fuzzy matching
    cursor.execute("SELECT whisky_id, name, age_statement, distillery_id FROM whiskies")
    all_whiskies = cursor.fetchall()
    
    for file_path in json_files:
        try:
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                data = json.load(f)
                
            if isinstance(data, dict) and "profiles" in data:
                 records = data["profiles"]
            elif isinstance(data, list):
                 records = data
            else:
                 records = [data]
                 
            for record in records:
                stats["input_rows"] += 1
                
                source_book = record.get("source_book") or record.get("book_source") or "unknown"
                record["source_book"] = source_book
                stats["source_book_dist"][source_book] += 1
                
                confidence = str(record.get("confidence", "")).lower()
                stats["confidence_dist"][confidence] += 1
                
                name = record.get("whisky_name", "")
                age = record.get("age_statement", "")
                distillery = record.get("distillery", "") or record.get("distillery_name", "")
                notes = record.get("notes_for_manual_review", "")
                radar = record.get("radar_scores_0_100")
                
                record["source_file"] = os.path.basename(file_path)
                record["conflict_existing_profile"] = False
                record["existing_profile_source"] = ""
                record["radar_conflict"] = False
                record["conflict_existing_note"] = False
                record["existing_note_source"] = ""
                record["bucket"] = ""
                record["decision_reason"] = ""
                record["match_strategy"] = "not_found"
                
                is_blocked = False
                blocked_reason = []
                is_manual = False
                manual_reason = []
                is_not_found = False
                
                if not name:
                    is_blocked = True
                    blocked_reason.append("Missing whisky_name")
                    
                has_proxy = contains_proxy_keywords(notes)
                if has_proxy:
                    if confidence == "low" and "exact expression not found" in str(notes).lower():
                        is_not_found = True
                    else:
                        is_manual = True
                        manual_reason.append("Proxy keyword detected in notes")
                        
                has_null_radar = False
                radar_invalid = False
                if radar is None:
                    has_null_radar = True
                    is_manual = True
                    manual_reason.append("Missing radar_scores_0_100")
                    stats["null_radar_count"] += 1
                elif not isinstance(radar, dict):
                    is_blocked = True
                    blocked_reason.append("radar_scores_0_100 is not an object")
                    radar_invalid = True
                else:
                    for axis in EXPECTED_AXES:
                        if axis not in radar:
                            is_blocked = True
                            blocked_reason.append(f"Missing radar axis: {axis}")
                            radar_invalid = True
                            break
                            
                        val = radar[axis]
                        if val is None:
                            pass
                        elif val == 0:
                            stats["explicit_zero_count"] += 1
                        elif val not in VALID_RADAR_VALUES:
                            is_blocked = True
                            blocked_reason.append(f"Invalid radar value {val} for {axis}")
                            radar_invalid = True
                            break
                            
                    if not radar_invalid:
                        lb = radar.get("light_body")
                        rb = radar.get("rich_body")
                        if lb is not None and rb is not None and lb >= 60 and rb >= 60:
                            is_manual = True
                            manual_reason.append("light_body and rich_body both >= 60")
                            stats["light_rich_conflict_count"] += 1
                            
                match = None
                strategy = "not_found"
                if name and not is_not_found:
                    match, strategy = match_whisky(all_whiskies, name, age, distillery)
                
                record["match_strategy"] = strategy
                stats["match_strategy_dist"][strategy] += 1
                
                if strategy in ["normalized_exact", "age_variant", "distillery_age"]:
                    stats["rescued_match_count"] += 1
                    
                if match:
                    w_id = match[0]
                    record["matched_whisky_id"] = w_id
                    record["matched_name"] = match[1]
                    stats["matched_whisky_id_count"] += 1
                    
                    c_fp, es_fp, rc, c_note, es_note = check_conflicts(cursor, w_id, radar)
                    record["conflict_existing_profile"] = c_fp
                    record["existing_profile_source"] = es_fp
                    record["radar_conflict"] = rc
                    record["conflict_existing_note"] = c_note
                    record["existing_note_source"] = es_note
                    
                    if c_fp: 
                        manual_reason.append("conflict_existing_profile")
                        is_manual = True
                    if c_note: 
                        manual_reason.append("conflict_existing_note")
                        is_manual = True
                    if rc: 
                        manual_reason.append("radar_conflict")
                        is_manual = True
                else:
                    stats["unmatched_count"] += 1
                    is_not_found = True
                    if not has_proxy:
                         stats["not_found_list"].append(f"{name} {age}".strip())
                
                if match and age is not None and str(age).strip() != "":
                    if str(match[2]) != str(age):
                         is_manual = True
                         manual_reason.append("Age mismatch with DB (flag)")
                
                if is_blocked:
                    record["decision_reason"] = "; ".join(blocked_reason)
                    record["bucket"] = "blocked"
                    for r in blocked_reason: stats["blocked_reasons"][r] += 1
                    blocked.append(record)
                elif is_not_found:
                    if confidence == "low" and "exact expression not found" in str(notes).lower():
                         record["decision_reason"] = "confidence=low + exact expression not found"
                    else:
                         record["decision_reason"] = "Not found in DB"
                    record["bucket"] = "not_found"
                    not_found.append(record)
                elif is_manual or confidence == "medium":
                    if confidence == "medium": manual_reason.append("confidence=medium")
                    record["decision_reason"] = "; ".join(manual_reason)
                    record["bucket"] = "manual_review"
                    for r in manual_reason: stats["manual_review_reasons"][r] += 1
                    manual_review.append(record)
                elif confidence == "low":
                    manual_reason.append("confidence=low")
                    record["decision_reason"] = "; ".join(manual_reason)
                    record["bucket"] = "manual_review"
                    for r in manual_reason: stats["manual_review_reasons"][r] += 1
                    manual_review.append(record)
                elif confidence == "high" and match and not has_null_radar and not has_proxy:
                    record["decision_reason"] = "Clean match"
                    record["bucket"] = "accept_preview"
                    accept_preview.append(record)
                else:
                    manual_reason.append("Fallback to manual")
                    record["decision_reason"] = "; ".join(manual_reason)
                    record["bucket"] = "manual_review"
                    for r in manual_reason: stats["manual_review_reasons"][r] += 1
                    manual_review.append(record)
                    
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            stats["input_errors"] += 1
            stats["input_error_files"].append(os.path.basename(file_path))
            traceback.print_exc()

    write_csv(accept_preview, os.path.join(OUTPUT_CSV_DIR, "book_profile_accept_preview.csv"))
    write_csv(manual_review, os.path.join(OUTPUT_CSV_DIR, "book_profile_manual_review.csv"))
    write_csv(not_found, os.path.join(OUTPUT_CSV_DIR, "book_profile_not_found.csv"))
    write_csv(blocked, os.path.join(OUTPUT_CSV_DIR, "book_profile_blocked.csv"))
    
    bucket_mismatch = 0
    if stats['input_rows'] != (len(accept_preview) + len(manual_review) + len(not_found) + len(blocked)):
        bucket_mismatch = 1

    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write(f"# NotebookLM Book Profile Validator Report\n\n")
        f.write("""\nEstimated API Cost: $0.00\nActual API Cost: $0.00\nLocal Compute Used: Yes\nFully Local Execution: Yes\n""")

        f.write(f"- generated_at: {datetime.now().isoformat()}\n")
        f.write(f"- input_files: {len(json_files)}\n")
        f.write(f"- input_rows: {stats['input_rows']}\n")
        f.write(f"- input_errors: {stats['input_errors']}\n")
        f.write(f"- accept_preview: {len(accept_preview)}\n")
        f.write(f"- manual_review: {len(manual_review)}\n")
        f.write(f"- not_found: {len(not_found)}\n")
        f.write(f"- blocked: {len(blocked)}\n")
        f.write(f"- matched_whisky_id_count: {stats['matched_whisky_id_count']}\n")
        f.write(f"- unmatched_count: {stats['unmatched_count']}\n")
        f.write(f"- explicit_zero_count: {stats['explicit_zero_count']}\n")
        f.write(f"- null_radar_count: {stats['null_radar_count']}\n")
        f.write(f"- light_rich_conflict_count: {stats['light_rich_conflict_count']}\n")
        f.write(f"- previous_not_found_estimate: 21\n")
        f.write(f"- current_not_found: {len(not_found)}\n")
        f.write(f"- rescued_match_count: {stats['rescued_match_count']}\n")
        f.write(f"- bucket_mismatch: {bucket_mismatch}\n\n")
        
        f.write("## Match Strategy Dağılımı\n")
        for k, v in stats['match_strategy_dist'].items():
            f.write(f"- {k}: {v}\n")
            
        f.write("\n## Confidence Dağılımı\n")
        for k, v in stats['confidence_dist'].items():
            f.write(f"- {k}: {v}\n")
            
        f.write("\n## Source/Book Dağılımı\n")
        for k, v in stats['source_book_dist'].items():
            f.write(f"- {k}: {v}\n")
            
        f.write("\n## Not Found Whisky Listesi (Top 50)\n")
        for w, count in Counter(stats['not_found_list']).most_common(50):
            f.write(f"- {w} ({count})\n")
            
        f.write("\n## Manual Review Sebepleri\n")
        for k, v in stats['manual_review_reasons'].items():
            f.write(f"- {k}: {v}\n")
            
        f.write("\n## Blocked Sebepleri\n")
        for k, v in stats['blocked_reasons'].items():
            f.write(f"- {k}: {v}\n")
            
        if stats['input_error_files']:
            f.write("\n## Input Error Files\n")
            for ef in stats['input_error_files']:
                f.write(f"- {ef}\n")

    with open(GATE_FILE, 'w', encoding='utf-8') as f:
        if stats['input_errors'] > 0:
            f.write("BOOK_NOTEBOOKLM_VALIDATOR_NO-GO\n")
        elif stats['input_rows'] == 0:
            f.write("BOOK_NOTEBOOKLM_VALIDATOR_EMPTY_INPUT\n")
        elif len(blocked) == 0 and bucket_mismatch == 0:
            f.write("BOOK_NOTEBOOKLM_VALIDATOR_GO\n")
        else:
            f.write("BOOK_NOTEBOOKLM_VALIDATOR_NO-GO\n")
            
        f.write(f"ACCEPT_PREVIEW={len(accept_preview)}\n")
        f.write(f"MANUAL_REVIEW={len(manual_review)}\n")
        f.write(f"NOT_FOUND={len(not_found)}\n")
        f.write(f"BLOCKED={len(blocked)}\n")
        f.write(f"INPUT_ERRORS={stats['input_errors']}\n")
        f.write(f"BUCKET_MISMATCH={bucket_mismatch}\n")

if __name__ == '__main__':
    main()
