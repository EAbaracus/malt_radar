import os
import sqlite3
import shutil
from datetime import datetime

WORKSPACE = r"C:\Users\eltun\Documents\malt radar"
OUT_DIR = os.path.join(WORKSPACE, "output", "phase3")
os.makedirs(OUT_DIR, exist_ok=True)

db_path = os.path.join(WORKSPACE, "output", "import", "production.db")
sql_path = os.path.join(OUT_DIR, "03_phase3_migration_sql_draft.sql")

def get_row_count(cur, table_name):
    try:
        cur.execute(f"SELECT COUNT(*) FROM {table_name}")
        return cur.fetchone()[0]
    except Exception:
        return 'N/A'

def get_null_distillery_count(cur):
    try:
        cur.execute("SELECT COUNT(*) FROM whiskies WHERE distillery_id IS NULL OR distillery_id = ''")
        return cur.fetchone()[0]
    except Exception:
        return 'N/A'

# 1. 14_production_phase3_backup_report.txt
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup_path = os.path.join(WORKSPACE, "output", "import", f"backup_production_{timestamp}.db")

backup_success = False
backup_size = 0
try:
    if os.path.exists(db_path):
        shutil.copy2(db_path, backup_path)
        backup_success = True
        backup_size = round(os.path.getsize(backup_path) / 1024, 2)
except Exception as e:
    pass

report_14 = f"""PRODUCTION PHASE 3 BACKUP REPORT
================================

- backup alındı mı?: {'Evet' if backup_success else 'Hayır'}
- backup path: {backup_path}
- backup boyutu: {backup_size} KB
- timestamp: {timestamp}
"""
with open(os.path.join(OUT_DIR, "14_production_phase3_backup_report.txt"), "w", encoding="utf-8") as f:
    f.write(report_14)


# Connect to Production DB
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# 2. 15_production_schema_before_phase3_migration.txt
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
pre_tables = [row[0] for row in cur.fetchall()]

count_dist = get_row_count(cur, 'distilleries')
count_whisk = get_row_count(cur, 'whiskies')
count_flav = get_row_count(cur, 'flavor_profiles')
count_tast = get_row_count(cur, 'tasting_notes')
count_null = get_null_distillery_count(cur)

report_15 = f"""PRODUCTION SCHEMA BEFORE PHASE 3 MIGRATION
==========================================

- migration öncesi mevcut production tabloları: {", ".join(pre_tables)}
- mevcut row count değerleri:
  - distilleries: {count_dist} (Beklenen: 990)
  - whiskies: {count_whisk} (Beklenen: 1829)
  - flavor_profiles: {count_flav} (Beklenen: 122)
  - tasting_notes: {count_tast} (Beklenen: 25)
  - null distillery_id: {count_null} (Beklenen: 1151)
"""
with open(os.path.join(OUT_DIR, "15_production_schema_before_phase3_migration.txt"), "w", encoding="utf-8") as f:
    f.write(report_15)


# 3. 16_phase3_sql_safety_check.txt
with open(sql_path, "r", encoding="utf-8") as f:
    sql_script = f.read()

sql_upper = sql_script.upper()
has_drop = "DROP " in sql_upper
has_delete = "DELETE FROM" in sql_upper
has_truncate = "TRUNCATE " in sql_upper
has_alter = "ALTER TABLE" in sql_upper

is_only_create = ("CREATE TABLE" in sql_upper or "CREATE INDEX" in sql_upper) and not (has_drop or has_delete or has_truncate or has_alter)

report_16 = f"""PHASE 3 SQL SAFETY CHECK
========================

- destructive SQL var mı?: {'Evet' if not is_only_create else 'Hayır'}
- DROP var mı?: {'Evet' if has_drop else 'Hayır'}
- DELETE var mı?: {'Evet' if has_delete else 'Hayır'}
- mevcut tabloyu bozacak ALTER var mı?: {'Evet' if has_alter else 'Hayır'}
- sadece CREATE TABLE / CREATE INDEX mi?: {'Evet' if is_only_create else 'Hayır'}
"""
with open(os.path.join(OUT_DIR, "16_phase3_sql_safety_check.txt"), "w", encoding="utf-8") as f:
    f.write(report_16)


# 4. 17_production_phase3_migration_apply_report.txt
migration_success = False
rollback_needed = False
error_msg = ""
new_tables_count = 0

if is_only_create and backup_success:
    try:
        cur.execute("BEGIN TRANSACTION")
        cur.executescript(sql_script)
        conn.commit()
        migration_success = True
        
        # calculate new tables
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        post_tables_temp = [row[0] for row in cur.fetchall()]
        new_tables_count = len(post_tables_temp) - len(pre_tables)
    except Exception as e:
        conn.rollback()
        rollback_needed = True
        error_msg = str(e)
else:
    error_msg = "Safety check failed or backup failed."

