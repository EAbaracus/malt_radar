import os
import re
import pandas as pd
import fitz  # PyMuPDF
from thefuzz import fuzz, process

PDF_PATH = r"C:\Users\eltun\Documents\malt radar\backend\data\The_Malt_List.pdf"
DB_PATH = r"C:\Users\eltun\Documents\malt radar\backend\data\whisky_database_merged_max.csv"
OUTPUT_DIR = r"C:\Users\eltun\Documents\malt radar\output\malt_list"

# Create output dir if not exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

typo_map = {
    "Glenfraclas": "Glenfarclas",
    "Laphroig": "Laphroaig",
    "Kilochman": "Kilchoman",
    "Glen Garrioch": "Glen Garioch",
    "Clynliesh": "Clynelish",
    "Jonnie Walker": "Johnnie Walker",
    "Glenkinnchie": "Glenkinchie"
}

def clean_text(t):
    return t.strip()

def parse_age_statement(age_str):
    if not age_str:
        return None, None, False
    age_str = str(age_str).lower()
    no_age = "no statement" in age_str
    
    age = None
    vintage = None
    
    # regex for yo e.g. 10yo, 16yo
    yo_match = re.search(r'(\d+)yo', age_str)
    if yo_match:
        age = int(yo_match.group(1))
        
    # regex for vintage e.g. 1995, 1983
    vint_match = re.search(r'(19\d{2}|20\d{2})', age_str)
    if vint_match:
        vintage = int(vint_match.group(1))
        
    return age, vintage, no_age

