import sqlite3
import json
import os

DB_PATH = r"C:\Users\eltun\Documents\malt radar CLEAN\output\import\production.db"

def run_audit():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Get active production lists
    c.execute("SELECT whisky_id, name FROM whiskies")
    whiskies_prod = {r[0]: r[1] for r in c.fetchall()}

    c.execute("SELECT whisky_id FROM flavor_profiles")
    fp_prod = {r[0] for r in c.fetchall()}

    c.execute("SELECT rowid, whisky_id, nose_notes, palate_notes, finish_notes FROM tasting_notes")
    tn_prod = c.fetchall()

    print("=== OLLAMA STAGING SNAPSHOT AUDIT ===")
    print(f"Production Whiskies: {len(whiskies_prod)}")
    print(f"Production Flavor Profiles: {len(fp_prod)}")
    print(f"Production Tasting Notes: {len(tn_prod)}")

    # 1. Audit staging_tasting_notes (470 rows)
    c.execute("SELECT staging_note_id, whisky_id, product_name, source_system, nose, palate FROM staging_tasting_notes")
    stg_notes = c.fetchall()
    
    stg_notes_orphans = []
    stg_notes_duplicates = []
    stg_notes_inconsistent = []
    seen_stg_notes = set()
    
    for row in stg_notes:
        rid, wid, name, src_sys, nose, palate = row
        # Check orphan (if whisky_id is not empty and not in production whiskies)
        if wid and wid.strip() != "" and wid not in whiskies_prod:
            stg_notes_orphans.append((rid, wid, name))
        # Check duplicate
        key = (wid, nose, palate)
        if key in seen_stg_notes:
            stg_notes_duplicates.append((rid, wid, name))
        else:
            seen_stg_notes.add(key)
            
        # Check inconsistency (e.g. empty notes)
        if (not nose or not nose.strip()) and (not palate or not palate.strip()):
            stg_notes_inconsistent.append((rid, wid, "Empty nose and palate notes"))

    # 2. Audit staging_flavor_profile_candidates (650 rows)
    c.execute("SELECT id, whisky_id, whisky_name, flavor_profile, flavor_vector, active_axis_count, overall_confidence FROM staging_flavor_profile_candidates")
    stg_fps = c.fetchall()
    
    stg_fps_orphans = []
    stg_fps_duplicates = []
    stg_fps_inconsistent = []
    seen_stg_fps = set()
    
    for row in stg_fps:
        fid, wid, name, profile_json, vector_json, active_axis, confidence = row
        # Check orphan
        if wid and wid.strip() != "" and wid not in whiskies_prod:
            stg_fps_orphans.append((fid, wid, name))
        # Check duplicate
        if wid in seen_stg_fps:
            stg_fps_duplicates.append((fid, wid, name))
        else:
            seen_stg_fps.add(wid)
            
        # Check inconsistency
        try:
            vector = json.loads(vector_json) if vector_json else {}
            # Out of bounds or invalid values
            invalid_vals = {k: v for k, v in vector.items() if not (0.0 <= float(v) <= 1.0)}
            if invalid_vals:
                stg_fps_inconsistent.append((fid, wid, f"Out of bounds vector values: {invalid_vals}"))
            # Zero vector check
            if all(float(v) == 0.0 for v in vector.values()):
                stg_fps_inconsistent.append((fid, wid, "Zero vector flavor profile"))
        except Exception as e:
            stg_fps_inconsistent.append((fid, wid, f"JSON parse error: {e}"))

    # 3. Audit staging_p6_flavor_profile_candidates (17 rows)
    c.execute("SELECT whisky_id, whisky_name, flavor_vector FROM staging_p6_flavor_profile_candidates")
    stg_p6 = c.fetchall()
    
    stg_p6_orphans = []
    stg_p6_duplicates = []
    stg_p6_inconsistent = []
    seen_stg_p6 = set()
    
    for row in stg_p6:
        wid, name, vector_json = row
        if wid and wid.strip() != "" and wid not in whiskies_prod:
            stg_p6_orphans.append((wid, name))
        if wid in seen_stg_p6:
            stg_p6_duplicates.append((wid, name))
        else:
            seen_stg_p6.add(wid)
            
        try:
            vector = json.loads(vector_json) if vector_json else {}
            if all(float(v) == 0.0 for v in vector.values()):
                stg_p6_inconsistent.append((wid, "Zero vector p6 candidate"))
        except Exception as e:
            stg_p6_inconsistent.append((wid, f"P6 JSON parse error: {e}"))

    print("\n--- AUDIT FINDINGS ---")
    print(f"Staging Tasting Notes: {len(stg_notes)}")
    print(f" - Orphans: {len(stg_notes_orphans)}")
    print(f" - Duplicates: {len(stg_notes_duplicates)}")
    print(f" - Inconsistent (Empty): {len(stg_notes_inconsistent)}")
    
    print(f"Staging FP Candidates: {len(stg_fps)}")
    print(f" - Orphans: {len(stg_fps_orphans)}")
    print(f" - Duplicates: {len(stg_fps_duplicates)}")
    print(f" - Inconsistent (Out of bounds / Zero / Parse): {len(stg_fps_inconsistent)}")
    
    print(f"Staging P6 Candidates: {len(stg_p6)}")
    print(f" - Orphans: {len(stg_p6_orphans)}")
    print(f" - Duplicates: {len(stg_p6_duplicates)}")
    print(f" - Inconsistent (Zero / Parse): {len(stg_p6_inconsistent)}")

    # Details print
    if stg_notes_orphans:
        print("\n[Sample Tasting Notes Orphans]:", stg_notes_orphans[:5])
    if stg_fps_orphans:
        print("\n[Sample FP Candidates Orphans]:", stg_fps_orphans[:5])
    if stg_fps_inconsistent:
        print("\n[Sample FP Candidates Inconsistent]:", stg_fps_inconsistent[:5])

    conn.close()
    
    # Save detailed data for output report
    return {
        "stg_notes_count": len(stg_notes),
        "stg_notes_orphans": stg_notes_orphans,
        "stg_notes_duplicates": stg_notes_duplicates,
        "stg_notes_inconsistent": stg_notes_inconsistent,
        "stg_fps_count": len(stg_fps),
        "stg_fps_orphans": stg_fps_orphans,
        "stg_fps_duplicates": stg_fps_duplicates,
        "stg_fps_inconsistent": stg_fps_inconsistent,
        "stg_p6_count": len(stg_p6),
        "stg_p6_orphans": stg_p6_orphans,
        "stg_p6_duplicates": stg_p6_duplicates,
        "stg_p6_inconsistent": stg_p6_inconsistent
    }

if __name__ == '__main__':
    run_audit()
