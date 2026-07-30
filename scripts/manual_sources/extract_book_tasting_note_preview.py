import csv
import json
import sqlite3
import re
import difflib
from pathlib import Path
from datetime import datetime
from collections import Counter

ROOT = Path(__file__).resolve().parent.parent.parent
BOOK_DIR = Path(r"C:\Users\eltun\Downloads\kitaplar")
SCAN_CSV = ROOT / "data/manual_sources/books/book_relevance_scan.csv"
DB_PATH = ROOT / "output/import/production.db"

OUT_JSONL = ROOT / "data/manual_sources/books/extracted_jsonl/book_tasting_note_extraction_preview.jsonl"
OUT_CSV = ROOT / "data/manual_sources/books/review_csv/book_tasting_note_extraction_review.csv"
REPORT_MD = ROOT / "output/reports/12p_book_tasting_note_extraction_report.md"
GATE_TXT = ROOT / "output/reports/12p_book_tasting_note_extraction_gate.txt"

OUT_JSONL.parent.mkdir(parents=True, exist_ok=True)
OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
REPORT_MD.parent.mkdir(parents=True, exist_ok=True)

whiskies = []
if DB_PATH.exists():
    try:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='whiskies'")
        if cur.fetchone():
            cur.execute("SELECT id, name, distillery FROM whiskies")
            for row in cur.fetchall():
                whiskies.append({"id": row["id"], "name": row["name"], "distillery": row["distillery"]})
        conn.close()
    except Exception as e:
        pass

def fuzzy_match(name: str):
    if not name or not whiskies:
        return None, None, 0.0
    best_id, best_name, best_score = None, None, 0.0
    low_name = name.lower()
    for w in whiskies:
        w_name = w["name"].lower()
        score = difflib.SequenceMatcher(None, low_name, w_name).ratio()
        if score > best_score:
            best_score = score
            best_id = w["id"]
            best_name = w["name"]
        if score == 1.0:
            break
    return best_id, best_name, best_score

FLAVOR_KEYWORDS = [
    "smoky", "sherry", "fruity", "floral", "spicy", "sweet", "woody",
    "malty", "maritime", "peaty", "vanilla", "nutty", "citrus",
    "dried fruit", "chocolate", "honey", "oak", "cereal"
]

def extract_flavors(text: str) -> list[str]:
    found = set()
    low = text.lower()
    for f in FLAVOR_KEYWORDS:
        if f in low:
            found.add(f.replace(" ", "_"))
    return list(found)

def get_text(path_str):
    p = BOOK_DIR / path_str
    if not p.exists(): return ""
    ext = p.suffix.lower()
    if ext == ".pdf":
        try:
            from pypdf import PdfReader
            # Extract first 150 pages to avoid hanging on massive books
            reader = PdfReader(str(p))
            pages = []
            for i, page in enumerate(reader.pages[:150]):
                try:
                    pages.append(page.extract_text() or "")
                except Exception:
                    pass
            return "\n\n".join(pages)
        except: return ""
    elif ext == ".epub":
        try:
            from ebooklib import epub
            from bs4 import BeautifulSoup
            book = epub.read_epub(str(p))
            chunks = []
            for item in book.get_items():
                if item.get_type() == 9: # ITEM_DOCUMENT
                    try:
                        chunks.append(BeautifulSoup(item.get_content(), "html.parser").get_text(" "))
                    except Exception:
                        pass
            return "\n\n".join(chunks)
        except: return ""
    elif ext in {".txt", ".md", ".csv"}:
        try:
            return p.read_text(encoding="utf-8", errors="ignore")
        except: return ""
    return ""

candidates = []
seen_hashes = set()

