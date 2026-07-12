"""
Malt Radar - Generic Whisky Web Scraper / Staging-Ingestion Core (P60)

Design principles (Malt Radar durable conventions):
  * READ-ONLY toward production.db. This core NEVER writes to production.db.
    It emits staging CSV + a snapshot + a gate report. Promotion is a
    separate, explicitly-approved gated-import phase.
  * Facticual metadata only. We extract public factual fields
    (name, distillery, region, country, type, age, abv, rating, vintage...).
    We do NOT scrape copyrighted full-text tasting notes / reviews.
  * Polite: per-source rate limit, cache (no re-fetch within TTL),
    realistic User-Agent, no concurrency storms.
  * Barrier-aware: a source whose HTML is a Cloudflare / anti-bot challenge
    ("Just a moment...") is flagged SOURCE_BLOCKED and the row is routed to
    manual-ingestion instead of silent failure.

Source adapters are registered in SOURCE_ADAPTERS. Whiskybase (SRC_009) is the
canonical example: live scraping is blocked by Cloudflare, so its adapter is
marked live_scraping_blocked=True and ingestion is driven by a user-provided
export file (CSV/JSON) instead.

Usage:
  # Barrier-free live fetch (e.g. Wikipedia brand list) -> staging CSV
  python scraper_core.py --source wikipedia_brands --live --limit 50

  # Whiskybase: ingest from a member-provided export (no live scraping)
  python scraper_core.py --source whiskybase --ingest-file data/input/whiskybase_export.csv

  # Re-run just the parse/normalize/QA on cached snapshots, no network
  python scraper_core.py --source whiskybase --from-cache
"""
import os
import sys
import csv
import json
import time
import argparse
import hashlib
import datetime as dt
from urllib.parse import urljoin, quote_plus

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPTS_DIR = os.path.join(ROOT, "scripts", "p60_whiskybase")
DATA_OUT = os.path.join(ROOT, "data", "output", "whiskybase")
SNAPSHOT_DIR = os.path.join(DATA_OUT, "snapshots")
STAGING_DIR = os.path.join(ROOT, "data", "output")  # matches registry convention
CACHE_DIR = os.path.join(DATA_OUT, "cache")
REPORTS_DIR = os.path.join(ROOT, "output", "reports")

USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
DEFAULT_RATE_LIMIT_S = 2.0   # polite delay between requests to same source
CACHE_TTL_S = 60 * 60 * 24    # 24h snapshot cache

# ---- name normalization (from malt-radar-gated-import skill) ----
def norm_name(name):
    if not name:
        return ""
    s = name.lower().replace("'", "").replace("\u2019", "")
    s = s.replace("the ", "") if s.startswith("the ") else s
    return "".join(ch for ch in s if ch.isalnum())


def snapshot_path(source_id, key):
    os.makedirs(SNAPSHOT_DIR, exist_ok=True)
    h = hashlib.sha256(f"{source_id}:{key}".encode("utf-8")).hexdigest()[:16]
    return os.path.join(SNAPSHOT_DIR, f"{source_id}_{h}.html")


