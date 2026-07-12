"""
P44-LEGACY-FLAVOR-BACKFILL (Dry-Run Phase)
Computes candidate inserts and updates for legacy whisky flavor profiles.
NO database writes, commits, or backups deletion.
"""
import os, sys, sqlite3, json, hashlib, re
from datetime import datetime

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

ROOT      = r"C:\Users\eltun\Documents\malt radar CLEAN"
REPORTS   = os.path.join(ROOT, "output", "reports")
PROD_DB   = os.path.join(ROOT, "output", "import", "production.db")
PRE_HASH  = "BCED0910907E00811BFEC2860A0635769F4F8CB88D6F76503D446771E6B54629"

OUT_DRY_RUN = os.path.join(REPORTS, "p44_legacy_flavor_backfill_dry_run.md")

AXES_KEYWORDS = {
    'smoky': ['smoke', 'smoky', 'campfire', 'ash', 'charcoal', 'tar', 'coal', 'soot', 'bonfire', 'barbecue'],
    'peaty': ['peat', 'peaty', 'earthy', 'bog', 'moss', 'phenolic', 'medicinal', 'hospital', 'heather'],
    'sherry': ['sherry', 'px', 'oloroso', 'pedro ximenez', 'raisin', 'raisins', 'fig', 'figs', 'date', 'dates', 'dried fruit', 'fruitcake'],
    'fruity': ['fruit', 'fruity', 'apple', 'apples', 'pear', 'pears', 'peach', 'apricot', 'citrus', 'lemon', 'orange', 'tropical', 'pineapple', 'mango', 'banana', 'cherry', 'cherries', 'lime', 'plum', 'zest', 'grapefruit'],
    'sweet': ['sweet', 'honey', 'caramel', 'toffee', 'vanilla', 'sugar', 'chocolate', 'candy', 'syrup', 'butterscotch', 'maple', 'fudge'],
    'spicy': ['spice', 'spicy', 'pepper', 'peppery', 'cinnamon', 'nutmeg', 'ginger', 'clove', 'cloves', 'chili', 'anise', 'licorice'],
    'maritime': ['salt', 'salty', 'brine', 'seaweed', 'iodine', 'fish', 'maritime', 'sea', 'kipper', 'coastal', 'coastal-fresh']
}

