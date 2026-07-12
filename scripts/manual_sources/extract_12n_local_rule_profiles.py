from pathlib import Path
import json
import re
import csv
from collections import Counter

IN_FILE = Path("data/manual_sources/books/expression_blocks/12n_pilot_expression_blocks_deduped.jsonl")
OUT_DIR = Path("data/manual_sources/books/extracted_jsonl")
CSV_DIR = Path("data/manual_sources/books/review_csv")
REPORT_DIR = Path("output/reports")

OUT_DIR.mkdir(parents=True, exist_ok=True)
CSV_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)

JSONL_OUT = OUT_DIR / "12n_local_rule_book_profile_extractions.jsonl"
CSV_OUT = CSV_DIR / "12n_local_rule_book_profile_review.csv"
REPORT_OUT = REPORT_DIR / "12n_local_rule_book_profile_report.md"
GATE_OUT = REPORT_DIR / "12n_local_rule_book_profile_gate.txt"

SCORE_KEYS = [
    "smoky", "peaty", "sherry", "fruity", "floral", "spicy", "sweet",
    "oak", "maritime", "winey", "malty", "nutty", "herbal", "waxy",
    "oily", "light_body", "rich_body"
]

KEYWORD_MAP = {
    "smoky": ["smoke", "smoky", "bonfire", "barbecue", "soot", "charcoal", "ash", "ashy"],
    "peaty": ["peat", "peated", "peaty", "bog", "earthy"],
    "sherry": ["sherry", "manzanilla", "px", "pedro ximenez", "oloroso", "fino", "amontillado"],
    "fruity": ["fruit", "fruity", "pear", "apple", "lemon", "lime", "orange", "banana", "peach", "citrus", "raisin", "cherry", "plum", "zest"],
    "floral": ["floral", "flower", "violet", "heather", "rose", "blossom"],
    "spicy": ["spice", "spicy", "pepper", "ginger", "cinnamon", "clove", "aniseed", "nutmeg"],
    "sweet": ["sweet", "honey", "caramel", "toffee", "vanilla", "sugar", "chocolate", "candy", "syrup"],
    "oak": ["oak", "wood", "cask", "barrel", "tannin", "woody"],
    "maritime": ["salt", "salty", "brine", "seaweed", "iodine", "fish", "maritime", "sea", "kipper"],
    "winey": ["wine", "port", "sauternes", "madeira", "burgundy", "claret"],
    "malty": ["malt", "malty", "cereal", "barley", "biscuit", "cookie"],
    "nutty": ["nut", "nutty", "almond", "walnut", "chestnut", "hazelnut"],
    "herbal": ["herbal", "mint", "grass", "pine", "medicinal", "medicine", "antiseptic", "licorice", "eucalyptus", "heather"],
    "waxy": ["wax", "waxy", "lanolin", "candle"],
    "oily": ["oil", "oily", "viscous", "greasy"],
    "light_body": ["light body", "body light", "light, firm", "delicate"],
    "rich_body": ["full body", "body full", "rich", "robust", "viscous", "supple", "heavy", "thick"],
}