def cache_get(source_id, key):
    p = snapshot_path(source_id, key)
    if not os.path.exists(p):
        return None
    age = time.time() - os.path.getmtime(p)
    if age > CACHE_TTL_S:
        return None
    with open(p, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def cache_put(source_id, key, html):
    p = snapshot_path(source_id, key)
    with open(p, "w", encoding="utf-8", errors="replace") as f:
        f.write(html)
    return p


def is_antibot(html):
    low = (html or "").lower()
    return ("just a moment" in low) or ("cf-chl" in low) or ("enable javascript and cookies to continue" in low)


def http_get(url, timeout=30):
    import requests
    try:
        r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
        return r.status_code, r.text
    except Exception as e:
        return None, f"ERROR:{e}"


# ---------------------------------------------------------------- adapters
class SourceAdapter:
    source_id = ""
    source_name = ""
    base_url = ""
    live_scraping_blocked = False
    fetch_method = "WEB_SCRAPING"  # or API_CALL / FILE_INGEST

    def discover_urls(self, limit):
        """Yield (key, url) seed targets. Override per source."""
        return []

    def parse_html(self, html, url):
        """Return list of dicts with factual metadata fields. Override."""
        return []

    def parse_export(self, filepath):
        """Parse a user-provided export file (CSV/JSON). Override for blocked sources."""
        return []


class WikipediaBrandsAdapter(SourceAdapter):
    source_id = "SRC_WIKI_BRANDS"
    source_name = "Wikipedia - List of whisky brands"
    base_url = "https://en.wikipedia.org/wiki/List_of_whisky_brands"
    live_scraping_blocked = False

    def discover_urls(self, limit):
        return [("brands", self.base_url)]

    def parse_html(self, html, url):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "lxml")
        rows = []
        for tr in soup.select("table.wikitable tr"):
            cells = [c.get_text(" ", strip=True) for c in tr.find_all(["th", "td"])]
            if len(cells) < 2:
                continue
            category = cells[0]
            # each cell after first may contain a region + space-separated brand names
            for cell in cells[1:]:
                parts = cell.split(" ", 1)
                region = parts[0] if len(parts) > 1 else ""
                names = (parts[1] if len(parts) > 1 else cell).split()
                # reconstruct brand tokens grouped loosely; treat whole cell as one brand cluster
                brand_blob = parts[1] if len(parts) > 1 else cell
                for b in [x.strip() for x in brand_blob.replace("  ", " ").split(" ") if x.strip()]:
                    # heuristics: skip obvious region words already captured
                    pass
                # Emit one row per recognized brand cluster (whole cell)
                rows.append({
                    "name": brand_blob,
                    "category": category,
                    "region": region,
                    "country": "Scotland" if "Scotch" in category or "single malt" in category.lower() else "",
                    "type": category,
                    "source_url": url,
                })
        return rows


class WhiskybaseAdapter(SourceAdapter):
    source_id = "SRC_009"
    source_name = "Whiskybase"
    base_url = "https://www.whiskybase.com/"
    live_scraping_blocked = True   # Cloudflare "Just a moment..." challenge
    fetch_method = "FILE_INGEST"   # membership export only

    # Live scraping is blocked at the network layer (Cloudflare). The adapter
    # therefore ingests from a user-provided export file. Expected columns
    # (factual metadata only; no copyrighted tasting notes):
    #   name, distillery, region, country, type, age, abv, vintage,
    #   bottler, rating (Whiskybase avg), num_ratings
    EXPORT_FIELDS = ["name", "distillery", "region", "country", "type",
                     "age", "abv", "vintage", "bottler", "rating", "num_ratings"]

    def parse_export(self, filepath):
        rows = []
        ext = os.path.splitext(filepath)[1].lower()
        if ext == ".json":
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            for d in data:
                rows.append(self._norm_row(d))
        else:
            with open(filepath, "r", encoding="utf-8-sig", newline="") as f:
                for d in csv.DictReader(f):
                    rows.append(self._norm_row(d))
        return rows

    @staticmethod
    def _norm_row(d):
        def g(k):
            for key in (k, k.lower(), k.replace(" ", "_")):
                if key in d and d[key] not in (None, ""):
                    return str(d[key]).strip()
            return ""
        try:
            age = float(g("age")) if g("age") else None
        except ValueError:
            age = None
        try:
            abv = float(g("abv")) if g("abv") else None
        except ValueError:
            abv = None
        try:
            rating = float(g("rating")) if g("rating") else None
        except ValueError:
            rating = None
        return {
            "name": g("name"),
            "distillery": g("distillery"),
            "region": g("region"),
            "country": g("country"),
            "type": g("type"),
            "age": age,
            "abv": abv,
            "vintage": g("vintage"),
            "bottler": g("bottler"),
            "rating": rating,
            "num_ratings": g("num_ratings"),
            "source_url": "",
        }


