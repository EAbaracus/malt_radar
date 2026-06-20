import csv
import re
from difflib import SequenceMatcher
from pathlib import Path
from collections import Counter, defaultdict

WM_PATH = Path("data/output/whiskeymapper_joined_candidates.csv")
OUT = Path("data/output/whiskeymapper_malt_radar_match_candidates.csv")
REPORT = Path("output/reports/188_whiskeymapper_malt_radar_match_report.md")

MASTER_CANDIDATES = [
    Path("backend/data/whisky_database_merged_max.csv"),
    Path("data/output/whisky_database_merged_max.csv"),
    Path("output/import/whisky_database_merged_max.csv"),
    Path("data/output/60_FINAL_import_ready_whiskies_distillery_patched.csv"),
    Path("output/final/60_FINAL_import_ready_whiskies_distillery_patched.csv"),
    Path("data/output/whisky_products.csv"),
    Path("data/input/whisky_products.csv"),
]

STOPWORDS = {
    "the", "and", "of", "a", "an", "single", "malt", "whisky", "whiskey",
    "scotch", "year", "old", "yo", "proof", "cask", "finish", "finished"
}

def norm(s):
    s = "" if s is None else str(s)
    s = s.lower()
    s = s.replace("&", " and ")

    # age normalization
    s = re.sub(r"\b(\d+)\s*(yo|y|yr|yrs|year|years)\b", r"\1", s)
    s = re.sub(r"\b(\d+)\s*year\s*old\b", r"\1", s)

    # common variants
    s = re.sub(r"\bnon[- ]chill[- ]filtered\b", " non chill filtered ", s)
    s = re.sub(r"\bsmall batch bourbon\b", " small batch ", s)
    s = re.sub(r"\bfull proof bourbon\b", " full proof ", s)
    s = re.sub(r"\bport finished bourbon\b", " port finish ", s)
    s = re.sub(r"\bfinished\b", " finish ", s)
    s = re.sub(r"\bbourbon\b", " ", s)

    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def tokens(s):
    out = []
    for t in norm(s).split():
        if t in STOPWORDS:
            continue
        if t.isdigit():
            out.append(t)
        elif len(t) >= 3:
            out.append(t)
    return out

def ratio(a, b):
    a = norm(a)
    b = norm(b)
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()

def token_bonus(a, b):
    aa = set(tokens(a))
    bb = set(tokens(b))
    if not aa or not bb:
        return 0.0
    return len(aa & bb) / len(aa | bb)

def pick(row, candidates):
    lower = {k.lower(): k for k in row.keys()}
    for c in candidates:
        key = lower.get(c.lower())
        if key is not None:
            return row.get(key, "")
    return ""

def load_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

master_path = None
for p in MASTER_CANDIDATES:
    if p.exists():
        master_path = p
        break

if master_path is None:
    raise RuntimeError("Master CSV not found.")

print("master_path:", master_path, flush=True)

wm_rows = load_csv(WM_PATH)
master_rows = load_csv(master_path)

master_index = []
token_index = defaultdict(set)

for i, row in enumerate(master_rows):
    product_id = pick(row, ["record_id", "id", "product_id", "whisky_id", "whiskey_id"])
    name = pick(row, ["canonical_name", "whisky_name", "name", "product_name", "whiskey_name", "title"])
    distillery = pick(row, ["distillery", "distillery_name", "brand", "brand_or_company"])
    category = pick(row, ["category", "type", "style", "class"])
    region = pick(row, ["region"])
    country = pick(row, ["country"])

    if not name:
        continue

    item = {
        "master_row_index": i,
        "product_id": product_id,
        "name": name,
        "distillery": distillery,
        "category": category,
        "region": region,
        "country": country,
    }

    idx = len(master_index)
    master_index.append(item)

    for t in set(tokens(name) + tokens(distillery)):
        token_index[t].add(idx)

print("wm_rows:", len(wm_rows), flush=True)
print("master_rows:", len(master_rows), flush=True)
print("master_index:", len(master_index), flush=True)

results = []

