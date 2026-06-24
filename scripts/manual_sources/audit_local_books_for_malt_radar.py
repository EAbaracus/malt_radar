from pathlib import Path
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime

BOOK_DIR = Path(r"C:\Users\eltun\Downloads\kitaplar")
ROOT = Path(r"C:\Users\eltun\Documents\malt radar")

OUT_DIR = ROOT / "data/manual_sources/books"
REPORT_DIR = ROOT / "output/reports"

OUT_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)

inventory_csv = OUT_DIR / "book_inventory.csv"
scan_csv = OUT_DIR / "book_relevance_scan.csv"
snippets_csv = OUT_DIR / "book_candidate_snippets.csv"
dupes_csv = OUT_DIR / "book_source_duplicates.csv"
report_md = REPORT_DIR / "12o_book_source_audit_report.md"
gate_txt = REPORT_DIR / "12o_book_source_audit_gate.txt"

SUPPORTED = {".pdf", ".txt", ".md", ".csv", ".json", ".jsonl", ".epub", ".docx"}

WHISKY_TERMS = [
    "whisky", "whiskey", "single malt", "scotch", "bourbon", "rye",
    "distillery", "distilleries", "bottler", "independent bottler",
    "cask", "barrel", "sherry", "bourbon cask", "peated", "peat",
    "nose", "aroma", "palate", "taste", "finish", "tasting note",
    "abv", "%", "region", "islay", "speyside", "highland", "lowland",
    "campbeltown", "islands"
]

TR_TERMS = [
    "viski", "damıtımevi", "damıtım", "fıçı", "burun", "damak",
    "bitiş", "tadım", "aroma", "isli", "turba", "şeri"
]

SIGNAL_WEIGHTS = {
    "nose": 5,
    "aroma": 4,
    "palate": 5,
    "finish": 5,
    "tasting note": 7,
    "distillery": 4,
    "single malt": 5,
    "abv": 4,
    "cask": 4,
    "bourbon cask": 5,
    "sherry": 4,
    "peated": 4,
    "viski": 4,
    "tadım": 5,
    "damıtımevi": 4,
    "burun": 5,
    "damak": 5,
    "bitiş": 5,
}

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def read_text_file(path: Path) -> str:
    for enc in ("utf-8", "utf-8-sig", "cp1254", "latin-1"):
        try:
            return path.read_text(encoding=enc, errors="ignore")
        except Exception:
            continue
    return ""

def read_pdf(path: Path) -> str:
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(path))
        pages = []
        for i, page in enumerate(reader.pages[:80]):
            try:
                pages.append(page.extract_text() or "")
            except Exception:
                pass
        return "\n".join(pages)
    except Exception:
        return ""

def read_docx(path: Path) -> str:
    try:
        import docx
        d = docx.Document(str(path))
        return "\n".join(p.text for p in d.paragraphs)
    except Exception:
        return ""

def read_epub(path: Path) -> str:
    try:
        from ebooklib import epub
        from bs4 import BeautifulSoup
        book = epub.read_epub(str(path))
    except Exception:
        return ""

    chunks = []
    for item in book.get_items():
        try:
            body = item.get_content()
            soup = BeautifulSoup(body, "html.parser")
            chunks.append(soup.get_text(" "))
        except Exception:
            pass
    return "\n".join(chunks)

def extract_text(path: Path) -> tuple[str, str]:
    ext = path.suffix.lower()
    if ext in {".txt", ".md", ".csv", ".json", ".jsonl"}:
        txt = read_text_file(path)
    elif ext == ".pdf":
        txt = read_pdf(path)
    elif ext == ".docx":
        txt = read_docx(path)
    elif ext == ".epub":
        txt = read_epub(path)
    else:
        txt = ""

    if not txt.strip():
        return "", "EXTRACTION_FAILED"
    return txt[:400_000], "OK"