def sha256_file(fp):
    h = hashlib.sha256()
    with open(fp, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest().upper()

def pct(a, b):
    return round(a/b*100, 1) if b else 0.0

def is_zero_vector(prof):
    if not prof:
        return True
    return all(prof.get(ax, 0.0) == 0.0 for ax in ['smoky', 'peaty', 'sherry', 'fruity', 'sweet', 'spicy', 'maritime'])

def calculate_flavor(text):
    text_lower = (text or "").lower()
    scores = {}
    evidence = {}
    
    for axis, keywords in AXES_KEYWORDS.items():
        matched_words = []
        for kw in keywords:
            matches = len(re.findall(rf'\b{re.escape(kw)}\b', text_lower))
            if matches > 0:
                matched_words.extend([kw] * matches)
        
        # min(1.0, hits * 0.25)
        scores[axis] = min(1.0, round(len(matched_words) * 0.25, 2))
        evidence[axis] = sorted(list(set(matched_words)))
        
    return scores, evidence

def main():
    print("="*65)
    print("P44 LEGACY FLAVOR BACKFILL DRY-RUN")
    print("="*65)

    db_hash = sha256_file(PROD_DB)
    print(f"Pre-flight DB Hash: {db_hash}")
    assert db_hash == PRE_HASH, f"ABORT: DB hash mismatch! {db_hash}"

    conn = sqlite3.connect(PROD_DB)
    cursor = conn.cursor()

    cursor.execute("PRAGMA integrity_check")
    integrity = cursor.fetchone()[0]
    print(f"integrity_check: {integrity.upper()}")
    assert integrity == "ok", "Database corrupted!"

    try:
        cursor.execute("PRAGMA foreign_key_check")
        fk_check = cursor.fetchall()
        fk_status = "PASS" if not fk_check else f"FAIL ({len(fk_check)} violations)"
    except sqlite3.OperationalError as e:
        fk_status = f"WARNING ({e})"
    print(f"foreign_key_check: {fk_status}")

    # Fetch legacy whiskies
    cursor.execute("SELECT whisky_id, name FROM whiskies WHERE data_confidence IS NOT 'staged_import'")
    legacy_whiskies = cursor.fetchall()
    legacy_wids = {w[0]: w[1] for w in legacy_whiskies}

    # Fetch legacy tasting notes
    cursor.execute("""
        SELECT whisky_id, nose_notes, palate_notes, finish_notes, notes_for_review 
        FROM tasting_notes 
        WHERE source_system IS NOT 'Whisky Advocate'
    """)
    legacy_tn_rows = cursor.fetchall()
    legacy_tns = {}
    for r in legacy_tn_rows:
        wid = r[0]
        full_text = " ".join(filter(None, [r[1], r[2], r[3], r[4]]))
        legacy_tns[wid] = full_text

    # Fetch legacy flavor profiles
    cursor.execute("SELECT whisky_id, flavor_profile, flavor_source FROM flavor_profiles WHERE flavor_source IS NOT 'Whisky Advocate'")
    legacy_fp_rows = cursor.fetchall()
    
    # Store profiles per whisky_id
    legacy_fps = {}
    for wid, fp_json, src in legacy_fp_rows:
        try:
            prof = json.loads(fp_json)
        except:
            prof = {}
        # Keep track of profiles
        if wid not in legacy_fps:
            legacy_fps[wid] = []
        legacy_fps[wid].append((prof, src))

    # Analyze backfill potential
    planned_inserts = []
    planned_updates = []
    skipped_nonzero = []
    skipped_no_tn = []
    skipped_zero_still_zero = []
    
    for wid, name in legacy_wids.items():
        # Check if has tasting note
        tn_text = legacy_tns.get(wid)
        if not tn_text:
            skipped_no_tn.append((wid, name))
            continue
            
        # Calculate new profile
        scores, evidence = calculate_flavor(tn_text)
        is_new_zero = is_zero_vector(scores)
        
        # Check if has existing profiles
        existing = legacy_fps.get(wid)
        
        if not existing:
            # Candidate for INSERT
            if not is_new_zero:
                planned_inserts.append((wid, name, scores, evidence, tn_text))
            else:
                skipped_zero_still_zero.append((wid, name, "no existing profile, new profile is zero"))
        else:
            # Check if all existing are zero-vector
            all_zero = True
            for prof, src in existing:
                if not is_zero_vector(prof):
                    all_zero = False
                    break
                    
            if all_zero:
                # Candidate for UPDATE
                if not is_new_zero:
                    planned_updates.append((wid, name, scores, evidence, tn_text))
                else:
                    skipped_zero_still_zero.append((wid, name, "existing profile is zero, new profile is also zero"))
            else:
                # Keep as-is (non-zero exists)
                skipped_nonzero.append((wid, name))

    print(f"Total legacy whiskies: {len(legacy_wids)}")
    print(f"Candidates for INSERT: {len(planned_inserts)}")
    print(f"Candidates for UPDATE: {len(planned_updates)}")
    print(f"Skipped (Tasting note has non-zero profile): {len(skipped_nonzero)}")
    print(f"Skipped (No tasting note): {len(skipped_no_tn)}")
    print(f"Skipped (Tasting note yields zero-vector): {len(skipped_zero_still_zero)}")

    # Predict non-zero coverage
    total_legacy_profiles = len(legacy_wids)
    # Profiles with non-zero vectors before:
    nonzero_before = 0
    for wid, plist in legacy_fps.items():
        if not all(is_zero_vector(p[0]) for p in plist):
            nonzero_before += 1
            
    nonzero_after = nonzero_before + len(planned_inserts) + len(planned_updates)
    
    cov_before = pct(nonzero_before, len(legacy_wids))
    cov_after = pct(nonzero_after, len(legacy_wids))

    print(f"Legacy non-zero profiles before: {nonzero_before} ({cov_before}%)")
    print(f"Legacy non-zero profiles after: {nonzero_after} ({cov_after}%)")

    # Generate Dry-run Report
    dry_run_md = f"""# P44 Legacy Flavor Backfill Dry-Run Report

**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Pre-backfill production.db hash:** `{db_hash}`

---

## 1. Backfill Statistics
- **Total Legacy Whiskies:** {len(legacy_wids)}
- **Legacy Whiskies with Tasting Notes:** {len(legacy_tns)}
- **Legacy Whiskies without Tasting Notes:** {len(skipped_no_tn)}
- **Planned INSERT Candidates (No existing profile):** {len(planned_inserts)}
- **Planned UPDATE Candidates (Zero-vector profile exists):** {len(planned_updates)}
- **Skipped (Already contains non-zero profile):** {len(skipped_nonzero)}
- **Skipped (New calculation still zero-vector):** {len(skipped_zero_still_zero)}

---

## 2. Predicted Coverage Impact
- **Non-Zero Legacy Profiles Before:** {nonzero_before} ({cov_before}%)
- **Non-Zero Legacy Profiles After:** {nonzero_after} ({cov_after}%)
- **Net Coverage Increase:** +{round(cov_after - cov_before, 2)}%
- **Remaining Zero-Vector Legacy Profiles:** {len(legacy_fps) - nonzero_after}

---

## 3. 20 Example Backfill Candidates
| Whisky ID | Expression Name | Type | smoky | peaty | sherry | fruity | sweet | spicy | maritime | Evidence Keywords |
|-----------|-----------------|------|-------|-------|--------|--------|-------|-------|----------|-------------------|
"""
    examples = (planned_inserts + planned_updates)[:20]
    for wid, name, scores, evidence, tn in examples:
        ctype = "INSERT" if any(wid == x[0] for x in planned_inserts) else "UPDATE"
        all_ev = []
        for axis, terms in evidence.items():
            if terms:
                all_ev.append(f"{axis}: {', '.join(terms)}")
        ev_str = " | ".join(all_ev)
        
        dry_run_md += f"| {wid} | {name[:30]} | {ctype} | {scores['smoky']:.2f} | {scores['peaty']:.2f} | {scores['sherry']:.2f} | {scores['fruity']:.2f} | {scores['sweet']:.2f} | {scores['spicy']:.2f} | {scores['maritime']:.2f} | {ev_str} |\n"

    with open(OUT_DRY_RUN, 'w', encoding='utf-8') as f:
        f.write(dry_run_md)
    print(f"Dry-run report successfully written to {OUT_DRY_RUN}")

    conn.close()

if __name__ == "__main__":
    main()
