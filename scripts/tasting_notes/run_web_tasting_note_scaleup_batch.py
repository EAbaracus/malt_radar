import os
import shutil
import subprocess
import argparse
import csv

base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
output_dir = os.path.join(base_dir, "data", "output")
reports_dir = os.path.join(base_dir, "output", "reports")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, default=200)
    parser.add_argument('--max-results-per-whisky', type=int, default=5)
    args = parser.parse_args()
    
    print(f"Starting Web Tasting Note Scale-Up Batch (limit={args.limit}, max-results={args.max_results_per_whisky})...")
    
    # Step 1: Discover
    print("\n--- Step 1: Discover ---")
    subprocess.run(["python", "scripts/tasting_notes/discover_real_web_tasting_note_sources.py", "--limit", str(args.limit), "--max-results-per-whisky", str(args.max_results_per_whisky)], cwd=base_dir)
    shutil.copy(os.path.join(output_dir, "web_tasting_note_real_source_candidates.csv"), os.path.join(output_dir, "web_tasting_note_real_source_candidates_scaleup.csv"))
    shutil.copy(os.path.join(output_dir, "web_tasting_note_real_source_manual_review.csv"), os.path.join(output_dir, "web_tasting_note_real_source_manual_review_scaleup.csv"))
    
    # Step 2: Fetch
    print("\n--- Step 2: Fetch ---")
    subprocess.run(["python", "scripts/tasting_notes/fetch_web_tasting_note_snapshots.py", "--input", os.path.join(output_dir, "web_tasting_note_real_source_candidates_scaleup.csv")], cwd=base_dir)
    shutil.copy(os.path.join(output_dir, "web_tasting_note_snapshots_index.csv"), os.path.join(output_dir, "web_tasting_note_snapshots_index_scaleup.csv"))
    
    # Step 3: Extract
    print("\n--- Step 3: Extract ---")
    subprocess.run(["python", "scripts/tasting_notes/extract_web_tasting_notes_from_snapshots.py", "--input", os.path.join(output_dir, "web_tasting_note_real_source_candidates_scaleup.csv"), "--suffix", "_scaleup"], cwd=base_dir)
    
    # Step 4: Refine
    print("\n--- Step 4: Refine ---")
    shutil.copy(os.path.join(output_dir, "web_tasting_note_extraction_manual_review_scaleup.csv"), os.path.join(output_dir, "web_tasting_note_extraction_manual_review.csv"))
    subprocess.run(["python", "scripts/tasting_notes/refine_web_tasting_note_manual_review.py"], cwd=base_dir)
    shutil.copy(os.path.join(output_dir, "web_tasting_note_manual_review_refined.csv"), os.path.join(output_dir, "web_tasting_note_manual_review_refined_scaleup.csv"))
    shutil.copy(os.path.join(output_dir, "web_tasting_note_parser_improvement_candidates.csv"), os.path.join(output_dir, "web_tasting_note_parser_improvement_candidates_scaleup.csv"))
    shutil.copy(os.path.join(output_dir, "web_tasting_note_safe_summary_candidates.csv"), os.path.join(output_dir, "web_tasting_note_safe_summary_candidates_scaleup.csv"))
    shutil.copy(os.path.join(output_dir, "web_tasting_note_wrong_match_rejects.csv"), os.path.join(output_dir, "web_tasting_note_wrong_match_rejects_scaleup.csv"))
    
    # Step 5: Staging Preview
    print("\n--- Step 5: Staging Dry-Run ---")
    shutil.copy(os.path.join(output_dir, "web_tasting_note_extractable_candidates_scaleup.csv"), os.path.join(output_dir, "web_tasting_note_extractable_candidates_v2.csv"))
    subprocess.run(["python", "scripts/tasting_notes/build_web_tasting_note_staging_preview.py"], cwd=base_dir)
    shutil.copy(os.path.join(output_dir, "web_tasting_note_staging_preview.csv"), os.path.join(output_dir, "web_tasting_note_staging_preview_scaleup.csv"))
    shutil.copy(os.path.join(output_dir, "web_flavor_profile_vector_preview.csv"), os.path.join(output_dir, "web_flavor_profile_vector_preview_scaleup.csv"))
    
    # Step 6: Apply Dry-Run
    print("\n--- Step 6: Apply Dry-Run ---")
    subprocess.run(["python", "scripts/tasting_notes/dry_run_apply_web_tasting_notes_to_staging.py"], cwd=base_dir)
    shutil.copy(os.path.join(output_dir, "web_tasting_note_staging_apply_plan.csv"), os.path.join(output_dir, "web_tasting_note_staging_apply_plan_scaleup.csv"))
    shutil.copy(os.path.join(output_dir, "web_tasting_note_staging_apply_blocked.csv"), os.path.join(output_dir, "web_tasting_note_staging_apply_blocked_scaleup.csv"))
    
    # Gather Stats for Reports
    def row_count(filename):
        try:
            with open(os.path.join(output_dir, filename), 'r', encoding='utf-8') as f:
                return sum(1 for _ in f) - 1
        except:
            return 0
            
    discovery_count = row_count("web_tasting_note_real_source_candidates_scaleup.csv")
    snapshot_count = row_count("web_tasting_note_snapshots_index_scaleup.csv")
    extractable_count = row_count("web_tasting_note_extractable_candidates_scaleup.csv")
    staging_count = row_count("web_tasting_note_staging_preview_scaleup.csv")
    apply_plan_count = row_count("web_tasting_note_staging_apply_plan_scaleup.csv")
    
    # Write Reports
    r1 = os.path.join(reports_dir, "233_web_tasting_note_scaleup_discovery_report.md")
    with open(r1, 'w', encoding='utf-8') as f:
        f.write("# Scale-Up Discovery Report\n\n")
        f.write(f"- Real source candidates discovered: {discovery_count}\n")
        
    r2 = os.path.join(reports_dir, "234_web_tasting_note_scaleup_extraction_report.md")
    with open(r2, 'w', encoding='utf-8') as f:
        f.write("# Scale-Up Extraction Report\n\n")
        f.write(f"- Successful snapshots: {snapshot_count}\n")
        f.write(f"- Extractable candidates (Prod Ready): {extractable_count}\n")
        
    r3 = os.path.join(reports_dir, "235_web_tasting_note_scaleup_staging_report.md")
    with open(r3, 'w', encoding='utf-8') as f:
        f.write("# Scale-Up Staging Report\n\n")
        f.write(f"- Staging preview generated: {staging_count}\n")
        f.write(f"- Validated apply plan candidates: {apply_plan_count}\n")
        
    r4 = os.path.join(reports_dir, "236_12i_web_tasting_note_scaleup_gate.txt")
    if apply_plan_count > 0:
        decision = "GO"
        msg = f"Scale-up successful. Generated {apply_plan_count} safe candidates."
    else:
        decision = "NO-GO"
        msg = "Scale-up failed to generate any valid apply plan candidates."
        
    with open(r4, 'w', encoding='utf-8') as f:
        f.write("12I Web Tasting Note Scale-Up Gate\n==================================\n")
        f.write(f"Decision: {decision}\n\n{msg}")

    print("\nScale-Up Batch Complete.")
    print(f"Discovery: {discovery_count}")
    print(f"Extractable: {extractable_count}")
    print(f"Staging Apply Plan: {apply_plan_count}")

if __name__ == "__main__":
    main()
