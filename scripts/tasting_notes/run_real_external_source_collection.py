import csv
import difflib
import json
import os
import re
import sqlite3
import sys
from html import unescape
from urllib.parse import urljoin

from bs4 import BeautifulSoup

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from scripts.tasting_notes.masterofmalt_adapter import MasterOfMaltAdapter
from scripts.tasting_notes.whiskynotes_adapter import WhiskyNotesAdapter
from scripts.tasting_notes.whiskyedition_adapter import WhiskyEditionAdapter
from scripts.tasting_notes.whiskybase_adapter import WhiskybaseAdapter


DB_PATH = os.path.join(BASE_DIR, "output", "import", "production.db")
OUTPUT_DIR = os.path.join(BASE_DIR, "data", "output")
REPORTS_DIR = os.path.join(BASE_DIR, "output", "reports")

FIELDS = [
    "source_system",
    "source_type",
    "product_name",
    "normalized_product_name",
    "source_url",
    "nose",
    "palate",
    "finish",
    "conclusion",
    "score",
    "rating",
    "price",
    "top_flavors",
    "source_profile",
    "converted_flavor_profile",
    "flavour_camp",
    "similar_whiskies",
    "source_verified",
    "matched_master_whisky_id",
    "match_score",
    "match_method",
    "match_status",
    "approval_status",
    "import_recommendation",
    "notes_for_review",
]

SEEDS = {
    "whiskynotes": {
        "adapter": WhiskyNotesAdapter,
        "source_type": "tasting_note",
        "source_verified": 1,
        "output": "real_whiskynotes_tasting_note_candidates.csv",
        "urls": [
            "https://www.whiskynotes.be/2024/glenfarclas/glenfarclas-8-year-old/",
            "https://www.whiskynotes.be/2024/springbank/springbank-10-years-2024/",
            "https://www.whiskynotes.be/2024/clynelish/clynelish-14-years/",
        ],
    },
    "masterofmalt": {
        "adapter": MasterOfMaltAdapter,
        "source_type": "tasting_note",
        "source_verified": 1,
        "output": "real_masterofmalt_tasting_note_candidates.csv",
        "urls": [
            "https://www.masterofmalt.com/whiskies/arran/arran-10-year-old-whisky/?sku=1743",
            "https://www.masterofmalt.com/whiskies/ardbeg/ardbeg-10-year-old-whisky/",
            "https://www.masterofmalt.com/whiskies/lagavulin/lagavulin-16-year-old-whisky/",
        ],
    },
    "whiskyedition": {
        "adapter": WhiskyEditionAdapter,
        "source_type": "tasting_note",
        "source_verified": 1,
        "output": "real_whiskyedition_tasting_note_candidates.csv",
        "urls": [
            "https://thewhiskyedition.com/whisky-reviews/dalmore-2007-2017-10-years-a-d-rattray",
        ],
    },
    "thewhiskyexchange": {
        "source_type": "flavour_category",
        "source_verified": 1,
        "output": "real_twe_flavour_category_candidates.csv",
        "urls": [
            "https://www.thewhiskyexchange.com/feature/whiskybyflavour",
        ],
    },
    "whiskybase": {
        "adapter": WhiskybaseAdapter,
        "source_type": "tasting_note_crowd_audit",
        "source_verified": 0,
        "output": "real_whiskybase_tasting_note_candidates.csv",
        "urls": [
            "https://www.whiskybase.com/whiskies/whisky/246529/ardbeg-ten",
        ],
    },
}