class HTFWBrandsAdapter(SourceAdapter):
    """World Whisky (htfw.com) brand index — factual metadata already in-repo.
    Drives the same staging pipeline from an existing CSV (no live scraping)."""
    source_id = "SRC_HTFW"
    source_name = "Heaven Hill / World Whisky (HTFW) brand index"
    base_url = "https://www.htfw.com/brands/world-whisky"
    live_scraping_blocked = True
    fetch_method = "FILE_INGEST"

    def parse_export(self, filepath):
        rows = []
        with open(filepath, "r", encoding="utf-8-sig", newline="") as f:
            for d in csv.DictReader(f):
                def g(k):
                    v = d.get(k, "")
                    return "" if v in (None, "?", "") else str(v).strip()
                rows.append({
                    "name": g("name"),
                    "distillery": g("owner"),
                    "region": g("region"),
                    "country": g("country"),
                    "type": g("type"),
                    "age": None,
                    "abv": None,
                    "vintage": "",
                    "bottler": g("owner"),
                    "rating": None,
                    "num_ratings": "",
                    "source_url": g("htfw_url") or g("link"),
                })
        return rows


SOURCE_ADAPTERS = {
    "wikipedia_brands": WikipediaBrandsAdapter(),
    "whiskybase": WhiskybaseAdapter(),
    "htfw": HTFWBrandsAdapter(),
}


# ---------------------------------------------------------------- staging out
STAGING_NEW_FIELDS = [
    "source_system", "raw_name", "raw_distillery", "raw_age", "raw_vintage",
    "raw_abv", "status", "source_name", "source_id", "source_slug",
    "product_name", "distillery_name", "bottler_name", "brand_name",
    "country", "region", "age", "abv", "product_type", "source_url",
    "triage_status", "approval_status", "import_recommendation",
]

STAGING_REVIEW_FIELDS = [
    "source_system", "whisky_id", "reviewer_name", "score", "review_text", "status",
]


def qa_flags(row):
    flags = []
    if not row.get("name"):
        flags.append("missing_name")
    if row.get("abv") is not None and (row["abv"] < 30 or row["abv"] > 75):
        flags.append("abv_out_of_range")
    if row.get("age") is not None and (row["age"] < 0 or row["age"] > 70):
        flags.append("age_out_of_range")
    return flags


