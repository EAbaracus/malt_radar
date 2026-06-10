import os
import pandas as pd

WORKSPACE = r"C:\Users\eltun\Documents\malt radar"
OUT_DIR = os.path.join(WORKSPACE, "output", "phase3")
os.makedirs(OUT_DIR, exist_ok=True)

sources = {
    'Whisky Edition API': [
        'output/whisky_edition_api/24_tasting_notes_candidate_quality_audit.csv',
        'output/whisky_edition_api/25_manual_review_5_detailed_audit.csv',
        'output/whisky_edition_api/26_new_product_candidates_triage.csv',
        'output/whisky_edition_api/27_new_product_import_strategy.md',
        'output/whisky_edition_api/29_whisky_edition_candidate_closure_report.txt'
    ],
    'Malt List': [
        'output/malt_list/rematch_final_master_fuzzy_v2/final_candidates/06_reconciled_LOW_RISK_historical_menu_price_candidates.csv',
        'output/malt_list/rematch_final_master_fuzzy_v2/final_candidates/07_reconciled_manual_review_price_candidates.csv',
        'output/malt_list/rematch_final_master_fuzzy_v2/final_candidates/08_malt_list_price_candidate_closure_report.txt'
    ],
    'WhiskeyFYI': [
        'output/whiskeyfyi/26_regions_knowledge_import_preview.csv',
        'output/whiskeyfyi/27_glossary_knowledge_import_preview.csv',
        'output/whiskeyfyi/28_guides_reference_import_preview.csv',
        'output/whiskeyfyi/37_whiskeyfyi_candidate_closure_report.txt'
    ],
    'Production baseline': [
        'output/final/60_FINAL_import_ready_whiskies_distillery_patched.csv',
        'output/final/67_FINAL_import_ready_distilleries_whiskycom_enriched.csv',
        'output/import/production.db'
    ]
}

inventory = []

for group, files in sources.items():
    for rel_path in files:
        abs_path = os.path.join(WORKSPACE, os.path.normpath(rel_path))
        exists = os.path.exists(abs_path)
        
        row_count = 'N/A'
        file_size_kb = 0
        
        if exists:
            file_size_kb = round(os.path.getsize(abs_path) / 1024, 2)
            if abs_path.endswith('.csv'):
                try:
                    df = pd.read_csv(abs_path)
                    row_count = len(df)
                except Exception:
                    pass
                    
        inventory.append({
            'source_group': group,
            'file_path': rel_path,
            'file_exists': 'Yes' if exists else 'No',
            'file_size_kb': file_size_kb,
            'row_count': row_count
        })

df_inv = pd.DataFrame(inventory)
df_inv.to_csv(os.path.join(OUT_DIR, "04_candidate_source_inventory.csv"), index=False)
print("Inventory generation complete.")