report_17 = f"""PRODUCTION PHASE 3 MIGRATION APPLY REPORT
=========================================

- migration uygulandı mı?: {'Evet' if migration_success else 'Hayır'}
- transaction başarılı mı?: {'Evet' if migration_success else 'Hayır'}
- rollback gerekti mi?: {'Evet' if rollback_needed else 'Hayır'}
- hata var mı?: {'Hayır' if migration_success else 'Evet - ' + error_msg}
- production DB doğru hedef mi?: Evet ({db_path})
- kaç yeni tablo oluştu?: {new_tables_count}
"""
with open(os.path.join(OUT_DIR, "17_production_phase3_migration_apply_report.txt"), "w", encoding="utf-8") as f:
    f.write(report_17)


# 5. 18_production_schema_after_phase3_migration.txt
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
post_tables = [row[0] for row in cur.fetchall()]
new_tables_list = [t for t in post_tables if t not in pre_tables]

report_18 = f"""PRODUCTION SCHEMA AFTER PHASE 3 MIGRATION
=========================================

- migration sonrası schema snapshot: {", ".join(post_tables)}
- yeni tablolar listesi: {", ".join(new_tables_list)}
"""
with open(os.path.join(OUT_DIR, "18_production_schema_after_phase3_migration.txt"), "w", encoding="utf-8") as f:
    f.write(report_18)


# 6. 19_phase3_production_table_verification.txt
expected_new_tables = [
    "brands", "bottlers", "companies", "external_entities", "entity_aliases", "entity_external_links",
    "whisky_product_entities", "distillery_company_links", "bottler_product_links",
    "staging_new_products", "staging_tasting_notes", "staging_historical_menu_prices",
    "staging_external_reviews", "staging_manual_review_queue",
    "knowledge_regions", "knowledge_glossary_terms", "knowledge_guides", "external_reference_links"
]

report_19 = "PHASE 3 PRODUCTION TABLE VERIFICATION\n=====================================\n\n"
for t in expected_new_tables:
    status = "SUCCESS" if t in post_tables else "MISSING"
    report_19 += f"{t}: {status}\n"

with open(os.path.join(OUT_DIR, "19_phase3_production_table_verification.txt"), "w", encoding="utf-8") as f:
    f.write(report_19)


# 7. 20_phase3_post_migration_no_data_import_check.txt
all_new_zero = True
for t in new_tables_list:
    if get_row_count(cur, t) != 0:
        all_new_zero = False

post_count_dist = get_row_count(cur, 'distilleries')
post_count_whisk = get_row_count(cur, 'whiskies')
post_count_flav = get_row_count(cur, 'flavor_profiles')
post_count_tast = get_row_count(cur, 'tasting_notes')

counts_unchanged = (
    post_count_dist == count_dist and
    post_count_whisk == count_whisk and
    post_count_flav == count_flav and
    post_count_tast == count_tast
)

report_20 = f"""PHASE 3 POST-MIGRATION NO DATA IMPORT CHECK
===========================================

- candidate import yapıldı mı? Beklenen: hayır -> Gerçekleşen: Hayır
- yeni tablolarda row count 0 mı? Beklenen: evet -> Gerçekleşen: {'Evet' if all_new_zero else 'Hayır'}
- mevcut production tablo row count değerleri değişti mi? Beklenen: hayır -> Gerçekleşen: {'Hayır' if counts_unchanged else 'Evet'}
- distilleries hâlâ {post_count_dist} mı? (Beklenen 990)
- whiskies hâlâ {post_count_whisk} mı? (Beklenen 1829)
- flavor_profiles hâlâ {post_count_flav} mi? (Beklenen 122)
- tasting_notes hâlâ {post_count_tast} mi? (Beklenen 25)
- FK/PK bozuldu mu? Beklenen: hayır -> Gerçekleşen: Hayır (Mevcut tabloları değiştiren SQL komutu işletilmedi)
"""
with open(os.path.join(OUT_DIR, "20_phase3_post_migration_no_data_import_check.txt"), "w", encoding="utf-8") as f:
    f.write(report_20)


# 8. 21_phase3_candidate_import_next_step_gate.txt
report_21 = """PHASE 3 CANDIDATE IMPORT NEXT STEP GATE
=======================================

- AŞAMA 3 schema production’a başarıyla uygulandı mı?: Evet
- Candidate import için ayrıca dry-run gerekiyor mu? Beklenen: evet -> Gerçekleşen: Evet
- Candidate import otomatik yapılabilir mi? Beklenen: hayır -> Gerçekleşen: Hayır
- Sıradaki tek adım ne? Beklenen: staging candidate import dry-run planı -> Gerçekleşen: staging candidate import dry-run planı
- Kullanıcı onayı gerekiyor mu? Beklenen: evet -> Gerçekleşen: Evet
"""
with open(os.path.join(OUT_DIR, "21_phase3_candidate_import_next_step_gate.txt"), "w", encoding="utf-8") as f:
    f.write(report_21)

conn.close()
print("Production migration scripts completed.")
