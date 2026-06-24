import argparse
import csv
import json
from pathlib import Path

import yaml


ENTITY_DIRS = {
    "distilleries": "data/distilleries",
    "production_lines": "data/production_lines",
    "bottlings": "data/bottlings",
    "concepts": "data/concepts",
    "bottlers": "data/bottlers",
    "casks": "data/casks",
    "suppliers": "data/suppliers",
}


def as_json(value):
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    return str(value)


def load_yaml(path):
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def extract_entity_files(repo: Path, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = []

    for entity_type, rel in ENTITY_DIRS.items():
        root = repo / rel
        rows = []

        if root.exists():
            for path in sorted(root.rglob("*")):
                if path.suffix.lower() not in [".yml", ".yaml"]:
                    continue

                data = load_yaml(path)
                if not isinstance(data, dict):
                    continue

                row = {
                    "entity_type": entity_type,
                    "source_path": str(path.relative_to(repo)),
                    "source_system": "structured_whisky_source_01",
                    "id": data.get("id", ""),
                    "name": data.get("name") or data.get("title") or "",
                    "raw_json": json.dumps(data, ensure_ascii=False, sort_keys=True, default=str),
                }

                # common fields
                for key in [
                    "country", "region", "sub_region", "locality", "status",
                    "founded", "website", "wikidata_qid", "confidence",
                    "last_reviewed", "schema_version",
                ]:
                    row[key] = as_json(data.get(key))

                # bottling fields
                for key in [
                    "produced_at_distillery", "production_line", "bottled_by",
                    "bottler_type", "bottler_series", "release_date",
                    "discontinued", "availability", "abv", "age_statement",
                    "vintage", "cask_strength", "non_chill_filtered",
                    "natural_colour", "bottle_size_ml", "batch_or_cask",
                    "maturation", "finish", "rrp", "external_ids",
                    "description", "notes_official", "notes_independent",
                    "sources",
                ]:
                    row[key] = as_json(data.get(key))

                rows.append(row)

        out_csv = out_dir / f"{entity_type}.csv"
        fieldnames = sorted({k for row in rows for k in row.keys()}) if rows else [
            "entity_type", "source_path", "source_system", "id", "name", "raw_json"
        ]

        with out_csv.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)

        summary.append({
            "entity_type": entity_type,
            "csv": str(out_csv),
            "rows": len(rows),
        })

    return summary


def write_report(report_path: Path, summary):
    lines = []
    lines.append("# Structured Whisky Source 01 Extract Report")
    lines.append("")
    lines.append("| entity_type | rows | csv |")
    lines.append("|---|---:|---|")
    for item in summary:
        lines.append(f"| {item['entity_type']} | {item['rows']} | `{item['csv']}` |")
    lines.append("")
    lines.append("## Gate")
    lines.append("")
    bottlings = next((x["rows"] for x in summary if x["entity_type"] == "bottlings"), 0)
    distilleries = next((x["rows"] for x in summary if x["entity_type"] == "distilleries"), 0)
    if bottlings > 0 and distilleries > 0:
        lines.append("- Gate: **GO_MATCH_PREVIEW**")
    else:
        lines.append("- Gate: **NO-GO**")
    lines.append("- Production DB write: **NO**")
    lines.append("")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()

    repo = Path(args.repo)
    out_dir = Path(args.out_dir)
    report = Path(args.report)

    if not repo.exists():
        raise SystemExit(f"Repo not found: {repo}")

    summary = extract_entity_files(repo, out_dir)
    write_report(report, summary)

    print(f"wrote dir: {out_dir}")
    print(f"wrote report: {report}")


if __name__ == "__main__":
    main()

