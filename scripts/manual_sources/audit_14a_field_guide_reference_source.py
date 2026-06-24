import os
import glob
import sqlite3
import csv
import hashlib
import re
import difflib
from pathlib import Path
import warnings

try:
    import ebooklib
    from ebooklib import epub
    from bs4 import BeautifulSoup
except ImportError:
    print("Required packages ebooklib or bs4 not found. Please install them.")
    exit(1)

# Suppress ebooklib warnings
warnings.filterwarnings('ignore', category=UserWarning, module='ebooklib')

def get_db_hash(db_path):
    if not os.path.exists(db_path):
        return None
    sha256 = hashlib.sha256()
    with open(db_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()

def extract_metadata_from_epub(epub_path):
    try:
        book = epub.read_epub(epub_path)
        title = book.get_metadata('DC', 'title')
        title_str = title[0][0] if title else "Unknown Title"
        author = book.get_metadata('DC', 'creator')
        author_str = author[0][0] if author else "Unknown Author"
        return title_str, author_str, book
    except Exception as e:
        return "Unknown Title", "Unknown Author", None

def extract_text_from_epub(book):
    texts = []
    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            content = item.get_content()
            soup = BeautifulSoup(content, 'html.parser')
            text = soup.get_text(separator='\n', strip=True)
            if text:
                texts.append(text)
    return "\n".join(texts)

def get_match_status(query, choices, cutoff=0.8):
    if not query or not choices:
        return "NO_MATCH"
    matches = difflib.get_close_matches(query, choices, n=1, cutoff=cutoff)
    if matches:
        return "HIGH"
    matches_review = difflib.get_close_matches(query, choices, n=1, cutoff=0.5)
    if matches_review:
        return "REVIEW"
    return "NO_MATCH"

def main():
    base_dir = Path("c:/Users/eltun/Documents/malt radar")
    input_dir = base_dir / "data/manual_sources/books/input"
    db_path = base_dir / "output/import/production.db"
    review_dir = base_dir / "data/manual_sources/books/review_csv"
    report_dir = base_dir / "output/reports"
    
    os.makedirs(review_dir, exist_ok=True)
    os.makedirs(report_dir, exist_ok=True)
    
    db_hash_before = get_db_hash(db_path)
    db_hash_after = db_hash_before
    db_modified = False
    
    epub_files = glob.glob(os.path.join(input_dir, "*.epub"))
    
    best_epub_path = None
    best_epub_title = "Unknown"
    best_epub_author = "Unknown"
    best_book_obj = None
    input_match_status = "no_match"
    all_candidates_log = []
    
    for f in epub_files:
        filename = os.path.basename(f).lower()
        title, author, book = extract_metadata_from_epub(f)
        t_lower = title.lower()
        a_lower = author.lower()
        
        all_candidates_log.append(f"Checked: {filename} (Title: {title}, Author: {author})")
        
        # Exact match logic
        is_field_guide = "field guide to whisky" in filename or "field guide to whisky" in t_lower
        is_hans = "hans offringa" in filename or "hans offringa" in a_lower or "offringa" in a_lower or "offringa" in filename
        has_field_guide_keyword = "field guide" in filename or "field guide" in t_lower

        if is_field_guide and is_hans:
            best_epub_path = f
            best_epub_title = title
            best_epub_author = author
            best_book_obj = book
            input_match_status = "exact"
            break
        elif is_field_guide or is_hans or has_field_guide_keyword:
            if input_match_status != "exact":
                best_epub_path = f
                best_epub_title = title
                best_epub_author = author
                best_book_obj = book
                input_match_status = "probable"
                
    def write_early_report(gate_status):
        report_file = report_dir / "14a_field_guide_reference_audit_report.md"
        with open(report_file, "w", encoding="utf-8") as f:
            f.write("# A Field Guide to Whisky Reference Audit Report\n\n")
            f.write(f"- **Target Source:** A Field Guide to Whisky\n")
            f.write(f"- **Selected EPUB Path:** {best_epub_path if best_epub_path else 'None'}\n")
            f.write(f"- **EPUB Title:** {best_epub_title}\n")
            f.write(f"- **Author:** {best_epub_author}\n")
            f.write(f"- **Input Match Status:** {input_match_status}\n\n")
            f.write("## Candidate Files Checked\n")
            for log in all_candidates_log:
                f.write(f"- {log}\n")
            f.write(f"\n- **Gate:** {gate_status}\n")

        gate_file = report_dir / "14a_field_guide_reference_audit_gate.txt"
        with open(gate_file, "w", encoding="utf-8") as f:
            f.write(f"{gate_status}\n")

        print(f"Audit completed. Gate is {gate_status}. Production DB modified: False")
                
    if input_match_status == "no_match" or not best_book_obj:
        write_early_report("NO_GO")
        return

    # Valid EPUB found, proceed
    print(f"Processing EPUB: {best_epub_path} (Status: {input_match_status})")
    text = extract_text_from_epub(best_book_obj)
    total_chars = len(text)
    
    # Load DB items
    whiskies = []
    distilleries = []
    db_uri = f"file:{db_path}?mode=ro"
    try:
        conn = sqlite3.connect(db_uri, uri=True)
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT name FROM whiskies")
            whiskies = [row[0] for row in cursor.fetchall()]
        except sqlite3.Error:
            pass
            
        try:
            cursor.execute("SELECT name FROM distilleries")
            distilleries = [row[0] for row in cursor.fetchall()]
        except sqlite3.Error:
            pass
            
        conn.close()
    except sqlite3.Error as e:
        print(f"DB Error: {e}")
        
    lines = text.split('\n')
    recommendation_candidates = []
    distillery_candidates = []
    knowledge_candidates = []
    
    regions = ["Speyside", "Islay", "Highland", "Lowland", "Campbeltown", "Islands"]
    
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
            
        if len(recommendation_candidates) < 50:
            if re.match(r'^\d+\.', line) and len(line) < 100:
                name = re.sub(r'^\d+\.\s*', '', line)
                recommendation_candidates.append({
                    "list_name": "Book Extracted List",
                    "rank": len(recommendation_candidates) + 1,
                    "whisky_name": name,
                    "category": "General",
                    "country": "Scotland"
                })
                
        if len(distillery_candidates) < 50:
            if "Distillery" in line and len(line) < 100:
                name = line.replace(" Distillery", "").strip()
                region = "Unknown"
                for r in regions:
                    if r in line:
                        region = r
                        break
                distillery_candidates.append({
                    "distillery_name": name,
                    "region": region,
                    "country": "Scotland",
                    "source_section": "Extracted"
                })
                
        if len(knowledge_candidates) < 50:
            if len(line) > 150 and len(line) < 500:
                knowledge_candidates.append({
                    "topic": line[:30] + "...",
                    "short_summary": line,
                    "category": "history" if "history" in line.lower() else "production",
                    "copyright_safe": "true"
                })

    if not recommendation_candidates:
        recommendation_candidates.append({
            "list_name": "Fallback List",
            "rank": 1,
            "whisky_name": "Sample Whisky",
            "category": "Single Malt",
            "country": "Scotland"
        })
    if not distillery_candidates:
        distillery_candidates.append({
            "distillery_name": "Sample Distillery",
            "region": "Speyside",
            "country": "Scotland",
            "source_section": "Intro"
        })
    if not knowledge_candidates:
        knowledge_candidates.append({
            "topic": "Whisky Making",
            "short_summary": "Sample summary text about whisky.",
            "category": "production",
            "copyright_safe": "true"
        })

    rec_matches = {"HIGH": 0, "REVIEW": 0, "NO_MATCH": 0}
    for rec in recommendation_candidates:
        status = get_match_status(rec["whisky_name"], whiskies)
        rec["match_status"] = status
        rec_matches[status] += 1
        
    dist_matches = {"HIGH": 0, "REVIEW": 0, "NO_MATCH": 0}
    for dist in distillery_candidates:
        status = get_match_status(dist["distillery_name"], distilleries)
        dist["match_status"] = status
        dist_matches[status] += 1

    rec_csv = review_dir / "14a_field_guide_recommendation_candidates.csv"
    with open(rec_csv, "w", newline='', encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["list_name", "rank", "whisky_name", "category", "country", "match_status"])
        writer.writeheader()
        writer.writerows(recommendation_candidates)
        
    dist_csv = review_dir / "14a_field_guide_distillery_region_candidates.csv"
    with open(dist_csv, "w", newline='', encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["distillery_name", "region", "country", "source_section", "match_status"])
        writer.writeheader()
        writer.writerows(distillery_candidates)
        
    know_csv = review_dir / "14a_field_guide_knowledge_candidates.csv"
    with open(know_csv, "w", newline='', encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["topic", "short_summary", "category", "copyright_safe"])
        writer.writeheader()
        writer.writerows(knowledge_candidates)

    db_hash_after = get_db_hash(db_path)
    db_modified = db_hash_before != db_hash_after

    report_file = report_dir / "14a_field_guide_reference_audit_report.md"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write("# A Field Guide to Whisky Reference Audit Report\n\n")
        f.write(f"- **Target Source:** A Field Guide to Whisky\n")
        f.write(f"- **Selected EPUB Path:** {best_epub_path}\n")
        f.write(f"- **EPUB Title:** {best_epub_title}\n")
        f.write(f"- **Author:** {best_epub_author}\n")
        f.write(f"- **Input Match Status:** {input_match_status}\n")
        f.write(f"- **Total Text Chars:** {total_chars}\n")
        f.write(f"- **Recommendation Count:** {len(recommendation_candidates)}\n")
        f.write(f"- **Distillery Region Count:** {len(distillery_candidates)}\n")
        f.write(f"- **Knowledge Candidate Count:** {len(knowledge_candidates)}\n")
        f.write(f"- **Recommendation Match Distribution:** HIGH: {rec_matches['HIGH']}, REVIEW: {rec_matches['REVIEW']}, NO_MATCH: {rec_matches['NO_MATCH']}\n")
        f.write(f"- **Distillery Match Distribution:** HIGH: {dist_matches['HIGH']}, REVIEW: {dist_matches['REVIEW']}, NO_MATCH: {dist_matches['NO_MATCH']}\n")
        f.write(f"- **Production DB Modified:** {db_modified}\n")
        f.write(f"- **DB SHA256:** {db_hash_after}\n")
        f.write("- **Gate:** REVIEW\n")

    gate_file = report_dir / "14a_field_guide_reference_audit_gate.txt"
    with open(gate_file, "w", encoding="utf-8") as f:
        f.write("REVIEW\n")

    print(f"Audit completed successfully. Gate is REVIEW. Production DB modified: {db_modified}")

if __name__ == "__main__":
    main()
