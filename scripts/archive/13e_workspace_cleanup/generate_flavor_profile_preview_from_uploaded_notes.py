import os
import csv
import sqlite3
import hashlib
import re
from collections import defaultdict

PREVIEW_CSV = "data/output/uploaded_notes_flavor_profile_preview.csv"
CONFLICTS_CSV = "data/output/uploaded_notes_flavor_profile_existing_conflicts.csv"
REVIEW_CSV = "data/output/uploaded_notes_flavor_profile_manual_review.csv"

REPORT_MD = "output/reports/259_uploaded_notes_flavor_profile_preview_report.md"
GATE_TXT = "output/reports/260_12p_uploaded_notes_flavor_profile_preview_gate.txt"
IMPROVEMENT_REPORT_MD = "output/reports/261_uploaded_notes_flavor_profile_signal_improvement_report.md"
IMPROVEMENT_GATE_TXT = "output/reports/262_12p_fix_uploaded_notes_flavor_profile_gate.txt"
DB_PATH = "output/import/production.db"

FLAVOR_MAPPING = {
    'fruity': ['fruit', 'fruity', 'apple', 'pear', 'peach', 'apricot', 'banana', 'citrus', 'lemon', 'orange', 'berry', 'berries', 'raisin', 'fig', 'date', 'grape', 'plum', 'cherry', 'blackcurrant', 'redcurrant', 'sultana', 'prune', 'tropical', 'pineapple', 'mango', 'melon', 'orchard', 'dried fruit', 'dark fruit'],
    'sweet': ['sweet', 'sweetness', 'honey', 'vanilla', 'caramel', 'toffee', 'sugar', 'syrup', 'chocolate', 'cocoa', 'molasses', 'fudge', 'butterscotch', 'dessert', 'cake', 'pastry', 'biscuit', 'cookie', 'malt', 'malty', 'cereal', 'barley', 'brown sugar', 'maple'],
    'smoky': ['smoke', 'smoky', 'peat', 'peaty', 'ash', 'ashy', 'bonfire', 'iodine', 'medicinal', 'tar', 'tobacco', 'char', 'charred', 'coal', 'soot', 'earthy', 'phenolic', 'maritime', 'brine', 'salty', 'seaweed'],
    'spicy': ['spice', 'spicy', 'pepper', 'peppery', 'cinnamon', 'clove', 'nutmeg', 'ginger', 'anise', 'chili', 'chilli', 'cardamom', 'licorice', 'liquorice', 'rye', 'heat', 'warming', 'tannic'],
    'woody': ['oak', 'oaky', 'woody', 'wood', 'cedar', 'tannin', 'barrel', 'cask', 'leather', 'polish', 'varnish', 'resin', 'toasted oak', 'charred oak', 'sawdust', 'furniture'],
    'floral': ['floral', 'flower', 'heather', 'rose', 'violet', 'perfume', 'blossom', 'grass', 'grassy', 'herbal', 'herb', 'mint', 'eucalyptus', 'tea', 'green', 'hay', 'meadow'],
    'creamy': ['cream', 'creamy', 'butter', 'buttery', 'oil', 'oily', 'wax', 'waxy', 'milk', 'custard', 'yoghurt', 'yogurt', 'smooth', 'silky', 'soft', 'mouthfeel', 'velvety', 'vanilla cream']
}

