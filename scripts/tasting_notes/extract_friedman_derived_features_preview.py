import csv
import hashlib
import os
import re
from pathlib import Path
from datetime import datetime

BASE = Path("data/external/github/friedman_whisky_reviews_analysis")
DB = Path("output/import/production.db")

OUT_OK = Path("data/output/friedman_derived_features_with_identity.csv")
OUT_REJ = Path("data/output/friedman_derived_features_rejected.csv")
REPORT = Path("output/reports/321_12s_friedman_derived_feature_report.md")
GATE = Path("output/reports/322_12s_friedman_derived_feature_gate.txt")

FORBIDDEN = {"review_text", "review", "notes", "nose", "palate", "finish", "comments", "description"}

NAME_HINTS = ["whisky", "whiskey", "product", "name", "title"]
TEXT_HINTS = ["review", "text", "body", "comment", "notes", "nose", "palate", "finish", "description"]
RATING_HINTS = ["rating", "score", "points"]
DATE_HINTS = ["date", "year"]
URL_HINTS = ["url", "source", "link"]

TERMS = {
    "fruity_signal": ["fruit", "fruity", "apple", "pear", "peach", "apricot", "citrus", "orange", "lemon", "berry", "raisin", "sultana", "banana", "pineapple"],
    "sweet_signal": ["sweet", "honey", "vanilla", "caramel", "toffee", "sugar", "syrup", "chocolate", "candy", "jam"],
    "smoky_signal": ["smoke", "smoky", "peat", "peated", "ash", "tar", "iodine", "medicinal", "phenol"],
    "spicy_signal": ["spice", "spicy", "pepper", "ginger", "cinnamon", "nutmeg", "clove"],
    "oaky_signal": ["oak", "wood", "woody", "cask", "barrel", "tannin"],
    "floral_signal": ["floral", "flower", "rose", "heather", "violet"],
    "malty_signal": ["malt", "malty", "cereal", "grain", "barley", "muesli", "cookie", "biscuit"],
    "winey_signal": ["sherry", "wine", "port", "madeira", "sauternes", "marsala"]
}

ACCEPTED_FIELDS = [
    "dedupe_hash", "whisky_name_raw", "source_score", "rating_points", "review_year",
    "extracted_terms",
    "fruity_signal", "sweet_signal", "smoky_signal", "spicy_signal",
    "oaky_signal", "floral_signal", "malty_signal", "winey_signal",
    "identity_status", "internal_source_url", "internal_audit_only"
]

REJECTED_FIELDS = [
    "source_file", "row_number", "reject_reason", "whisky_name_raw",
    "detected_name_col", "detected_text_col", "internal_audit_only"
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def norm_col(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(s).strip().lower()).strip("_")


def pick_col(cols, hints):
    normalized = [(c, norm_col(c)) for c in cols]
    for c, nc in normalized:
        for h in hints:
            if nc == h or nc.endswith("_" + h) or h in nc:
                return c
    return None


def safe_text(v) -> str:
    if v is None:
        return ""
    return str(v).strip()


def parse_float(v):
    s = safe_text(v)
    if not s:
        return ""
    m = re.search(r"\d+(?:\.\d+)?", s)
    return m.group(0) if m else ""


def parse_year(*values):
    for v in values:
        s = safe_text(v)
        m = re.search(r"(19|20)\d{2}", s)
        if m:
            return m.group(0)
    return ""


def extract_terms(text: str):
    low = text.lower()
    signals = {}
    matched = []
    for signal, terms in TERMS.items():
        hit_terms = []
        for term in terms:
            if re.search(r"\b" + re.escape(term) + r"s?\b", low):
                hit_terms.append(term)
        signals[signal] = bool(hit_terms)
        matched.extend(hit_terms)
    matched = sorted(set(matched))
    return signals, "|".join(matched)


def dedupe_hash(name: str, text: str) -> str:
    raw = norm_col(name) + "|" + hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def ensure_dirs():
    for p in [OUT_OK, OUT_REJ, REPORT, GATE]:
        p.parent.mkdir(parents=True, exist_ok=True)


def write_csv(path: Path, fields, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fields})


