import argparse
import json
from collections import Counter
from pathlib import Path

REQUIRED_FIELDS = [
    "whisky_name", "distillery", "brand", "region", "country", "type",
    "abv", "proof", "age_statement", "cask_or_edition",
    "nose_summary", "palate_summary", "finish_summary",
    "flavour_tags", "radar_signals", "source_hint",
    "confidence", "missing_fields",
]

RADAR_FIELDS = ["smoky", "sherry", "fruity", "sweet", "spicy", "oaky", "maritime"]


def extract_json_objects(text):
    decoder = json.JSONDecoder()
    objects = []
    errors = []
    i = 0

    while i < len(text):
        start = text.find("{", i)
        if start == -1:
            break
        try:
            obj, end = decoder.raw_decode(text[start:])
            objects.append(obj)
            i = start + end
        except json.JSONDecodeError as e:
            errors.append({
                "position": start,
                "error": str(e),
                "snippet": text[start:start + 220].replace("\n", "\\n"),
            })
            i = start + 1

    return objects, errors


def to_number(value, integer=False):
    if value is None or value == "":
        return None
    try:
        n = float(value)
        if integer and n.is_integer():
            return int(n)
        return n
    except Exception:
        return None


def normalize_record(obj):
    rec = {field: obj.get(field) for field in REQUIRED_FIELDS}

    for field in [
        "whisky_name", "distillery", "brand", "region", "country", "type",
        "cask_or_edition", "nose_summary", "palate_summary",
        "finish_summary", "source_hint", "confidence",
    ]:
        if rec[field] == "":
            rec[field] = None

    rec["abv"] = to_number(rec["abv"])
    rec["proof"] = to_number(rec["proof"], integer=True)
    rec["age_statement"] = to_number(rec["age_statement"], integer=True)

    if not isinstance(rec["flavour_tags"], list):
        rec["flavour_tags"] = []
    rec["flavour_tags"] = [str(x).strip() for x in rec["flavour_tags"] if str(x).strip()]

    if not isinstance(rec["missing_fields"], list):
        rec["missing_fields"] = []
    rec["missing_fields"] = [str(x).strip() for x in rec["missing_fields"] if str(x).strip()]

    if not isinstance(rec["radar_signals"], dict):
        rec["radar_signals"] = {}

    radar = {}
    for key in RADAR_FIELDS:
        val = to_number(rec["radar_signals"].get(key))
        if val is not None:
            val = max(0, min(100, val))
            if float(val).is_integer():
                val = int(val)
        radar[key] = val

    rec["radar_signals"] = radar

    if rec["confidence"] not in ["high", "medium", "low"]:
        rec["confidence"] = "low"

    missing = set(rec["missing_fields"])
    for field in REQUIRED_FIELDS:
        if field == "missing_fields":
            continue
        val = rec.get(field)
        if val is None or val == [] or val == {}:
            missing.add(field)

    rec["missing_fields"] = sorted(missing)
    return rec


def record_key(rec):
    return (
        (rec.get("whisky_name") or "").strip().lower(),
        (rec.get("distillery") or "").strip().lower(),
        rec.get("age_statement"),
        rec.get("abv"),
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    report_path = Path(args.report)

    if not input_path.exists():
        raise FileNotFoundError(f"Input not found: {input_path}")

    text = input_path.read_text(encoding="utf-8-sig", errors="replace")

    raw_objects, parse_errors = extract_json_objects(text)

    normalized = []
    duplicates = []
    seen = set()

    for obj in raw_objects:
        if not isinstance(obj, dict):
            continue
        rec = normalize_record(obj)
        key = record_key(rec)
        if key in seen:
            duplicates.append(rec)
            continue
        seen.add(key)
        normalized.append(rec)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8", newline="\n") as f:
        for rec in normalized:
            f.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")

    confidence_counts = Counter(rec.get("confidence") for rec in normalized)
    type_counts = Counter(rec.get("type") or "NULL" for rec in normalized)
    country_counts = Counter(rec.get("country") or "NULL" for rec in normalized)

    missing_counts = Counter()
    for rec in normalized:
        for field in rec.get("missing_fields", []):
            missing_counts[field] += 1

    report = []
    report.append("# NotebookLM JSONL Batch Validation Report")
    report.append("")
    report.append(f"- Input: `{input_path}`")
    report.append(f"- Output: `{output_path}`")
    report.append(f"- Parsed objects: {len(raw_objects)}")
    report.append(f"- Clean records: {len(normalized)}")
    report.append(f"- Duplicates removed: {len(duplicates)}")
    report.append(f"- Parse errors: {len(parse_errors)}")
    report.append("")

    report.append("## Confidence")
    for k, v in confidence_counts.most_common():
        report.append(f"- {k}: {v}")
    report.append("")

    report.append("## Type Counts")
    for k, v in type_counts.most_common():
        report.append(f"- {k}: {v}")
    report.append("")

    report.append("## Country Counts")
    for k, v in country_counts.most_common():
        report.append(f"- {k}: {v}")
    report.append("")

    report.append("## Missing Field Counts")
    for k, v in missing_counts.most_common():
        report.append(f"- {k}: {v}")
    report.append("")

    report.append("## Low Confidence Records")
    for rec in normalized:
        if rec.get("confidence") == "low":
            report.append(f"- {rec.get('whisky_name')} | {rec.get('distillery')} | {rec.get('type')} | ABV={rec.get('abv')}")
    report.append("")

    report.append("## Records Without ABV")
    for rec in normalized:
        if rec.get("abv") is None:
            report.append(f"- {rec.get('whisky_name')} | {rec.get('distillery')} | {rec.get('type')}")
    report.append("")

    if parse_errors:
        report.append("## Parse Errors")
        for err in parse_errors[:50]:
            report.append(f"- pos={err['position']} error={err['error']} snippet=`{err['snippet']}`")
        report.append("")

    report_path.write_text("\n".join(report), encoding="utf-8")

    print(f"parsed_objects={len(raw_objects)}")
    print(f"clean_records={len(normalized)}")
    print(f"duplicates_removed={len(duplicates)}")
    print(f"parse_errors={len(parse_errors)}")
    print(f"output={output_path}")
    print(f"report={report_path}")


if __name__ == "__main__":
    main()