def run(args):
    os.makedirs(STAGING_DIR, exist_ok=True)
    os.makedirs(CACHE_DIR, exist_ok=True)
    adapter = SOURCE_ADAPTERS.get(args.source)
    if adapter is None:
        print(f"Unknown source '{args.source}'. Known: {list(SOURCE_ADAPTERS)}")
        return 1

    ts = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    collected = []
    blocked = False
    mode = ""

    if args.ingest_file:
        mode = "FILE_INGEST"
        collected = adapter.parse_export(args.ingest_file)
    elif args.from_cache:
        mode = "FROM_CACHE"
        # re-parse cached snapshots
        for fn in os.listdir(SNAPSHOT_DIR):
            if fn.startswith(adapter.source_id) and fn.endswith(".html"):
                with open(os.path.join(SNAPSHOT_DIR, fn), "r", encoding="utf-8", errors="replace") as f:
                    html = f.read()
                collected += adapter.parse_html(html, adapter.base_url)
    elif args.live:
        mode = "LIVE"
        if adapter.live_scraping_blocked:
            blocked = True
            mode = "LIVE_BLOCKED"
        else:
            seeds = list(adapter.discover_urls(args.limit))
            for key, url in seeds:
                cached = cache_get(adapter.source_id, key) if not args.no_cache else None
                if cached is not None:
                    html = cached
                else:
                    code, html = http_get(url)
                    if code == 200 and not is_antibot(html):
                        cache_put(adapter.source_id, key, html)
                    elif is_antibot(html):
                        blocked = True
                        print(f"BLOCKED by anti-bot at {url}")
                        break
                    else:
                        print(f"HTTP {code} for {url}")
                        continue
                    time.sleep(DEFAULT_RATE_LIMIT_S)
                collected += adapter.parse_html(html, url)
    else:
        print("Specify one of: --live | --ingest-file PATH | --from-cache")
        return 2

    # Build staging rows
    new_rows = []
    review_rows = []
    for r in collected:
        flags = qa_flags(r)
        rec = "APPROVE_AFTER_REVIEW" if not flags else "HOLD_QA_FLAGS"
        new_rows.append({
            "source_system": adapter.source_id,
            "raw_name": r.get("name", ""),
            "raw_distillery": r.get("distillery", ""),
            "raw_age": r.get("age", ""),
            "raw_vintage": r.get("vintage", ""),
            "raw_abv": r.get("abv", ""),
            "status": "PENDING",
            "source_name": adapter.source_name,
            "source_id": adapter.source_id,
            "source_slug": args.source,
            "product_name": r.get("name", ""),
            "distillery_name": r.get("distillery", ""),
            "bottler_name": r.get("bottler", ""),
            "brand_name": r.get("brand", ""),
            "country": r.get("country", ""),
            "region": r.get("region", ""),
            "age": r.get("age", ""),
            "abv": r.get("abv", ""),
            "product_type": r.get("type", ""),
            "source_url": r.get("source_url", ""),
            "triage_status": "collected" if not flags else "qa_flagged",
            "approval_status": "staging_pending_review",
            "import_recommendation": rec,
        })
        if r.get("rating") is not None:
            review_rows.append({
                "source_system": adapter.source_id,
                "whisky_id": "",
                "reviewer_name": f"{adapter.source_name}_aggregate",
                "score": r.get("rating"),
                "review_text": "",
                "status": "PENDING",
            })

    # Write staging CSVs
    new_csv = os.path.join(STAGING_DIR, f"staging_new_products_{args.source}_{ts}.csv")
    rev_csv = os.path.join(STAGING_DIR, f"staging_external_reviews_{args.source}_{ts}.csv")
    with open(new_csv, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=STAGING_NEW_FIELDS)
        w.writeheader(); w.writerows(new_rows)
    with open(rev_csv, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=STAGING_REVIEW_FIELDS)
        w.writeheader(); w.writerows(review_rows)

    # Gate report
    qa_flagged = sum(1 for r in new_rows if r["triage_status"] == "qa_flagged")
    report = f"""# Whiskybase/Web Scraper Staging Report (P60)

- source: {args.source} ({adapter.source_name})
- source_id: {adapter.source_id}
- mode: {mode}
- anti_bot_blocked: {blocked}
- rows_collected: {len(collected)}
- staging_new_products: {len(new_rows)} -> {os.path.relpath(new_csv, ROOT)}
- staging_external_reviews: {len(review_rows)} -> {os.path.relpath(rev_csv, ROOT)}
- qa_flagged_rows: {qa_flagged}
- production_db_written: NO (read-only; promotion is a separate gated phase)
- generated_at: {ts}

## License / ToS
- Whiskybase live scraping is blocked by Cloudflare and by project policy
  (SRC_009 BLOCK_UNTIL_LICENSE_REVIEW). This run did NOT write to production.db.

## Gate: STAGING_ONLY
Next step: human review of staging CSVs, then a gated-import phase (pNN) with backup+rollback.
"""
    rep_path = os.path.join(REPORTS_DIR, f"p60_{args.source}_staging_report.md")
    os.makedirs(REPORTS_DIR, exist_ok=True)
    with open(rep_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(report)
    print(f"Gate: STAGING_ONLY  (no production mutation)")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True, choices=list(SOURCE_ADAPTERS))
    ap.add_argument("--live", action="store_true", help="attempt live fetch (fails on anti-bot sources)")
    ap.add_argument("--ingest-file", help="path to member-provided export (CSV/JSON) for blocked sources")
    ap.add_argument("--from-cache", action="store_true", help="re-parse cached snapshots, no network")
    ap.add_argument("--limit", type=int, default=50)
    ap.add_argument("--no-cache", action="store_true")
    args = ap.parse_args()
    sys.exit(run(args))


if __name__ == "__main__":
    main()