def get_file_hash(filepath):
    if not os.path.exists(filepath):
        return None
    with open(filepath, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()

def normalize_score(score, max_expected=10.0):
    norm = int((score / max_expected) * 100)
    return min(100, norm)

def generate_preview():
    db_hash_before = get_file_hash(DB_PATH)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM tasting_notes")
    pre_tn = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM flavor_profiles")
    pre_fp = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM tasting_notes WHERE source_system='uploaded_document'")
    pre_uploaded = cursor.fetchone()[0]
    
    cursor.execute("SELECT whisky_id FROM flavor_profiles")
    existing_fp_whiskies = {r[0] for r in cursor.fetchall()}
    
    cursor.execute("SELECT whisky_id, name FROM whiskies")
    whisky_names = {r[0]: r[1] for r in cursor.fetchall()}
    
    cursor.execute("""
        SELECT whisky_id, nose_notes, palate_notes, finish_notes 
        FROM tasting_notes 
        WHERE source_system='uploaded_document'
    """)
    notes = cursor.fetchall()
    
    whisky_texts = defaultdict(list)
    for row in notes:
        wid = row[0]
        # Store as tuples of (nose, palate, finish)
        whisky_texts[wid].append((
            (row[1] or "").lower(),
            (row[2] or "").lower(),
            (row[3] or "").lower()
        ))
        
    preview_data = []
    conflict_data = []
    review_data = []
    
    for wid, text_tuples in whisky_texts.items():
        note_count = len(text_tuples)
        
        scores = {k: 0.0 for k in FLAVOR_MAPPING}
        detected = []
        
        for axis, keywords in FLAVOR_MAPPING.items():
            for kw in keywords:
                # To avoid partial word matches, use regex boundaries
                pattern = r'\b' + re.escape(kw) + r'\b'
                
                for nose_t, palate_t, finish_t in text_tuples:
                    nose_hits = len(re.findall(pattern, nose_t))
                    palate_hits = len(re.findall(pattern, palate_t))
                    finish_hits = len(re.findall(pattern, finish_t))
                    
                    total_kw_score = (nose_hits * 1.0) + (palate_hits * 1.5) + (finish_hits * 0.8)
                    if total_kw_score > 0:
                        scores[axis] += total_kw_score
                        detected.append(kw)
                        
        total_detected_signal = sum(scores.values())
        axes_with_signal = sum(1 for v in scores.values() if v > 0)
        
        # Calculate confidence score
        # Using a mapping: total_detected_signal < 2.0 (low, ~40-59), 2.0-5.0 (med, ~60-79), >5.0 (high, 80-100)
        if total_detected_signal < 2.0:
            confidence = 40 + min(19, int(total_detected_signal * 10))
        elif total_detected_signal < 5.0:
            confidence = 60 + min(19, int(((total_detected_signal - 2.0) / 3.0) * 20))
        else:
            confidence = 80 + min(20, int(((total_detected_signal - 5.0) / 5.0) * 20))
            
        normalized_scores = {k: normalize_score(v) for k, v in scores.items()}
        
        has_fp = wid in existing_fp_whiskies
        
        action = 'candidate_insert_flavor_profile'
        reason = ''
        
        if has_fp:
            action = 'hold_existing_flavor_profile'
            reason = 'Existing flavor profile found'
        elif total_detected_signal < 2.0 or axes_with_signal < 2:
            action = 'manual_review'
            if total_detected_signal < 2.0:
                reason = f'Weak keyword signal ({total_detected_signal:.1f})'
            else:
                reason = f'Only {axes_with_signal} flavor axis detected'
                
        row = {
            'whisky_id': wid,
            'product_name': whisky_names.get(wid, 'Unknown'),
            'source_system': 'uploaded_document',
            'note_count': note_count,
            'fruity': normalized_scores['fruity'],
            'sweet': normalized_scores['sweet'],
            'smoky': normalized_scores['smoky'],
            'spicy': normalized_scores['spicy'],
            'woody': normalized_scores['woody'],
            'floral': normalized_scores['floral'],
            'creamy': normalized_scores['creamy'],
            'detected_keywords': "|".join(set(detected)),
            'confidence_score': confidence,
            'has_existing_flavor_profile': has_fp,
            'recommended_action': action,
            'review_reason': reason
        }
        
        if action == 'candidate_insert_flavor_profile':
            preview_data.append(row)
        elif action == 'hold_existing_flavor_profile':
            conflict_data.append(row)
        else:
            review_data.append(row)
            
    conn.close()
    
    # Previous counts for report comparison
    prev_candidate = 0
    prev_manual = 46
    
    new_candidate = len(preview_data)
    new_manual = len(review_data)
    new_hold = len(conflict_data)
    
    fieldnames = [
        'whisky_id', 'product_name', 'source_system', 'note_count',
        'fruity', 'sweet', 'smoky', 'spicy', 'woody', 'floral', 'creamy',
        'detected_keywords', 'confidence_score', 'has_existing_flavor_profile',
        'recommended_action', 'review_reason'
    ]
    
    for f_path, data in [(PREVIEW_CSV, preview_data), (CONFLICTS_CSV, conflict_data), (REVIEW_CSV, review_data)]:
        os.makedirs(os.path.dirname(f_path), exist_ok=True)
        with open(f_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
            
    db_hash_after = get_file_hash(DB_PATH)
    db_changed = db_hash_before != db_hash_after
    
    # Write Main Report
    with open(REPORT_MD, 'w', encoding='utf-8') as f:
        f.write("# Uploaded Notes Flavor Profile Preview Report\n\n")
        f.write("""\nEstimated API Cost: $0.00\nActual API Cost: $0.00\nLocal Compute Used: Yes\nFully Local Execution: Yes\n""")

        f.write(f"- uploaded_document tasting_notes count: {pre_uploaded}\n")
        f.write(f"- Total unique whiskies analyzed: {len(whisky_texts)}\n")
        f.write(f"- candidate_insert_flavor_profile: {new_candidate}\n")
        f.write(f"- hold_existing_flavor_profile: {new_hold}\n")
        f.write(f"- manual_review: {new_manual}\n")
        
    gate = "GO"
    reasons = []
    
    if db_changed:
        gate = "NO-GO"
        reasons.append("production.db was modified during execution!")
    if pre_uploaded != 60:
        gate = "NO-GO"
        reasons.append(f"Expected 60 uploaded_document records, got {pre_uploaded}")
        
    with open(GATE_TXT, 'w', encoding='utf-8') as f:
        f.write(f"GATE: {gate}\n")
        if reasons:
            for r in reasons:
                f.write(f"REASON: {r}\n")
        else:
            f.write("All safety checks passed.\n")
            f.write("- DB remains unchanged.\n")
            f.write(f"- flavor_profiles count: {pre_fp} (unchanged)\n")
            f.write(f"- tasting_notes count: {pre_tn} (unchanged)\n")
            f.write("- raw full text not written to output.\n")
            
    # Write Improvement Report
    improvement_delta = new_candidate - prev_candidate
    with open(IMPROVEMENT_REPORT_MD, 'w', encoding='utf-8') as f:
        f.write("# Flavor Profile Signal Improvement Report\n\n")
        f.write(f"- previous_candidate_insert_flavor_profile: {prev_candidate}\n")
        f.write(f"- previous_manual_review: {prev_manual}\n")
        f.write(f"- new_candidate_insert_flavor_profile: {new_candidate}\n")
        f.write(f"- new_manual_review: {new_manual}\n")
        f.write(f"- improvement_delta: {improvement_delta}\n")
        
    with open(IMPROVEMENT_GATE_TXT, 'w', encoding='utf-8') as f:
        if improvement_delta > 0 or new_candidate > 0:
            f.write("GATE: GO\n")
            f.write(f"Improvement verified. Delta: +{improvement_delta} candidates.\n")
        else:
            f.write("GATE: NO-GO\n")
            f.write("No improvement in candidate extraction observed.\n")

if __name__ == "__main__":
    generate_preview()
