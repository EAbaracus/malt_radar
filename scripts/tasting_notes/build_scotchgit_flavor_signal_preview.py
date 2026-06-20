import csv
import hashlib
import re
from collections import Counter, defaultdict
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
HIGH_CSV = BASE_DIR / "data" / "output" / "scotchgit_candidates_high_confidence.csv"
MEDIUM_CSV = BASE_DIR / "data" / "output" / "scotchgit_candidates_medium_confidence.csv"
DB_PATH = BASE_DIR / "output" / "import" / "production.db"
OUTPUT_CSV = BASE_DIR / "data" / "output" / "scotchgit_flavor_signal_preview.csv"
REPORT_PATH = BASE_DIR / "output" / "reports" / "196_scotchgit_7_axis_flavor_signal_preview.md"
SAMPLES_CSV = BASE_DIR / "output" / "reports" / "197_scotchgit_flavor_signal_samples.csv"
FIX_REPORT_PATH = BASE_DIR / "output" / "reports" / "200_scotchgit_flavor_signal_normalization_fix_report.md"

AXES = ["smoky", "sweet", "fruity", "spicy", "woody", "maritime", "sherry"]
KEYWORDS = {
    "smoky": ["smoke", "smoky", "peat", "peated", "bonfire", "ash", "medicinal"],
    "sweet": ["sweet", "honey", "vanilla", "caramel", "toffee", "sugar", "syrup"],
    "fruity": ["fruit", "fruity", "apple", "pear", "citrus", "orange", "lemon", "raisin", "fig", "date", "berry"],
    "spicy": ["spice", "spicy", "pepper", "cinnamon", "nutmeg", "ginger", "clove", "chili"],
    "woody": ["oak", "wood", "woody", "leather", "tobacco", "dry", "tannin"],
    "maritime": ["maritime", "sea", "seaweed", "salt", "salty", "brine", "iodine", "coastal"],
    "sherry": ["sherry", "oloroso", "px", "raisin", "fig", "date", "wine", "dark chocolate", "abunadh"],
}
REGION_HELPERS = {
    "islay": {"smoky": 0.20, "maritime": 0.10},
    "island": {"maritime": 0.15, "smoky": 0.05},
    "campbeltown": {"maritime": 0.08, "woody": 0.05},
    "speyside": {"fruity": 0.08, "sweet": 0.08, "sherry": 0.05},
    "highland": {"woody": 0.05, "fruity": 0.04},
}
OUTPUT_FIELDS = [
    "matched_master_whisky_id",
    "product_name",
    "product_name_variants",
    "source_rows",
    "high_rows",
    "medium_rows",
    "source_url_count",
    "review_count_total",
    "avg_rating",
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
    "production_import_status",
]
SAMPLE_FIELDS = [
    "sample_type",
    "matched_master_whisky_id",
    "product_name",
    "product_name_variants",
    "source_rows",
    "high_rows",
    "medium_rows",
    "review_count_total",
    "avg_rating",
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
]


def clean(value):
    return str(value or "").strip()


def norm(value):
    return " ".join(clean(value).lower().split())


def to_int(value, default=0):
    try:
        return int(float(clean(value)))
    except ValueError:
        return default


def to_float(value):
    try:
        text = clean(value)
        return float(text) if text else None
    except ValueError:
        return None


def sha256_file(path):
    if not path.exists():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_segment(path, segment):
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        rows = []
        for row in csv.DictReader(fh):
            row = dict(row)
            row["_segment"] = segment
            if clean(row.get("matched_master_whisky_id")):
                rows.append(row)
        return rows


def contains_keyword(text, keyword):
    escaped = re.escape(keyword)
    if " " in keyword:
        return re.search(rf"(?<![a-z0-9]){escaped}(?![a-z0-9])", text) is not None
    if re.search(rf"(?<![a-z0-9]){escaped}(?:ed|y|s)?(?![a-z0-9])", text):
        return True
    compact_text = re.sub(r"[^a-z0-9]+", "", text)
    compact_keyword = re.sub(r"[^a-z0-9]+", "", keyword)
    return bool(compact_keyword and compact_keyword in compact_text)


def row_weight(row):
    base = 1.0 if row["_segment"] == "high" else 0.35
    review_count = to_int(row.get("review_count"), 0)
    return base * (1 + min(review_count, 5) / 10)


