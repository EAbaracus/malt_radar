import csv
import re
from pathlib import Path

IN = Path("data/output/whiskeymapper_no_match_candidates.csv")
OUT = Path("data/output/whiskeymapper_no_match_rescue_candidates.csv")
REPORT = Path("output/reports/190_whiskeymapper_no_match_rescue_report.md")

GENERIC_TERMS = {
    "port", "wood", "sherry", "cask", "finish", "finished", "edition", "release",
    "distillers", "classic", "cut", "single", "barrel", "batch", "bond", "bib",
    "bourbon", "rye", "malt", "whisky", "whiskey", "old", "yo", "year", "years",
    "all", "vintages", "releases", "batches", "collection"
}

STOP = GENERIC_TERMS | {
    "the", "and", "of", "a", "an", "scotch"
}

def norm(s):
    s = "" if s is None else str(s)
    s = s.lower()
    s = s.replace("’", "'").replace("‘", "'")
    s = s.replace("&", " and ")
    s = re.sub(r"\b(\d+)\s*(yo|y|yr|yrs|year|years)\b", r"\1", s)
    s = re.sub(r"\b(\d+)\s*year\s*old\b", r"\1", s)
    s = re.sub(r"\b1st\b", "first", s)
    s = re.sub(r"\b2nd\b", "second", s)
    s = re.sub(r"\b3rd\b", "third", s)
    s = re.sub(r"\b4th\b", "fourth", s)
    s = re.sub(r"\b5th\b", "fifth", s)
    s = re.sub(r"\b6th\b", "sixth", s)
    s = re.sub(r"\b7th\b", "seventh", s)
    s = re.sub(r"\b8th\b", "eighth", s)
    s = re.sub(r"\b9th\b", "ninth", s)
    s = s.replace("portwood", "port wood")
    s = s.replace("triplewood", "triple wood")
    s = s.replace("de luxe", "deluxe")
    s = s.replace("bottled in bond", "bib")
    s = re.sub(r"\(.*?\)", " ", s)
    s = re.sub(r"\ball releases\b|\ball batches\b|\ball editions\b|\ball vintages\b", " ", s)
    s = re.sub(r"[^a-z0-9']+", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def tokens(s):
    return [t for t in norm(s).split() if t not in STOP and (t.isdigit() or len(t) >= 3)]

def brand_token(s):
    for t in norm(s).split():
        if t not in GENERIC_TERMS and not t.isdigit() and len(t) >= 3:
            return t
    return ""

def overlap(a, b):
    aa = set(tokens(a))
    bb = set(tokens(b))
    if not aa or not bb:
        return 0.0, aa, bb
    return len(aa & bb) / len(aa | bb), aa, bb

rows = list(csv.DictReader(IN.open("r", encoding="utf-8-sig", newline="")))

out = []
for r in rows:
    wm = r.get("wm_name", "")
    mt = r.get("matched_name", "")
    score = float(r.get("match_score") or 0)

    ov, wm_tok, mt_tok = overlap(wm, mt)
    shared = wm_tok & mt_tok

    wm_brand = brand_token(wm)
    mt_brand = brand_token(mt)
    same_brand_family = bool(wm_brand and mt_brand and wm_brand == mt_brand)

    reasons = []

    if same_brand_family:
        reasons.append("same_brand_family")

    if same_brand_family and len(shared) >= 2:
        reasons.append("shared>=2_same_brand")

    if same_brand_family and ov >= 0.40:
        reasons.append("token_overlap>=0.40_same_brand")

    wm_n = norm(wm)
    mt_n = norm(mt)

    safe_terms = [
        "port wood",
        "triple wood",
        "deluxe",
        "bib",
        "harmony",
        "distillers edition",
        "classic cut",
        "vault edition",
        "heritage",
        "old scout",
        "midwinter",
    ]

    for term in safe_terms:
        if same_brand_family and term in wm_n and term in mt_n:
            reasons.append(f"safe_term_same_brand:{term}")

    if reasons and score >= 0.60:
        rescue_decision = "RESCUE_REVIEW"
    else:
        rescue_decision = "KEEP_NO_MATCH"

    r2 = dict(r)
    r2["normalized_wm_name"] = wm_n
    r2["normalized_matched_name"] = mt_n
    r2["rescue_token_overlap"] = round(ov, 4)
    r2["wm_brand_token"] = wm_brand
    r2["matched_brand_token"] = mt_brand
    r2["same_brand_family"] = str(same_brand_family).upper()
    r2["wm_tokens"] = "|".join(sorted(wm_tok))
    r2["matched_tokens"] = "|".join(sorted(mt_tok))
    r2["shared_tokens"] = "|".join(sorted(shared))
    r2["rescue_decision"] = rescue_decision
    r2["rescue_reason"] = ";".join(reasons) if reasons else "weak_or_cross_brand"
    out.append(r2)

OUT.parent.mkdir(parents=True, exist_ok=True)
REPORT.parent.mkdir(parents=True, exist_ok=True)

with OUT.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=list(out[0].keys()))
    writer.writeheader()
    writer.writerows(out)

rescue = [r for r in out if r["rescue_decision"] == "RESCUE_REVIEW"]
keep = [r for r in out if r["rescue_decision"] == "KEEP_NO_MATCH"]

lines = []
lines.append("# Whiskey Mapper No-Match Rescue Report")
lines.append("")
lines.append("## Safety")
lines.append("- Production DB write: NO")
lines.append("- Existing match CSV modified: NO")
lines.append("- This report only proposes rescue review candidates.")
lines.append("")
lines.append("## Counts")
lines.append(f"- Input NO_MATCH rows: {len(rows)}")
lines.append(f"- RESCUE_REVIEW: {len(rescue)}")
lines.append(f"- KEEP_NO_MATCH: {len(keep)}")
lines.append("")
lines.append("## Output")
lines.append(f"- `{OUT}`")
lines.append("")
lines.append("## RESCUE_REVIEW examples")
for r in rescue:
    lines.append(f"- `{r['wm_name']}` -> `{r['matched_name']}` score={r['match_score']} overlap={r['rescue_token_overlap']} reason={r['rescue_reason']}")
lines.append("")
lines.append("## KEEP_NO_MATCH examples")
for r in keep:
    lines.append(f"- `{r['wm_name']}` -> `{r['matched_name']}` score={r['match_score']} overlap={r['rescue_token_overlap']} reason={r['rescue_reason']}")

REPORT.write_text("\n".join(lines), encoding="utf-8")

print(REPORT)
print("RESCUE_REVIEW:", len(rescue))
print("KEEP_NO_MATCH:", len(keep))
