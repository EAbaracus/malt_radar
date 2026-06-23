from pathlib import Path
import json
from collections import Counter, defaultdict

CHUNK_DIR = Path("data/manual_sources/books/chunks")
REPORT_DIR = Path("output/reports")
REPORT_DIR.mkdir(parents=True, exist_ok=True)

rows = []
by_book = Counter()
by_target = Counter()
score_stats = defaultdict(list)

for path in CHUNK_DIR.glob("*_chunks.jsonl"):
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        book = obj.get("book_source", "")
        target = obj.get("target", "")
        score = int(obj.get("quality_score", 0))

        by_book[book] += 1
        by_target[target] += 1
        score_stats[(book, target)].append(score)

for (book, target), scores in sorted(score_stats.items()):
    rows.append({
        "book_source": book,
        "target": target,
        "chunk_count": len(scores),
        "max_quality_score": max(scores),
        "avg_quality_score": round(sum(scores) / len(scores), 2),
    })

report = ["# Book Chunk Quality Preview", ""]
report.append("## By book")
for book, count in by_book.items():
    report.append(f"- {book}: {count}")

report.append("")
report.append("## By target")
for target, count in sorted(by_target.items()):
    report.append(f"- {target}: {count}")

report.append("")
report.append("## Detail")
for r in rows:
    report.append(
        f"- {r['book_source']} | {r['target']} | chunks={r['chunk_count']} | "
        f"max={r['max_quality_score']} | avg={r['avg_quality_score']}"
    )

out = REPORT_DIR / "book_chunk_quality_preview.md"
out.write_text("\n".join(report), encoding="utf-8")
print(f"WROTE {out}")