def row_signals(row):
    text = norm(f"{row.get('product_name', '')} {row.get('normalized_product_name', '')}")
    weight = row_weight(row)
    keyword_values = {axis: 0.0 for axis in AXES}
    region_values = {axis: 0.0 for axis in AXES}
    keyword_hit = False
    region_hit = False

    for axis, keywords in KEYWORDS.items():
        hits = sum(1 for keyword in keywords if contains_keyword(text, keyword))
        if hits:
            keyword_hit = True
            keyword_values[axis] += weight * hits

    region = norm(row.get("region"))
    if region in REGION_HELPERS:
        region_hit = True
        for axis, value in REGION_HELPERS[region].items():
            region_values[axis] += weight * value

    return keyword_values, region_values, keyword_hit, region_hit


def normalize_axis_values(keyword_raw, region_raw, signal_basis):
    keyword_max = max(keyword_raw.values()) if keyword_raw else 0.0
    if keyword_max > 0:
        keyword_norm = {axis: keyword_raw[axis] / keyword_max for axis in AXES}
    else:
        keyword_norm = {axis: 0.0 for axis in AXES}

    if signal_basis == "keyword_only":
        return {axis: round(keyword_norm[axis], 4) for axis in AXES}

    if signal_basis == "region_only":
        region_sum = sum(region_raw.values())
        region_max = max(region_raw.values()) if region_raw else 0.0
        if region_sum <= 0 or region_max <= 0:
            return {axis: 0.0 for axis in AXES}
        scale = min(1.0, 0.25 / region_max, 0.75 / region_sum)
        return {axis: round(region_raw[axis] * scale, 4) for axis in AXES}

    if signal_basis == "keyword_plus_region":
        region_sum = sum(region_raw.values())
        keyword_sum = sum(keyword_norm.values())
        if region_sum > 0 and keyword_sum > 0:
            # R <= 20% of final total, equivalent to R <= 25% of keyword total.
            max_region_sum = keyword_sum * 0.25
            scale = min(1.0, max_region_sum / region_sum)
        else:
            scale = 0.0
        return {axis: round(min(1.0, keyword_norm[axis] + region_raw[axis] * scale), 4) for axis in AXES}

    return {axis: 0.0 for axis in AXES}


def confidence_warning(signal_basis, confidence_note, signal_strength):
    warnings = []
    if signal_strength == 0:
        warnings.append("zero_signal")
    if signal_basis == "region_only":
        warnings.append("region_only_low_confidence")
    if signal_basis in {"keyword_only", "keyword_plus_region"}:
        warnings.append("keyword_signal_present")
    if confidence_note == "medium_only":
        warnings.append("medium_only_low_weight")
    return "|".join(warnings)


def representative_name(rows):
    counts = Counter(clean(row.get("product_name")) for row in rows if clean(row.get("product_name")))
    max_reviews = defaultdict(int)
    for row in rows:
        name = clean(row.get("product_name"))
        max_reviews[name] = max(max_reviews[name], to_int(row.get("review_count"), 0))
    return sorted(counts, key=lambda name: (-counts[name], -max_reviews[name], name))[0] if counts else ""


def aggregate(rows):
    grouped = defaultdict(list)
    for row in rows:
        grouped[clean(row.get("matched_master_whisky_id"))].append(row)

    output_rows = []
    variant_examples = []
    for whisky_id, whisky_rows in sorted(grouped.items()):
        keyword_raw = {axis: 0.0 for axis in AXES}
        region_raw = {axis: 0.0 for axis in AXES}
        any_keyword = False
        any_region = False
        weighted_rating_sum = 0.0
        rating_weight_sum = 0
        rating_values = []

        for row in whisky_rows:
            keyword_signals, region_signals, keyword_hit, region_hit = row_signals(row)
            any_keyword = any_keyword or keyword_hit
            any_region = any_region or region_hit
            for axis in AXES:
                keyword_raw[axis] += keyword_signals[axis]
                region_raw[axis] += region_signals[axis]

            avg_rating = to_float(row.get("avg_rating"))
            review_count = to_int(row.get("review_count"), 0)
            if avg_rating is not None and review_count > 0:
                weighted_rating_sum += avg_rating * review_count
                rating_weight_sum += review_count
            elif avg_rating is not None:
                rating_values.append(avg_rating)

        if rating_weight_sum:
            avg_rating = round(weighted_rating_sum / rating_weight_sum, 2)
        elif rating_values:
            avg_rating = round(sum(rating_values) / len(rating_values), 2)
        else:
            avg_rating = ""

        high_rows = sum(1 for row in whisky_rows if row["_segment"] == "high")
        medium_rows = sum(1 for row in whisky_rows if row["_segment"] == "medium")
        product_variants = {clean(row.get("product_name")) for row in whisky_rows if clean(row.get("product_name"))}
        if len(product_variants) > 1:
            variant_examples.append((whisky_id, sorted(product_variants), len(whisky_rows)))

        if any_keyword and any_region:
            signal_basis = "keyword_plus_region"
        elif any_keyword:
            signal_basis = "keyword_only"
        elif any_region:
            signal_basis = "region_only"
        else:
            signal_basis = "none"

        axis_norm = normalize_axis_values(keyword_raw, region_raw, signal_basis)

        if high_rows and medium_rows:
            confidence_note = "high_plus_medium"
        elif high_rows:
            confidence_note = "high_only"
        else:
            confidence_note = "medium_only"

        strength = round(sum(axis_norm.values()), 4)
        warning = confidence_warning(signal_basis, confidence_note, strength)

        output = {
            "matched_master_whisky_id": whisky_id,
            "product_name": representative_name(whisky_rows),
            "product_name_variants": len(product_variants),
            "source_rows": len(whisky_rows),
            "high_rows": high_rows,
            "medium_rows": medium_rows,
            "source_url_count": len({clean(row.get("source_url")) for row in whisky_rows if clean(row.get("source_url"))}),
            "review_count_total": sum(to_int(row.get("review_count"), 0) for row in whisky_rows),
            "avg_rating": avg_rating,
            "signal_strength": strength,
            "signal_basis": signal_basis,
            "confidence_note": confidence_note,
            "confidence_warning": warning,
            "production_import_status": "candidate_preview_only",
        }
        output.update(axis_norm)
        output_rows.append(output)

    return output_rows, variant_examples


