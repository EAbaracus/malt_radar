import argparse
import csv
import re
import sqlite3
from difflib import SequenceMatcher
from pathlib import Path


def norm(s):
    s = (s or "").lower()
    s = s.replace("&", " and ")
    s = re.sub(r"\b(years?|year old|yo|old|single malt|scotch whisky|whisky|whiskey)\b", " ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def score(a, b):
    a2 = norm(a)
    b2 = norm(b)
    if not a2 or not b2:
        return 0.0
    if a2 == b2:
        return 1.0
    if a2 in b2 or b2 in a2:
        return max(0.88, SequenceMatcher(None, a2, b2).ratio())
    return SequenceMatcher(None, a2, b2).ratio()


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def fetch_whiskies(db):
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cols = [r[1] for r in cur.execute("PRAGMA table_info(whiskies)").fetchall()]
    name_col = "name" if "name" in cols else "whisky_name" if "whisky_name" in cols else None
    id_col = "whisky_id" if "whisky_id" in cols else "id" if "id" in cols else None

    if not name_col or not id_col:
        raise SystemExit(f"Cannot find whisky id/name columns. Columns: {cols}")

    distillery_col = "distillery_name" if "distillery_name" in cols else None

    select_cols = [id_col, name_col]
    if distillery_col:
        select_cols.append(distillery_col)

    sql = f"SELECT {', '.join(select_cols)} FROM whiskies"
    rows = []
    for r in cur.execute(sql):
        rows.append({
            "whisky_id": r[id_col],
            "whisky_name": r[name_col],
            "distillery_name": r[distillery_col] if distillery_col else "",
        })

    conn.close()
    return rows


def best_matches(source_name, candidates, topn=3):
    scored = []
    for c in candidates:
        s = score(source_name, c["whisky_name"])
        scored.append((s, c))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:topn]


def classify(best, second):
    margin = best - second
    if best >= 0.94 and margin >= 0.02:
        return "high"
    if best >= 0.88 and margin >= 0.03:
        return "review"
    if best >= 0.82:
        return "manual"
    return "no_match"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--entities-dir", required=True)
    parser.add_argument("--db", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()

    entities_dir = Path(args.entities_dir)
    db = Path(args.db)
    out = Path(args.out)
    report = Path(args.report)

    bottlings_csv = entities_dir / "bottlings.csv"
    if not bottlings_csv.exists():
        raise SystemExit(f"Missing {bottlings_csv}")

    source_rows = read_csv(bottlings_csv)
    whisky_rows = fetch_whiskies(db)

    output = []
    for row in source_rows:
        source_name = row.get("name", "")
        matches = best_matches(source_name, whisky_rows, 3)
        best_score = matches[0][0] if matches else 0.0
        second_score = matches[1][0] if len(matches) > 1 else 0.0
        status = classify(best_score, second_score)

        best = matches[0][1] if matches else {}
        second = matches[1][1] if len(matches) > 1 else {}

        output.append({
            "source_system": "structured_whisky_source_01",
            "source_path": row.get("source_path", ""),
            "source_id": row.get("id", ""),
            "source_name": source_name,
            "source_distillery": row.get("produced_at_distillery", ""),
            "source_abv": row.get("abv", ""),
            "source_age": row.get("age_statement", ""),
            "source_bottler": row.get("bottled_by", ""),
            "source_external_ids": row.get("external_ids", ""),
            "match_status": status,
            "best_score": f"{best_score:.4f}",
            "second_score": f"{second_score:.4f}",
            "margin": f"{best_score - second_score:.4f}",
            "matched_whisky_id": best.get("whisky_id", ""),
            "matched_whisky_name": best.get("whisky_name", ""),
            "second_whisky_id": second.get("whisky_id", ""),
            "second_whisky_name": second.get("whisky_name", ""),
        })

    out.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(output[0].keys()) if output else []
    with out.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output)

    counts = {}
    for r in output:
        counts[r["match_status"]] = counts.get(r["match_status"], 0) + 1

    lines = []
    lines.append("# Structured Whisky Source 01 Match Preview")
    lines.append("")
    lines.append(f"- Source rows: {len(source_rows)}")
    lines.append(f"- Production whiskies scanned: {len(whisky_rows)}")
    lines.append(f"- Output: `{out}`")
    lines.append("")
    lines.append("## Match status")
    lines.append("")
    for k in ["high", "review", "manual", "no_match"]:
        lines.append(f"- {k}: {counts.get(k, 0)}")
    lines.append("")
    lines.append("## Gate")
    lines.append("")
    if counts.get("high", 0) > 0:
        lines.append("- Gate: **GO_REVIEW_CSV**")
    else:
        lines.append("- Gate: **NO-GO**")
    lines.append("- Production DB write: **NO**")
    lines.append("")
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("\n".join(lines), encoding="utf-8")
    lines.append("Estimated API Cost: $0.00")
    lines.append("Actual API Cost: $0.00")
    lines.append("Local Compute Used: Yes")
    lines.append("Fully Local Execution: Yes")


    print(f"wrote: {out}")
    print(f"wrote: {report}")


if __name__ == "__main__":
    main()

