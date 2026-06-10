import csv
import os

MASTER_FILE = r"C:\Users\eltun\Documents\malt radar\recovered_from_radiant_bardeen\output\final\67_FINAL_import_ready_distilleries_whiskycom_enriched.csv"
HIGH_CONF_MATCHES = "15_distillery_high_confidence_matches.csv"
REF_DISTILLERY = "09_distillery_reference_candidates.csv"
REF_REGION = "10_region_reference.csv"
REF_GLOSSARY = "11_glossary_terms.csv"
REF_GUIDES = "12_guides_index.csv"

# 1. Load Master Distilleries
master_dist = {}
try:
    with open(MASTER_FILE, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            master_dist[row.get("UUID", "")] = row
except Exception as e:
    print(f"Error reading master file: {e}")

# 2. Load Reference Distilleries
ref_dist = {}
try:
    with open(REF_DISTILLERY, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            ref_dist[row["name"]] = row
except Exception as e:
    pass

# 3. Distillery Enrichment Preview
distillery_enrichment = []
try:
    with open(HIGH_CONF_MATCHES, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            m_uuid = row["master_uuid"]
            r_name = row["ref_name"]
            master = master_dist.get(m_uuid, {})
            ref = ref_dist.get(r_name, {})
            
            enrich = {
                "master_uuid": m_uuid,
                "master_name": master.get("Distillery", ""),
                "new_url": "",
                "new_short_description": ""
            }
            
            has_enrichment = False
            if not master.get("Website", "") and ref.get("url", ""):
                enrich["new_url"] = ref["url"]
                has_enrichment = True
                
            if not master.get("Description", "") and ref.get("description", ""):
                enrich["new_short_description"] = ref["description"]
                has_enrichment = True
                
            if has_enrichment:
                distillery_enrichment.append(enrich)
except Exception as e:
    pass

if not distillery_enrichment:
    with open("21_distillery_enrichment_patch_preview.csv", "w", newline="", encoding="utf-8") as f:
        f.write("master_uuid,master_name,new_url,new_short_description\n")
else:
    with open("21_distillery_enrichment_patch_preview.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["master_uuid", "master_name", "new_url", "new_short_description"])
        writer.writeheader()
        writer.writerows(distillery_enrichment)

# 4. Region and Taxonomy Preview
try:
    with open(REF_REGION, "r", encoding="utf-8") as f1, \
         open("20_region_reference_patch_preview.csv", "w", newline="", encoding="utf-8") as f2, \
         open("18_taxonomy_patch_preview.csv", "w", newline="", encoding="utf-8") as f3:
        
        reader = csv.DictReader(f1)
        writer20 = csv.DictWriter(f2, fieldnames=["slug", "region", "country", "description", "url"])
        writer20.writeheader()
        
        writer18 = csv.DictWriter(f3, fieldnames=["country", "region"])
        writer18.writeheader()
        
        for row in reader:
            writer20.writerow({
                "slug": row.get("slug", ""),
                "region": row.get("name", row.get("region", "")),
                "country": row.get("country", ""),
                "description": row.get("description", ""),
                "url": row.get("url", "")
            })
            writer18.writerow({
                "country": row.get("country", ""),
                "region": row.get("name", row.get("region", ""))
            })
except Exception as e:
    pass

# 5. Glossary
try:
    with open(REF_GLOSSARY, "r", encoding="utf-8") as f1, \
         open("19_glossary_import_candidates.csv", "w", newline="", encoding="utf-8") as f2:
        reader = csv.DictReader(f1)
        writer = csv.DictWriter(f2, fieldnames=reader.fieldnames)
        writer.writeheader()
        for row in reader:
            writer.writerow(row)
except Exception as e:
    pass

# Count stats for final report
def count_lines(filename):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return max(0, sum(1 for _ in f) - 1)
    except:
        return 0

final_report = []
final_report.append("WHISKEYFYI FINAL FETCH & MATCH REPORT")
final_report.append("=====================================")
final_report.append(f"Whiskey Expressions fetched: {count_lines('08_whiskey_expressions.csv')}")
final_report.append(f"Distilleries reference items: {count_lines('09_distillery_reference_candidates.csv')}")
final_report.append(f"Regions: {count_lines('10_region_reference.csv')}")
final_report.append(f"Glossary terms: {count_lines('11_glossary_terms.csv')}")
final_report.append(f"Guides: {count_lines('12_guides_index.csv')}")
final_report.append("")
final_report.append("MATCHING RESULTS")
final_report.append("----------------")
final_report.append(f"High Confidence Matches: {count_lines('15_distillery_high_confidence_matches.csv')}")
final_report.append(f"Manual Review Matches: {count_lines('16_distillery_manual_review_matches.csv')}")
final_report.append(f"No Match: {count_lines('17_distillery_no_match.csv')}")
final_report.append("")
final_report.append("KNOWLEDGE BASE CANDIDATES")
final_report.append("-------------------------")
final_report.append(f"Taxonomy items (Country/Region): {count_lines('18_taxonomy_patch_preview.csv')}")
final_report.append(f"Glossary items: {count_lines('19_glossary_import_candidates.csv')}")
final_report.append(f"Region descriptions: {count_lines('20_region_reference_patch_preview.csv')}")
final_report.append(f"Distilleries with enrichment (url/desc): {count_lines('21_distillery_enrichment_patch_preview.csv')}")
final_report.append("")
final_report.append("EXCLUSIONS")
final_report.append("----------")
final_report.append("- Product Tasting notes are excluded from master (kept as reference only if they existed).")
final_report.append("- No new entries are added to the distillery master.")

with open("22_final_report.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(final_report))