def main():
    ensure_dirs()

    if not BASE.exists():
        GATE.write_text("NO_GO_INPUT_MISSING\n", encoding="utf-8")
        REPORT.write_text("# Friedman Derived Feature Report\n\nInput folder missing.\n", encoding="utf-8")
        write_csv(OUT_OK, ACCEPTED_FIELDS, [])
        write_csv(OUT_REJ, REJECTED_FIELDS, [])
        return

    db_before = sha256_file(DB) if DB.exists() else "missing"

    accepted = []
    rejected = []
    csv_files = list(BASE.rglob("*.csv"))
    rows_scanned = 0
    files_scanned = 0

    for csv_path in csv_files:
        files_scanned += 1
        try:
            with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                cols = reader.fieldnames or []
                name_col = pick_col(cols, NAME_HINTS)
                text_col = pick_col(cols, TEXT_HINTS)
                rating_col = pick_col(cols, RATING_HINTS)
                date_col = pick_col(cols, DATE_HINTS)
                url_col = pick_col(cols, URL_HINTS)

                for idx, row in enumerate(reader, start=2):
                    rows_scanned += 1
                    name = safe_text(row.get(name_col, "")) if name_col else ""
                    text = safe_text(row.get(text_col, "")) if text_col else ""

                    if not name or not text:
                        rejected.append({
                            "source_file": str(csv_path),
                            "row_number": idx,
                            "reject_reason": "missing_name_or_review_text",
                            "whisky_name_raw": name,
                            "detected_name_col": name_col or "",
                            "detected_text_col": text_col or "",
                            "internal_audit_only": "true",
                        })
                        continue

                    signals, terms = extract_terms(text)
                    rating = parse_float(row.get(rating_col, "")) if rating_col else ""
                    year = parse_year(row.get(date_col, "") if date_col else "", text)
                    url = safe_text(row.get(url_col, "")) if url_col else ""

                    out = {
                        "dedupe_hash": dedupe_hash(name, text),
                        "whisky_name_raw": name,
                        "source_score": rating,
                        "rating_points": rating,
                        "review_year": year,
                        "extracted_terms": terms,
                        "identity_status": "name_matched",
                        "internal_source_url": url,
                        "internal_audit_only": "true",
                    }
                    for signal in TERMS:
                        out[signal] = "true" if signals.get(signal) else "false"
                    accepted.append(out)
        except Exception as e:
            rejected.append({
                "source_file": str(csv_path),
                "row_number": "",
                "reject_reason": f"file_error:{type(e).__name__}:{e}",
                "whisky_name_raw": "",
                "detected_name_col": "",
                "detected_text_col": "",
                "internal_audit_only": "true",
            })

    # de-duplicate accepted by dedupe_hash
    seen = set()
    deduped = []
    for row in accepted:
        h = row["dedupe_hash"]
        if h not in seen:
            seen.add(h)
            deduped.append(row)
    accepted = deduped

    write_csv(OUT_OK, ACCEPTED_FIELDS, accepted)
    write_csv(OUT_REJ, REJECTED_FIELDS, rejected)

    db_after = sha256_file(DB) if DB.exists() else "missing"

    forbidden_leak = []
    for path in [OUT_OK, OUT_REJ]:
        with path.open("r", encoding="utf-8") as f:
            header = f.readline().strip().split(",")
            forbidden_leak.extend([c for c in header if norm_col(c) in FORBIDDEN])

    if db_before != db_after:
        gate = "NO_GO_DB_CHANGED"
    elif forbidden_leak:
        gate = "NO_GO_FULL_TEXT_LEAK"
    elif not accepted:
        gate = "NO_GO_NO_ACCEPTED_ROWS"
    else:
        gate = "GO_DERIVED_FEATURE_PREVIEW"

    GATE.write_text(gate + "\n", encoding="utf-8")
    GATE.write_text("
Estimated API Cost: $0.00
Actual API Cost: $0.00
Local Compute Used: Yes
Fully Local Execution: Yes
", encoding="utf-8")


    report = f"""# 321_12s Friedman Derived Feature Report

- Generated at: {datetime.utcnow().isoformat()}Z
- Input folder: `{BASE}`
- CSV files scanned: {files_scanned}
- Rows scanned: {rows_scanned}
- Accepted derived rows: {len(accepted)}
- Rejected rows: {len(rejected)}
- Forbidden output columns: {sorted(set(forbidden_leak))}
- Raw review text output: NO
- Internal audit only: true
- production.db hash before: {db_before}
- production.db hash after: {db_after}
- Gate: {gate}

## Safety
Raw review text was used only in-memory for keyword extraction and hashing. It was not written to accepted or rejected outputs.
"""
    REPORT.write_text(report, encoding="utf-8")


if __name__ == "__main__":
    main()
