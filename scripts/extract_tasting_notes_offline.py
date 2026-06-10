import os
import json
import csv
from pathlib import Path
from run_whisky_edition_api_extraction import OUTPUT_DIR, FINAL_DIR, extract_tasting_note

def run_offline():
    print("Running offline extraction...")
    tasting_notes = []
    api_records = []
    
    # Load list parsed
    with open(OUTPUT_DIR / "10_full_review_list_parsed.csv", "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            api_records.append(row)
            
    # Load details
    with open(OUTPUT_DIR / "11_full_detail_raw.jsonl", "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip(): continue
            detail = json.loads(line)
            note = extract_tasting_note(detail)
            if note["nose"] or note["palate"] or note["finish"]:
                tasting_notes.append(note)
                
    if tasting_notes:
        with open(OUTPUT_DIR / "12_full_tasting_notes_candidates.csv", "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=tasting_notes[0].keys())
            writer.writeheader()
            writer.writerows(tasting_notes)
            
    with open(OUTPUT_DIR / "14_api_fetch_report.txt", "w", encoding="utf-8") as f:
        f.write(f"Total list items parsed: {len(api_records)}\n")
        f.write(f"Total details processed: {len(api_records)}\n")
        f.write(f"Total tasting notes extracted: {len(tasting_notes)}\n")
        
    print(f"Extracted {len(tasting_notes)} tasting notes.")
    
    # Master matching
    from run_whisky_edition_api_extraction import resolve_openapi_path, resolve_master_path, stage5_master_match, stage6_patch_preview
    
    master_path = resolve_master_path()
    openapi_path = resolve_openapi_path()
    
    if master_path:
        matches = stage5_master_match(api_records, master_path)
        stage6_patch_preview(api_records, tasting_notes, matches)
    else:
        print("Master file not found. Skipping Stage 5 and 6.")
        with open(OUTPUT_DIR / "24_master_missing_report.txt", "w", encoding="utf-8") as f:
            f.write("Master missing report\n")
            f.write(f"Searched master path: {FINAL_DIR / '60_FINAL_import_ready_whiskies_distillery_patched.csv'}\n")
            f.write(f"Searched manifest path: {FINAL_DIR / '65_FINAL_IMPORT_FILE_MANIFEST.csv'}\n")
            f.write("Manifest found: No\n")
            f.write("Skipped stages: Stage 5 and Stage 6\n")
            f.write("Required to rerun: Ensure final master CSV is at output/final/60_FINAL_import_ready_whiskies_distillery_patched.csv or specified in manifest.\n")
            
        with open(OUTPUT_DIR / "23_final_report.txt", "w", encoding="utf-8") as f:
            f.write("API extraction completed\n")
            f.write("Master matching skipped\n")
            f.write("Reason: final master file not found\n")
            f.write("Patch preview not generated\n")
            f.write("No master files changed\n")
            if openapi_path:
                f.write(f"OpenAPI path used: {openapi_path}\n")

if __name__ == "__main__":
    run_offline()