def process_pdf():
    doc = fitz.open(PDF_PATH)
    
    products = []
    tasting_notes_structured = []
    raw_lines = []
    
    # Pages 2-13 (0-indexed 1-12)
    current_product = None
    
    for page_num in range(1, min(13, len(doc))):
        page = doc[page_num]
        text = page.get_text("text")
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        i = 0
        while i < len(lines):
            line = lines[i]
            raw_lines.append(f"Page {page_num+1}: {line}")
            
            # Skip headers
            if line in ["2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "ISLAY", "HIGHLAND", "SPEYSIDE", "LOWLAND", "DISTILERY", "AGE", "ABV", "PRICE"]:
                i += 1
                continue
                
            # If line is a general note
            if line.startswith('‘') or line.startswith('"') or (current_product and not re.search(r'\d', line) and len(line)>20):
                note = line
                # Consume lines until quote ends or 'MK' or another condition
                while i + 1 < len(lines) and not note.endswith('MK') and not note.endswith('”') and not note.endswith('’') and not note.endswith('"'):
                    i += 1
                    note += " " + lines[i]
                    raw_lines.append(f"Page {page_num+1}: {lines[i]}")
                if current_product:
                    current_product['general_note'] = note.strip('‘’”" ')
                i += 1
                continue
                
            # Look ahead to see if this is a name by finding the % and price
            # Pattern 1: Name, Age, ABV, Price
            # Pattern 2: Name, ABV, Price
            is_new_product = False
            name = ""
            age_str = ""
            abv = ""
            price = ""
            
            # Try 4 lines: Name, Age, ABV, Price
            if i + 3 < len(lines) and '%' in lines[i+2] and re.match(r'^\d+\.$', lines[i+3]):
                name = line
                age_str = lines[i+1]
                abv = lines[i+2]
                price = lines[i+3].replace('.', '')
                is_new_product = True
                i += 4
            # Try 3 lines: Name, ABV, Price
            elif i + 2 < len(lines) and '%' in lines[i+1] and re.match(r'^\d+\.$', lines[i+2]):
                name = line
                age_str = ""
                abv = lines[i+1]
                price = lines[i+2].replace('.', '')
                is_new_product = True
                i += 3
            # Try 3 lines: Name, Age, ABV (missing price) - probably not common but possible
            # Or Name + Age + ABV on same line? No, we saw they are separate
            else:
                # Could be something else, just advance
                i += 1
                
            if is_new_product:
                is_cs = False
                if ' cs' in name.lower() or '(cs)' in name.lower():
                    is_cs = True
                    name = re.sub(r'(?i)\s*\(?cs\)?', '', name).strip()
                
                age, vintage, no_age = parse_age_statement(age_str)
                
                product = {
                    'raw_name': name,
                    'age_raw': age_str,
                    'age': age,
                    'vintage': vintage,
                    'no_age_statement': no_age,
                    'abv': abv.replace('%', ''),
                    'historical_menu_price': price,
                    'is_cask_strength': is_cs,
                    'general_note': '',
                    'page_number': page_num + 1,
                    'source_file': 'The_Malt_List.pdf',
                    'source_type': 'historical_bar_menu',
                    'source_confidence': 'medium',
                    'raw_line': name
                }
                products.append(product)
                current_product = product
            
    # Pages 14-17 (0-indexed 13-16) - Structured tasting notes
    current_tasting_product = None
    for page_num in range(13, min(17, len(doc))):
        page = doc[page_num]
        text = page.get_text("text")
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        for line in lines:
            raw_lines.append(f"Page {page_num+1}: {line}")
            lower_line = line.lower()
            if lower_line in ["highland", "island", "speyside", "lowland", "rare malt collection"]:
                continue
                
            if lower_line.startswith("nose:"):
                if current_tasting_product:
                    current_tasting_product['nose'] = line[5:].strip()
            elif lower_line.startswith("palate:"):
                if current_tasting_product:
                    current_tasting_product['palate'] = line[7:].strip()
            elif lower_line.startswith("finish:"):
                if current_tasting_product:
                    current_tasting_product['finish'] = line[7:].strip()
            elif lower_line.startswith("when?"):
                continue
            elif not lower_line.startswith("nose:") and not lower_line.startswith("palate:") and not lower_line.startswith("finish:"):
                # Could be a new product name
                if len(line) > 3 and not line.endswith('.') and '%' not in line:
                    current_tasting_product = {
                        'raw_name': line,
                        'nose': '',
                        'palate': '',
                        'finish': '',
                        'page_number': page_num + 1,
                        'source_file': 'The_Malt_List.pdf',
                        'source_type': 'historical_bar_menu',
                        'source_confidence': 'medium',
                        'raw_note': line
                    }
                    tasting_notes_structured.append(current_tasting_product)

    return products, tasting_notes_structured, raw_lines

def match_products(products, df_db):
    high_confidence = []
    manual_review = []
    rejected = []
    candidates = []
    
    db_names = df_db['canonical_name'].dropna().tolist()
    
    for p in products:
        raw_name = p['raw_name']
        
        # Typo Check
        has_typo = False
        for typo, correction in typo_map.items():
            if typo.lower() in raw_name.lower():
                has_typo = True
                p['typo_candidate'] = True
                p['suggested_correction'] = raw_name.replace(typo, correction)
                break
                
        # Matching
        best_match, score = process.extractOne(raw_name, db_names, scorer=fuzz.token_sort_ratio)
        p['best_match'] = best_match
        p['match_score'] = score
        
        if score > 80:
            db_record = df_db[df_db['canonical_name'] == best_match].iloc[0]
            db_age = str(db_record.get('age_years', '')).strip()
            db_abv = str(db_record.get('abv_percent', '')).strip()
            
            p['db_age'] = db_age
            p['db_abv'] = db_abv
            p['record_id'] = db_record['record_id']
            
            age_match = False
            if p.get('age'):
                age_match = str(p['age']) == db_age
            elif p.get('no_age_statement'):
                age_match = (db_age == '' or db_age.lower() == 'nan')
            else:
                age_match = True # If we didn't parse an age, we don't strict match it unless we want to
                
            abv_match = False
            if p.get('abv'):
                try:
                    abv_match = float(p['abv']) == float(db_abv)
                except:
                    abv_match = False
            
            if score >= 95 and age_match and abv_match and not has_typo:
                high_confidence.append(p)
            elif score >= 85 and age_match and not abv_match:
                p['review_reason'] = 'ABV mismatch or missing'
                manual_review.append(p)
            elif has_typo:
                p['review_reason'] = 'OCR Typo Detected'
                manual_review.append(p)
            elif score >= 70:
                p['review_reason'] = 'Fuzzy match threshold'
                manual_review.append(p)
            else:
                p['review_reason'] = 'Low match score'
                rejected.append(p)
        else:
            p['review_reason'] = 'No close match found'
            rejected.append(p)
            candidates.append(p)
            
    return high_confidence, manual_review, rejected, candidates

def main():
    print("Reading Database...")
    df_db = pd.read_csv(DB_PATH)
    
    print("Parsing PDF...")
    products, tasting_notes, raw_lines = process_pdf()
    
    print("Matching Products...")
    high_confidence, manual_review, rejected, new_candidates = match_products(products, df_db)
    
    # Process Tasting Notes Matching similarly
    t_high, t_manual, t_rejected, _ = match_products(tasting_notes, df_db)
    
    # Save outputs
    print("Saving outputs...")
    with open(os.path.join(OUTPUT_DIR, "01_pdf_profile_report.txt"), "w", encoding="utf-8") as f:
        f.write("PDF Profile Report: The_Malt_List.pdf\n")
        f.write(f"Products Extracted: {len(products)}\n")
        f.write(f"Tasting Notes Extracted: {len(tasting_notes)}\n")
        f.write("This run utilized fallback database: whisky_database_merged_max.csv\n")
        f.write("All outputs are candidate only. No master files were mutated.\n")
        
    with open(os.path.join(OUTPUT_DIR, "02_raw_extracted_text.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(raw_lines))
        
    pd.DataFrame(products).to_csv(os.path.join(OUTPUT_DIR, "03_malt_list_product_candidates.csv"), index=False)
    
    # 04 and 05 are parse specific, but we'll use our product matches
    pd.DataFrame(manual_review).to_csv(os.path.join(OUTPUT_DIR, "04_malt_list_parse_manual_review.csv"), index=False)
    pd.DataFrame([p for p in products if not p.get('age') and not p.get('no_age_statement')]).to_csv(os.path.join(OUTPUT_DIR, "05_malt_list_parse_rejected.csv"), index=False)
    
    pd.DataFrame(tasting_notes).to_csv(os.path.join(OUTPUT_DIR, "06_malt_list_tasting_note_candidates.csv"), index=False)
    pd.DataFrame(t_manual).to_csv(os.path.join(OUTPUT_DIR, "07_malt_list_tasting_note_manual_review.csv"), index=False)
    
    # 08 all master match candidates
    all_matches = high_confidence + manual_review + rejected
    pd.DataFrame(all_matches).to_csv(os.path.join(OUTPUT_DIR, "08_malt_list_master_match_candidates.csv"), index=False)
    
    pd.DataFrame(high_confidence).to_csv(os.path.join(OUTPUT_DIR, "09_malt_list_high_confidence_matches.csv"), index=False)
    pd.DataFrame(manual_review).to_csv(os.path.join(OUTPUT_DIR, "10_malt_list_manual_review_matches.csv"), index=False)
    pd.DataFrame(rejected).to_csv(os.path.join(OUTPUT_DIR, "11_malt_list_rejected_matches.csv"), index=False)
    
    # 12 and 13 previews
    pd.DataFrame(t_high).to_csv(os.path.join(OUTPUT_DIR, "12_malt_list_tasting_notes_patch_preview.csv"), index=False)
    pd.DataFrame(high_confidence).to_csv(os.path.join(OUTPUT_DIR, "13_malt_list_historical_price_patch_preview.csv"), index=False)
    
    pd.DataFrame(new_candidates).to_csv(os.path.join(OUTPUT_DIR, "14_malt_list_new_product_candidates.csv"), index=False)
    
    with open(os.path.join(OUTPUT_DIR, "15_malt_list_final_report.txt"), "w", encoding="utf-8") as f:
        f.write("Final Extraction Report\n")
        f.write("========================\n")
        f.write(f"Total Products: {len(products)}\n")
        f.write(f"High Confidence Matches: {len(high_confidence)}\n")
        f.write(f"Manual Review Needed: {len(manual_review)}\n")
        f.write(f"Rejected Matches: {len(rejected)}\n")
        f.write(f"New Candidates: {len(new_candidates)}\n")
        f.write(f"Tasting Notes Parsed: {len(tasting_notes)}\n")
        f.write("Status: RUN COMPLETED IN ISOLATION. AWAITING USER APPROVAL FOR PATCH.\n")
        
    print("Done!")

if __name__ == "__main__":
    main()
