import csv
from pathlib import Path

csv_path = Path("data/external/scotchgit/scotchfile.csv")
ts_path = Path("data/external/scotchgit/whiskysList.ts")

print("SCOTCHGIT CSV INSPECTION")
print("========================")
print("File:", csv_path)
print("Size:", csv_path.stat().st_size)

with csv_path.open(encoding="utf-8", errors="ignore", newline="") as f:
    reader = csv.DictReader(f)
    rows = []
    for i, row in enumerate(reader):
        rows.append(row)
        if i >= 9:
            break

print()
print("Columns:")
print(reader.fieldnames)

print()
print("First 10 rows:")
for i, row in enumerate(rows, start=1):
    print()
    print("--- ROW", i, "---")
    for k, v in row.items():
        if v and len(v) > 250:
            v = v[:250] + "..."
        print(f"{k}: {v}")

print()
print("WHISKYS LIST TS INSPECTION")
print("==========================")
print("File:", ts_path)
print("Size:", ts_path.stat().st_size)
print()
print(ts_path.read_text(encoding="utf-8", errors="ignore")[:3000])
