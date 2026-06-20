import json
from pathlib import Path
from collections import Counter

BASE = Path("data/raw/whiskeymapper")
REPORT = Path("output/reports/184_whiskeymapper_endpoint_schema_inspection.md")

files = [
    BASE / "whiskey_table.json",
    BASE / "whiskey_scatter.json",
    BASE / "whiskey_specific_aberlour_10.json",
]

lines = []
lines.append("# Whiskey Mapper Endpoint Schema Inspection")
lines.append("")
lines.append("## Safety")
lines.append("- Production DB write: NO")
lines.append("- Raw capture only: YES")
lines.append("- Google Maps requests ignored: YES")
lines.append("")

def inspect_value(name, data):
    lines.append(f"## {name}")
    lines.append("")
    lines.append(f"- Python type: `{type(data).__name__}`")

    if isinstance(data, list):
        lines.append(f"- Rows: {len(data)}")
        if data:
            lines.append(f"- First item type: `{type(data[0]).__name__}`")
            if isinstance(data[0], dict):
                keys = list(data[0].keys())
                lines.append(f"- First item keys: `{keys}`")
                lines.append("")
                lines.append("### First row sample")
                lines.append("```json")
                lines.append(json.dumps(data[0], ensure_ascii=False, indent=2)[:4000])
                lines.append("```")

                key_counter = Counter()
                for row in data:
                    if isinstance(row, dict):
                        key_counter.update(row.keys())
                lines.append("")
                lines.append("### Key coverage")
                for k, count in key_counter.most_common():
                    lines.append(f"- `{k}`: {count}/{len(data)}")

    elif isinstance(data, dict):
        keys = list(data.keys())
        lines.append(f"- Top keys: `{keys}`")
        lines.append("")
        lines.append("### Top-level sample")
        lines.append("```json")
        lines.append(json.dumps(data, ensure_ascii=False, indent=2)[:4000])
        lines.append("```")

        for k, v in data.items():
            lines.append(f"- `{k}`: `{type(v).__name__}`")
            if isinstance(v, list):
                lines.append(f"  - len: {len(v)}")
                if v and isinstance(v[0], dict):
                    lines.append(f"  - first keys: `{list(v[0].keys())}`")
    else:
        lines.append(f"- Value sample: `{str(data)[:500]}`")

    lines.append("")

for path in files:
    if not path.exists():
        lines.append(f"## {path.name}")
        lines.append("")
        lines.append("- MISSING")
        lines.append("")
        continue

    raw = path.read_text(encoding="utf-8", errors="replace")
    lines.append(f"## File: {path.name}")
    lines.append("")
    lines.append(f"- Size bytes: {path.stat().st_size}")

    try:
        data = json.loads(raw)
        inspect_value(path.name, data)
    except Exception as exc:
        lines.append(f"- JSON parse failed: `{exc}`")
        lines.append("### Raw preview")
        lines.append("```text")
        lines.append(raw[:2000])
        lines.append("```")
        lines.append("")

REPORT.write_text("\n".join(lines), encoding="utf-8")
print(REPORT)
