import csv
import json
import sqlite3
import re
from pathlib import Path
from datetime import datetime
from collections import Counter

ROOT = Path(r"C:\Users\eltun\Documents\malt radar")
BOOK_DIR = Path(r"C:\Users\eltun\Downloads\kitaplar")
SCAN_CSV = ROOT / "data/manual_sources/books/book_relevance_scan.csv"
DB_PATH = ROOT / "output/import/production.db"

OUT_JSONL = ROOT / "data/manual_sources/books/extracted_jsonl/book_anchored_tasting_note_rescue_preview.jsonl"
OUT_CSV = ROOT / "data/manual_sources/books/review_csv/book_anchored_tasting_note_rescue_review.csv"
REPORT_MD = ROOT / "output/reports/12q_book_anchored_extraction_rescue_report.md"
GATE_TXT = ROOT / "output/reports/12q_book_anchored_extraction_rescue_gate.txt"

OUT_JSONL.parent.mkdir(parents=True, exist_ok=True)
OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
REPORT_MD.parent.mkdir(parents=True, exist_ok=True)

stats = {
    "scan_csv_path": str(SCAN_CSV),
    "scan_csv_exists": SCAN_CSV.exists(),
    "scan_rows": 0,
    "high_value_rows": 0,
    "high_value_ok_rows": 0,
    "source_files_found": 0,
    "source_files_missing": 0,
    "db_path": str(DB_PATH),
    "db_exists": DB_PATH.exists(),
    "db_whisky_count": 0,
    "db_distillery_count": 0,
    "generated_anchor_count": 0,
    "processed_books": 0,
    "anchor_hits": 0,
    "extracted_candidates": 0,
    "staging_candidate": 0,
    "manual_review": 0,
    "blocked": 0,
}

missing_files_list = []

whiskies = []
if DB_PATH.exists():
    try:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='whiskies'")
        if cur.fetchone():
            cur.execute("SELECT count(*) as cnt FROM whiskies")
            stats["db_whisky_count"] = cur.fetchone()["cnt"]
            
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='distilleries'")
            has_dist = cur.fetchone()
            if has_dist:
                cur.execute("SELECT count(*) as cnt FROM distilleries")
                stats["db_distillery_count"] = cur.fetchone()["cnt"]
                cur.execute("""
                    SELECT w.whisky_id as id, w.name, d.name as distillery 
                    FROM whiskies w
                    LEFT JOIN distilleries d ON w.distillery_id = d.distillery_id
                """)
            else:
                try:
                    cur.execute("SELECT whisky_id as id, name, distillery_id as distillery FROM whiskies")
                except:
                    cur.execute("SELECT whisky_id as id, name, '' as distillery FROM whiskies")
            for row in cur.fetchall():
                whiskies.append({"id": row["id"], "name": row["name"], "distillery": row["distillery"]})
        conn.close()
    except Exception as e:
        print(f"Warning: Could not read DB: {e}")

GENERIC_ANCHORS = {
    "whisky", "whiskey", "scotch", "malt", "single malt", "bourbon", 
    "rye", "highland", "speyside", "islay", "the", "a", "an", "and"
}

FLAVOR_KEYWORDS = [
    "nose", "aroma", "palate", "taste", "finish", "flavour", "flavor",
    "sweet", "smoky", "peaty", "sherry", "fruity", "floral", "spicy",
    "oak", "vanilla", "honey", "citrus", "chocolate", "maritime"
]

def clean_name(name):
    if not name:
        return ""
    name = re.sub(r'\(.*?\)', '', name)
    name = name.replace("single malt", "").replace("scotch whisky", "").replace("whisky", "")
    return re.sub(r'[^\w\s]', '', name).strip().lower()