if SCAN_CSV.exists():
    with SCAN_CSV.open("r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("value_class") == "HIGH_VALUE":
                file_rel = row["file"]
                sha256 = row["sha256"]
                text = get_text(file_rel)
                
                # Split text into paragraphs
                paragraphs = re.split(r'\n\s*\n', text)
                
                for p in paragraphs:
                    p = p.strip()
                    if not p:
                        continue
                    
                    low_p = p.lower()
                    has_nose = "nose" in low_p or "aroma" in low_p or "burun" in low_p
                    has_palate = "palate" in low_p or "taste" in low_p or "damak" in low_p
                    has_finish = "finish" in low_p or "bitiş" in low_p
                    
                    if (has_nose and has_palate) or "tasting note" in low_p or "tadım" in low_p:
                        snippet = p[:280].replace("\n", " ")
                        
                        extracted_whisky_name = snippet.split("-")[0].split(":")[0].split(",")[0].strip()[:50]
                        if not extracted_whisky_name:
                            extracted_whisky_name = "Unknown"
                            
                        extracted_distillery_name = ""
                        
                        abv_match = re.search(r'(\d{2}(?:\.\d)?)\s*%', p)
                        abv = abv_match.group(1) if abv_match else ""
                        
                        age_match = re.search(r'(\d{1,2})\s*(?:year|yo|-year-old)', low_p)
                        age = age_match.group(1) if age_match else ""
                        
                        flavors = extract_flavors(p)
                        
                        match_id, match_name, match_score = fuzzy_match(extracted_whisky_name)
                        
                        if match_score >= 0.92:
                            import_status = "staging_candidate"
                        elif match_score >= 0.84:
                            import_status = "manual_review"
                        else:
                            import_status = "blocked"
                            
                        block_reason = "Low match score" if import_status == "blocked" else ""
                        
                        cand = {
                            "source_file": file_rel,
                            "source_sha256": sha256,
                            "source_type": "local_book",
                            "extracted_whisky_name": extracted_whisky_name,
                            "extracted_distillery_name": extracted_distillery_name,
                            "candidate_text_snippet": snippet,
                            "nose_text": "",
                            "palate_text": "",
                            "finish_text": "",
                            "flavor_terms": ",".join(flavors),
                            "abv": abv,
                            "age_statement": age,
                            "region": "",
                            "score_or_rating": "",
                            "extraction_confidence": "medium",
                            "match_status": "matched" if import_status != "blocked" else "unmatched",
                            "matched_whisky_id": match_id or "",
                            "matched_whisky_name": match_name or "",
                            "match_score": f"{match_score:.3f}",
                            "import_status": import_status,
                            "block_reason": block_reason
                        }
                        
                        dedup_key = f"{file_rel}_{match_id}_{snippet}"
                        if dedup_key not in seen_hashes:
                            seen_hashes.add(dedup_key)
                            candidates.append(cand)

with OUT_JSONL.open("w", encoding="utf-8") as f:
    for c in candidates:
        f.write(json.dumps(c, ensure_ascii=False) + "\n")

if candidates:
    with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=candidates[0].keys())
        w.writeheader()
        w.writerows(candidates)
else:
    with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=[
            "source_file", "source_sha256", "source_type", "extracted_whisky_name",
            "extracted_distillery_name", "candidate_text_snippet", "nose_text",
            "palate_text", "finish_text", "flavor_terms", "abv", "age_statement",
            "region", "score_or_rating", "extraction_confidence", "match_status",
            "matched_whisky_id", "matched_whisky_name", "match_score",
            "import_status", "block_reason"
        ])
        w.writeheader()

staging_candidate = sum(1 for c in candidates if c["import_status"] == "staging_candidate")
manual_review = sum(1 for c in candidates if c["import_status"] == "manual_review")
blocked = sum(1 for c in candidates if c["import_status"] == "blocked")

gate = "NO-GO"
if len(candidates) > 0:
    if staging_candidate >= 10:
        gate = "GO_FOR_STAGING_REVIEW"
    elif manual_review > 0:
        gate = "WARN_GO_MANUAL_REVIEW"
        
production_gate = "PRODUCTION_IMPORT_NO-GO"

lines = []
lines.append("# 12P Book Tasting Note Extraction Report")
lines.append("")
lines.append(f"- generated_at: {datetime.now().isoformat(timespec='seconds')}")
lines.append(f"- extracted_candidates: {len(candidates)}")
lines.append(f"- staging_candidate: {staging_candidate}")
lines.append(f"- manual_review: {manual_review}")
lines.append(f"- blocked: {blocked}")
lines.append(f"- manual_review_gate: **{gate}**")
lines.append(f"- production_import_gate: **{production_gate}**")
lines.append("")
lines.append("## Output Files")
lines.append(f"- `{OUT_JSONL}`")
lines.append(f"- `{OUT_CSV}`")

REPORT_MD.write_text("\n".join(lines), encoding="utf-8")

GATE_TXT.write_text(
    f"{gate}\n{production_gate}\nCANDIDATES={len(candidates)}\nSTAGING={staging_candidate}\nREVIEW={manual_review}\nBLOCKED={blocked}\n",
    encoding="utf-8"
)
GATE_TXT.write_text(
    "\n"
    "Estimated API Cost: $0.00\n"
    "Actual API Cost: $0.00\n"
    "Local Compute Used: Yes\n"
    "Fully Local Execution: Yes\n",
    encoding="utf-8"
)


print(REPORT_MD)
print(GATE_TXT)
