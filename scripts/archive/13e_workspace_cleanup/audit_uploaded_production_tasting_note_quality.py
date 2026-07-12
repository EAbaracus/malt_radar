import sqlite3
import re
import os
import csv
import hashlib
from collections import Counter

DB_PATH = "output/import/production.db"
AUDIT_CSV = "data/output/uploaded_production_tasting_notes_quality_audit.csv"
QUARANTINE_CSV = "data/output/uploaded_production_tasting_notes_quarantine_candidates.csv"
REPORT_MD = "output/reports/265_uploaded_production_tasting_notes_quality_audit_report.md"
GATE_TXT = "output/reports/266_12o_uploaded_production_tasting_notes_quality_gate.txt"

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

def audit():
    db_hash_before = get_file_hash(DB_PATH)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM tasting_notes")
    pre_tn = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM flavor_profiles")
    pre_fp = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM tasting_notes WHERE source_system='uploaded_document'")
    pre_uploaded = cursor.fetchone()[0]
    
    cursor.execute("SELECT whisky_id, name FROM whiskies")
    whisky_names = {r[0]: r[1] for r in cursor.fetchall()}
    
    cursor.execute("""
        SELECT rowid, whisky_id, source_system, nose_notes, palate_notes, finish_notes 
        FROM tasting_notes 
        WHERE source_system='uploaded_document'
    """)
    rows = cursor.fetchall()
    
    audit_data = []
    quarantine_data = []
    
    stats = Counter()
    
    for row in rows:
        rowid = row[0]
        wid = row[1]
        source_system = row[2]
        nose = str(row[3] or "").strip()
        palate = str(row[4] or "").strip()
        finish = str(row[5] or "").strip()
        
        full_text = f"{nose} {palate} {finish}".strip()
        total_text_length = len(full_text)
        
        axes_hit = set()
        kws_hit = 0
        
        lower_text = full_text.lower()
        for axis, keywords in FLAVOR_MAPPING.items():
            for kw in keywords:
                pattern = r'\b' + re.escape(kw) + r'\b'
                hits = len(re.findall(pattern, lower_text))
                if hits > 0:
                    kws_hit += hits
                    axes_hit.add(axis)
                    
        axis_count = len(axes_hit)
        
        placeholder_pattern = False
        if "nice aroma for" in lower_text or "nice taste for" in lower_text or "nice finish for" in lower_text:
            placeholder_pattern = True
        if "aroma profile for" in lower_text or "taste profile for" in lower_text:
            placeholder_pattern = True
            
        low_signal = total_text_length < 150 or kws_hit < 2 or axis_count < 2
        
        if placeholder_pattern:
            decision = "quarantine_recommended"
            reason = "Placeholder / Mock pattern detected"
        elif low_signal:
            decision = "quarantine_recommended"
            reason = "Low signal / Too short or insufficient keywords"
        elif axis_count >= 2 and total_text_length >= 150:
            decision = "keep_production_candidate"
            reason = "Good quality"
        else:
            decision = "manual_review"
            reason = "Borderline quality"
            
        stats[decision] += 1
        if placeholder_pattern:
            stats["placeholder_pattern"] += 1
            
        snippet = full_text[:80] + "..." if len(full_text) > 80 else full_text
        
        out_row = {
            'tasting_note_id': rowid,
            'whisky_id': wid,
            'product_name': whisky_names.get(wid, 'Unknown'),
            'source_system': source_system,
            'total_text_length': total_text_length,
            'keyword_hit_count': kws_hit,
            'axis_count': axis_count,
            'placeholder_pattern': placeholder_pattern,
            'low_signal': low_signal,
            'production_quality_decision': decision,
            'reason': reason,
            'short_snippet': snippet
        }
        
        audit_data.append(out_row)
        if decision == "quarantine_recommended":
            quarantine_data.append(out_row)
            
    conn.close()
    
    # Check DB hash
    db_hash_after = get_file_hash(DB_PATH)
    db_changed = db_hash_before != db_hash_after
    
    fieldnames = [
        'tasting_note_id', 'whisky_id', 'product_name', 'source_system', 
        'total_text_length', 'keyword_hit_count', 'axis_count', 
        'placeholder_pattern', 'low_signal', 'production_quality_decision', 
        'reason', 'short_snippet'
    ]
    
    for f_path, data in [(AUDIT_CSV, audit_data), (QUARANTINE_CSV, quarantine_data)]:
        os.makedirs(os.path.dirname(f_path), exist_ok=True)
        with open(f_path, 'w', newline='', encoding='utf-8') as f:
            if data:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(data)
                
    with open(REPORT_MD, 'w', encoding='utf-8') as f:
        f.write("# Uploaded Production Tasting Notes Quality Audit Report\n\n")
        f.write("
Estimated API Cost: $0.00
Actual API Cost: $0.00
Local Compute Used: Yes
Fully Local Execution: Yes
")

        f.write(f"- Total notes audited: {len(audit_data)}\n")
        f.write(f"- keep_production_candidate: {stats['keep_production_candidate']}\n")
        f.write(f"- quarantine_recommended: {stats['quarantine_recommended']}\n")
        f.write(f"- manual_review: {stats['manual_review']}\n")
        f.write(f"- Notes with placeholder patterns: {stats['placeholder_pattern']}\n\n")
        if stats['quarantine_recommended'] >= 30:
            f.write("## Recommendation\n")
            f.write("A large majority of the production tasting notes from uploaded documents are of poor quality (placeholders or low signal). It is strongly recommended to initiate `12O-ROLLBACK` to remove these records from the `tasting_notes` table and reset their status in `staging_tasting_notes`.\n")
            
    gate = "GO"
    reasons = []
    
    if db_changed:
        gate = "NO-GO_TECHNICAL"
        reasons.append("production.db was modified during execution!")
    elif pre_uploaded != 60:
        gate = "NO-GO_TECHNICAL"
        reasons.append(f"Expected 60 uploaded_document records, got {pre_uploaded}")
    elif stats['quarantine_recommended'] >= 30 or stats['placeholder_pattern'] >= 30:
        gate = "NO-GO_FOR_DATA_QUALITY"
        reasons.append(f"quarantine_recommended = {stats['quarantine_recommended']}, placeholder_pattern = {stats['placeholder_pattern']}. Quality threshold failed.")
        
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
            f.write("- Quality audit completed successfully.\n")

if __name__ == "__main__":
    audit()
