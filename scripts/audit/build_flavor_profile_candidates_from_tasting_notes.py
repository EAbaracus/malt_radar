import sqlite3
import os
import csv
import re

DB_PATH = "output/import/production.db"
OUTPUT_DIR = "data/output"
CANDIDATES_CSV = os.path.join(OUTPUT_DIR, "flavor_profile_candidates_from_tasting_notes.csv")
PRIORITY_CSV = os.path.join(OUTPUT_DIR, "flavor_profile_candidates_from_tasting_notes_priority_queue.csv")
REPORT_MD = "output/reports/flavor_profile_candidates_from_tasting_notes_report.md"

AXES_KEYWORDS = {
    'smoky': ['smoke', 'smoky', 'campfire', 'ash', 'charcoal', 'tar', 'coal', 'soot'],
    'peaty': ['peat', 'peaty', 'earthy', 'bog', 'moss', 'iodine', 'medicinal', 'phenolic', 'hospital'],
    'sherry': ['sherry', 'px', 'oloroso', 'pedro ximenez', 'raisin', 'fig', 'date', 'dried fruit', 'fruitcake'],
    'fruity': ['fruit', 'fruity', 'apple', 'pear', 'peach', 'apricot', 'citrus', 'lemon', 'orange', 'tropical', 'pineapple', 'mango', 'banana', 'cherry'],
    'spicy': ['spice', 'spicy', 'pepper', 'cinnamon', 'nutmeg', 'ginger', 'clove', 'chili', 'anise'],
    'sweet': ['sweet', 'vanilla', 'caramel', 'toffee', 'honey', 'butterscotch', 'syrup', 'sugar', 'malt', 'maple'],
    'rich': ['rich', 'full-bodied', 'thick', 'oily', 'waxy', 'leather', 'tobacco', 'chocolate', 'coffee', 'nut', 'walnut', 'almond', 'oak']
}

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(REPORT_MD), exist_ok=True)

    if not os.path.exists(DB_PATH):
        print(f"Error: DB not found at {DB_PATH}")
        return

    conn = sqlite3.connect(f"file:{os.path.abspath(DB_PATH)}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    whiskies = {str(w['whisky_id']): dict(w) for w in cur.execute("SELECT * FROM whiskies").fetchall()}
    distilleries = {str(d['distillery_id']): dict(d) for d in cur.execute("SELECT * FROM distilleries").fetchall()}
    
    # Get all tasting notes
    tasting_notes = [dict(n) for n in cur.execute("SELECT * FROM tasting_notes").fetchall()]
    
    # Get existing flavor profiles to exclude
    existing_fps = {str(f['whisky_id']) for f in cur.execute("SELECT whisky_id FROM flavor_profiles").fetchall()}
    
    candidates = []
    
    # Stats
    stats = {
        'total_tn_without_fp': 0,
        'profile_candidate_ready': 0,
        'needs_manual_review': 0,
        'weak_signal': 0,
        'blocked_weak_content': 0
    }
    
    keyword_freq = {}

    for note in tasting_notes:
        wid = str(note.get('whisky_id', ''))
        if not wid or wid in existing_fps:
            continue
            
        stats['total_tn_without_fp'] += 1
        
        nose = str(note.get('nose_notes', '')).lower()
        palate = str(note.get('palate_notes', '')).lower()
        finish = str(note.get('finish_notes', '')).lower()
        summary = str(note.get('notes_for_review', '')).lower()
        
        full_text = f"{nose} {palate} {finish} {summary}"
        full_len = len(full_text.replace(" ", ""))
        
        has_url = bool(str(note.get('source_url', '')).strip())
        
        # Calculate axes
        scores = {}
        matched_words = []
        for axis, keywords in AXES_KEYWORDS.items():
            axis_count = 0
            for kw in keywords:
                # regex to find whole words
                matches = len(re.findall(rf'\b{re.escape(kw)}\b', full_text))
                if matches > 0:
                    axis_count += matches
                    matched_words.extend([kw] * matches)
                    keyword_freq[kw] = keyword_freq.get(kw, 0) + matches
            
            # Simple normalization: 3 mentions of an axis = 1.0
            scores[axis] = min(1.0, round(axis_count * 0.33, 2))
            
        unique_matched = set(matched_words)
        
        # Calculate confidence
        confidence = 0.0
        if full_len > 150: confidence += 0.3
        elif full_len > 50: confidence += 0.1
        
        if len(unique_matched) > 5: confidence += 0.4
        elif len(unique_matched) > 2: confidence += 0.2
        
        if has_url: confidence += 0.2
        
        if nose and palate and finish: confidence += 0.1
        
        confidence = min(1.0, round(confidence, 2))
        
        # Categorize
        if full_len < 40 and not has_url:
            status = 'blocked_weak_content'
            action = 'do_not_import'
            reason = 'Content too short and no URL'
        elif len(unique_matched) == 0:
            status = 'weak_signal'
            action = 'needs_enrichment'
            reason = 'No recognizable flavor keywords found'
        elif confidence >= 0.7:
            status = 'profile_candidate_ready'
            action = 'import_as_flavor_profile'
            reason = 'Strong signal and high confidence'
        elif confidence >= 0.4:
            status = 'needs_manual_review'
            action = 'review_before_import'
            reason = 'Moderate confidence, review recommended'
        else:
            status = 'weak_signal'
            action = 'needs_enrichment'
            reason = 'Low confidence score'
            
        stats[status] += 1
        
        dist_id = str(whiskies.get(wid, {}).get('distillery_id', ''))
        
        candidates.append({
            'priority_rank': 0,
            'whisky_id': wid,
            'whisky_name': whiskies.get(wid, {}).get('name', ''),
            'distillery_name': distilleries.get(dist_id, {}).get('name', ''),
            'source_system': note.get('source_system', ''),
            'source_name': note.get('source_name', ''),
            'source_url': note.get('source_url', ''),
            'note_length_total': full_len,
            'matched_keywords': ", ".join(sorted(list(unique_matched))),
            'smoky_score': scores['smoky'],
            'peaty_score': scores['peaty'],
            'sherry_score': scores['sherry'],
            'fruity_score': scores['fruity'],
            'spicy_score': scores['spicy'],
            'sweet_score': scores['sweet'],
            'rich_score': scores['rich'],
            'confidence_score': confidence,
            'candidate_status': status,
            'recommended_action': action,
            'reason': reason,
            'nose_notes_preview': nose[:50] + "..." if len(nose) > 50 else nose,
            'palate_notes_preview': palate[:50] + "..." if len(palate) > 50 else palate,
            'finish_notes_preview': finish[:50] + "..." if len(finish) > 50 else finish
        })

    # Sort candidates
    def sort_key(c):
        priority = 0
        if c['candidate_status'] == 'profile_candidate_ready': priority = 3
        elif c['candidate_status'] == 'needs_manual_review': priority = 2
        elif c['candidate_status'] == 'weak_signal': priority = 1
        return (priority, c['confidence_score'], c['note_length_total'])
        
    candidates.sort(key=sort_key, reverse=True)
    for i, c in enumerate(candidates):
        c['priority_rank'] = i + 1

    # Write CSVs
    if candidates:
        with open(CANDIDATES_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=candidates[0].keys())
            writer.writeheader()
            writer.writerows(candidates)
            
    priority_queue = [c for c in candidates if c['candidate_status'] in ['profile_candidate_ready', 'needs_manual_review']]
    if priority_queue:
        with open(PRIORITY_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=priority_queue[0].keys())
            writer.writeheader()
            writer.writerows(priority_queue)

    conn.close()

    # Generate Report
    report = []
    report.append("# Flavor Profile Candidate Builder From Tasting Notes Report\n")
    
    report.append("## Generation Summary")
    report.append(f"- Total tasting-note-without-profile count: {stats['total_tn_without_fp']}")
    report.append(f"- Generated candidate count: {len(candidates)}")
    report.append(f"- `profile_candidate_ready` count: {stats['profile_candidate_ready']}")
    report.append(f"- `needs_manual_review` count: {stats['needs_manual_review']}")
    report.append(f"- `weak_signal` count: {stats['weak_signal']}")
    report.append(f"- `blocked_weak_content` count: {stats['blocked_weak_content']}")
    
    cov_gain = (stats['profile_candidate_ready'] / len(whiskies)) * 100 if whiskies else 0
    report.append(f"- Expected immediate coverage gain if ready candidates imported: +{cov_gain:.1f}%")

    report.append("\n## Top 30 Candidates")
    report.append("| Rank | Whisky ID | Whisky Name | Distillery | Confidence | Status | Matched Keywords |")
    report.append("|---|---|---|---|---|---|---|")
    for c in candidates[:30]:
        report.append(f"| {c['priority_rank']} | {c['whisky_id']} | {c['whisky_name']} | {c['distillery_name']} | {c['confidence_score']} | {c['candidate_status']} | {c['matched_keywords']} |")

    top_keywords = sorted(keyword_freq.items(), key=lambda x: x[1], reverse=True)[:15]
    report.append("\n## Most Common Matched Keywords")
    for kw, count in top_keywords:
        report.append(f"- **{kw}**: {count} matches")

    report.append("\n## Recommended Next Phase")
    report.append("- **AŞAMA X3 — Flavor Profile Candidate Dry-Run Import On Backup Copy**: Run a test import of the `profile_candidate_ready` records into a copy of `production.db` to verify schema compliance and calculate the final profile coverage metrics.")

    report.append("\n## Final GO/NO-GO")
    report.append("**GO** (Candidate pack generated successfully and ready for review/dry-run without mutating production).")

    with open(REPORT_MD, 'w', encoding='utf-8') as f:
        f.write("\n".join(report))
        
    print(f"Report generated at: {REPORT_MD}")

if __name__ == "__main__":
    main()
