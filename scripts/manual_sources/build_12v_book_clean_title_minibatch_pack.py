import sqlite3
import csv
import json
import hashlib
from pathlib import Path
from collections import defaultdict, Counter
import uuid

def get_hash(filepath):
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            h.update(chunk)
    return h.hexdigest().upper()

def main():
    root = Path(__file__).resolve().parent.parent.parent
    db_path = root / "output" / "import" / "production.db"
    
    in_csv = root / "data" / "manual_sources" / "books" / "review_csv" / "12u_clean_book_entry_title_rematch.csv"
    chunks_dir = root / "data" / "manual_sources" / "books" / "chunks"
    
    out_csv = root / "data" / "manual_sources" / "books" / "review_csv" / "12v_book_clean_title_minibatch_review.csv"
    out_jsonl = root / "data" / "manual_sources" / "books" / "extracted_jsonl" / "12v_book_clean_title_minibatch_input.jsonl"
    
    report_out = root / "output" / "reports" / "12v_book_clean_title_minibatch_pack_report.md"
    gate_out = root / "output" / "reports" / "12v_book_clean_title_minibatch_pack_gate.txt"
    
    Path(out_jsonl).parent.mkdir(parents=True, exist_ok=True)
    
    hash_before = get_hash(db_path)
    
    candidates = []
    input_no_match_count = 0
    with open(in_csv, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("match_status") == "NO_MATCH":
                input_no_match_count += 1
                if row.get("candidate_title_clean"):
                    candidates.append(row)
                    
    dist_groups = defaultdict(list)
    for c in candidates:
        score = 1 if c.get("body_confidence") == "HIGH" else 0
        dist_groups[c.get("possible_distillery", "")].append((score, c))
        
    for k in dist_groups:
        dist_groups[k].sort(key=lambda x: x[0], reverse=True)
        
    selected = []
    keys = list(dist_groups.keys())
    idx = 0
    while len(selected) < 20 and keys:
        k = keys[idx % len(keys)]
        if dist_groups[k]:
            _, cand = dist_groups[k].pop(0)
            selected.append(cand)
        else:
            keys.remove(k)
            idx -= 1 
        idx += 1
        if not keys:
            break
            
    chunks_by_book = defaultdict(list)
    if chunks_dir.exists():
        for jsonl_file in chunks_dir.glob("*.jsonl"):
            book_name = jsonl_file.stem
            with open(jsonl_file, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip(): continue
                    try:
                        data = json.loads(line)
                        text = data.get("chunk_text", "") or data.get("text", "")
                        chunks_by_book[book_name].append(text)
                    except:
                        pass
                        
    batch_id = f"batch_12v_{uuid.uuid4().hex[:6]}"
    
    out_csv_rows = []
    out_jsonl_rows = []
    
    for cand in selected:
        book = cand.get("book_sources", "").split(" | ")[0]
        orig_title = cand.get("candidate_title_original", "")
        
        context_excerpt = ""
        for text in chunks_by_book.get(book, []):
            idx = text.find(orig_title)
            if idx != -1:
                context_excerpt = text[idx:idx+1000]
                break
                
        if not context_excerpt:
            for text in chunks_by_book.get(book, []):
                idx = text.lower().find(orig_title.lower())
                if idx != -1:
                    context_excerpt = text[idx:idx+1000]
                    break
                    
        out_csv_rows.append({
            "batch_id": batch_id,
            "book_source": book,
            "possible_distillery": cand.get("possible_distillery", ""),
            "candidate_title_clean": cand.get("candidate_title_clean", ""),
            "age": cand.get("age", ""),
            "abv": cand.get("abv", ""),
            "source_count": cand.get("source_count", ""),
            "book_sources": cand.get("book_sources", ""),
            "title_confidence": cand.get("title_confidence", ""),
            "body_confidence": cand.get("body_confidence", ""),
            "match_status": cand.get("match_status", ""),
            "nearest_db_name": cand.get("best_match_name", ""),
            "selected_for_extraction": "true",
            "review_status": "pending_extraction",
            "notes": ""
        })
        
        out_jsonl_rows.append({
            "batch_id": batch_id,
            "source_type": "book_entry_boundary_clean_title",
            "book_source": book,
            "possible_distillery": cand.get("possible_distillery", ""),
            "candidate_title_clean": cand.get("candidate_title_clean", ""),
            "age": cand.get("age", ""),
            "abv": cand.get("abv", ""),
            "context_excerpt": context_excerpt,
            "extraction_instruction": "Extract copyright-safe structured tasting summary only. Do not quote long source text. Use null for missing fields."
        })
        
    if out_csv_rows:
        with open(out_csv, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=list(out_csv_rows[0].keys()))
            w.writeheader()
            w.writerows(out_csv_rows)
            
    with open(out_jsonl, "w", encoding="utf-8") as f:
        for jrow in out_jsonl_rows:
            f.write(json.dumps(jrow, ensure_ascii=False) + "\n")
            f.write("""\nEstimated API Cost: $0.00\nActual API Cost: $0.00\nLocal Compute Used: Yes\nFully Local Execution: Yes\n""")

            
    hash_after = get_hash(db_path)
    
    distillery_counts = Counter()
    for row in selected:
        distillery_counts[row["possible_distillery"]] += 1
        
    top_dists = "\n".join([f"- {k}: {v}" for k, v in distillery_counts.most_common(10)])
    
    md = f"""# 12V Book Clean Title Minibatch Pack Report

## Security & DB Status
- DB Modified: `{'true' if hash_before != hash_after else 'false'}`
- Production DB Hash: `{hash_after}`

## Metrics
- **Input NO_MATCH Count:** {input_no_match_count}
- **Selected Count:** {len(selected)}
- **Skipped Count:** {input_no_match_count - len(selected)}

## Top Distilleries in Batch
{top_dists}
"""
    with open(report_out, "w", encoding="utf-8") as f:
        f.write(md)
        
    with open(gate_out, "w", encoding="utf-8") as f:
        f.write("REVIEW")

if __name__ == "__main__":
    main()
