import sqlite3
import json
import csv
import re
import hashlib
from pathlib import Path

def get_hash(filepath):
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            h.update(chunk)
    return h.hexdigest().upper()

def parse_chunk(text, book_name):
    candidates = []
    
    # We will split text into logical lines/blocks.
    lines = text.split('\n')
    
    # Identify if chunk is likely a distillery profile or expression
    text_upper = text.upper()
    has_nose = 'NOSE' in text_upper
    has_palate = 'PALATE' in text_upper
    has_finish = 'FINISH' in text_upper
    has_score = 'SCORE' in text_upper
    has_tasting_notes = 'TASTING NOTES' in text_upper
    
    # Try to find ABV
    abv_match = re.search(r'(\d{2,3}(?:\.\d)?)\s*(?:%|vol|abv)', text, re.IGNORECASE)
    abv = abv_match.group(1) if abv_match else None
    
    # Try to find Age
    age_match = re.search(r'\b(\d{1,2})\s*(?:yo|y\.o\.|year|years)\b', text, re.IGNORECASE)
    age_statement = age_match.group(1) if age_match else None
    
    if has_nose or has_palate or has_tasting_notes or abv or age_statement:
        c_type = "whisky_expression"
        
        # Name heuristic: the first non-empty line or the line before 'NOSE'/'AGE'
        candidate_name = "Unknown Expression"
        if lines:
            # Often the expression name is in the first 1-3 lines
            for l in lines[:3]:
                l_clean = l.strip()
                if l_clean and len(l_clean) < 100:
                    candidate_name = l_clean
                    break
        
        confidence = "low"
        if has_nose and has_palate:
            confidence = "high"
        elif abv and (has_nose or has_palate or has_tasting_notes):
            confidence = "medium"
            
        import_status = "needs_manual_review"
        if confidence == "high":
            import_status = "parser_ready"
            
        candidates.append({
            "book_source": book_name,
            "candidate_type": c_type,
            "candidate_name": candidate_name[:100],
            "possible_distillery": None, # Hard to infer without structural context, leave blank or guess from name
            "abv": abv,
            "age_statement": age_statement,
            "has_nose": has_nose,
            "has_palate": has_palate,
            "has_finish": has_finish,
            "has_score": has_score,
            "confidence": confidence,
            "raw_snippet_length": len(text),
            "import_status": import_status
        })
    else:
        # Check if it looks like a distillery profile (long text, no specific tasting notes)
        if len(text) > 500 and not (has_nose or has_palate):
            c_type = "distillery_profile"
            candidate_name = lines[0].strip()[:50] if lines else "Unknown"
            candidates.append({
                "book_source": book_name,
                "candidate_type": c_type,
                "candidate_name": candidate_name,
                "possible_distillery": candidate_name,
                "abv": None,
                "age_statement": None,
                "has_nose": False,
                "has_palate": False,
                "has_finish": False,
                "has_score": False,
                "confidence": "medium",
                "raw_snippet_length": len(text),
                "import_status": "inventory_only"
            })
            
    return candidates

def fuzzy_match(cur, name):
    if not name or name == "Unknown Expression":
        return "no_match"
    
    # Try exact or partial match
    safe_name = name.lower().replace("'", "").replace("%", "")
    cur.execute("SELECT COUNT(*) FROM whiskies WHERE LOWER(name) LIKE ?", (f"%{safe_name[:15]}%",))
    count = cur.fetchone()[0]
    
    if count == 1:
        return "high_match"
    elif count > 1:
        return "review_match"
    else:
        return "no_match"

def main():
    root = Path(__file__).resolve().parent.parent.parent
    chunks_dir = root / "data" / "manual_sources" / "books" / "chunks"
    db_path = root / "output" / "import" / "production.db"
    
    csv_out = root / "data" / "manual_sources" / "books" / "review_csv" / "12o_full_book_inventory.csv"
    csv_out.parent.mkdir(parents=True, exist_ok=True)
    report_out = root / "output" / "reports" / "12o_full_book_inventory_report.md"
    report_out.parent.mkdir(parents=True, exist_ok=True)
    gate_out = root / "output" / "reports" / "12o_full_book_inventory_gate.txt"
    
    hash_before = get_hash(db_path)
    
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    cur = conn.cursor()
    
    all_candidates = []
    
    total_books = 0
    total_candidate_sections = 0
    
    if chunks_dir.exists():
        for f in chunks_dir.glob("*.jsonl"):
            total_books += 1
            book_name = f.stem.replace("_chunks", "")
            
            with open(f, 'r', encoding='utf-8') as jf:
                for idx, line in enumerate(jf):
                    if not line.strip(): continue
                    try:
                        data = json.loads(line)
                        text = data.get("text", "")
                        cands = parse_chunk(text, book_name)
                        for c in cands:
                            c["source_position"] = idx
                            match = fuzzy_match(cur, c["candidate_name"])
                            c["match_status"] = match
                            all_candidates.append(c)
                            total_candidate_sections += 1
                    except Exception as e:
                        print("Error parsing line", e)
                        
    # Aggregation
    distillery_profiles = sum(1 for c in all_candidates if c["candidate_type"] == "distillery_profile")
    whisky_expressions = sum(1 for c in all_candidates if c["candidate_type"] == "whisky_expression")
    high_conf = sum(1 for c in all_candidates if c["confidence"] == "high")
    parser_ready = sum(1 for c in all_candidates if c["import_status"] == "parser_ready")
    
    high_match = sum(1 for c in all_candidates if c.get("match_status") == "high_match")
    review_match = sum(1 for c in all_candidates if c.get("match_status") == "review_match")
    no_match = sum(1 for c in all_candidates if c.get("match_status") == "no_match")
    
    # Write CSV
    headers = ["book_source", "candidate_type", "candidate_name", "possible_distillery", "abv", "age_statement", 
               "has_nose", "has_palate", "has_finish", "has_score", "confidence", "source_position", 
               "raw_snippet_length", "import_status", "match_status"]
               
    with open(csv_out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        w.writerows(all_candidates)
        
    hash_after = get_hash(db_path)
    
    md = f"""# 12O Full Book Inventory Audit

## Security & DB Status
- DB Modified: `{'true' if hash_before != hash_after else 'false'}`
- Production DB Hash: `{hash_after}`

## Books Scanned
- **Total Books:** {total_books}
- **Total Candidate Sections:** {total_candidate_sections}

## Metrics
- **Distillery Profiles Detected:** {distillery_profiles}
- **Whisky Expressions Detected:** {whisky_expressions}
- **High Confidence Expressions:** {high_conf}
- **Parser Ready Candidates:** {parser_ready}

## Production DB Match Attempt (Fuzzy Name)
- **High Match (Exact/Single):** {high_match}
- **Review Match (Multiple):** {review_match}
- **No Match:** {no_match}

## Recommendations
- The heuristic caught {whisky_expressions} potential whiskies across {total_books} books.
- {high_conf} of these are high confidence and can be safely piped to an LLM extraction stage.
"""
    with open(report_out, "w", encoding="utf-8") as f:
        f.write(md)
        f.write("""\nEstimated API Cost: $0.00\nActual API Cost: $0.00\nLocal Compute Used: Yes\nFully Local Execution: Yes\n""")

        
    with open(gate_out, "w", encoding="utf-8") as f:
        f.write("REVIEW")
        
if __name__ == "__main__":
    main()