def clean_text(value):
    if value is None:
        return ""
    value = unescape(str(value))
    if any(marker in value for marker in ("â", "Ã", "Â")):
        try:
            value = value.encode("latin1").decode("utf-8")
        except UnicodeError:
            pass
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def normalize_name(value):
    value = clean_text(value).lower()
    value = re.sub(r"\b(\d{1,2})\s*years?\s*old\b", r"\1yo", value)
    value = re.sub(r"\b(\d{1,2})\s*years?\b", r"\1yo", value)
    value = re.sub(r"\b70\s*cl\b|\b700\s*ml\b|\bwhisk(?:y|ey)\b|\bsingle malt\b", " ", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def has_tasting_note(row):
    return any(clean_text(row.get(field)) for field in ("nose", "palate", "finish", "conclusion"))


class MasterWhiskyMatcher:
    def __init__(self):
        self.whiskies = []
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        try:
            cur = conn.cursor()
            cur.execute("SELECT whisky_id, name, brand, region, country, type, age FROM whiskies")
            self.whiskies = [dict(row) for row in cur.fetchall()]
        finally:
            conn.close()

    def match(self, product_name):
        product_norm = normalize_name(product_name)
        if not product_norm:
            return "", "", "difflib_name_region", "unmatched"

        best_id = ""
        best_score = 0.0
        for whisky in self.whiskies:
            names = [whisky.get("name"), whisky.get("brand")]
            if whisky.get("brand") and whisky.get("name"):
                names.append(f"{whisky.get('brand')} {whisky.get('name')}")
            for candidate in names:
                candidate_norm = normalize_name(candidate)
                if not candidate_norm:
                    continue
                score = max(
                    difflib.SequenceMatcher(None, product_norm, candidate_norm).ratio() * 100,
                    self.token_overlap_score(product_norm, candidate_norm),
                )
                if whisky.get("region") and normalize_name(whisky["region"]) in product_norm:
                    score = min(100, score + 3)
                if score > best_score:
                    best_score = score
                    best_id = whisky.get("whisky_id") or ""

        rounded = int(round(best_score))
        if rounded >= 92:
            status = "high_confidence_match"
        elif rounded >= 80:
            status = "needs_review"
        else:
            status = "unmatched"
        return best_id, rounded, "difflib_name_region", status

    @staticmethod
    def token_overlap_score(left, right):
        left_tokens = set(left.split())
        right_tokens = set(right.split())
        if not left_tokens or not right_tokens:
            return 0
        overlap = left_tokens & right_tokens
        precision = len(overlap) / len(left_tokens)
        recall = len(overlap) / len(right_tokens)
        if precision + recall == 0:
            return 0
        return 100 * (2 * precision * recall) / (precision + recall)


def with_match(row, matcher):
    matched_id, score, method, status = matcher.match(row.get("product_name", ""))
    row["matched_master_whisky_id"] = matched_id
    row["match_score"] = score
    row["match_method"] = method
    row["match_status"] = status
    row["approval_status"] = "pending_review"
    row["import_recommendation"] = "review_before_import"
    row["normalized_product_name"] = normalize_name(row.get("product_name", ""))
    return {field: row.get(field, "") for field in FIELDS}


def extract_score(html, text):
    candidates = [
        r"(?i)\bscore\b\s*[:\-]?\s*(\d{1,3}(?:\.\d+)?(?:\s*/\s*\d{1,3})?)",
        r"(?i)\brating\b\s*[:\-]?\s*(\d{1,3}(?:\.\d+)?(?:\s*/\s*\d{1,3})?)",
    ]
    for pattern in candidates:
        match = re.search(pattern, text) or re.search(pattern, html)
        if match:
            return clean_text(match.group(1))
    return ""


def collect_tasting_source(source_system, config, matcher):
    adapter = config["adapter"](db_path=DB_PATH, request_delay=0.25)
    rows = []
    details = []

    for url in config["urls"]:
        html = adapter.fetch_html(url, timeout=20)
        if not html:
            details.append((url, "FETCH_ERROR", ""))
            continue
        try:
            parsed = adapter.parse(url, html) or {}
        except Exception as exc:
            details.append((url, "PARSE_ERROR", str(exc)))
            continue

        row = {
            "source_system": source_system,
            "source_type": config["source_type"],
            "product_name": clean_text(parsed.get("product_name")),
            "source_url": url,
            "nose": clean_text(parsed.get("nose")),
            "palate": clean_text(parsed.get("palate")),
            "finish": clean_text(parsed.get("finish")),
            "conclusion": clean_text(parsed.get("conclusion")),
            "score": clean_text(parsed.get("score")),
            "rating": clean_text(parsed.get("rating")),
            "price": clean_text(parsed.get("price")),
            "top_flavors": clean_text(parsed.get("top_flavors")),
            "source_profile": clean_text(parsed.get("source_profile")),
            "converted_flavor_profile": clean_text(parsed.get("converted_flavor_profile")),
            "flavour_camp": clean_text(parsed.get("flavour_camp")),
            "similar_whiskies": clean_text(parsed.get("similar_whiskies")),
            "source_verified": config["source_verified"],
            "notes_for_review": "",
        }
        if not row["score"]:
            row["score"] = extract_score(html, BeautifulSoup(html, "html.parser").get_text(" ", strip=True))

        if not row["product_name"] or row["product_name"].lower() == "unknown product":
            details.append((url, "PARSE_EMPTY", "missing product_name"))
            continue
        if not has_tasting_note(row):
            details.append((url, "PARSE_EMPTY", "missing tasting note fields"))
            continue

        rows.append(with_match(row, matcher))
        details.append((url, "SUCCESS", row["product_name"]))

    return rows, details


def parse_twe_flavour_categories(url, html, matcher):
    soup = BeautifulSoup(html, "html.parser")
    rows = []
    seen = set()

    for link in soup.find_all("a", href=True):
        text = clean_text(link.get_text(" ", strip=True))
        href = link["href"]
        if not text:
            continue
        href_lower = href.lower()
        text_lower = text.lower()
        category_like = (
            "flavour" in href_lower
            or "flavour" in text_lower
            or "smoky" in text_lower
            or "peat" in text_lower
            or "rich" in text_lower
            or "delicate" in text_lower
            or "fruity" in text_lower
        )
        if not category_like:
            continue
        if len(text) > 90 or len(text) < 3:
            continue
        category_url = urljoin(url, href)
        key = (text.lower(), category_url)
        if key in seen:
            continue
        seen.add(key)
        row = {
            "source_system": "thewhiskyexchange",
            "source_type": "flavour_category",
            "product_name": text,
            "source_url": category_url,
            "source_profile": text,
            "converted_flavor_profile": text,
            "flavour_camp": text,
            "source_verified": 1,
            "notes_for_review": "TWE Whisky by Flavour category row; not a tasting note.",
        }
        rows.append(with_match(row, matcher))
        if len(rows) >= 25:
            break

    if rows:
        return rows

    title = clean_text(soup.find("h1").get_text(" ", strip=True) if soup.find("h1") else soup.title.string if soup.title else "")
    if title:
        row = {
            "source_system": "thewhiskyexchange",
            "source_type": "flavour_category",
            "product_name": title,
            "source_url": url,
            "source_profile": title,
            "converted_flavor_profile": title,
            "flavour_camp": title,
            "source_verified": 1,
            "notes_for_review": "TWE page title fallback; no tasting notes parsed.",
        }
        return [with_match(row, matcher)]
    return []


def collect_twe(config, matcher):
    from scripts.tasting_notes.base_adapter import BaseAdapter

    class FetchOnlyAdapter(BaseAdapter):
        def parse(self, url, html):
            return {}

    adapter = FetchOnlyAdapter(db_path=DB_PATH, request_delay=0.25)
    rows = []
    details = []
    for url in config["urls"]:
        html = adapter.fetch_html(url, timeout=20)
        if not html:
            details.append((url, "FETCH_ERROR", ""))
            continue
        parsed_rows = parse_twe_flavour_categories(url, html, matcher)
        rows.extend(parsed_rows)
        details.append((url, "SUCCESS" if parsed_rows else "PARSE_EMPTY", f"{len(parsed_rows)} category rows"))
    return rows, details


def write_csv(filename, rows):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return path


def write_collection_report(summary, details):
    os.makedirs(REPORTS_DIR, exist_ok=True)
    path = os.path.join(REPORTS_DIR, "194_real_external_source_collection_report.md")
    lines = [
        "# Real External Source Collection Report",
        "",
        "No database tables were written. Outputs are CSV candidates only.",
        "",
        "## Source Summary",
    ]
    for source, count in summary.items():
        lines.append(f"- {source}: {count} candidate rows")
    lines.extend(["", "## URL Results"])
    for source, source_details in details.items():
        lines.append(f"### {source}")
        for url, status, note in source_details:
            suffix = f" - {note}" if note else ""
            lines.append(f"- {status}: {url}{suffix}")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")
    return path


def main():
    matcher = MasterWhiskyMatcher()
    summary = {}
    details = {}

    for source_system, config in SEEDS.items():
        if source_system == "thewhiskyexchange":
            rows, source_details = collect_twe(config, matcher)
        else:
            rows, source_details = collect_tasting_source(source_system, config, matcher)
        write_csv(config["output"], rows)
        summary[source_system] = len(rows)
        details[source_system] = source_details
        print(f"{source_system}: {len(rows)} rows")

    report_path = write_collection_report(summary, details)
    print(f"Collection report: {report_path}")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
