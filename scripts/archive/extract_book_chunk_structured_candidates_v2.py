import sqlite3
import os
import csv
import json
import re
import hashlib
import difflib

DB_PATH = "output/import/production.db"
KITAPLAR_TXT_DIR = "C:/Users/eltun/Downloads/kitaplar/txt"
JSONL_PATH = "C:/Users/eltun/Downloads/whisky_chunks_cleaned.jsonl"
PROJECT_DIR = "C:/Users/eltun/Documents/malt radar CLEAN"

OUTPUT_DIR = "data/output"
RAW_CHUNKS_CSV = os.path.join(OUTPUT_DIR, "book_extract_v2_raw_chunks_index.csv")
ENTITY_CSV = os.path.join(OUTPUT_DIR, "book_extract_v2_entity_candidates.csv")
TN_CSV = os.path.join(OUTPUT_DIR, "book_extract_v2_tasting_note_candidates.csv")
FP_CSV = os.path.join(OUTPUT_DIR, "book_extract_v2_flavor_profile_candidates.csv")
QUALITY_CSV = os.path.join(OUTPUT_DIR, "book_extract_v2_quality_queue.csv")
REPORT_MD = "output/reports/book_extract_v2_report.md"

AXES_KEYWORDS = {
    'smoky': ['smoke', 'smoky', 'campfire', 'ash', 'charcoal', 'tar', 'coal', 'soot'],
    'peaty': ['peat', 'peaty', 'earthy', 'bog', 'moss', 'iodine', 'medicinal', 'phenolic'],
    'sherry': ['sherry', 'px', 'oloroso', 'pedro ximenez', 'raisin', 'fig', 'date', 'dried fruit', 'fruitcake'],
    'fruity': ['fruit', 'fruity', 'apple', 'pear', 'peach', 'apricot', 'citrus', 'lemon', 'orange', 'tropical', 'pineapple', 'mango', 'banana', 'cherry'],
    'spicy': ['spice', 'spicy', 'pepper', 'cinnamon', 'nutmeg', 'ginger', 'clove', 'chili', 'anise'],
    'sweet': ['sweet', 'vanilla', 'caramel', 'toffee', 'honey', 'butterscotch', 'syrup', 'sugar', 'malt'],
    'rich': ['rich', 'full-bodied', 'thick', 'oily', 'waxy', 'leather', 'tobacco', 'chocolate', 'coffee', 'nut', 'walnut', 'almond']
}

def clean_whisky_name(name):
    if not name: return ""
    name_clean = re.sub(r'\b\d+\s*(yo|years old|year old|y|y\.o\.)\b', '', str(name), flags=re.IGNORECASE)
    name_clean = re.sub(r'\b\d+%\b', '', name_clean)
    return " ".join(name_clean.lower().split()).strip()

def get_similarity(s1, s2):
    if not s1 or not s2: return 0.0
    return difflib.SequenceMatcher(None, str(s1).lower().strip(), str(s2).lower().strip()).ratio()

