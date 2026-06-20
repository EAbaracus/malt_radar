from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]

QA_PACK_PATH = ROOT / "output" / "reports" / "201_scotchgit_flavor_manual_qa_pack.csv"
PREVIEW_PATH = ROOT / "data" / "output" / "scotchgit_flavor_signal_preview.csv"

ACCEPTS_PATH = ROOT / "data" / "output" / "scotchgit_flavor_preview_manual_accepts.csv"
REJECTS_PATH = ROOT / "data" / "output" / "scotchgit_flavor_preview_manual_rejects.csv"
NEEDS_RAW_NOTE_PATH = ROOT / "data" / "output" / "scotchgit_flavor_preview_needs_raw_note.csv"
NEEDS_MANUAL_MATCH_PATH = ROOT / "data" / "output" / "scotchgit_flavor_preview_needs_manual_match.csv"

REPORT_PATH = ROOT / "output" / "reports" / "203_scotchgit_manual_qa_decision_gate.md"

AXES = ["smoky", "sweet", "fruity", "spicy", "woody", "maritime", "sherry"]

VALID_DECISIONS = {
    "accept_preview",
    "reject",
    "needs_raw_note",
    "needs_manual_match",
}


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def normalize_decision(value: object) -> str:
    if pd.isna(value):
        return "pending"

    text = str(value).strip().lower()

    if not text or text in {";", "nan", "none", "null", "pending"}:
        return "pending"

    return text


def ensure_dirs() -> None:
    ACCEPTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)