def detect_lang(text: str) -> str:
    low = text.lower()
    tr_hits = sum(low.count(t) for t in TR_TERMS)
    en_hits = sum(low.count(t) for t in WHISKY_TERMS)
    if tr_hits and en_hits:
        return "mixed"
    if tr_hits:
        return "TR"
    if en_hits:
        return "EN"
    return "unknown"

def score_text(text: str) -> tuple[int, dict]:
    low = text.lower()
    hits = {}
    score = 0
    for term, weight in SIGNAL_WEIGHTS.items():
        count = low.count(term.lower())
        if count:
            hits[term] = count
            score += min(count, 20) * weight
    return score, hits

def classify(score: int, hits: dict) -> str:
    note_terms = {"nose", "aroma", "palate", "finish", "tasting note", "burun", "damak", "bitiş", "tadım"}
    has_note = any(t in hits for t in note_terms)

    if score >= 180 and has_note:
        return "HIGH_VALUE"
    if score >= 80:
        return "MEDIUM_VALUE"
    if score >= 25:
        return "LOW_VALUE"
    return "IRRELEVANT"

def target_for(hits: dict) -> str:
    if any(t in hits for t in ["nose", "aroma", "palate", "finish", "tasting note", "burun", "damak", "bitiş", "tadım"]):
        return "tasting_note_candidate"
    if any(t in hits for t in ["cask", "sherry", "peated", "peat", "isli", "turba"]):
        return "flavor_profile_candidate"
    if any(t in hits for t in ["distillery", "distilleries", "damıtımevi"]):
        return "distillery_knowledge_candidate"
    if any(t in hits for t in ["abv", "region", "single malt"]):
        return "whisky_metadata_candidate"
    if hits:
        return "reference_only"
    return "reject"

def snippets(text: str, terms: list[str], max_n=5):
    out = []
    low = text.lower()
    for term in terms:
        idx = low.find(term.lower())
        if idx >= 0:
            start = max(0, idx - 140)
            end = min(len(text), idx + 260)
            s = re.sub(r"\s+", " ", text[start:end]).strip()
            out.append((term, s[:420]))
        if len(out) >= max_n:
            break
    return out

files = [p for p in BOOK_DIR.rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED]

inventory_rows = []
scan_rows = []
snippet_rows = []

hash_to_files = defaultdict(list)

for path in files:
    try:
        rel = str(path.relative_to(BOOK_DIR))
    except ValueError:
        rel = path.name
    ext = path.suffix.lower()
    size = path.stat().st_size
    h = sha256_file(path)
    hash_to_files[h].append(rel)

    text, status = extract_text(path)

    if status != "OK":
        lang = "unknown"
        score = 0
        hits = {}
        value_class = "EXTRACTION_FAILED"
        target = "reject"
    else:
        lang = detect_lang(text)
        score, hits = score_text(text)
        value_class = classify(score, hits)
        target = target_for(hits)

    inventory_rows.append({
        "file": rel,
        "extension": ext,
        "size_bytes": size,
        "sha256": h,
        "extract_status": status,
        "language": lang,
    })

    scan_rows.append({
        "file": rel,
        "extension": ext,
        "size_bytes": size,
        "sha256": h,
        "extract_status": status,
        "language": lang,
        "score": score,
        "value_class": value_class,
        "target": target,
        "top_hits_json": json.dumps(dict(sorted(hits.items(), key=lambda x: x[1], reverse=True)[:20]), ensure_ascii=False),
    })

    if status == "OK":
        for term, snip in snippets(text, list(SIGNAL_WEIGHTS.keys())):
            snippet_rows.append({
                "file": rel,
                "term": term,
                "snippet": snip,
            })

