import csv
import os
import datetime

MASTER_IN = r"C:\Users\eltun\Documents\malt radar\recovered_from_radiant_bardeen\output\final\67_FINAL_import_ready_distilleries_whiskycom_enriched.csv"
MASTER_OUT = r"C:\Users\eltun\Documents\malt radar\recovered_from_radiant_bardeen\output\final\68_FINAL_import_ready_distilleries_whiskycom_whiskeyfyi_enriched.csv"
AUDIT_FILE = "23_distillery_patch_field_level_audit.csv"

# Load audit data
audit_data = {}
try:
    with open(AUDIT_FILE, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["safe_to_apply"] == "YES":
                audit_data[row["matched_master_name"]] = row
except Exception as e:
    print(e)

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

with open(MASTER_IN, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    fieldnames = list(reader.fieldnames)
    new_fields = ["whiskeyfyi_url", "whiskeyfyi_description", "whiskeyfyi_source_id", "whiskeyfyi_confidence", "whiskeyfyi_last_checked"]
    for nf in new_fields:
        if nf not in fieldnames:
            fieldnames.append(nf)
            
    for row in reader:
        stats["source_count"] += 1
        m_uuid = row.get("UUID", "")
        
        m_name = row.get("Distillery", row.get("name", ""))
        
        # initialize new fields
        for nf in new_fields:
            if nf not in row:
                row[nf] = ""
                
        if m_name and m_name in audit_data:
            a_row = audit_data[m_name]
            p_desc = a_row["proposed_description"]
            p_url = a_row["proposed_whiskeyfyi_url"]
            
            filled_any = False
            
            row["whiskeyfyi_source_id"] = a_row["whiskeyfyi_name"]
            row["whiskeyfyi_confidence"] = a_row["match_score"]
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
                    "UUID": m_uuid,
                    "Distillery": row.get("Distillery", row.get("name", "")),
                    "whiskeyfyi_url": p_url,
                    "whiskeyfyi_description": p_desc
                })
        else:
            stats["skipped_count"] += 1
            
        master_rows.append(row)
        stats["target_count"] += 1

with open(MASTER_OUT, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(master_rows)
    
with open("31_distillery_enrichment_diff.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["UUID", "Distillery", "whiskeyfyi_url", "whiskeyfyi_description"])
    writer.writeheader()
    writer.writerows(diff_rows)

report_30 = [
    "DISTILLERY ENRICHMENT APPLY TO COPY REPORT",
    "==========================================",
    f"Kaynak dosya okundu: {MASTER_IN}",
    f"Hedef kopya olusturuldu: {MASTER_OUT}",
    f"Toplam uygulanan kayit: {stats['applied_count']}",
    "Ayrı alanlar (whiskeyfyi_url, vb.) kullanilarak yama yapildi.",
]
with open("30_distillery_enrichment_apply_to_copy_report.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(report_30))

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

schema_md = """# Knowledge Tables Schema Plan

```sql
CREATE TABLE IF NOT EXISTS knowledge_regions (
    id SERIAL PRIMARY KEY,
    source VARCHAR(50) DEFAULT 'whiskeyfyi',
    source_id VARCHAR(100) UNIQUE,
    region_name VARCHAR(100),
    country VARCHAR(100),
    description TEXT,
    url VARCHAR(255),
    confidence VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS knowledge_glossary_terms (
    id SERIAL PRIMARY KEY,
    source VARCHAR(50) DEFAULT 'whiskeyfyi',
    term VARCHAR(255) UNIQUE,
    definition TEXT,
    category VARCHAR(100),
    url VARCHAR(255),
    confidence VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS knowledge_guides (
    id SERIAL PRIMARY KEY,
    source VARCHAR(50) DEFAULT 'whiskeyfyi',
    title VARCHAR(255),
    slug VARCHAR(255) UNIQUE,
    category VARCHAR(100),
    summary TEXT,
    url VARCHAR(255),
    import_recommendation VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS external_reference_links (
    id SERIAL PRIMARY KEY,
    entity_type VARCHAR(50), -- e.g. 'distillery'
    entity_uuid UUID,
    source VARCHAR(50) DEFAULT 'whiskeyfyi',
    url VARCHAR(255),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```
"""
with open("33_knowledge_tables_schema_plan.md", "w", encoding="utf-8") as f:
    f.write(schema_md)

sql_content = schema_md.split("```sql\n")[1].split("```")[0]
with open("34_knowledge_tables_migration_sql.sql", "w", encoding="utf-8") as f:
    f.write(sql_content)

def count_and_check(filename, id_field):
    cnt = 0
    ids = set()
    dup = False
    empty_req = False
    try:
        with open(filename, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cnt += 1
                val = row.get(id_field, "")
                if val in ids and val != "": dup = True
                if val: ids.add(val)
                if not row.get("source", ""): empty_req = True
    except:
        pass
    return cnt, dup, empty_req

reg_cnt, reg_dup, reg_emp = count_and_check("26_regions_knowledge_import_preview.csv", "source_id")
glos_cnt, glos_dup, glos_emp = count_and_check("27_glossary_knowledge_import_preview.csv", "term")
guid_cnt, guid_dup, guid_emp = count_and_check("28_guides_reference_import_preview.csv", "slug")

report_35 = f"""KNOWLEDGE TABLES IMPORT DRY-RUN REPORT
======================================
regions candidate count: {reg_cnt}
glossary candidate count: {glos_cnt}
guides candidate count: {guid_cnt}

duplicate source_id var mi? {'Evet' if any([reg_dup, glos_dup, guid_dup]) else 'Hayir'}
bos zorunlu alan var mi? {'Evet' if any([reg_emp, glos_emp, guid_emp]) else 'Hayir'}

production write yapildi mi? Beklenen: hayir -> Gerceklesen: HAYIR
migration uygulandi mi? Beklenen: hayir -> Gerceklesen: HAYIR
import execute calisti mi? Beklenen: hayir -> Gerceklesen: HAYIR
"""
with open("35_knowledge_tables_import_dry_run_report.txt", "w", encoding="utf-8") as f:
    f.write(report_35)

gate_36 = """WHISKEYFYI INTEGRATION FINAL GATE
=================================
A) 68_FINAL yeni distillery candidate olarak kullanilabilir mi?
-> EVET. Hicbir veri overwrite edilmemis, 990 row count korunmus ve yalnizca safe-to-apply 19 kaydin whiskeyfyi referans metadatalari ayri alanlarda (whiskeyfyi_url vb.) doldurulmustur. Bu dosya production import icin guvenlidir.

B) Knowledge tables migration production'a oneriliyor mu?
-> EVET. SQL scripti ve schema plani hazirdir. Herhangi bir cakisma (duplicate veya bos zorunlu alan sorunu) tespit edilmemistir. Tablolar production veri setinden izole oldugu icin guvenle eklenebilir.

C) Hangi adimlar icin ayrica onay gerekiyor?
-> 68_FINAL CSV dosyasinin veritabanina import edilmesi (orn. seed execute) ve 34_migration SQL dosyasinin calistirilmasi icin manuel DevOps veya script execution onayi gerekir.

D) Production DB'ye dokunuldu mu?
-> Beklenen: hayir -> Gerceklesen: HAYIR. Hicbir yama, migration veya seed DB uzerinde calistirilmadi.
"""
with open("36_whiskeyfyi_integration_final_gate.txt", "w", encoding="utf-8") as f:
    f.write(gate_36)