def clean(s):
    if s is None:
        return None
    s = str(s)
    s = s.replace("â€“", "-").replace("Â", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s or None

def extract_between(text, start_label, end_labels):
    pattern = rf"{start_label}\s+(.*?)(?=" + "|".join([rf"\b{x}\b" for x in end_labels]) + r"|$)"
    m = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
    if not m:
        return None
    res = clean(m.group(1))
    # cut off prematurely if another major section starts that wasn't in end_labels
    next_section = re.search(r"\b(NOSE|PALATE|FINISH|BODY|SCORE|GENERAL|PRICE|AGE|ALC/VOL)\b", res, flags=re.IGNORECASE)
    if next_section:
        res = res[:next_section.start()].strip()
    return res

def extract_abv(text):
    m = re.search(r"(\d{1,2}(?:\.\d)?)\s*(?:vol|%|ALC/VOL)", text, flags=re.IGNORECASE)
    if not m:
        return None
    try:
        return float(m.group(1))
    except Exception:
        return None

def extract_age(text):
    m = re.search(r"(\d{1,2})\s*[- ]?(?:year|yr|yo)[- ]?old", text, flags=re.IGNORECASE)
    if m:
        return int(m.group(1))
    m = re.search(r"\bAGE\s+(\d{1,2})\s+years?\s+old", text, flags=re.IGNORECASE)
    if m:
        return int(m.group(1))
    if re.search(r"No age statement", text, flags=re.IGNORECASE):
        return None
    return None

def infer_name(target, text):
    first = clean(text[:250]) or target
    
    # World Atlas Format: "TASTING NOTES UIGEADAIL 54.2%"
    m_wa = re.search(r"TASTING NOTES\s+(.+?)(?:\d{1,2}(?:\.\d+)?\s*%|\s+COLOR|\s+NOSE|\s+AGE)", first, flags=re.IGNORECASE)
    if m_wa:
        extracted = clean(m_wa.group(1))
        if target.lower() not in extracted.lower():
            extracted = f"{target} {extracted}"
        return clean(extracted)
        
    # Risen and Jackson format
    m = re.search(rf"^{re.escape(target)}\s+(.+?)(?:\s+PRICE|\s+COLOR|\s+NOSE|\s+AGE|\s+ALC/VOL|,\s*\d+(\.\d+)?\s*vol|\d+(\.\d+)?%)", first, flags=re.IGNORECASE)
    if m:
        rest = clean(m.group(1))
        if rest:
            return clean(f"{target} {rest}")
            
    return target

def is_distillery_profile(target, text):
    low = text.lower()
    if "producer" in low or "owner:" in low or "founded:" in low or "house style" in low:
        if not any(x in low for x in ["nose", "palate", "finish", "alc/vol"]):
            return True
    if "house style" in low and not re.search(r"\d{1,2}\s*[- ]?(year|yo|yr)", low):
        return True
    return False

def pick_tags(text):
    low = text.lower()
    tags = []
    for key, words in KEYWORD_MAP.items():
        if any(w in low for w in words):
            tags.append(key)
    return tags

def score_radar(text):
    low = text.lower()
    scores = {}
    for key in SCORE_KEYS:
        hits = sum(1 for w in KEYWORD_MAP.get(key, []) if w in low)
        if hits == 0:
            scores[key] = None
        elif hits == 1:
            scores[key] = 45
        elif hits == 2:
            scores[key] = 60
        else:
            scores[key] = 75

    # stronger explicit signals
    if re.search(r"very peaty|heavily peated|intensely smoky|huge.*smoke|classic.*peat", low):
        scores["smoky"] = max(scores["smoky"] or 0, 85)
        scores["peaty"] = max(scores["peaty"] or 0, 85)

    if "lightly peated" in low:
        scores["peaty"] = 35
        scores["smoky"] = max(scores["smoky"] or 0, 35)

    return scores

def summarize_from_tags(prefix, text):
    tags = pick_tags(text)
    if not tags:
        return None
    selected = ", ".join(tags[:5])
    return f"{prefix} profile shows {selected} character."

def extract_profile(obj):
    target = obj.get("target")
    text = clean(obj.get("text")) or ""

    distillery_profile = is_distillery_profile(target, text)

    nose = extract_between(text, "NOSE", ["BODY", "PALATE", "FINISH", "GENERAL", "SCORE", "PRICE", "AGE", "ALC/VOL", "COLOR"])
    palate = extract_between(text, "PALATE", ["FINISH", "GENERAL", "SCORE", "BODY", "PRICE", "COLOR"])
    finish = extract_between(text, "FINISH", ["GENERAL", "SCORE", "BODY", "PRICE", "COLOR"])
    style = extract_between(text, "HOUSE STYLE", ["SCORE"])

    region = None
    m_region = re.search(r"\bREGION[:\s]+([A-Z][A-Za-z ]+)", text)
    if m_region:
        region = clean(m_region.group(1)).title()

    record_type = "distillery_profile" if distillery_profile else "whisky_profile"
    whisky_name = None if record_type == "distillery_profile" else infer_name(target, text)

    combined_for_radar = text
    scores = score_radar(combined_for_radar)
    tags = pick_tags(combined_for_radar)

    return {
        "record_type": record_type,
        "book_source": obj.get("book_source"),
        "source_page_or_section": None,
        "target": target,
        "distillery_name": target,
        "whisky_name": whisky_name,
        "age_statement": extract_age(text) if record_type == "whisky_profile" else None,
        "region": region,
        "abv": extract_abv(text) if record_type == "whisky_profile" else None,
        "cask_or_maturation": extract_between(text, "Matured", ["COLOR", "NOSE", "BODY", "PALATE", "FINISH"]),
        "nose_summary": summarize_from_tags("Nose", nose or "") if nose else None,
        "palate_summary": summarize_from_tags("Palate", palate or "") if palate else None,
        "finish_summary": summarize_from_tags("Finish", finish or "") if finish else None,
        "style_summary": summarize_from_tags("House style", style or text) if record_type == "distillery_profile" else None,
        "flavor_tags": tags,
        "radar_scores_0_100": scores,
        "confidence": "medium" if record_type == "whisky_profile" else "low",
        "copyright_safe": True,
        "import_status": "manual_review",
        "notes_for_manual_review": "Local rule-based extraction; review summaries and radar scores before staging import.",
        "_expression_block_id": obj.get("expression_block_id"),
        "_parent_chunk_id": obj.get("parent_chunk_id"),
        "_quality_score": obj.get("quality_score"),
        "_source_method": "local_rule_based_parser",
    }

rows = []
for line in IN_FILE.read_text(encoding="utf-8").splitlines():
    if not line.strip():
        continue
    rows.append(extract_profile(json.loads(line)))

with JSONL_OUT.open("w", encoding="utf-8") as f:
    for r in rows:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

fieldnames = [
    "record_type", "book_source", "target", "distillery_name", "whisky_name",
    "age_statement", "region", "abv", "cask_or_maturation",
    "nose_summary", "palate_summary", "finish_summary", "style_summary",
    "flavor_tags", "confidence", "import_status", "notes_for_manual_review",
    "_expression_block_id", "_parent_chunk_id", "_quality_score", "_source_method"
] + [f"score_{k}" for k in SCORE_KEYS]

with CSV_OUT.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    for r in rows:
        out = {k: r.get(k) for k in fieldnames if not k.startswith("score_")}
        out["flavor_tags"] = "|".join(r.get("flavor_tags") or [])
        for k in SCORE_KEYS:
            out[f"score_{k}"] = r["radar_scores_0_100"].get(k)
        writer.writerow(out)

counter = Counter(r["record_type"] for r in rows)
report = [
    "# 12N Local Rule-Based Book Profile Extraction Report",
    "",
    f"- input_blocks: {len(rows)}",
    f"- whisky_profile: {counter['whisky_profile']}",
    f"- distillery_profile: {counter['distillery_profile']}",
    "- production_db_modified: false",
    "- output_mode: review_only",
    "- gate: REVIEW",
    "",
    "## Outputs",
    f"- {JSONL_OUT}",
    f"- {CSV_OUT}",
]
REPORT_OUT.write_text("\n".join(report), encoding="utf-8")
GATE_OUT.write_text("REVIEW", encoding="utf-8")
GATE_OUT.write_text("
Estimated API Cost: $0.00
Actual API Cost: $0.00
Local Compute Used: Yes
Fully Local Execution: Yes
", encoding="utf-8")


print(f"WROTE {JSONL_OUT} records={len(rows)}")
print(f"WROTE {CSV_OUT}")
print(f"WROTE {REPORT_OUT}")
print(f"WROTE {GATE_OUT}")
print("gate=REVIEW")
