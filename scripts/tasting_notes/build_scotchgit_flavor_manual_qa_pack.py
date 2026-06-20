import csv
import random
import re
from collections import Counter
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
INPUT_CSV = BASE_DIR / "data" / "output" / "scotchgit_flavor_signal_preview.csv"
QA_CSV = BASE_DIR / "output" / "reports" / "201_scotchgit_flavor_manual_qa_pack.csv"
REPORT_PATH = BASE_DIR / "output" / "reports" / "202_scotchgit_flavor_manual_qa_report.md"

AXES = ["smoky", "sweet", "fruity", "spicy", "woody", "maritime", "sherry"]
QA_FIELDS = [
    "qa_group",
    "matched_master_whisky_id",
    "product_name",
    "smoky",
    "sweet",
    "fruity",
    "spicy",
    "woody",
    "maritime",
    "sherry",
    "signal_strength",
    "signal_basis",
    "confidence_note",
    "confidence_warning",
    "source_rows",
    "high_rows",
    "medium_rows",
    "source_url_count",
    "review_count_total",
    "qa_expected_profile",
    "qa_risk_note",
    "manual_decision",
]
EXPECTED_PATTERNS = {
    "islay_smoky_expected": {
        "terms": ["lagavulin", "laphroaig", "ardbeg", "caol ila", "bowmore"],
        "profile": "smoky/islay should be visible; check smoky and maritime balance.",
        "risk": "Expected Islay smoke may be underweighted if only region helper fired.",
    },
    "maritime_expected": {
        "terms": ["talisker", "oban", "springbank", "campbeltown"],
        "profile": "maritime/coastal should be visible.",
        "risk": "Maritime signal may be region-derived and low confidence.",
    },
    "sherry_expected": {
        "terms": ["aberlour", "macallan", "glendronach", "glenfarclas", "glengoyne"],
        "profile": "sherry/dried fruit profile should be visible when name indicates it.",
        "risk": "Region-only Speyside signals must not be treated as confirmed sherry.",
    },
    "sweet_fruity_expected": {
        "terms": ["glenmorangie", "balvenie", "glenlivet", "glenfiddich", "aberfeldy"],
        "profile": "sweet/fruity profile should be plausible.",
        "risk": "Sweet/fruity may be generic region helper rather than product-specific keyword.",
    },
}
SPICY_TERMS = ["spice", "spicy", "pepper", "cinnamon", "ginger"]


def clean(value):
    return str(value or "").strip()


def norm(value):
    return " ".join(clean(value).lower().split())


def fval(row, field):
    try:
        return float(clean(row.get(field)) or 0)
    except ValueError:
        return 0.0


