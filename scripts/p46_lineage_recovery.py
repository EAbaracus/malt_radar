import sqlite3, os, re

conn = sqlite3.connect(r'C:\Users\eltun\Documents\malt radar CLEAN\output\import\production.db')
c = conn.cursor()

sources = [
    'Whisky Advocate',
    'whiskeymapper',
    'tasting_note_rule_based',
    'production_data.csv',
    'scotchgit',
    'tasting_note_rule_based_backfill',
]

print("=" * 70)
for src in sources:
    print(f"\n>>> {src} (5 samples)")
    c.execute(
        "SELECT whisky_id, whisky_name, match_method, notes_for_review "
        "FROM flavor_profiles WHERE flavor_source=? LIMIT 5", (src,)
    )
    for row in c.fetchall():
        nfr = (row[3] or "")[:80].replace("\n", " ")
        print(f"  id={row[0]} | name={row[1]} | method={row[2]} | notes={nfr}")

conn.close()

# Search data/output for relevant CSVs
print("\n" + "=" * 70)
print("CSV files in data/output matching backfill/apply/p4/whisky_advocate:")
data_out = r'C:\Users\eltun\Documents\malt radar CLEAN\data\output'
keywords = ['p4', 'backfill', 'apply', 'advocate', 'whiskeymapper', 'harvest', 'import', 'merge', 'execute']
if os.path.exists(data_out):
    for f in os.listdir(data_out):
        fname = f.lower()
        if any(k in fname for k in keywords):
            size = os.path.getsize(os.path.join(data_out, f))
            print(f"  {f}  ({size} bytes)")

# Search output/reports for relevant reports
print("\n" + "=" * 70)
print("Reports matching backfill/apply/p4/advocate keywords:")
rep_dir = r'C:\Users\eltun\Documents\malt radar CLEAN\output\reports'
if os.path.exists(rep_dir):
    for f in os.listdir(rep_dir):
        fname = f.lower()
        if any(k in fname for k in keywords):
            size = os.path.getsize(os.path.join(rep_dir, f))
            print(f"  {f}  ({size} bytes)")

# Search scripts for DB-writing scripts
print("\n" + "=" * 70)
print("DB-writing scripts (apply/execute/backfill/insert/update/merge/import):")
scripts_dir = r'C:\Users\eltun\Documents\malt radar CLEAN\scripts'
scratch_dir = r'C:\Users\eltun\Documents\malt radar CLEAN\scratch'
write_keywords = ['apply', 'execute', 'backfill', 'import', 'merge', 'seeder', 'update', 'insert']

for base_dir in [scripts_dir, scratch_dir]:
    if os.path.exists(base_dir):
        for root, dirs, files in os.walk(base_dir):
            for f in files:
                if not f.endswith('.py'):
                    continue
                fname = f.lower()
                if any(k in fname for k in write_keywords):
                    rel = os.path.relpath(os.path.join(root, f), r'C:\Users\eltun\Documents\malt radar CLEAN')
                    size = os.path.getsize(os.path.join(root, f))
                    print(f"  {rel}  ({size} bytes)")
