import argparse
import csv
import json
import sqlite3
from collections import Counter
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None


ENTITY_DIRS = {
    "distilleries": "data/distilleries",
    "production_lines": "data/production_lines",
    "bottlings": "data/bottlings",
    "concepts": "data/concepts",
    "bottlers": "data/bottlers",
    "casks": "data/casks",
    "suppliers": "data/suppliers",
}


def read_yaml(path: Path):
    if yaml is None:
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception as exc:
        return {"__parse_error__": str(exc)}


def count_db(db_path: Path, table: str):
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        cur = conn.cursor()
        n = cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        conn.close()
        return n
    except Exception:
        return None


def scan_repo(repo: Path):
    rows = []
    yaml_parse_errors = []

    for entity_type, rel in ENTITY_DIRS.items():
        root = repo / rel
        if not root.exists():
            rows.append({
                "entity_type": entity_type,
                "path": rel,
                "exists": False,
                "file_count": 0,
                "yaml_count": 0,
                "md_count": 0,
                "parse_errors": 0,
            })
            continue

        files = [p for p in root.rglob("*") if p.is_file()]
        yaml_files = [p for p in files if p.suffix.lower() in [".yml", ".yaml"]]
        md_files = [p for p in files if p.suffix.lower() == ".md"]

        parse_error_count = 0
        for yf in yaml_files:
            data = read_yaml(yf)
            if isinstance(data, dict) and "__parse_error__" in data:
                parse_error_count += 1
                yaml_parse_errors.append((str(yf.relative_to(repo)), data["__parse_error__"]))

        rows.append({
            "entity_type": entity_type,
            "path": rel,
            "exists": True,
            "file_count": len(files),
            "yaml_count": len(yaml_files),
            "md_count": len(md_files),
            "parse_errors": parse_error_count,
        })

    return rows, yaml_parse_errors


def collect_bottling_fields(repo: Path):
    root = repo / "data/bottlings"
    counter = Counter()
    examples = []

    if not root.exists() or yaml is None:
        return counter, examples

    for path in root.rglob("*"):
        if path.suffix.lower() not in [".yml", ".yaml"]:
            continue
        data = read_yaml(path)
        if not isinstance(data, dict) or "__parse_error__" in data:
            continue
        counter.update(data.keys())
        if len(examples) < 10:
            examples.append({
                "path": str(path.relative_to(repo)),
                "name": data.get("name") or data.get("title"),
                "distillery": data.get("produced_at_distillery") or data.get("distillery"),
                "abv": data.get("abv"),
                "age": data.get("age_statement"),
                "bottler": data.get("bottled_by"),
            })

    return counter, examples


def write_report(out: Path, repo: Path, db: Path, rows, errors, bottling_fields, examples):
    db_counts = {
        "whiskies": count_db(db, "whiskies"),
        "distilleries": count_db(db, "distilleries"),
        "flavor_profiles": count_db(db, "flavor_profiles"),
        "tasting_notes": count_db(db, "tasting_notes"),
        "staging_tasting_notes": count_db(db, "staging_tasting_notes"),
    }

    lines = []
    lines.append("# Structured Whisky Source 01 Audit")
    lines.append("")
    lines.append(f"- Repo: `{repo}`")
    lines.append(f"- DB: `{db}`")
    lines.append(f"- YAML parser available: `{yaml is not None}`")
    lines.append("")
    lines.append("## Production DB counts")
    lines.append("")
    for k, v in db_counts.items():
        lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append("## Entity inventory")
    lines.append("")
    lines.append("| entity_type | path | exists | files | yaml | md | parse_errors |")
    lines.append("|---|---|---:|---:|---:|---:|---:|")
    for r in rows:
        lines.append(
            f"| {r['entity_type']} | `{r['path']}` | {r['exists']} | {r['file_count']} | {r['yaml_count']} | {r['md_count']} | {r['parse_errors']} |"
        )
    lines.append("")
    lines.append("## Bottling field frequency")
    lines.append("")
    for key, n in bottling_fields.most_common(80):
        lines.append(f"- `{key}`: {n}")
    lines.append("")
    lines.append("## Bottling examples")
    lines.append("")
    for ex in examples:
        lines.append(f"- `{ex['path']}` | name={ex['name']} | distillery={ex['distillery']} | abv={ex['abv']} | age={ex['age']} | bottler={ex['bottler']}")
    lines.append("")
    lines.append("## YAML parse errors")
    lines.append("")
    if errors:
        for path, err in errors[:50]:
            lines.append(f"- `{path}`: {err}")
    else:
        lines.append("- None")
    lines.append("")
    lines.append("## Gate")
    lines.append("")
    total_yaml = sum(r["yaml_count"] for r in rows)
    total_errors = sum(r["parse_errors"] for r in rows)
    if yaml is None:
        gate = "NO-GO"
        reason = "PyYAML missing"
    elif total_yaml == 0:
        gate = "NO-GO"
        reason = "No YAML files found"
    elif total_errors > 0:
        gate = "REVIEW"
        reason = "YAML parse errors found"
    else:
        gate = "GO_PREVIEW"
        reason = "Inventory parse passed; safe to proceed to extraction/matching preview"
    lines.append(f"- Gate: **{gate}**")
    lines.append(f"- Reason: {reason}")
    lines.append("")
    lines.append("## Recommendation")
    lines.append("")
    lines.append("- Production direct import: NO-GO")
    lines.append("- Extraction/matching preview: GO if gate is GO_PREVIEW")
    lines.append("- Preserve source/confidence fields")
    lines.append("- Do not write production DB in this phase")
    lines.append("")

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--db", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    repo = Path(args.repo)
    db = Path(args.db)
    out = Path(args.out)

    if not repo.exists():
        raise SystemExit(f"Repo not found: {repo}")
    if not db.exists():
        raise SystemExit(f"DB not found: {db}")

    rows, errors = scan_repo(repo)
    bottling_fields, examples = collect_bottling_fields(repo)
    write_report(out, repo, db, rows, errors, bottling_fields, examples)

    print(f"wrote: {out}")


if __name__ == "__main__":
    main()

