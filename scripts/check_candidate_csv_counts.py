import csv
from pathlib import Path

files = list(Path("data/output").glob("*candidate*.csv"))

print("CSV FILES")
for f in files:
    try:
        with open(f, encoding="utf-8", errors="ignore", newline="") as fh:
            row_count = sum(1 for _ in fh) - 1
        print(f"{f}: rows={max(row_count, 0)}")
    except Exception as e:
        print(f"{f}: ERROR {e}")
