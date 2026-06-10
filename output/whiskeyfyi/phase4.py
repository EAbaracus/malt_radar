import csv
import difflib
import re

MASTER_FILE = r"C:\Users\eltun\Documents\malt radar\recovered_from_radiant_bardeen\output\final\67_FINAL_import_ready_distilleries_whiskycom_enriched.csv"
REF_FILE = "09_distillery_reference_candidates.csv"

def normalize(name):
    if not name: return ""
    name = name.lower()
    name = re.sub(r'[^a-z0-9]', '', name)
    name = name.replace("distillery", "").replace("the", "")
    return name

master_records = []
with open(MASTER_FILE, "r", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        master_records.append(row)

ref_records = []
with open(REF_FILE, "r", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        ref_records.append(row)

high_confidence = []
manual_review = []
no_match = []
candidates_all = []

for ref in ref_records:
    r_name = ref.get("name", "")
    r_norm = normalize(r_name)
    best_score = 0
    best_match = None
    matches = []

    for m in master_records:
        m_name = m.get("Distillery", m.get("name", ""))
        m_norm = normalize(m_name)
        
        if r_norm == m_norm and len(r_norm) > 2:
            score = 100
        else:
            score = int(difflib.SequenceMatcher(None, r_norm, m_norm).ratio() * 100)
            
        if score >= 88:
            matches.append((score, m))
            if score > best_score:
                best_score = score
                best_match = m

    # Determine confidence
    confidence = "no_match"
    if best_score >= 94 and len([x for x in matches if x[0] >= 94]) == 1:
        confidence = "high_confidence"
    elif 88 <= best_score <= 93 or len([x for x in matches if x[0] >= 94]) > 1:
        confidence = "manual_review"

    # Region/Country conflict logic for high confidence
    if confidence == "high_confidence":
        r_country = ref.get("country", "").lower()
        m_country = best_match.get("Country", "").lower()
        if r_country and m_country and r_country not in m_country and m_country not in r_country:
            if not ((r_country == "scotland" and "uk" in m_country) or ("uk" in r_country and m_country == "scotland") or ("scotland" in r_country and "scotland" in m_country)):
                confidence = "manual_review"

    row_out = {
        "ref_name": r_name,
        "ref_slug": ref.get("slug", ""),
        "ref_country": ref.get("country", ""),
        "ref_region": ref.get("region", ""),
        "match_confidence": confidence,
        "best_score": best_score,
        "master_name": best_match.get("Distillery", "") if best_match else "",
        "master_uuid": best_match.get("UUID", "") if best_match else ""
    }
    
    candidates_all.append(row_out)
    
    if confidence == "high_confidence":
        high_confidence.append(row_out)
    elif confidence == "manual_review":
        manual_review.append(row_out)
    else:
        no_match.append(row_out)

def write_csv(filename, data):
    if not data:
        with open(filename, "w", newline="", encoding="utf-8") as f:
            f.write("ref_name,ref_slug,ref_country,ref_region,match_confidence,best_score,master_name,master_uuid\n")
        return
    keys = data[0].keys()
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(data)

write_csv("14_distillery_master_match_candidates.csv", candidates_all)
write_csv("15_distillery_high_confidence_matches.csv", high_confidence)
write_csv("16_distillery_manual_review_matches.csv", manual_review)
write_csv("17_distillery_no_match.csv", no_match)
