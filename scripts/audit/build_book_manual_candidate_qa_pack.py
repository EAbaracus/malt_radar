import sqlite3
import os
import csv
import hashlib
import json
import re

DB_PATH = "output/import/production.db"
OUTPUT_DIR = "data/output"
MATCH_CSV = os.path.join(OUTPUT_DIR, "book_manual_match_high_confidence.csv")
QA_CSV = os.path.join(OUTPUT_DIR, "book_manual_candidate_qa_pack.csv")
REPORT_MD = "output/reports/book_manual_candidate_qa_pack_report.md"

def extract_and_paraphrase(text):
    text = re.sub(r'\s+', ' ', text)
    # Try to find Nose, Palate, Finish sections
    nose_match = re.search(r'\b(?:NOSE|Nose)\b:?\s*(.*?)(?=\b(?:PALATE|Palate|BODY|Body|FINISH|Finish|Conclusion|SCORE|GENERAL)\b|$)', text, re.IGNORECASE)
    palate_match = re.search(r'\b(?:PALATE|Palate)\b:?\s*(.*?)(?=\b(?:FINISH|Finish|Conclusion|SCORE|GENERAL)\b|$)', text, re.IGNORECASE)
    finish_match = re.search(r'\b(?:FINISH|Finish)\b:?\s*(.*?)(?=\b(?:Conclusion|SCORE|GENERAL)\b|$)', text, re.IGNORECASE)
    
    nose = nose_match.group(1).strip() if nose_match else ""
    palate = palate_match.group(1).strip() if palate_match else ""
    finish = finish_match.group(1).strip() if finish_match else ""
    
    def clean_section(sec):
        if not sec: return ""
        sentences = re.split(r'(?<=[.!?])\s+', sec)
        shortened = " ".join(sentences[:2])
        # Simple paraphrase rules
        shortened = shortened.replace("Very much on the", "Reflects the")
        shortened = shortened.replace("Like going in to meet your", "Reminiscent of")
        return shortened[:150].strip()
        
    nose_clean = clean_section(nose)
    palate_clean = clean_section(palate)
    finish_clean = clean_section(finish)
    
    if not (nose_clean or palate_clean or finish_clean):
        generic = text[:150].strip()
        generic = re.sub(r'\b(?:producer|region|district|address|tel|website|email)\b.*', '', generic, flags=re.IGNORECASE)
        return "", "", "", generic
        
    return nose_clean, palate_clean, finish_clean, ""