with inventory_csv.open("w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=inventory_rows[0].keys() if inventory_rows else ["file"])
    w.writeheader()
    w.writerows(inventory_rows)

with scan_csv.open("w", newline="", encoding="utf-8-sig") as f:
    fields = ["file", "extension", "size_bytes", "sha256", "extract_status", "language", "score", "value_class", "target", "top_hits_json"]
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(scan_rows)

with snippets_csv.open("w", newline="", encoding="utf-8-sig") as f:
    fields = ["file", "term", "snippet"]
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(snippet_rows)

dupe_rows = []
for h, paths in hash_to_files.items():
    if len(paths) > 1:
        for p in paths:
            dupe_rows.append({"sha256": h, "file": p, "duplicate_group_size": len(paths)})

with dupes_csv.open("w", newline="", encoding="utf-8-sig") as f:
    fields = ["sha256", "file", "duplicate_group_size"]
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(dupe_rows)

class_counts = Counter(r["value_class"] for r in scan_rows)
lang_counts = Counter(r["language"] for r in scan_rows)
ext_counts = Counter(r["extension"] for r in scan_rows)
target_counts = Counter(r["target"] for r in scan_rows)

high = [r for r in scan_rows if r["value_class"] == "HIGH_VALUE"]
medium = [r for r in scan_rows if r["value_class"] == "MEDIUM_VALUE"]
failed = [r for r in scan_rows if r["value_class"] == "EXTRACTION_FAILED"]

gate = "GO_FOR_MANUAL_REVIEW" if len(high) >= 1 or len(medium) >= 3 else "NO-GO"
production_gate = "PRODUCTION_IMPORT_NO-GO"

lines = []
lines.append("# 12O Book Source Audit Report")
lines.append("")
lines.append(f"- generated_at: {datetime.now().isoformat(timespec='seconds')}")
lines.append(f"- source_dir: `{BOOK_DIR}`")
lines.append(f"- total_files: {len(files)}")
lines.append(f"- readable_files: {sum(1 for r in scan_rows if r['extract_status'] == 'OK')}")
lines.append(f"- failed_files: {len(failed)}")
lines.append(f"- duplicate_files: {len(dupe_rows)}")
lines.append(f"- manual_review_gate: **{gate}**")
lines.append(f"- production_import_gate: **{production_gate}**")
lines.append("")
lines.append("## Extension Distribution")
for k, v in ext_counts.most_common():
    lines.append(f"- {k}: {v}")
lines.append("")
lines.append("## Language Distribution")
for k, v in lang_counts.most_common():
    lines.append(f"- {k}: {v}")
lines.append("")
lines.append("## Value Class Distribution")
for k, v in class_counts.most_common():
    lines.append(f"- {k}: {v}")
lines.append("")
lines.append("## Target Distribution")
for k, v in target_counts.most_common():
    lines.append(f"- {k}: {v}")
lines.append("")
lines.append("## HIGH_VALUE Sources")
for r in sorted(high, key=lambda x: int(x["score"]), reverse=True)[:50]:
    lines.append(f"- `{r['file']}` | score={r['score']} | lang={r['language']} | target={r['target']}")
lines.append("")
lines.append("## MEDIUM_VALUE Sources")
for r in sorted(medium, key=lambda x: int(x["score"]), reverse=True)[:80]:
    lines.append(f"- `{r['file']}` | score={r['score']} | lang={r['language']} | target={r['target']}")
lines.append("")
lines.append("## Extraction Failed")
for r in failed[:80]:
    lines.append(f"- `{r['file']}`")
lines.append("")
lines.append("## Output Files")
lines.append(f"- `{inventory_csv}`")
lines.append(f"- `{scan_csv}`")
lines.append(f"- `{snippets_csv}`")
lines.append(f"- `{dupes_csv}`")

report_md.write_text("\n".join(lines), encoding="utf-8")

gate_txt.write_text(
    f"{gate}\n{production_gate}\nHIGH_VALUE={len(high)}\nMEDIUM_VALUE={len(medium)}\nFAILED={len(failed)}\n",
    encoding="utf-8"
)

print(report_md)
print(gate_txt)