def main() -> None:
    ensure_dirs()

    if not QA_PACK_PATH.exists():
        raise FileNotFoundError(f"Missing QA pack: {QA_PACK_PATH}")

    if not PREVIEW_PATH.exists():
        raise FileNotFoundError(f"Missing preview CSV: {PREVIEW_PATH}")

    qa = pd.read_csv(QA_PACK_PATH)
    preview = pd.read_csv(PREVIEW_PATH)

    required_qa_cols = {
        "matched_master_whisky_id",
        "product_name",
        "manual_decision",
        "signal_basis",
        "signal_strength",
        *AXES,
    }

    missing = sorted(required_qa_cols - set(qa.columns))
    if missing:
        raise ValueError(f"QA pack missing required columns: {missing}")

    qa["manual_decision_normalized"] = qa["manual_decision"].apply(normalize_decision)

    invalid = sorted(
        set(qa["manual_decision_normalized"].dropna().unique())
        - VALID_DECISIONS
        - {"pending"}
    )
    if invalid:
        raise ValueError(f"Invalid manual_decision values: {invalid}")

    axis_sum = qa[AXES].fillna(0).sum(axis=1)
    qa["is_zero_signal"] = axis_sum.eq(0)

    accepts = qa[qa["manual_decision_normalized"].eq("accept_preview")].copy()
    rejects = qa[qa["manual_decision_normalized"].eq("reject")].copy()
    needs_raw_note = qa[qa["manual_decision_normalized"].eq("needs_raw_note")].copy()
    needs_manual_match = qa[qa["manual_decision_normalized"].eq("needs_manual_match")].copy()
    pending = qa[qa["manual_decision_normalized"].eq("pending")].copy()

    accepts.to_csv(ACCEPTS_PATH, index=False, encoding="utf-8-sig")
    rejects.to_csv(REJECTS_PATH, index=False, encoding="utf-8-sig")
    needs_raw_note.to_csv(NEEDS_RAW_NOTE_PATH, index=False, encoding="utf-8-sig")
    needs_manual_match.to_csv(NEEDS_MANUAL_MATCH_PATH, index=False, encoding="utf-8-sig")

    accept_zero_signal_count = int(accepts["is_zero_signal"].sum()) if len(accepts) else 0
    accept_region_only_count = int(accepts["signal_basis"].eq("region_only").sum()) if len(accepts) else 0
    accept_region_only_ratio = (
        accept_region_only_count / len(accepts) if len(accepts) else 0.0
    )

    accept_with_warning_count = (
        int(
            accepts.get("confidence_warning", pd.Series(dtype=str))
            .fillna("")
            .astype(str)
            .str.strip()
            .ne("")
            .sum()
        )
        if len(accepts)
        else 0
    )

    gate_reasons: list[str] = []

    if len(pending) > 0:
        gate_reasons.append(f"manual_decision pending/empty rows remain: {len(pending)}")

    if len(accepts) < 30:
        gate_reasons.append(f"accept_preview count below minimum 30: {len(accepts)}")

    if accept_zero_signal_count > 0:
        gate_reasons.append(
            f"accept_preview includes zero-signal rows: {accept_zero_signal_count}"
        )

    if len(accepts) and accept_region_only_ratio > 0.50:
        gate_reasons.append(
            f"accept_preview majority is region_only: {accept_region_only_ratio:.2%}"
        )

    preview_whitelist_gate = "GO" if not gate_reasons else "NO-GO"
    production_import_gate = "NO-GO"

    decision_counts = qa["manual_decision_normalized"].value_counts(dropna=False)

    group_counts = (
        qa["qa_group"].value_counts(dropna=False)
        if "qa_group" in qa.columns
        else pd.Series(dtype=int)
    )

    accepted_group_counts = (
        accepts["qa_group"].value_counts(dropna=False)
        if "qa_group" in accepts.columns and len(accepts)
        else pd.Series(dtype=int)
    )

    report_lines = [
        "# 203 ScotchGit Manual QA Decision Gate",
        "",
        "## Inputs",
        f"- QA pack: `{QA_PACK_PATH.as_posix()}`",
        f"- QA pack SHA256: `{file_sha256(QA_PACK_PATH)}`",
        f"- Preview CSV: `{PREVIEW_PATH.as_posix()}`",
        f"- Preview CSV SHA256: `{file_sha256(PREVIEW_PATH)}`",
        "",
        "## Output files",
        f"- Accepts: `{ACCEPTS_PATH.as_posix()}`",
        f"- Rejects: `{REJECTS_PATH.as_posix()}`",
        f"- Needs raw note: `{NEEDS_RAW_NOTE_PATH.as_posix()}`",
        f"- Needs manual match: `{NEEDS_MANUAL_MATCH_PATH.as_posix()}`",
        "",
        "## Summary",
        f"- QA rows: `{len(qa)}`",
        f"- Preview rows: `{len(preview)}`",
        f"- accept_preview: `{len(accepts)}`",
        f"- reject: `{len(rejects)}`",
        f"- needs_raw_note: `{len(needs_raw_note)}`",
        f"- needs_manual_match: `{len(needs_manual_match)}`",
        f"- pending/empty: `{len(pending)}`",
        "",
        "## Decision counts",
        "```text",
        decision_counts.to_string(),
        "```",
        "",
        "## QA group counts",
        "```text",
        group_counts.to_string() if len(group_counts) else "NO qa_group column",
        "```",
        "",
        "## Accepted group counts",
        "```text",
        accepted_group_counts.to_string()
        if len(accepted_group_counts)
        else "No accepted rows",
        "```",
        "",
        "## Accept risk checks",
        f"- accept_preview zero signal rows: `{accept_zero_signal_count}`",
        f"- accept_preview region_only rows: `{accept_region_only_count}`",
        f"- accept_preview region_only ratio: `{accept_region_only_ratio:.2%}`",
        f"- accept_preview rows with confidence_warning: `{accept_with_warning_count}`",
        "",
        "## Gate decision",
        f"- Preview whitelist gate: **{preview_whitelist_gate}**",
        f"- Production import gate: **{production_import_gate}**",
        "",
    ]

    if gate_reasons:
        report_lines.extend(
            [
                "## NO-GO reasons",
                *[f"- {reason}" for reason in gate_reasons],
                "",
            ]
        )
    else:
        report_lines.extend(
            [
                "## GO notes",
                "- Manual QA preview whitelist passed.",
                "- This does not authorize production DB import.",
                "- Accepted rows remain preview-only candidates.",
                "",
            ]
        )

    report_lines.extend(
        [
            "## Safety",
            "- `production.db` was not opened or modified by this script.",
            "- Raw Reddit content was not fetched.",
            "- Frontend integration was not performed.",
            "- ScotchGit preview remains `candidate_preview_only`.",
            "",
        ]
    )

    REPORT_PATH.write_text("\n".join(report_lines), encoding="utf-8")

    print(f"QA rows: {len(qa)}")
    print(decision_counts.to_string())
    print(f"Preview whitelist gate: {preview_whitelist_gate}")
    print(f"Production import gate: {production_import_gate}")
    print(f"Wrote: {ACCEPTS_PATH}")
    print(f"Wrote: {REJECTS_PATH}")
    print(f"Wrote: {NEEDS_RAW_NOTE_PATH}")
    print(f"Wrote: {NEEDS_MANUAL_MATCH_PATH}")
    print(f"Wrote: {REPORT_PATH}")


if __name__ == "__main__":
    main()