for n, wm in enumerate(wm_rows, start=1):
    if n % 50 == 0:
        print(f"progress: {n}/{len(wm_rows)}", flush=True)

    wm_name = wm.get("whiskey_name", "")
    wm_distillery = wm.get("distillery", "")
    wm_brand = wm.get("brand", "")
    wm_type = wm.get("category_type", "")

    candidate_ids = set()
    for t in set(tokens(wm_name) + tokens(wm_distillery) + tokens(wm_brand)):
        candidate_ids.update(token_index.get(t, set()))

    if not candidate_ids:
        candidate_ids = set(range(min(len(master_index), 500)))

    if len(candidate_ids) > 1000:
        candidate_ids = set(list(candidate_ids)[:1000])

    scored = []

    for idx in candidate_ids:
        m = master_index[idx]

        name_score = ratio(wm_name, m["name"])
        token_score = token_bonus(wm_name, m["name"])
        dist_score = max(
            ratio(wm_distillery, m["distillery"]),
            ratio(wm_brand, m["distillery"]),
            ratio(wm_distillery, m["name"]),
        )

        final_score = (name_score * 0.66) + (token_score * 0.24) + (dist_score * 0.10)

        wm_norm = norm(wm_name)
        master_norm = norm(m["name"])
        wm_tok = set(tokens(wm_name))
        master_tok = set(tokens(m["name"]))

        if wm_norm == master_norm:
            final_score = max(final_score, 0.99)

        # Example: "1792 Full Proof" inside "Barton 1792 Full Proof Bourbon"
        if wm_norm and master_norm and (wm_norm in master_norm or master_norm in wm_norm):
            final_score = max(final_score, 0.94)

        # Example: "Aberlour 10" vs "Aberlour 10yo"
        if wm_tok and wm_tok.issubset(master_tok):
            final_score = max(final_score, 0.91)

        # Same distillery/brand + all meaningful name tokens overlap
        if wm_tok and wm_tok.issubset(master_tok) and dist_score >= 0.70:
            final_score = max(final_score, 0.93)

        scored.append((final_score, name_score, token_score, dist_score, m))

    scored.sort(key=lambda x: x[0], reverse=True)
    best = scored[0] if scored else None
    second = scored[1] if len(scored) > 1 else None

    if not best:
        results.append({
            "source": "whiskeymapper",
            "wm_row_index": wm.get("row_index", ""),
            "wm_name": wm_name,
            "wm_distillery": wm_distillery,
            "wm_brand": wm_brand,
            "wm_type": wm_type,
            "wm_avg_score": wm.get("avg_score", ""),
            "wm_review_count": wm.get("review_count", ""),
            "wm_component_1": wm.get("component_1", ""),
            "wm_component_2": wm.get("component_2", ""),
            "wm_component_3": wm.get("component_3", ""),
            "matched_product_id": "",
            "matched_name": "",
            "matched_distillery": "",
            "matched_category": "",
            "matched_region": "",
            "matched_country": "",
            "match_score": 0,
            "name_score": 0,
            "token_score": 0,
            "distillery_score": 0,
            "second_best_score": "",
            "score_margin": 0,
            "decision": "NO_MATCH",
            "reason": "no candidates",
        })
        continue

    final_score, name_score, token_score, dist_score, m = best
    margin = final_score - second[0] if second else final_score

    if final_score >= 0.92 and margin >= 0.03:
        decision = "HIGH"
    elif final_score >= 0.84:
        decision = "REVIEW"
    else:
        decision = "NO_MATCH"

    results.append({
        "source": "whiskeymapper",
        "wm_row_index": wm.get("row_index", ""),
        "wm_name": wm_name,
        "wm_distillery": wm_distillery,
        "wm_brand": wm_brand,
        "wm_type": wm_type,
        "wm_avg_score": wm.get("avg_score", ""),
        "wm_review_count": wm.get("review_count", ""),
        "wm_component_1": wm.get("component_1", ""),
        "wm_component_2": wm.get("component_2", ""),
        "wm_component_3": wm.get("component_3", ""),
        "matched_product_id": m["product_id"],
        "matched_name": m["name"],
        "matched_distillery": m["distillery"],
        "matched_category": m["category"],
        "matched_region": m["region"],
        "matched_country": m["country"],
        "match_score": round(final_score, 4),
        "name_score": round(name_score, 4),
        "token_score": round(token_score, 4),
        "distillery_score": round(dist_score, 4),
        "second_best_score": round(second[0], 4) if second else "",
        "score_margin": round(margin, 4),
        "decision": decision,
        "reason": f"name={name_score:.3f}; token={token_score:.3f}; distillery={dist_score:.3f}; margin={margin:.3f}",
    })

OUT.parent.mkdir(parents=True, exist_ok=True)
REPORT.parent.mkdir(parents=True, exist_ok=True)

with OUT.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
    writer.writeheader()
    writer.writerows(results)

counts = Counter(r["decision"] for r in results)

report = []
report.append("# Whiskey Mapper Malt Radar Match Dry Run Report")
report.append("")
report.append("## Safety")
report.append("- Production DB write: NO")
report.append("- Raw Whiskey Mapper data modified: NO")
report.append("- Malt Radar master modified: NO")
report.append("")
report.append("## Inputs")
report.append(f"- Whiskey Mapper joined candidates: `{WM_PATH}`")
report.append(f"- Malt Radar master CSV: `{master_path}`")
report.append("")
report.append("## Counts")
report.append(f"- Whiskey Mapper rows: {len(wm_rows)}")
report.append(f"- Malt Radar master rows indexed: {len(master_index)}")
report.append(f"- Output match rows: {len(results)}")
report.append("")
report.append("## Decisions")
for k in ["HIGH", "REVIEW", "NO_MATCH"]:
    report.append(f"- {k}: {counts.get(k, 0)}")
report.append("")
report.append("## Output")
report.append(f"- `{OUT}`")
report.append("")
report.append("## Decision rules")
report.append("- HIGH: score >= 0.92 and margin >= 0.03")
report.append("- REVIEW: score >= 0.84")
report.append("- NO_MATCH: below review threshold")
report.append("")
report.append("## Top HIGH examples")
for r in [x for x in results if x["decision"] == "HIGH"][:10]:
    report.append(f"- `{r['wm_name']}` -> `{r['matched_name']}` score={r['match_score']}")
report.append("")
report.append("## Top REVIEW examples")
for r in [x for x in results if x["decision"] == "REVIEW"][:10]:
    report.append(f"- `{r['wm_name']}` -> `{r['matched_name']}` score={r['match_score']}")
report.append("")
report.append("## NO_MATCH examples")
for r in [x for x in results if x["decision"] == "NO_MATCH"][:10]:
    report.append(f"- `{r['wm_name']}` -> `{r['matched_name']}` score={r['match_score']}")

REPORT.write_text("\n".join(report), encoding="utf-8")

print("results:", len(results), flush=True)
print("decisions:", dict(counts), flush=True)
print(OUT, flush=True)
print(REPORT, flush=True)
