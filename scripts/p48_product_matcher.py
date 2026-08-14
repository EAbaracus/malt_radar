import os
import sqlite3
import csv
import re
import difflib
from pathlib import Path

# Paths
REPO_ROOT = Path(r"C:\Users\eltun\Documents\malt radar CLEAN")
DB_PATH = REPO_ROOT / "output" / "import" / "production.db"
STAGING_DIR = REPO_ROOT / "output" / "import" / "books"
REPORT_DIR = REPO_ROOT / "output" / "reports"

# Inputs
APPROVED_NEW_PRODUCTS = STAGING_DIR / "approved_new_products.csv"
REMAINING_MANUAL_REVIEW = STAGING_DIR / "remaining_manual_review.csv"
STAGING_CAT = STAGING_DIR / "staging_catalogue.csv"

# Outputs
MATCH_CANDIDATES_CSV = REPORT_DIR / "p48_match_candidates.csv"
VALIDATION_MD = REPORT_DIR / "p48_validation.md"
GATE_MD = REPORT_DIR / "p48_gate.md"

def get_similarity(s1, s2):
    if not s1 or not s2:
        return 0.0
    return difflib.SequenceMatcher(None, s1.lower().strip(), s2.lower().strip()).ratio()

def extract_age(name):
    m = re.search(r'\b(\d{1,2})\b\s*(?:years|year|yo|y\.o\.|y|old)', name.lower())
    if m:
        return int(m.group(1))
    return None

def extract_abv(name):
    m = re.search(r'\b(\d{2}(?:\.\d+)?)\s*(?:%|vol)\b', name.lower())
    if m:
        return float(m.group(1))
    return None

def extract_cask(name):
    cask_keywords = ["sherry", "port", "rum", "wine", "cask finish", "wood finish", "amarone", "lustau", "madera", "bourbon"]
    name_lower = name.lower()
    found = [k for k in cask_keywords if k in name_lower]
    return ", ".join(found) if found else "standard"

def clean_whisky_name(name):
    name_lower = name.lower()
    name_lower = re.sub(r'\b\d{1,2}\b\s*(?:years|year|yo|y\.o\.|y|old)', '', name_lower)
    name_lower = re.sub(r'\b\d{2}(?:\.\d+)?\s*(?:%|vol)\b', '', name_lower)
    batch_words = ["batch", "release", "edition", "cask strength", "ltd", "limited", "single cask", "bottled", "distilled"]
    for w in batch_words:
        name_lower = name_lower.replace(w, "")
    name_lower = re.sub(r'\s+', ' ', name_lower).strip()
    return name_lower