def read_preview_rows():
    if not INPUT_CSV.exists():
        raise FileNotFoundError(f"Missing input CSV: {INPUT_CSV}")
    with INPUT_CSV.open("r", encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    return [row for row in rows if clean(row.get("production_import_status")) == "candidate_preview_only"]


def contains_any_name(row, terms):
    name = norm(row.get("product_name"))
    return any(term in name for term in terms)


def spicy_gap_candidate(row):
    name = norm(row.get("product_name"))
    return fval(row, "spicy") == 0.0 and any(re.search(rf"\b{re.escape(term)}\b", name) for term in SPICY_TERMS)


def qa_row(row, group, expected_profile, risk_note):
    out = {field: clean(row.get(field)) for field in QA_FIELDS if field not in {"qa_group", "qa_expected_profile", "qa_risk_note", "manual_decision"}}
    out["qa_group"] = group
    out["qa_expected_profile"] = expected_profile
    out["qa_risk_note"] = risk_note
    out["manual_decision"] = ""
    return out


def add_group(pack, used_ids, group, candidates, expected_profile, risk_note, limit=30):
    added = 0
    for row in candidates:
        whisky_id = clean(row.get("matched_master_whisky_id"))
        if not whisky_id or whisky_id in used_ids:
            continue
        pack.append(qa_row(row, group, expected_profile, risk_note))
        used_ids.add(whisky_id)
        added += 1
        if added >= limit:
            break


def build_pack(rows):
    pack = []
    used_ids = set()

    for group, config in EXPECTED_PATTERNS.items():
        candidates = [row for row in rows if contains_any_name(row, config["terms"])]
        candidates = sorted(candidates, key=lambda row: (fval(row, "signal_strength"), fval(row, "review_count_total")), reverse=True)
        add_group(pack, used_ids, group, candidates, config["profile"], config["risk"])

    add_group(
        pack,
        used_ids,
        "zero_signal_review",
        sorted([row for row in rows if fval(row, "signal_strength") == 0.0], key=lambda row: norm(row.get("product_name"))),
        "No axis signal expected from current keyword/region rules.",
        "Confirm whether zero signal is acceptable or needs future keyword expansion.",
    )

    add_group(
        pack,
        used_ids,
        "high_signal_review",
        sorted(rows, key=lambda row: fval(row, "signal_strength"), reverse=True),
        "Very strong flavor signal should be manually sanity checked.",
        "High signal may be keyword-heavy or duplicated across axes.",
    )

    add_group(
        pack,
        used_ids,
        "region_only_low_confidence_review",
        sorted([row for row in rows if clean(row.get("signal_basis")) == "region_only"], key=lambda row: fval(row, "signal_strength"), reverse=True),
        "Only low-confidence regional helper signal is present.",
        "Do not approve as product-specific flavor without manual support.",
    )

    add_group(
        pack,
        used_ids,
        "keyword_plus_region_review",
        sorted([row for row in rows if clean(row.get("signal_basis")) == "keyword_plus_region"], key=lambda row: fval(row, "signal_strength"), reverse=True),
        "Keyword signal is present with capped regional helper.",
        "Check whether keyword signal reflects product flavor rather than bottling name noise.",
    )

    add_group(
        pack,
        used_ids,
        "suspicious_spicy_gap",
        sorted([row for row in rows if spicy_gap_candidate(row)], key=lambda row: norm(row.get("product_name"))),
        "Product name suggests spice but spicy axis is zero.",
        "Potential keyword parsing gap or false expectation.",
    )

    rng = random.Random(42)
    random_candidates = list(rows)
    rng.shuffle(random_candidates)
    add_group(
        pack,
        used_ids,
        "random_sample",
        random_candidates,
        "Deterministic broad sample for manual QA.",
        "General spot-check across segments and signal bases.",
    )

    return pack


def write_csv(rows):
    QA_CSV.parent.mkdir(parents=True, exist_ok=True)
    with QA_CSV.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=QA_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_report(preview_rows, qa_rows):
    group_counts = Counter(row["qa_group"] for row in qa_rows)
    zero_signal_count = sum(1 for row in preview_rows if fval(row, "signal_strength") == 0.0)
    region_only_count = sum(1 for row in preview_rows if clean(row.get("signal_basis")) == "region_only")
    keyword_plus_region_count = sum(1 for row in preview_rows if clean(row.get("signal_basis")) == "keyword_plus_region")
    spicy_coverage = sum(1 for row in preview_rows if fval(row, "spicy") > 0.0)
    duplicate_ids = len(qa_rows) - len({row["matched_master_whisky_id"] for row in qa_rows})

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with REPORT_PATH.open("w", encoding="utf-8") as fh:
        fh.write("# ScotchGit Flavor Manual QA Report\n\n")
        fh.write("## Decision\n\n")
        fh.write("- QA pack generation GO/NO-GO: **GO**\n")
        fh.write("- Production import: **NO-GO**\n")
        fh.write("- QA pack is for manual review only; no application integration or DB write was performed.\n\n")

        fh.write("## Counts\n\n")
        fh.write(f"- QA pack total rows: {len(qa_rows)}\n")
        fh.write(f"- duplicate matched_master_whisky_id rows in QA pack: {duplicate_ids}\n")
        fh.write(f"- zero signal count in preview: {zero_signal_count}\n")
        fh.write(f"- region_only row count in preview: {region_only_count}\n")
        fh.write(f"- keyword_plus_region row count in preview: {keyword_plus_region_count}\n")
        fh.write(f"- spicy coverage count in preview: {spicy_coverage}\n\n")

        fh.write("## Group Counts\n\n")
        for group in [
            "islay_smoky_expected",
            "maritime_expected",
            "sherry_expected",
            "sweet_fruity_expected",
            "zero_signal_review",
            "high_signal_review",
            "region_only_low_confidence_review",
            "keyword_plus_region_review",
            "suspicious_spicy_gap",
            "random_sample",
        ]:
            fh.write(f"- {group}: {group_counts.get(group, 0)}\n")
        fh.write("\n")

        fh.write("## Spicy Coverage Warning\n\n")
        fh.write(f"- Spicy coverage remains low at {spicy_coverage}; no synthetic spicy signal was generated.\n\n")

        fh.write("## Manual QA Production Import Criteria\n\n")
        fh.write("- Keep production import NO-GO until manual reviewers mark acceptable rows in `manual_decision`.\n")
        fh.write("- Region-only rows require independent approval before use as product flavor signals.\n")
        fh.write("- Zero-signal rows should remain excluded unless keyword mapping is intentionally expanded.\n")
        fh.write("- Suspicious spicy gap rows should be reviewed before changing keyword rules.\n")
        fh.write("- Only `candidate_preview_only` rows may be considered, and approval must happen in a later gated phase.\n\n")

        fh.write("## Output\n\n")
        fh.write(f"- `{QA_CSV.as_posix()}`\n")


def main():
    preview_rows = read_preview_rows()
    qa_rows = build_pack(preview_rows)
    write_csv(qa_rows)
    write_report(preview_rows, qa_rows)
    print(f"Manual QA pack rows: {len(qa_rows)}")
    print("QA pack generation decision: GO")
    print("Production import decision: NO-GO")
    print(f"Report written: {REPORT_PATH}")


if __name__ == "__main__":
    main()