def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def sample_rows(preview_rows):
    samples = []
    for axis in ("smoky", "sherry", "maritime", "fruity"):
        for row in sorted(preview_rows, key=lambda item: (float(item[axis]), float(item["signal_strength"])), reverse=True)[:20]:
            sample = dict(row)
            sample["sample_type"] = f"top_{axis}"
            samples.append(sample)
    zero_rows = [row for row in preview_rows if float(row["signal_strength"]) == 0.0]
    for row in zero_rows[:20]:
        sample = dict(row)
        sample["sample_type"] = "zero_signal"
        samples.append(sample)
    return samples


def write_report(preview_rows, variant_examples, db_changed, generation_go):
    confidence_counts = Counter(row["confidence_note"] for row in preview_rows)
    warning_counts = Counter()
    for row in preview_rows:
        for warning in clean(row.get("confidence_warning")).split("|"):
            if warning:
                warning_counts[warning] += 1
    zero_signal_count = sum(1 for row in preview_rows if float(row["signal_strength"]) == 0.0)
    axis_coverage = {axis: sum(1 for row in preview_rows if float(row[axis]) > 0.0) for axis in AXES}

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with REPORT_PATH.open("w", encoding="utf-8") as fh:
        fh.write("# ScotchGit 7-Axis Flavor Signal Preview\n\n")
        fh.write("## Decision\n\n")
        fh.write(f"- preview generation GO/NO-GO: **{'GO' if generation_go else 'NO-GO'}**\n")
        fh.write("- production import status: **NO-GO**\n")
        fh.write(f"- production.db changed: {'YES' if db_changed else 'NO'}\n")
        fh.write("- output rows are `candidate_preview_only`.\n\n")

        fh.write("## Counts\n\n")
        fh.write(f"- total preview whisky count: {len(preview_rows)}\n")
        fh.write(f"- high_only count: {confidence_counts.get('high_only', 0)}\n")
        fh.write(f"- high_plus_medium count: {confidence_counts.get('high_plus_medium', 0)}\n")
        fh.write(f"- medium_only count: {confidence_counts.get('medium_only', 0)}\n")
        fh.write(f"- zero signal count: {zero_signal_count}\n\n")

        fh.write("## Axis Coverage Counts\n\n")
        for axis in AXES:
            fh.write(f"- {axis}: {axis_coverage[axis]}\n")
        fh.write("\n")

        fh.write("## Confidence Warnings\n\n")
        if warning_counts:
            for warning, count in warning_counts.most_common():
                fh.write(f"- {warning}: {count}\n")
        else:
            fh.write("- None\n")
        fh.write("\n")

        spicy_count = axis_coverage["spicy"]
        if spicy_count < max(1, int(len(preview_rows) * 0.02)):
            fh.write("## Coverage Warning\n\n")
            fh.write(f"- spicy coverage is low ({spicy_count}); no synthetic spicy signal was generated.\n\n")

        for axis in ("smoky", "sherry", "maritime", "fruity"):
            fh.write(f"## Top 20 {axis.title()}\n\n")
            for row in sorted(preview_rows, key=lambda item: (float(item[axis]), float(item["signal_strength"])), reverse=True)[:20]:
                fh.write(
                    f"- {row['product_name']} | id={row['matched_master_whisky_id']} | "
                    f"{axis}={row[axis]} | strength={row['signal_strength']} | {row['confidence_note']}\n"
                )
            fh.write("\n")

        fh.write("## Duplicate Variant Examples\n\n")
        if variant_examples:
            for whisky_id, variants, source_rows in sorted(variant_examples, key=lambda item: (-len(item[1]), item[0]))[:20]:
                fh.write(f"- {whisky_id} | variants={len(variants)} | source_rows={source_rows} | names={'; '.join(variants[:8])}\n")
        else:
            fh.write("- None\n")
        fh.write("\n## Output Files\n\n")
        fh.write(f"- `{OUTPUT_CSV.as_posix()}`\n")
        fh.write(f"- `{SAMPLES_CSV.as_posix()}`\n")


