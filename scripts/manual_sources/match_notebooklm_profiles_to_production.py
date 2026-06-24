import argparse
import json
import re
import sqlite3
from difflib import SequenceMatcher
from pathlib import Path


def norm(s):
    if s is None:
        return ""
    s = str(s).lower()
    s = s.replace("&", " and ")
    s = re.sub(r"\b(\d+)\s*year\s*old\b", r"\1", s)
    s = re.sub(r"\b(\d+)\s*years\s*old\b", r"\1", s)
    s = re.sub(r"\b(\d+)\s*yo\b", r"\1", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    s = re.sub(r"\b(the|distillery|single|malt|whisky|whiskey|year|years|old|yo)\b", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def ratio(a, b):
    a = norm(a)
    b = norm(b)
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def load_jsonl(path):
    rows = []
    with Path(path).open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            obj["_line_no"] = line_no
            rows.append(obj)
    return rows


def load_whiskies(db_path):
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    rows = cur.execute("""
        SELECT
            w.whisky_id,
            w.name AS whisky_name,
            w.distillery_id,
            d.name AS distillery_name,
            w.type,
            w.abv,
            w.region
        FROM whiskies w
        LEFT JOIN distilleries d ON d.distillery_id = w.distillery_id
    """).fetchall()

    conn.close()
    return [dict(r) for r in rows]


def score_candidate(src, dst):
    src_name = src.get("whisky_name")
    src_dist = src.get("distillery")
    src_brand = src.get("brand")
    src_abv = src.get("abv")
    src_type = src.get("type")

    dst_name = dst.get("whisky_name")
    dst_dist = dst.get("distillery_name")
    dst_abv = dst.get("abv")
    dst_cat = dst.get("category")

    name_score = ratio(src_name, dst_name)
    dist_score = max(ratio(src_dist, dst_dist), ratio(src_brand, dst_dist))

    abv_score = 0.0
    if src_abv is not None and dst_abv is not None:
        try:
            diff = abs(float(src_abv) - float(dst_abv))
            if diff <= 0.15:
                abv_score = 1.0
            elif diff <= 0.5:
                abv_score = 0.75
            elif diff <= 1.0:
                abv_score = 0.45
        except Exception:
            abv_score = 0.0

    type_score = 0.0
    if src_type and dst_cat:
        type_score = ratio(src_type, dst_cat)

    total = (
        name_score * 0.62 +
        dist_score * 0.22 +
        abv_score * 0.10 +
        type_score * 0.06
    )

    return {
        "score": round(total, 4),
        "name_score": round(name_score, 4),
        "distillery_score": round(dist_score, 4),
        "abv_score": round(abv_score, 4),
        "type_score": round(type_score, 4),
    }


def gate(best, second):
    if not best:
        return "NO_MATCH"

    score = best["score"]
    margin = score - second["score"] if second else score
    name_score = best.get("name_score", 0)
    distillery_score = best.get("distillery_score", 0)

    if name_score >= 0.97 and margin >= 0.05:
        return "HIGH"

    if name_score >= 0.94 and distillery_score >= 0.70 and margin >= 0.03:
        return "HIGH"

    if score >= 0.92 and margin >= 0.03:
        return "HIGH"

    if score >= 0.80 and margin >= 0.02:
        return "REVIEW"

    return "NO_MATCH"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--db", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--report", required=True)
    args = ap.parse_args()

    src_rows = load_jsonl(args.input)
    whiskies = load_whiskies(args.db)

    out_rows = []

    for src in src_rows:
        scored = []
        for dst in whiskies:
            s = score_candidate(src, dst)
            if s["name_score"] < 0.45 and s["distillery_score"] < 0.45:
                continue

            scored.append({
                **s,
                "source_whisky_name": src.get("whisky_name"),
                "source_distillery": src.get("distillery"),
                "source_brand": src.get("brand"),
                "source_type": src.get("type"),
                "source_abv": src.get("abv"),
                "source_confidence": src.get("confidence"),
                "matched_whisky_id": dst.get("whisky_id"),
                "matched_whisky_name": dst.get("whisky_name"),
                "matched_distillery": dst.get("distillery_name"),
                "matched_category": dst.get("category"),
                "matched_abv": dst.get("abv"),
                "matched_region": dst.get("region"),
            })

        scored.sort(key=lambda x: x["score"], reverse=True)
        best = scored[0] if scored else None
        second = scored[1] if len(scored) > 1 else None

        if best:
            best["second_score"] = second["score"] if second else None
            best["margin"] = round(best["score"] - (second["score"] if second else 0), 4)
            best["match_gate"] = gate(best, second)
            out_rows.append(best)
        else:
            out_rows.append({
                "source_whisky_name": src.get("whisky_name"),
                "source_distillery": src.get("distillery"),
                "source_brand": src.get("brand"),
                "source_type": src.get("type"),
                "source_abv": src.get("abv"),
                "source_confidence": src.get("confidence"),
                "matched_whisky_id": None,
                "matched_whisky_name": None,
                "matched_distillery": None,
                "score": 0,
                "second_score": None,
                "margin": 0,
                "match_gate": "NO_MATCH",
            })

    output_path = Path(args.output)
    report_path = Path(args.report)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    import csv
    fieldnames = sorted({k for row in out_rows for k in row.keys()})
    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(out_rows)

    counts = {}
    for row in out_rows:
        counts[row["match_gate"]] = counts.get(row["match_gate"], 0) + 1

    report = []
    report.append("# NotebookLM Profile Production Match Report")
    report.append("")
    report.append(f"- Source rows: {len(src_rows)}")
    report.append(f"- Production whiskies: {len(whiskies)}")
    report.append(f"- Output: `{output_path}`")
    report.append("")
    report.append("## Match Gates")
    for k in ["HIGH", "REVIEW", "NO_MATCH"]:
        report.append(f"- {k}: {counts.get(k, 0)}")
    report.append("")
    report.append("## HIGH Examples")
    for row in [r for r in out_rows if r["match_gate"] == "HIGH"][:30]:
        report.append(
            f"- {row['source_whisky_name']} -> {row['matched_whisky_id']} | "
            f"{row['matched_whisky_name']} | score={row['score']} margin={row['margin']}"
        )
    report.append("")
    report.append("## REVIEW Examples")
    for row in [r for r in out_rows if r["match_gate"] == "REVIEW"][:50]:
        report.append(
            f"- {row['source_whisky_name']} -> {row['matched_whisky_id']} | "
            f"{row['matched_whisky_name']} | score={row['score']} margin={row['margin']}"
        )
    report.append("")
    report.append("## NO_MATCH Examples")
    for row in [r for r in out_rows if r["match_gate"] == "NO_MATCH"][:80]:
        report.append(
            f"- {row['source_whisky_name']} | distillery={row.get('source_distillery')} | "
            f"type={row.get('source_type')} | abv={row.get('source_abv')}"
        )
    report.append("")

    report_path.write_text("\n".join(report), encoding="utf-8")

    print(f"source_rows={len(src_rows)}")
    print(f"production_whiskies={len(whiskies)}")
    print(f"HIGH={counts.get('HIGH', 0)}")
    print(f"REVIEW={counts.get('REVIEW', 0)}")
    print(f"NO_MATCH={counts.get('NO_MATCH', 0)}")
    print(f"output={output_path}")
    print(f"report={report_path}")


if __name__ == "__main__":
    main()