anchors = []
for w in whiskies:
    c_name = clean_name(w["name"])
    if c_name and c_name not in GENERIC_ANCHORS and len(c_name) > 4:
        anchors.append({
            "id": w["id"],
            "name": w["name"],
            "distillery": w["distillery"],
            "anchor_text": c_name,
            "strategy": "exact_normalized"
        })
    
    dist = clean_name(w["distillery"] or "")
    if dist and dist not in GENERIC_ANCHORS:
        age_match = re.search(r'(\d{1,2})\s*(?:year|yo|-year-old)', w["name"].lower())
        if age_match:
            age = age_match.group(1)
            for v in [f"{dist} {age}", f"{dist} {age} year old", f"{dist} {age}yo"]:
                if v not in GENERIC_ANCHORS:
                    anchors.append({
                        "id": w["id"],
                        "name": w["name"],
                        "distillery": w["distillery"],
                        "anchor_text": v,
                        "strategy": "distillery_age_variant"
                    })

stats["generated_anchor_count"] = len(anchors)

def get_text(path_str):
    p = BOOK_DIR / path_str
    ext = p.suffix.lower()
    if ext == ".pdf":
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(p))
            return "\n".join(page.extract_text() or "" for page in reader.pages[:150])
        except: return ""
    elif ext == ".epub":
        try:
            from ebooklib import epub
            from bs4 import BeautifulSoup
            book = epub.read_epub(str(p))
            chunks = []
            for item in book.get_items():
                if item.get_type() == 9:
                    try:
                        chunks.append(BeautifulSoup(item.get_content(), "html.parser").get_text(" "))
                    except: pass
            return "\n".join(chunks)
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
            stats["scan_rows"] += 1
            value_class = row.get("value_class", "").strip().upper()
            extract_status = row.get("extract_status", "").strip().upper()
            
            if value_class == "HIGH_VALUE":
                stats["high_value_rows"] += 1
                if extract_status == "OK":
                    stats["high_value_ok_rows"] += 1
                    
                    file_rel = row.get("file", "")
                    sha256 = row.get("sha256", "")
                    
                    source_path = BOOK_DIR / file_rel
                    if not source_path.exists():
                        stats["source_files_missing"] += 1
                        missing_files_list.append(file_rel)
                        continue
                        
                    stats["source_files_found"] += 1
                    stats["processed_books"] += 1
                    
                    text = get_text(file_rel)
                    low_text = text.lower()
                    
                    for a in anchors:
                        anchor = a["anchor_text"]
                        idx = low_text.find(anchor)
                        while idx != -1:
                            stats["anchor_hits"] += 1
                            
                            start = max(0, idx - 1200)
                            end = min(len(text), idx + 1200)
                            context = text[start:end]
                            low_ctx = context.lower()
                            
                            confidence = 0.40
                            
                            if "nose" in low_ctx or "aroma" in low_ctx or "palate" in low_ctx or "taste" in low_ctx or "finish" in low_ctx:
                                confidence += 0.20
                            
                            flavor_found = [f for f in FLAVOR_KEYWORDS if f in low_ctx]
                            if len(flavor_found) >= 3:
                                confidence += 0.15
                                
                            abv_match = re.search(r'(\d{2}(?:\.\d)?)\s*%', low_ctx)
                            age_match = re.search(r'(\d{1,2})\s*(?:year|yo|-year-old)', low_ctx)
                            if abv_match or age_match:
                                confidence += 0.10
                                
                            if a["distillery"] and clean_name(a["distillery"]) in low_ctx:
                                confidence += 0.10
                                
                            confidence = min(1.0, confidence)
                            
                            import_status = "blocked"
                            if confidence >= 0.70:
                                import_status = "staging_candidate"
                                stats["staging_candidate"] += 1
                            elif confidence >= 0.45:
                                import_status = "manual_review"
                                stats["manual_review"] += 1
                            else:
                                stats["blocked"] += 1
                                
                            block_reason = "Low confidence" if import_status == "blocked" else ""
                            
                            snippet = context.replace("\n", " ")
                            snippet_start = max(0, 1200 - 140)
                            snippet_end = min(len(snippet), 1200 + 140)
                            final_snippet = snippet[snippet_start:snippet_end]
                            
                            cand = {
                                "source_file": file_rel,
                                "source_sha256": sha256,
                                "source_type": "local_book",
                                "matched_whisky_id": a["id"],
                                "matched_whisky_name": a["name"],
                                "anchor_text": anchor,
                                "anchor_strategy": a["strategy"],
                                "candidate_text_snippet": final_snippet,
                                "nose_text": "",
                                "palate_text": "",
                                "finish_text": "",
                                "flavor_terms": ",".join(flavor_found),
                                "abv": abv_match.group(1) if abv_match else "",
                                "age_statement": age_match.group(1) if age_match else "",
                                "region": "",
                                "extraction_confidence": f"{confidence:.2f}",
                                "import_status": import_status,
                                "block_reason": block_reason
                            }
                            
                            dedup_key = f"{file_rel}_{a['id']}_{final_snippet}"
                            if dedup_key not in seen_hashes:
                                seen_hashes.add(dedup_key)
                                candidates.append(cand)
                                stats["extracted_candidates"] += 1
                                
                            idx = low_text.find(anchor, idx + len(anchor))

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
            "source_file", "source_sha256", "source_type", "matched_whisky_id",
            "matched_whisky_name", "anchor_text", "anchor_strategy", "candidate_text_snippet",
            "nose_text", "palate_text", "finish_text", "flavor_terms", "abv", "age_statement",
            "region", "extraction_confidence", "import_status", "block_reason"
        ])
        w.writeheader()