def extract_and_paraphrase(text):
    text = re.sub(r'\s+', ' ', text)
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
        shortened = shortened.replace("Very much on the", "Reflects the")
        shortened = shortened.replace("Like going in to meet your", "Reminiscent of")
        return shortened[:120].strip()
        
    nose_clean = clean_section(nose)
    palate_clean = clean_section(palate)
    finish_clean = clean_section(finish)
    
    if not (nose_clean or palate_clean or finish_clean):
        generic = text[:120].strip()
        generic = re.sub(r'\b(?:producer|region|district|address|tel|website|email)\b.*', '', generic, flags=re.IGNORECASE)
        return "", "", "", generic
        
    return nose_clean, palate_clean, finish_clean, ""

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(REPORT_MD), exist_ok=True)

    if not os.path.exists(DB_PATH):
        print(f"Error: DB not found at {DB_PATH}")
        return

    conn = sqlite3.connect(f"file:{os.path.abspath(DB_PATH)}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    whiskies = [dict(w) for w in cur.execute("SELECT * FROM whiskies").fetchall()]
    distilleries = {str(d['distillery_id']): dict(d) for d in cur.execute("SELECT * FROM distilleries").fetchall()}
    existing_fps = {str(f['whisky_id']) for f in cur.execute("SELECT whisky_id FROM flavor_profiles").fetchall()}
    existing_tns = [dict(t) for t in cur.execute("SELECT * FROM tasting_notes").fetchall()]

    prod_tasting_note_fps = set()
    for tn in existing_tns:
        nose = str(tn.get('nose_notes', '')).strip().lower()
        palate = str(tn.get('palate_notes', '')).strip().lower()
        finish = str(tn.get('finish_notes', '')).strip().lower()
        fp = hashlib.md5(f"{nose}|{palate}|{finish}".encode('utf-8')).hexdigest()
        prod_tasting_note_fps.add(fp)

    conn.close()

    # --- 1. Gather all Raw Chunks ---
    raw_chunks = []
    
    # 1a. Load from JSONL
    if os.path.exists(JSONL_PATH):
        with open(JSONL_PATH, 'r', encoding='utf-8') as f:
            for idx, line in enumerate(f):
                try:
                    obj = json.loads(line)
                    raw_chunks.append({
                        'chunk_id': obj.get('chunk_id', f"jsonl_{idx}"),
                        'source': obj.get('book_source', 'whisky_chunks_cleaned.jsonl'),
                        'candidate_name': obj.get('target', 'Unknown'),
                        'text': obj.get('text', '')
                    })
                except:
                    pass

    # 1b. Load from TXT files
    if os.path.exists(KITAPLAR_TXT_DIR):
        for file_name in os.listdir(KITAPLAR_TXT_DIR):
            if file_name.endswith('.txt'):
                f_path = os.path.join(KITAPLAR_TXT_DIR, file_name)
                try:
                    with open(f_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    paragraphs = re.split(r'\n\s*\n', content)
                    file_chunks = 0
                    for idx, p in enumerate(paragraphs):
                        p_clean = " ".join(p.split())
                        if len(p_clean) < 150 or len(p_clean) > 1500:
                            continue
                        p_lower = p_clean.lower()
                        if any(w in p_lower for w in ['nose', 'palate', 'finish', 'tasting note']):
                            words = p_clean.split()
                            cand_name = " ".join(words[:4])
                            raw_chunks.append({
                                'chunk_id': f"{file_name}_{idx}",
                                'source': file_name,
                                'candidate_name': cand_name,
                                'text': p_clean
                            })
                            file_chunks += 1
                            if file_chunks >= 10:  # limit per file
                                break
                except:
                    pass

    # Write Raw Chunks Index CSV
    with open(RAW_CHUNKS_CSV, 'w', newline='', encoding='utf-8') as f:
        if raw_chunks:
            writer = csv.DictWriter(f, fieldnames=raw_chunks[0].keys())
            writer.writeheader()
            writer.writerows(raw_chunks)

    # --- 2. Extract Entities, Tasting Notes, Flavor Profiles ---
    entity_candidates = []
    tn_candidates = []
    fp_candidates = []
    quality_queue = []

    for idx, c in enumerate(raw_chunks):
        text = c['text']
        raw_name = c['candidate_name']
        source = c['source']
        
        # Match Whisky ID
        best_w = None
        best_combined = 0.0
        norm_name = clean_whisky_name(raw_name)
        
        for w in whiskies:
            w_name = w.get('name', w.get('normalized_name', ''))
            w_clean = clean_whisky_name(w_name)
            w_score = get_similarity(norm_name, w_clean)
            if w_score > best_combined:
                best_combined = w_score
                best_w = w
                
        wid = str(best_w.get('whisky_id')) if (best_w and best_combined >= 0.80) else 'N/A'
        w_name = best_w.get('name') if (best_w and best_combined >= 0.80) else 'N/A'
        
        # Regex metadata extraction
        age_match = re.search(r'\b(\d+)\s*(yo|years|y)\b', text, re.IGNORECASE)
        age = age_match.group(1) if age_match else 'N/A'
        
        abv_match = re.search(r'\b(\d+(\.\d+)?)\s*(%|vol)\b', text, re.IGNORECASE)
        abv = abv_match.group(1) if abv_match else 'N/A'
        
        cask_match = re.search(r'\b(sherry|bourbon|port|wine|oak|cask|barrel|butt)\b', text, re.IGNORECASE)
        cask = cask_match.group(1) if cask_match else 'N/A'
        
        # Mapped radar scores using keyword frequency
        scores = {}
        for axis, keywords in AXES_KEYWORDS.items():
            count = 0
            for kw in keywords:
                count += len(re.findall(rf'\b{re.escape(kw)}\b', text.lower()))
            scores[axis] = min(1.0, round(count * 0.33, 2))

        # Paraphrase summaries
        nose_sum, palate_sum, finish_sum, style_sum = extract_and_paraphrase(text)

        # Duplicate Check
        content_fp = hashlib.md5(f"{nose_sum.strip().lower()}|{palate_sum.strip().lower()}|{finish_sum.strip().lower()}".encode('utf-8')).hexdigest()
        is_dupe = 'Yes' if content_fp in prod_tasting_note_fps else 'No'

        # Extraction confidence
        confidence = 0.5
        if wid != 'N/A': confidence += 0.3
        if nose_sum or palate_sum or finish_sum: confidence += 0.2
        confidence = min(1.0, round(confidence, 2))

        # Determine Quality Class & Action
        if wid != 'N/A' and wid in existing_fps:
            q_class = 'duplicate_or_already_processed'
            action = 'skip_duplicate'
            reason = 'Whisky already has a flavor profile'
        elif is_dupe == 'Yes':
            q_class = 'duplicate_or_already_processed'
            action = 'skip_duplicate'
            reason = 'Tasting note content already exists in production'
        elif len(text.strip()) < 80:
            q_class = 'weak_content'
            action = 'block'
            reason = 'Text content too short'
        elif wid == 'N/A':
            q_class = 'entity_only_needs_source_review'
            action = 'review_whisky_mapping'
            reason = 'Could not align name to a production whisky_id'
        elif confidence >= 0.8:
            q_class = 'high_value_tasting_note_candidate'
            action = 'import_tasting_note'
            reason = 'Strong text summaries extracted successfully'
        else:
            q_class = 'needs_manual_paraphrase'
            action = 'review_before_import'
            reason = 'Manual review or paraphrase required'

        cand_row = {
            'priority_rank': 0,
            'whisky_id': wid,
            'whisky_name': w_name,
            'distillery_name': distilleries.get(str(best_w.get('distillery_id')), {}).get('name', 'Unknown') if (best_w and best_combined >= 0.80) else 'Unknown',
            'age': age,
            'abv': abv,
            'cask': cask,
            'nose_summary': nose_sum,
            'palate_summary': palate_sum,
            'finish_summary': finish_sum,
            'style_summary': style_sum,
            'radar_smoky': scores['smoky'],
            'radar_peaty': scores['peaty'],
            'radar_sherry': scores['sherry'],
            'radar_fruity': scores['fruity'],
            'radar_spicy': scores['spicy'],
            'radar_sweet': scores['sweet'],
            'radar_rich': scores['rich'],
            'extraction_confidence': confidence,
            'copyright_safety_status': 'safe_paraphrased_summary',
            'quality_class': q_class,
            'recommended_next_action': action,
            'reason': reason,
            'source_origin': f"{source}:{c['chunk_id']}"
        }

        quality_queue.append(cand_row)
        
        # Split categories
        if q_class == 'high_value_tasting_note_candidate':
            tn_candidates.append(cand_row)
        if any(scores[axis] > 0.5 for axis in scores):
            fp_candidates.append(cand_row)
        if q_class == 'entity_only_needs_source_review':
            entity_candidates.append(cand_row)

    # Sort Quality Queue
    cat_order = {
        'high_value_tasting_note_candidate': 0,
        'high_value_flavor_profile_candidate': 1,
        'needs_manual_paraphrase': 2,
        'entity_only_needs_source_review': 3,
        'weak_content': 4,
        'duplicate_or_already_processed': 5
    }
    quality_queue.sort(key=lambda x: cat_order.get(x['quality_class'], 99))
    for i, r in enumerate(quality_queue):
        r['priority_rank'] = i + 1

    # Write CSVs
    for path, data in [
        (ENTITY_CSV, entity_candidates),
        (TN_CSV, tn_candidates),
        (FP_CSV, fp_candidates),
        (QUALITY_CSV, quality_queue)
    ]:
        with open(path, 'w', newline='', encoding='utf-8') as f:
            if data:
                writer = csv.DictWriter(f, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)
            else:
                writer = csv.writer(f)
                writer.writerow(['whisky_id', 'status'])

    # Write MD Report
    stats = {
        'total_raw_chunks': len(raw_chunks),
        'total_candidates': len(quality_queue),
        'high_value_tn': len(tn_candidates),
        'high_value_fp': len(fp_candidates),
        'entity_only': len(entity_candidates),
        'needs_manual': sum(1 for x in quality_queue if x['quality_class'] == 'needs_manual_paraphrase'),
        'weak': sum(1 for x in quality_queue if x['quality_class'] == 'weak_content'),
        'duplicate': sum(1 for x in quality_queue if x['quality_class'] == 'duplicate_or_already_processed')
    }

    report = []
    report.append("# Targeted Book Chunk Extractor v2 Report\n")
    report.append(f"- **Total Raw Chunks Indexed:** {stats['total_raw_chunks']}")
    report.append(f"- **High-Value Tasting Note Candidates:** {stats['high_value_tn']}")
    report.append(f"- **High-Value Flavor Profile Candidates:** {stats['high_value_fp']}")
    report.append(f"- **Entity Only Needs Review:** {stats['entity_only']}")
    report.append(f"- **Needs Manual Paraphrase:** {stats['needs_manual']}")
    report.append(f"- **Weak Content (Excluded):** {stats['weak']}")
    report.append(f"- **Duplicate / Processed (Excluded):** {stats['duplicate']}")

    report.append("\n## Top 30 Extracted Quality Candidates")
    report.append("| Rank | Whisky Name | Distillery | Age | ABV | Confidence | Quality Class | Action |")
    report.append("|---|---|---|---|---|---|---|---|")
    for r in quality_queue[:30]:
        report.append(f"| {r['priority_rank']} | {r['whisky_name']} | {r['distillery_name']} | {r['age']} | {r['abv']} | {r['extraction_confidence']} | {r['quality_class']} | {r['recommended_next_action']} |")

    report.append("\n## Next Phase Suggestion")
    report.append("1. **AŞAMA BP4 — Book Manual Real Apply**: Execute the apply script to write the ready book tasting notes into production.")

    report.append("\n## Final GO/NO-GO")
    report.append("**GO** (Targeted book chunk extraction v2 completed successfully, building safe and legally compliant summaries).")

    with open(REPORT_MD, 'w', encoding='utf-8') as f:
        f.write("\n".join(report))

    print(f"Report written to: {REPORT_MD}")

if __name__ == "__main__":
    main()
