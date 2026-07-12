from __future__ import annotations

from collections import Counter
from pathlib import Path

import pandas as pd


INPUT = Path("data/output/whiskyfun_derived_feature_product_match_preview.csv")
SUMMARY_OUT = Path("data/output/whiskyfun_match_conflict_summary.csv")
SAMPLES_OUT = Path("data/output/whiskyfun_match_conflict_samples.csv")
REPORT_OUT = Path("output/reports/317_12r_whiskyfun_conflict_audit_report.md")
GATE_OUT = Path("output/reports/318_12r_whiskyfun_conflict_audit_gate.txt")

FORBIDDEN = {"review_text", "nose", "mouth", "finish", "comments", "nmf"}


def split_flags(value):
    if pd.isna(value):
        return []
    text = str(value).strip()
    if not text or text.lower() in {"none", "nan", "[]"}:
        return []
    for sep in ["|", ";", ","]:
        if sep in text:
            return [x.strip() for x in text.split(sep) if x.strip()]
    return [text]


def write_text(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main():
    SUMMARY_OUT.parent.mkdir(parents=True, exist_ok=True)
    SAMPLES_OUT.parent.mkdir(parents=True, exist_ok=True)
    REPORT_OUT.parent.mkdir(parents=True, exist_ok=True)
    GATE_OUT.parent.mkdir(parents=True, exist_ok=True)

    if not INPUT.exists():
        write_text(GATE_OUT, "NO_GO_INPUT_MISSING\n")
        write_text(REPORT_OUT, "# 12R Whiskyfun Conflict Audit\n\nInput CSV bulunamadı.\n")
        return 1

    df = pd.read_csv(INPUT)

    forbidden = sorted(FORBIDDEN.intersection(df.columns))
    if forbidden:
        write_text(GATE_OUT, "NO_GO_FULL_TEXT_LEAK\n")
        write_text(
            REPORT_OUT,
            "# 12R Whiskyfun Conflict Audit\n\n"
            f"Full text kolonları bulundu: {forbidden}\n",
        )
        return 1

    if "decision" not in df.columns:
        write_text(GATE_OUT, "NO_GO_INPUT_MISSING\nMissing decision column\n")
        write_text(REPORT_OUT, "# 12R Whiskyfun Conflict Audit\n\n`decision` kolonu eksik.\n")
        return 1

    rows = len(df)
    decision_counts = df["decision"].fillna("MISSING").value_counts()

    reject_conflict = df[df["decision"] == "REJECT_CONFLICT"].copy()
    reject_low = df[df["decision"] == "REJECT_LOW_CONFIDENCE"].copy()
    review = df[df["decision"] == "REVIEW_PRODUCT_FEATURE"].copy()
    distillery_only = df[df["decision"] == "KEEP_DISTILLERY_FEATURE_ONLY"].copy()

    flag_counter = Counter()
    combo_counter = Counter()

    if "conflict_flags" in reject_conflict.columns:
        for val in reject_conflict["conflict_flags"]:
            flags = split_flags(val)
            if flags:
                flags = sorted(flags)
                flag_counter.update(flags)
                combo_counter["|".join(flags)] += 1
            else:
                combo_counter["NO_FLAGS"] += 1
    else:
        combo_counter["MISSING_CONFLICT_FLAGS_COLUMN"] = len(reject_conflict)

    if "name_match_score" in df.columns:
        review_scores = pd.to_numeric(review["name_match_score"], errors="coerce").fillna(0)
        distillery_scores = pd.to_numeric(distillery_only["name_match_score"], errors="coerce").fillna(0)
        review_upgrade = int(review_scores.ge(94).sum())
        distillery_upgrade = int(distillery_scores.ge(90).sum())
    else:
        review_upgrade = 0
        distillery_upgrade = 0

    summary_rows = [
        {"metric": "total_rows", "value": rows},
        {"metric": "reject_conflict_rows", "value": len(reject_conflict)},
        {"metric": "reject_low_confidence_rows", "value": len(reject_low)},
        {"metric": "review_upgrade_candidates_score_ge_94", "value": review_upgrade},
        {"metric": "distillery_upgrade_candidates_score_ge_90", "value": distillery_upgrade},
    ]

    for k, v in decision_counts.items():
        summary_rows.append({"metric": f"decision:{k}", "value": int(v)})

    for k, v in flag_counter.most_common():
        summary_rows.append({"metric": f"conflict_flag:{k}", "value": int(v)})

    for k, v in combo_counter.most_common(30):
        summary_rows.append({"metric": f"conflict_combo:{k}", "value": int(v)})

    pd.DataFrame(summary_rows).to_csv(SUMMARY_OUT, index=False)

    safe_cols = [
        "dedupe_hash",
        "whisky_name_raw",
        "distillery",
        "source_score",
        "review_year",
        "review_date",
        "identity_status",
        "match_source",
        "matched_whisky_id",
        "matched_whisky_name",
        "matched_distillery",
        "name_match_score",
        "distillery_match",
        "conflict_flags",
        "decision",
        "decision_reason",
        "internal_audit_only",
        "internal_source_url",
    ]
    safe_cols = [c for c in safe_cols if c in df.columns and c not in FORBIDDEN]

    sample_parts = []
    for decision in [
        "REJECT_CONFLICT",
        "REJECT_LOW_CONFIDENCE",
        "REVIEW_PRODUCT_FEATURE",
        "KEEP_DISTILLERY_FEATURE_ONLY",
    ]:
        part = df[df["decision"] == decision].head(20)
        if not part.empty:
            sample_parts.append(part[safe_cols])

    if sample_parts:
        samples = pd.concat(sample_parts, ignore_index=True)
    else:
        samples = pd.DataFrame(columns=safe_cols)

    samples.to_csv(SAMPLES_OUT, index=False)

    gate = (
        "GO_MATCHER_TUNING_RECOMMENDED"
        if len(reject_conflict) > rows * 0.40 or review_upgrade > 0 or distillery_upgrade > 0
        else "GO_CONFLICT_AUDIT_ONLY"
    )

    top_flags = "\n".join([f"- {k}: {v}" for k, v in flag_counter.most_common(20)])
    top_combos = "\n".join([f"- {k}: {v}" for k, v in combo_counter.most_common(20)])

    report = f"""# 12R Whiskyfun Conflict Audit

## Sonuç

- Gate: `{gate}`
- Toplam satır: `{rows}`
- REJECT_CONFLICT: `{len(reject_conflict)}`
- REJECT_LOW_CONFIDENCE: `{len(reject_low)}`
- REVIEW score >= 94 yükseltme adayı: `{review_upgrade}`
- Distillery-only score >= 90 yükseltme adayı: `{distillery_upgrade}`
- Full text sızıntısı: Yok
- production.db kullanıldı mı: Hayır
- Source public output var mı: Hayır

## Decision dağılımı

{decision_counts.to_string()}

## En sık conflict flag

{top_flags if top_flags else "Conflict flag bulunamadı."}

## En sık conflict kombinasyonları

{top_combos if top_combos else "Conflict kombinasyonu bulunamadı."}

## Öneri

REJECT_CONFLICT oranı yüksekse matcher fazla muhafazakâr olabilir.

Bir sonraki aşamada:
- Age/vintage mismatch güçlü conflict olarak kalmalı.
- Cask/bottler mismatch bazı durumlarda REJECT yerine REVIEW yapılabilir.
- Low name score tek başına varsa distillery-level feature olarak değerlendirilebilir.
"""

    write_text(REPORT_OUT, report)
    write_text(GATE_OUT, gate + "\n")
    write_text(GATE_OUT, "
Estimated API Cost: $0.00
Actual API Cost: $0.00
Local Compute Used: Yes
Fully Local Execution: Yes
", encoding="utf-8")


    print("rows:", rows)
    print("gate:", gate)
    print("reject_conflict:", len(reject_conflict))
    print("reject_low_confidence:", len(reject_low))
    print("review_upgrade_candidates_score_ge_94:", review_upgrade)
    print("distillery_upgrade_candidates_score_ge_90:", distillery_upgrade)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())