fail_fast_reason = ""
if stats["high_value_ok_rows"] == 0:
    fail_fast_reason = "FAIL_FAST: No HIGH_VALUE sources with OK extraction status found."
elif stats["db_whisky_count"] == 0:
    fail_fast_reason = "FAIL_FAST: No whiskies found in database (DB schema/kolon okuma hatası)."
elif stats["generated_anchor_count"] == 0:
    fail_fast_reason = "FAIL_FAST: No anchors generated (anchor üretim hatası)."
elif stats["anchor_hits"] == 0:
    fail_fast_reason = "FAIL_FAST: No anchor hits found (kitap metni / normalization / path sorunu)."

gate = "NO-GO"
if len(candidates) > 0:
    if stats["staging_candidate"] >= 10:
        gate = "GO_FOR_STAGING_REVIEW"
    elif stats["manual_review"] >= 10:
        gate = "WARN_GO_MANUAL_REVIEW"
        
production_gate = "PRODUCTION_IMPORT_NO-GO"

lines = []
lines.append("# 12Q Book Anchored Tasting Note Rescue Report")
lines.append("")
lines.append(f"- generated_at: {datetime.now().isoformat(timespec='seconds')}")
if fail_fast_reason:
    lines.append(f"**{fail_fast_reason}**")
lines.append("")
lines.append("## Debug Stats")
for k, v in stats.items():
    lines.append(f"- {k}: {v}")
    
if missing_files_list:
    lines.append("")
    lines.append("## Missing Source Files")
    for f in missing_files_list:
        lines.append(f"- {f}")

lines.append("")
lines.append("## Result Summary")
lines.append(f"- extracted_candidates: {stats['extracted_candidates']}")
lines.append(f"- staging_candidate: {stats['staging_candidate']}")
lines.append(f"- manual_review: {stats['manual_review']}")
lines.append(f"- blocked: {stats['blocked']}")
lines.append(f"- manual_review_gate: **{gate}**")
lines.append(f"- production_import_gate: **{production_gate}**")
lines.append("")
lines.append("## Output Files")
lines.append(f"- `{OUT_JSONL}`")
lines.append(f"- `{OUT_CSV}`")

REPORT_MD.write_text("\n".join(lines), encoding="utf-8")

GATE_TXT.write_text(
    f"{gate}\n{production_gate}\nCANDIDATES={stats['extracted_candidates']}\nSTAGING={stats['staging_candidate']}\nREVIEW={stats['manual_review']}\nBLOCKED={stats['blocked']}\n",
    encoding="utf-8"
)
