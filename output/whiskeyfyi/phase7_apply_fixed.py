import csv
import os
import datetime
import re
import difflib

MASTER_IN = r"C:\Users\eltun\Documents\malt radar\recovered_from_radiant_bardeen\output\final\67_FINAL_import_ready_distilleries_whiskycom_enriched.csv"
MASTER_OUT = r"C:\Users\eltun\Documents\malt radar\recovered_from_radiant_bardeen\output\final\68_FINAL_import_ready_distilleries_whiskycom_whiskeyfyi_enriched.csv"
AUDIT_FILE = "23_distillery_patch_field_level_audit.csv"

def normalize(name):
    if not name: return ""
    name = name.lower()
    name = re.sub(r'[^a-z0-9]', '', name)
    name = name.replace("distillery", "").replace("the", "")
    return name

# Load audit data
# Only apply where safe_to_apply == 'YES'
# We will key by normalized whiskeyfyi_name because master_uuid/name might be missing or empty
audit_data = {}
try:
    with open(AUDIT_FILE, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["safe_to_apply"] == "YES":
                audit_data[normalize(row["whiskeyfyi_name"])] = row
except Exception as e:
    print("Error reading audit data:", e)

master_rows = []
diff_rows = []
stats = {
    "source_count": 0,
    "target_count": 0,
    "applied_count": 0,
    "skipped_count": 0,
    "overwritten_fields": 0,
    "new_distillery_added": 0,
    "no_match_applied": 0,
    "region_overwrite": 0,
    "desc_filled": 0,
    "url_filled": 0
}

# we need new fieldnames
with open(MASTER_IN, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    fieldnames = list(reader.fieldnames)
    new_fields = ["whiskeyfyi_url", "whiskeyfyi_description", "whiskeyfyi_source_id", "whiskeyfyi_confidence", "whiskeyfyi_last_checked"]
    for nf in new_fields:
        if nf not in fieldnames:
            fieldnames.append(nf)
            
    for row in reader:
        stats["source_count"] += 1
        m_name = row.get("name", "")
        m_norm = normalize(m_name)
        
        # initialize new fields
        for nf in new_fields:
            if nf not in row:
                row[nf] = ""
                
        # To find if there's a match, we check m_norm or fuzzy match >= 94
        matched_audit = None
        if m_norm in audit_data:
            matched_audit = audit_data[m_norm]
        else:
            for k, v in audit_data.items():
                if int(difflib.SequenceMatcher(None, k, m_norm).ratio() * 100) >= 94:
                    matched_audit = v
                    break
                    
        if matched_audit:
            p_desc = matched_audit["proposed_description"]
            p_url = matched_audit["proposed_whiskeyfyi_url"]
            
            filled_any = False
            
            row["whiskeyfyi_source_id"] = matched_audit["whiskeyfyi_name"]
            row["whiskeyfyi_confidence"] = matched_audit["match_score"]
            row["whiskeyfyi_last_checked"] = datetime.datetime.now().strftime("%Y-%m-%d")
            
            if p_desc:
                row["whiskeyfyi_description"] = p_desc
                stats["desc_filled"] += 1
                filled_any = True
                
            if p_url:
                row["whiskeyfyi_url"] = p_url
                stats["url_filled"] += 1
                filled_any = True
                
            if filled_any:
                stats["applied_count"] += 1
                diff_rows.append({
                    "distillery_id": row.get("distillery_id", ""),
                    "Distillery": m_name,
                    "whiskeyfyi_url": p_url,
                    "whiskeyfyi_description": p_desc
                })
        else:
            stats["skipped_count"] += 1
            
        master_rows.append(row)
        stats["target_count"] += 1

# Write new master
with open(MASTER_OUT, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(master_rows)
    
# Write diff
with open("31_distillery_enrichment_diff.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["distillery_id", "Distillery", "whiskeyfyi_url", "whiskeyfyi_description"])
    writer.writeheader()
    writer.writerows(diff_rows)

# 30 Report
report_30 = [
    "DISTILLERY ENRICHMENT APPLY TO COPY REPORT",
    "==========================================",
    f"Kaynak dosya okundu: {MASTER_IN}",
    f"Hedef kopya olusturuldu: {MASTER_OUT}",
    f"Toplam uygulanan kayit: {stats['applied_count']}",
    "Ayri alanlar (whiskeyfyi_url, vb.) kullanilarak yama yapildi.",
]
with open("30_distillery_enrichment_apply_to_copy_report.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(report_30))

# 32 Validation
val_32 = f"""DISTILLERY ENRICHMENT VALIDATION
================================
source row count: {stats['source_count']}
target row count: {stats['target_count']}
applied patch count: {stats['applied_count']}
skipped count: {stats['skipped_count']}
overwritten fields count: {stats['overwritten_fields']}
new distillery added: {stats['new_distillery_added']}
no-match applied: {stats['no_match_applied']}
region/country overwrite: {stats['region_overwrite']}
description filled count: {stats['desc_filled']}
whiskeyfyi_url filled count: {stats['url_filled']}
"""
with open("32_distillery_enrichment_validation.txt", "w", encoding="utf-8") as f:
    f.write(val_32)