def write_fix_report(preview_rows, db_changed):
    region_only_rows = [row for row in preview_rows if row["signal_basis"] == "region_only"]
    region_only_max_axis = max((max(float(row[axis]) for axis in AXES) for row in region_only_rows), default=0.0)
    region_only_max_strength = max((float(row["signal_strength"]) for row in region_only_rows), default=0.0)
    macallan_rows = [row for row in preview_rows if norm(row["product_name"]) == "macallan 12 double cask"]
    abunadh_rows = [row for row in preview_rows if "bunadh" in norm(row["product_name"])]

    with FIX_REPORT_PATH.open("w", encoding="utf-8") as fh:
        fh.write("# ScotchGit Flavor Signal Normalization Fix Report\n\n")
        fh.write("## Scope\n\n")
        fh.write("- Keyword and region signals are now tracked separately.\n")
        fh.write("- Per-whisky max normalization is applied only to keyword scores.\n")
        fh.write("- Region-only rows are capped at max axis <= 0.25 and signal_strength <= 0.75.\n")
        fh.write("- Keyword plus region rows cap total region contribution to 20% of final score.\n\n")
        fh.write("## Validation\n\n")
        fh.write(f"- region_only rows: {len(region_only_rows)}\n")
        fh.write(f"- region_only max axis: {round(region_only_max_axis, 4)}\n")
        fh.write(f"- region_only max signal_strength: {round(region_only_max_strength, 4)}\n")
        fh.write(f"- production.db changed: {'YES' if db_changed else 'NO'}\n\n")
        fh.write("## Named Checks\n\n")
        if macallan_rows:
            for row in macallan_rows:
                fh.write(
                    f"- Macallan 12 Double Cask | basis={row['signal_basis']} | "
                    f"sweet={row['sweet']} | fruity={row['fruity']} | warning={row['confidence_warning']}\n"
                )
        else:
            fh.write("- Macallan 12 Double Cask not present in preview output.\n")
        if abunadh_rows:
            for row in abunadh_rows[:10]:
                fh.write(
                    f"- {row['product_name']} | basis={row['signal_basis']} | "
                    f"sherry={row['sherry']} | fruity={row['fruity']} | warning={row['confidence_warning']}\n"
                )
        else:
            fh.write("- Aberlour A'bunadh rows not present in preview output.\n")


def main():
    db_hash_before = sha256_file(DB_PATH)
    high_rows = read_segment(HIGH_CSV, "high")
    medium_rows = read_segment(MEDIUM_CSV, "medium")
    preview_rows, variant_examples = aggregate(high_rows + medium_rows)
    write_csv(OUTPUT_CSV, preview_rows, OUTPUT_FIELDS)
    write_csv(SAMPLES_CSV, sample_rows(preview_rows), SAMPLE_FIELDS)
    db_hash_after = sha256_file(DB_PATH)
    db_changed = bool(db_hash_before and db_hash_after and db_hash_before != db_hash_after)
    generation_go = OUTPUT_CSV.exists() and not db_changed
    write_report(preview_rows, variant_examples, db_changed, generation_go)
    write_fix_report(preview_rows, db_changed)

    print(f"Flavor signal preview rows: {len(preview_rows)}")
    print(f"Preview generation decision: {'GO' if generation_go else 'NO-GO'}")
    print(f"Production import decision: NO-GO")
    print(f"Report written: {REPORT_PATH}")
    print(f"Fix report written: {FIX_REPORT_PATH}")


if __name__ == "__main__":
    main()