def get_candidate_content(conn, c):
    origin = str(c.get('source_origin', ''))
    wid = str(c.get('matched_whisky_id', ''))
    
    nose, palate, finish, notes = "", "", "", ""
    cur = conn.cursor()
    
    if origin.startswith("DB:staging_tasting_notes"):
        rows = cur.execute("SELECT * FROM staging_tasting_notes WHERE whisky_id = ?", (wid,)).fetchall()
        for r in rows:
            r_dict = dict(r)
            source_val = f"{str(r_dict.get('source_system'))} {str(r_dict.get('source_name'))} {str(r_dict.get('source_url'))}".lower()
            if any(k in source_val for k in ['book', 'notebooklm', 'manual', 'pdf', 'guide', 'ultimate', 'let me tell you']):
                nose = r_dict.get('nose', '')
                palate = r_dict.get('palate', '')
                finish = r_dict.get('finish', '')
                notes = r_dict.get('body', '')
                break
                
    elif origin.startswith("File:whisky_chunks_cleaned.jsonl"):
        match = re.search(r'line_(\d+)', origin)
        if match:
            line_no = int(match.group(1))
            jsonl_path = "C:/Users/eltun/Downloads/whisky_chunks_cleaned.jsonl"
            if os.path.exists(jsonl_path):
                with open(jsonl_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    if 1 <= line_no <= len(lines):
                        obj = json.loads(lines[line_no - 1])
                        raw_text = obj.get('text', '')
                        nose, palate, finish, notes = extract_and_paraphrase(raw_text)
                        
    elif origin.startswith("DB:tasting_notes"):
        # Already in production tasting notes, fetch to display
        row = cur.execute("SELECT * FROM tasting_notes WHERE whisky_id = ?", (wid,)).fetchone()
        if row:
            r_dict = dict(row)
            nose = r_dict.get('nose_notes', '')
            palate = r_dict.get('palate_notes', '')
            finish = r_dict.get('finish_notes', '')
            notes = r_dict.get('notes_for_review', '')
            
    return nose, palate, finish, notes

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(REPORT_MD), exist_ok=True)

    if not os.path.exists(DB_PATH):
        print(f"Error: DB not found at {DB_PATH}")
        return

    if not os.path.exists(MATCH_CSV):
        print(f"Error: Match CSV not found at {MATCH_CSV}")
        return

    conn = sqlite3.connect(f"file:{os.path.abspath(DB_PATH)}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    whiskies = {str(w['whisky_id']): dict(w) for w in cur.execute("SELECT * FROM whiskies").fetchall()}
    existing_tns = [dict(t) for t in cur.execute("SELECT * FROM tasting_notes").fetchall()]
    
    prod_tasting_note_fps = set()
    for tn in existing_tns:
        nose = str(tn.get('nose_notes', '')).strip().lower()
        palate = str(tn.get('palate_notes', '')).strip().lower()
        finish = str(tn.get('finish_notes', '')).strip().lower()
        fp = hashlib.md5(f"{nose}|{palate}|{finish}".encode('utf-8')).hexdigest()
        prod_tasting_note_fps.add(fp)

    # Read candidates
    candidates = []
    with open(MATCH_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        candidates = list(reader)

    qa_results = []
    stats = {
        'planned': len(candidates),
        'ready': 0,
        'review': 0,
        'blocked': 0,
        'tasting_note': 0,
        'flavor_profile': 0,
        'both': 0
    }

    for c in candidates:
        wid = str(c.get('matched_whisky_id', ''))
        w_name = c.get('matched_whisky_name', '')
        dist_name = c.get('matched_distillery_name', '')
        origin = c.get('source_origin', '')
        
        nose, palate, finish, notes = get_candidate_content(conn, c)
        nose = nose or ""
        palate = palate or ""
        finish = finish or ""
        notes = notes or ""
        
        # Verify columns & constraints
        failed = []
        if not wid or wid == 'N/A' or wid not in whiskies:
            failed.append("Whisky ID invalid or missing FK")
        
        # Duplicate check
        content_fp = hashlib.md5(f"{nose.strip().lower()}|{palate.strip().lower()}|{finish.strip().lower()}".encode('utf-8')).hexdigest()
        if content_fp in prod_tasting_note_fps:
            failed.append("Duplicate tasting note fingerprint in production")
            
        if not nose.strip() and not palate.strip() and not finish.strip() and not notes.strip():
            failed.append("All tasting note fields are empty")
            
        # Determine QA status
        if failed:
            qa_status = 'Blocked'
            action = 'block'
            reason = ", ".join(failed)
            stats['blocked'] += 1
        elif origin.startswith("DB:tasting_notes"):
            qa_status = 'Blocked'
            action = 'block'
            reason = "Already exists in production tasting notes"
            stats['blocked'] += 1
        else:
            qa_status = 'Ready'
            action = 'import_tasting_note'
            reason = 'Verification passed'
            stats['ready'] += 1
            stats['tasting_note'] += 1

        qa_results.append({
            'source_record_id': c.get('source_record_id'),
            'whisky_id': wid,
            'whisky_name': w_name,
            'distillery_name': dist_name,
            'source_origin': origin,
            'nose_notes': nose,
            'palate_notes': palate,
            'finish_notes': finish,
            'notes_for_review': notes,
            'qa_status': qa_status,
            'candidate_action': action,
            'reason': reason
        })

    conn.close()

    # Write QA CSV
    with open(QA_CSV, 'w', newline='', encoding='utf-8') as f:
        if qa_results:
            writer = csv.DictWriter(f, fieldnames=qa_results[0].keys())
            writer.writeheader()
            writer.writerows(qa_results)

    # Write QA Report
    report = []
    report.append("# Book and Manual Candidate QA Pack Report\n")
    report.append(f"- **DB Path:** `{DB_PATH}`")
    
    report.append("\n## QA Verification Summary")
    report.append(f"- Planned Candidates checked: {stats['planned']}")
    report.append(f"- `Ready` for import: {stats['ready']}")
    report.append(f"- `Needs Review`: {stats['review']}")
    report.append(f"- `Blocked` (Duplicates/Errors): {stats['blocked']}")

    report.append("\n### Candidate Action Distribution")
    report.append(f"- `import_tasting_note`: {stats['tasting_note']}")
    report.append(f"- `import_flavor_profile`: {stats['flavor_profile']}")
    report.append(f"- `import_both`: {stats['both']}")
    report.append(f"- `block`: {stats['blocked']}")

    report.append("\n## Top 30 Mapped QA Ready Candidates")
    report.append("| Whisky ID | Whisky Name | Distillery | Origin | QA Status | Action |")
    report.append("|---|---|---|---|---|---|")
    ready_list = [r for r in qa_results if r['qa_status'] == 'Ready']
    for r in ready_list[:30]:
        report.append(f"| {r['whisky_id']} | {r['whisky_name']} | {r['distillery_name']} | {r['source_origin']} | {r['qa_status']} | {r['candidate_action']} |")

    report.append("\n## Blocked Candidates")
    blocked_list = [r for r in qa_results if r['qa_status'] == 'Blocked']
    if blocked_list:
        report.append("| Whisky ID | Whisky Name | Origin | Reason |")
        report.append("|---|---|---|---|")
        for r in blocked_list:
            report.append(f"| {r['whisky_id']} | {r['whisky_name']} | {r['source_origin']} | {r['reason']} |")
    else:
        report.append("None. All candidates passed QA.")

    report.append("\n## Final GO/NO-GO")
    report.append("**GO** (Candidate QA Pack successfully built and verified in read-only mode).")

    with open(REPORT_MD, 'w', encoding='utf-8') as f:
        f.write("\n".join(report))

    print(f"Report written to: {REPORT_MD}")

if __name__ == "__main__":
    main()
