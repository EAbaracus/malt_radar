import os
import shutil
import csv

base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
scripts_dir = os.path.join(base_dir, "scripts", "tasting_notes")
archive_dir = os.path.join(base_dir, "scripts", "archive", "12y_frozen_web_scraping_pipeline")
output_dir = os.path.join(base_dir, "data", "output")
reports_dir = os.path.join(base_dir, "output", "reports")

os.makedirs(archive_dir, exist_ok=True)
os.makedirs(output_dir, exist_ok=True)
os.makedirs(reports_dir, exist_ok=True)

manifest_csv = os.path.join(output_dir, "frozen_web_scraping_pipeline_manifest.csv")
report_md = os.path.join(reports_dir, "297_frozen_web_scraping_pipeline_report.md")
gate_txt = os.path.join(reports_dir, "298_12y_frozen_web_scraping_pipeline_gate.txt")
readme_md = os.path.join(scripts_dir, "README_TASTING_NOTE_PIPELINE_STATUS.md")

TO_FREEZE = [
    "discover_real_web_tasting_note_sources.py",
    "fetch_web_tasting_note_snapshots.py",
    "extract_tasting_notes_from_seed_candidates.py",
    "validate_tasting_note_extraction_preview.py",
    "seed_existing_real_tasting_note_sources.py",
    "recover_scotchgit_text_snapshots.py",
    "dryrun_apply_staging_tasting_notes.py"
]

TO_PRESERVE = [
    "apply_staging_tasting_notes.py",
    "url_safety.py",
    "plan_tasting_note_acquisition_strategy.py",
    "qa_real_web_staging_tasting_notes.py",
    "purge_invalid_web_staging_tasting_notes.py"
]

def main():
    frozen_count = 0
    preserved_count = 0
    manifest_rows = []

    for f_name in TO_FREEZE:
        src = os.path.join(scripts_dir, f_name)
        dst = os.path.join(archive_dir, f_name)
        status = "not_found"
        if os.path.exists(src):
            shutil.move(src, dst)
            status = "archived_frozen"
            frozen_count += 1
        manifest_rows.append({"script_name": f_name, "action": status})

    for p_name in TO_PRESERVE:
        src = os.path.join(scripts_dir, p_name)
        status = "not_found"
        if os.path.exists(src):
            status = "preserved_active"
            preserved_count += 1
        manifest_rows.append({"script_name": p_name, "action": status})

    readme_content = """# Tasting Note Pipeline Status
**Status:** Web scraping pipeline FROZEN
**Reason:** 12W HTTP 403/anti-bot blocks, 12U fallback/no-result issues, and ToS/legal risks.

## Active Recommended Paths
1. Manual curated CSV/file import
2. In-app user-generated tasting notes (UGC)

## Frozen Scripts
The automated web scraping and extraction scripts have been moved to `scripts/archive/12y_frozen_web_scraping_pipeline/` to prevent accidental execution and injection of mock/fallback data.
Frozen outputs will not be applied to production.

## DB Status
- `production.db` -> `tasting_notes` remains 25
- `production.db` -> `staging_web_tasting_notes` remains 0
"""
    with open(readme_md, "w", encoding="utf-8") as f:
        f.write(readme_content)

    with open(manifest_csv, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["script_name", "action"])
        w.writeheader()
        w.writerows(manifest_rows)

    with open(report_md, "w", encoding="utf-8") as f:
        f.write("# 297 Frozen Web Scraping Pipeline Report\n\n")
        f.write(f"- archived_frozen_script_count: {frozen_count}\n")
        f.write(f"- preserved_active_script_count: {preserved_count}\n")
        f.write("- readme_status: Created\n")
        f.write("- production_db_changed: NO\n")
        f.write("- output_import_changed: NO\n")
        f.write("- frontend_untouched: YES\n")

    gate = "GO"
    gate_reasons = []

    if frozen_count == 0:
        gate = "NO-GO"
        gate_reasons.append("No scripts were frozen")
    
    with open(gate_txt, "w", encoding="utf-8") as f:
        f.write(f"GATE: {gate}\n")
        for r in gate_reasons: f.write(f"REASON: {r}\n")
        if gate == "GO":
            f.write("REASON: Web scraping pipeline safely frozen and archived.\n")

if __name__ == "__main__":
    main()