def main():
    print("Connecting to DB...")
    if not DB_PATH.exists():
        print(f"Error: DB not found at {DB_PATH}")
        return
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Load existing distilleries
    existing_distilleries = {} # id -> details
    cursor.execute("SELECT distillery_id, name, country, region, owner FROM distilleries;")
    for row in cursor.fetchall():
        existing_distilleries[row[0]] = {
            "name": row[1].strip() if row[1] else "",
            "country": row[2].strip() if row[2] else "",
            "region": row[3].strip() if row[3] else "",
            "owner": row[4].strip() if row[4] else ""
        }
        
    # Load existing whiskies
    existing_whiskies = []
    cursor.execute("SELECT whisky_id, name, brand, abv, age_statement, type, cask_type, distillery_id FROM whiskies;")
    for row in cursor.fetchall():
        w_id = row[0]
        w_name = row[1].strip() if row[1] else ""
        brand = row[2].strip() if row[2] else ""
        abv = row[3]
        age = row[4] if row[4] else ""
        w_type = row[5] if row[5] else ""
        cask = row[6] if row[6] else ""
        dist_id = row[7]
        
        dist_name = ""
        country = ""
        region = ""
        if dist_id in existing_distilleries:
            dist_name = existing_distilleries[dist_id]["name"]
            country = existing_distilleries[dist_id]["country"]
            region = existing_distilleries[dist_id]["region"]
            
        existing_whiskies.append({
            "whisky_id": w_id,
            "name": w_name,
            "brand": brand,
            "abv": abv,
            "age": age,
            "category": w_type,
            "cask": cask,
            "distid": dist_id,
            "distname": dist_name,
            "country": country,
            "region": region
        })
    conn.close()
    print(f"Loaded {len(existing_whiskies)} existing whiskies.")
    
    # Load candidate lists
    candidates = []
    
    cat_raw = {}
    if STAGING_CAT.exists():
        with open(STAGING_CAT, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                cat_raw[int(r["source_row"])] = r
                
    if APPROVED_NEW_PRODUCTS.exists():
        with open(APPROVED_NEW_PRODUCTS, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                candidates.append({
                    "name": r["product_name"],
                    "distillery": r["distillery"],
                    "brand": r["brand"],
                    "country": r["country"],
                    "abv": float(r["abv"]) if r["abv"] else None,
                    "age": int(r["age"]) if r["age"] else None,
                    "source_file": r["source_file"],
                    "source_row": int(r["source_row"])
                })
                
    if REMAINING_MANUAL_REVIEW.exists():
        with open(REMAINING_MANUAL_REVIEW, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                s_row = int(r["source_row"])
                raw_r = cat_raw.get(s_row, {})
                
                dbo = raw_r.get("distillery_brand_owner", "")
                parts = [p.strip() for p in dbo.split("-")]
                dist = parts[0] if parts else ""
                brand = parts[1] if len(parts) >= 2 else dist
                
                candidates.append({
                    "name": r["candidate_name"],
                    "distillery": dist,
                    "brand": brand,
                    "country": raw_r.get("country", ""),
                    "abv": extract_abv(r["candidate_name"]),
                    "age": extract_age(r["candidate_name"]),
                    "source_file": r["source_file"],
                    "source_row": s_row
                })
                
    print(f"Loaded {len(candidates)} candidates to match.")
    
    # Match Candidates
    match_results = []
    
    for cand in candidates:
        c_name = cand["name"]
        c_dist = cand["distillery"]
        c_brand = cand["brand"]
        c_country = cand["country"]
        c_abv = cand["abv"]
        c_age = cand["age"]
        c_cask = extract_cask(c_name)
        
        best_match = None
        best_overall = 0.0
        best_scores = {}
        
        db_subset = []
        for ex in existing_whiskies:
            dist_sim = get_similarity(c_dist, ex["distname"])
            if dist_sim >= 0.70 or c_dist.lower() in ex["distname"].lower() or ex["distname"].lower() in c_dist.lower():
                db_subset.append((ex, dist_sim))
                
        for ex, dist_sim in db_subset:
            c_name_clean = clean_whisky_name(c_name)
            ex_name_clean = clean_whisky_name(ex["name"])
            name_sim = get_similarity(c_name_clean, ex_name_clean)
            
            ex_age = None
            if ex["age"]:
                try:
                    age_m = re.search(r'\d+', str(ex["age"]))
                    if age_m: ex_age = int(age_m.group())
                except:
                    pass
                
            age_sim = 0.0
            if c_age is None and ex_age is None:
                age_sim = 1.0
            elif c_age is not None and ex_age is not None:
                if c_age == ex_age:
                    age_sim = 1.0
                else:
                    age_sim = 0.0
            else:
                age_sim = 0.5
                
            abv_sim = 0.0
            if c_abv is None and ex["abv"] is None:
                abv_sim = 1.0
            elif c_abv is not None and ex["abv"] is not None:
                abv_diff = abs(c_abv - ex["abv"])
                abv_sim = max(0.0, 1.0 - abv_diff / 10.0)
            else:
                abv_sim = 0.5
                
            ex_cask = extract_cask(ex["name"])
            cask_sim = get_similarity(c_cask, ex_cask)
            
            brand_sim = get_similarity(c_brand, ex["brand"])
            
            country_sim = 0.0
            if c_country and ex["country"]:
                c_country_clean = c_country.split("-")[0].strip().lower()
                ex_country_clean = ex["country"].split("-")[0].strip().lower()
                if c_country_clean == ex_country_clean or c_country_clean in ex_country_clean or ex_country_clean in c_country_clean:
                    country_sim = 1.0
            else:
                country_sim = 1.0
                
            region_sim = get_similarity(cand.get("region", ""), ex["region"])
            bottler_sim = 1.0
            
            overall = (
                dist_sim * 0.30 +
                name_sim * 0.25 +
                age_sim * 0.15 +
                abv_sim * 0.10 +
                cask_sim * 0.08 +
                bottler_sim * 0.05 +
                brand_sim * 0.03 +
                country_sim * 0.02 +
                region_sim * 0.02
            )
            
            if age_sim == 0.0:
                overall = min(overall, 0.79)
            if country_sim == 0.0:
                overall = min(overall, 0.79)
            if dist_sim < 0.70:
                overall = 0.0
                
            if overall > best_overall:
                best_overall = overall
                best_match = ex
                best_scores = {
                    "distillery": dist_sim,
                    "name": name_sim,
                    "age": age_sim,
                    "abv": abv_sim,
                    "cask": cask_sim,
                    "brand": brand_sim,
                    "country": country_sim,
                    "region": region_sim
                }
                
        rec_action = "NEW_PRODUCT"
        if best_overall >= 0.95:
            rec_action = "AUTO_MATCH"
        elif best_overall >= 0.90:
            rec_action = "HIGH_CONFIDENCE"
        elif best_overall >= 0.80:
            rec_action = "MANUAL_REVIEW"
            
        trace = ""
        if best_match:
            age_status = "exact" if best_scores["age"] == 1.0 else ("diff" if best_scores["age"] == 0.0 else "nas_vs_aged")
            trace = f"Distillery exact ({round(best_scores['distillery'], 2)}); Age {age_status}; ABV sim {round(best_scores['abv'], 2)}; Cask sim {round(best_scores['cask'], 2)}; Rule={rec_action}"
        else:
            trace = "No matching distillery found; Rule=NEW_PRODUCT"
            best_scores = {k: 0.0 for k in ["distillery", "name", "age", "abv", "cask", "brand", "country", "region"]}
            
        match_results.append({
            "candidate_name": c_name,
            "matched_whisky_id": best_match["whisky_id"] if best_match else "None",
            "matched_name": best_match["name"] if best_match else "None",
            "overall_similarity": round(best_overall, 4),
            "distillery_score": round(best_scores["distillery"], 4),
            "name_score": round(best_scores["name"], 4),
            "age_score": round(best_scores["age"], 4),
            "abv_score": round(best_scores["abv"], 4),
            "cask_score": round(best_scores["cask"], 4),
            "brand_score": round(best_scores["brand"], 4),
            "country_score": round(best_scores["country"], 4),
            "region_score": round(best_scores["region"], 4),
            "recommended_action": rec_action,
            "reason": trace
        })
        
    # Write p48_match_candidates.csv
    with open(MATCH_CANDIDATES_CSV, "w", newline="", encoding="utf-8") as f:
        if match_results:
            writer = csv.DictWriter(f, fieldnames=match_results[0].keys())
            writer.writeheader()
            writer.writerows(match_results)
    print(f"Saved candidates report: {MATCH_CANDIDATES_CSV}")
    
    # ---------------- VALIDATIONS ----------------
    total_candidates = len(candidates)
    auto_matches = sum(1 for r in match_results if r["recommended_action"] == "AUTO_MATCH")
    high_conf = sum(1 for r in match_results if r["recommended_action"] == "HIGH_CONFIDENCE")
    manual_reviews = sum(1 for r in match_results if r["recommended_action"] == "MANUAL_REVIEW")
    new_products = sum(1 for r in match_results if r["recommended_action"] == "NEW_PRODUCT")
    
    mapped_ids = [r["matched_whisky_id"] for r in match_results if r["matched_whisky_id"] != "None"]
    dupes_mapped = set([x for x in mapped_ids if mapped_ids.count(x) > 1])
    
    age_conflicts = 0
    country_conflicts = 0
    cross_distillery = 0
    
    for r in match_results:
        if r["recommended_action"] in ("AUTO_MATCH", "HIGH_CONFIDENCE"):
            if r["age_score"] == 0.0:
                age_conflicts += 1
            if r["country_score"] == 0.0:
                country_conflicts += 1
            if r["distillery_score"] < 0.70:
                cross_distillery += 1
                
    # Write p48_validation.md
    print("Writing validation report...")
    with open(VALIDATION_MD, "w", encoding="utf-8") as f:
        f.write("# Malt Radar P48 - Eşleştirme Validasyon Raporu\n\n")
        f.write("**Oluşturulma Tarihi:** 2026-07-12\n\n")
        f.write(f"- **Toplam Eşleştirme Adayı (candidate count):** {total_candidates}\n")
        f.write(f"  - AUTO_MATCH: {auto_matches}\n")
        f.write(f"  - HIGH_CONFIDENCE: {high_conf}\n")
        f.write(f"  - MANUAL_REVIEW: {manual_reviews}\n")
        f.write(f"  - NEW_PRODUCT: {new_products}\n\n")
        
        f.write("## 1. Çakışma ve Mükerrer Kontrolleri (Conflicts & Duplicates)\n")
        f.write(f"- **Mükerrer Eşleşmeler (duplicate matches):** {len(dupes_mapped)} farklı viski ID'sine birden fazla aday bağlandı.\n")
        if dupes_mapped:
            f.write("  - Çakışan ID'ler: " + ", ".join(list(dupes_mapped)[:10]) + "\n")
        f.write(f"- **Çelişkili Eşleşmeler (conflicting matches):** {age_conflicts} yaş çelişkisi, {country_conflicts} ülke çelişkisi saptandı.\n")
        f.write(f"- **Eşleşmeyen Kayıtlar (unmatched products):** {new_products} kayıt yeni ürün olarak işaretlendi.\n")
        f.write(f"- **Yanlış Pozitif Riskleri (false-positive risks):** Düşük güvenli fuzzy eşleşen {manual_reviews} kayıt yanlış pozitif riski taşımaktadır ve manuel incelemeye sevk edilmiştir.\n")
        
    # Write p48_gate.md Quality Gate
    gate_status = "PASS"
    gate_failures = []
    
    if len(dupes_mapped) > 0:
        gate_failures.append("Duplicate mappings detected (multiple candidates mapping to same ID).")
    if cross_distillery > 0:
        gate_status = "FAIL"
        gate_failures.append("Cross-distillery auto matches detected.")
    if age_conflicts > 0:
        gate_status = "FAIL"
        gate_failures.append("Age conflicts detected in auto/high confidence matches.")
    if country_conflicts > 0:
        gate_status = "FAIL"
        gate_failures.append("Country conflicts detected in auto/high confidence matches.")
        
    print("Writing quality gate report...")
    with open(GATE_MD, "w", encoding="utf-8") as f:
        f.write("# Malt Radar P48 - Kalite Geçidi Raporu (Quality Gate Report)\n\n")
        f.write("**Oluşturulma Tarihi:** 2026-07-12\n")
        f.write(f"**Geçit Statüsü (Gate Status):** **{gate_status}**\n\n")
        
        f.write("## 1. Geçit Kriterleri Kontrol Listesi\n")
        f.write("| Kriter | Durum | Gözlem |\n")
        f.write("| --- | --- | --- |\n")
        f.write(f"| Çapraz Damıtımevi Eşleşmesi Yok (No cross-distillery auto matches) | {'FAIL' if cross_distillery > 0 else 'PASS'} | {cross_distillery} adet çapraz eşleşme bulundu. |\n")
        f.write(f"| Yaş Çelişkisi Yok (No age conflicts) | {'FAIL' if age_conflicts > 0 else 'PASS'} | {age_conflicts} adet yaş çelişkisi bulundu. |\n")
        f.write(f"| Ülke Çelişkisi Yok (No country conflicts) | {'FAIL' if country_conflicts > 0 else 'PASS'} | {country_conflicts} adet ülke çelişkisi bulundu. |\n")
        f.write(f"| Mükerrer Eşleme Yok (No duplicate mappings) | {'WARN' if len(dupes_mapped) > 0 else 'PASS'} | {len(dupes_mapped)} adet mükerrer eşleme bulundu. |\n")
        
        f.write("\n## 2. Hata Detayları ve Gerekçeler\n")
        if gate_failures:
            for fail in gate_failures:
                f.write(f"- [ ] **ENGEL:** {fail}\n")
        else:
            f.write("- [x] Tüm kalite geçidi kuralları başarıyla karşılanmıştır.\n")
            
        f.write("\n## 3. GO / NO-GO Kararı (GO / NO-GO Recommendation)\n")
        f.write(f"- Bu modül veritabanına **kesinlikle** veri yazmamıştır (Salt Okunur modda çalışmıştır).\n")
        if gate_status == "PASS":
            f.write("\n### Nihai Karar: **GO (Eşleştirme Kararları Güvenlidir)**\n")
        else:
            f.write("\n### Nihai Karar: **NO-GO (Kritik Eşleşme Çelişkileri Bulunmaktadır)**\n")
            
    print(f"Gate report written to {GATE_MD}")

if __name__ == "__main__":
    main()
