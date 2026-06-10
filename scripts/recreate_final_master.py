import os
import pandas as pd

def check_files():
    base_dir = r"C:\Users\eltun\Documents\malt radar"
    
    file_54 = os.path.join(base_dir, "54_FINAL_import_ready_whiskies.csv")
    file_39 = os.path.join(base_dir, "39_corrected_import_ready_whiskies.csv")
    file_60 = os.path.join(base_dir, "output", "final", "60_FINAL_import_ready_whiskies_distillery_patched.csv")
    file_08 = os.path.join(base_dir, "output", "orphan", "bulk", "08_orphan_bulk_high_confidence_patch.csv")
    file_62 = os.path.join(base_dir, "output", "final", "62_distillery_patch_diff.csv")
    file_63 = os.path.join(base_dir, "output", "final", "63_remaining_orphan_whiskies_after_patch.csv")
    
    out_dir = os.path.join(base_dir, "output", "final")
    os.makedirs(out_dir, exist_ok=True)
    
    # Check if 54 exists
    if not os.path.exists(file_54):
        # We don't even have the base file 54. 
        report_path = os.path.join(out_dir, "60_MISSING_PATCH_CANNOT_RECREATE_REPORT.txt")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("ERROR: Base file 54_FINAL_import_ready_whiskies.csv is missing.\n")
            f.write("Cannot proceed with recreation.\n")
        print("Base file 54 missing. Created 60_MISSING_PATCH_CANNOT_RECREATE_REPORT.txt and stopping.")
        return

    # Assuming 54 exists:
    if os.path.exists(file_08):
        print("Found 08 patch. Would apply to 54.")
        # implementation details ...
    elif os.path.exists(file_62):
        print("Found 62 diff. Would apply to 54.")
        # implementation details ...
    else:
        # Patch files are missing.
        df_54 = pd.read_csv(file_54)
        if len(df_54) == 1829:
            report_path = os.path.join(out_dir, "60_MISSING_PATCH_CANNOT_RECREATE_REPORT.txt")
            with open(report_path, "w", encoding="utf-8") as f:
                f.write("ERROR: Base file 54 found with 1829 rows, but patch files (08 or 62) are missing.\n")
                f.write("Cannot recreate 60_FINAL_import_ready_whiskies_distillery_patched.csv.\n")
            print("Patch missing. Created 60_MISSING_PATCH_CANNOT_RECREATE_REPORT.txt and stopping.")
        else:
            print("Base 54 has different row count. Stopping.")
            
if __name__ == "__main__":
    check_files()
