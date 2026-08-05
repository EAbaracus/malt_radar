#!/usr/bin/env python3
"""
P96-live — Whiskybase Live Scraper via Patchright (Playwright) + Cookie Injection

Bypasses both Cloudflare (via Chromium) and member auth wall (via session cookie).
Feeds scraped bottle pages directly into the existing WhiskybaseAdapter for parsing.

Usage:
  1. Manual:  python p96_scraper.py --interactive-login
       Opens browser, login manually, saves cookies to data/auth/whiskybase_cookies.json

  2. Scrape:  python p96_scraper.py --urls-file bottle_urls.txt
       Reads URLs from file, scrapes each, writes evidence JSONL to output/staging/

  3. Scrape one:  python p96_scraper.py --url https://www.whiskybase.com/whiskies/whisky/123456
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

# ── repo paths ──────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OUTPUT_STAGING = REPO_ROOT / "output" / "staging"
AUTH_DIR = REPO_ROOT / "data" / "auth"
AUTH_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_STAGING.mkdir(parents=True, exist_ok=True)

# ── sys.path for adapter imports ────────────────────────────────────
_ACQUISITION = str(HERE)
_MRKEP = str(HERE.parent)
for p in [_ACQUISITION, _MRKEP]:
    if p not in sys.path:
        sys.path.insert(0, p)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("p96-scraper")

COOKIE_FILE = AUTH_DIR / "whiskybase_cookies.json"

SOURCE_ID = "whiskybase"
AUTHORITY_TIER = "T1_authoritative"
EVIDENCE_CONFIDENCE = 0.95
CRAWL_DELAY = 2.0  # seconds between pages


# ── helpers ─────────────────────────────────────────────────────────

def make_evidence_id(source_id: str, whisky_id: str, field: str, timestamp: str) -> str:
    raw = f"{source_id}|{whisky_id}|{field}|{timestamp}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def build_envelope(
    whisky_id: str, field_name: str, field_value: Any,
    quote: str, source_url: str,
) -> Dict[str, Any]:
    ts = datetime.now(timezone.utc).isoformat()
    return {
        "evidence_id": make_evidence_id(SOURCE_ID, whisky_id, field_name, ts),
        "whisky_id": whisky_id,
        "source_id": SOURCE_ID,
        "authority_tier": AUTHORITY_TIER,
        "field_name": field_name,
        "field_value": field_value,
        "confidence": EVIDENCE_CONFIDENCE,
        "quote": quote,
        "source_url": source_url,
        "retrieved_at": ts,
        "provenance": {
            "source_type": "live_scrape",
            "fallback": False,
        },
    }


def is_real_bottle_page(markdown: str) -> bool:
    """Check if markdown looks like a real bottle page, not ToS/login."""
    if not markdown:
        return False
    lower = markdown.lower()
    # ToS/login pages
    if "terms and conditions" in lower[:300] and "whiskybase b.v." in lower[:300]:
        return False
    if "sign in" in lower[:200] and "password" in lower[:200]:
        return False
    if "create an account" in lower[:200]:
        return False
    # Real bottle pages have spec keywords
    spec_keywords = ["abv", "strength", "distillery", "region", "cask", "bottler", "age", "vintage", "rating"]
    return any(kw in lower for kw in spec_keywords)


def extract_bottle_data(markdown: str, url: str) -> List[Dict[str, Any]]:
    """Parse markdown with WhiskybaseAdapter, return evidence envelopes."""
    from adapters.whiskybase_adapter import WhiskybaseAdapter
    adapter = WhiskybaseAdapter()
    parsed = adapter.parse(markdown)
    if not parsed.get("evidence"):
        return []

    name = parsed.get("name", "unknown")
    whisky_id = f"WB-LIVE-{hashlib.sha256(url.encode()).hexdigest()[:8]}"

    envelopes = []
    for ev in parsed["evidence"]:
        env = build_envelope(
            whisky_id=whisky_id,
            field_name=ev["field_name"],
            field_value=ev["field_value"],
            quote=ev["quote"],
            source_url=url,
        )
        envelopes.append(env)
    return envelopes


# ── Playwright / Patchright scraper ─────────────────────────────────


def _import_playwright():
    """Return playwright.sync_api (verified working on this host)."""
    import playwright.sync_api
    logger.info("Using playwright.sync_api")
    return playwright.sync_api


def interactive_login() -> Dict[str, str]:
    """Open browser, let user login manually, save cookies."""
    pw_mod = _import_playwright()
    sync_pw = pw_mod.sync_playwright()
    pw_instance = sync_pw.start()

    try:
        browser = pw_instance.chromium.launch(
            headless=False,
            channel="chromium",
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()
        page.goto("https://www.whiskybase.com/login", wait_until="domcontentloaded")

        logger.info("Browser opened. Log in to Whiskybase manually, then press Enter here...")
        input("  Press Enter after login...")

        # Wait for navigation away from login page
        try:
            page.wait_for_url("**/whiskies/**", timeout=15000)
        except Exception:
            pass

        cookies = context.cookies("https://www.whiskybase.com")
        cookie_dict = {c["name"]: c["value"] for c in cookies}
        logger.info(f"Captured {len(cookie_dict)} cookies")

        # Save to file
        with open(COOKIE_FILE, "w") as f:
            json.dump(cookies, f, indent=2)
        logger.info(f"Cookies saved to {COOKIE_FILE}")

        browser.close()
        return cookie_dict

    except Exception as e:
        logger.exception(f"Login failed: {e}")
        return {}
    finally:
        pw_instance.stop()


def load_cookies() -> Optional[Dict[str, str]]:
    """Load saved cookies from file."""
    if not COOKIE_FILE.exists():
        logger.warning(f"No cookie file found at {COOKIE_FILE}")
        return None
    with open(COOKIE_FILE) as f:
        cookies = json.load(f)
    return {c["name"]: c["value"] for c in cookies}


def _real_chrome_exe() -> Optional[str]:
    """Locate the real installed Google Chrome (for correct TLS fingerprint
    binding of cf_clearance). Falls back to None (let Playwright pick)."""
    candidates = [
        os.environ.get("PROGRAMFILES", "") + r"\Google\Chrome\Application\chrome.exe",
        os.environ.get("PROGRAMFILES(X86)", "") + r"\Google\Chrome\Application\chrome.exe",
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Google", "Chrome", "Application", "chrome.exe"),
    ]
    for c in candidates:
        if c and os.path.exists(c):
            return c
    return None


def scrape_urls(urls: List[str], cookies: Optional[Dict[str, str]] = None, use_profile: bool = False, profile_dir: str = "", max_pages: int = 20) -> List[Dict[str, Any]]:
    """Scrape Whiskybase bottle URLs via Playwright with cookie injection.

    Returns list of evidence envelopes.
    """
    pw_mod = _import_playwright()
    sync_pw = pw_mod.sync_playwright()
    pw_instance = sync_pw.start()

    all_envelopes = []
    stats = {"scraped": 0, "skipped_tos": 0, "failed": 0, "parsed_fields": 0}

    try:
        chrome_exe = _real_chrome_exe()
        if use_profile:
            # Real Chrome profile via persistent context — required for
            # cf_clearance (TLS fingerprint binding). No cookie injection.
            user_data_dir = profile_dir or os.path.join(
                os.environ.get("LOCALAPPDATA", ""), "Google", "Chrome", "User Data"
            )
            logger.info(f"Using real Chrome profile (persistent): {user_data_dir}")
            context = pw_instance.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                headless=False,
                executable_path=chrome_exe,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                ],
            )
            browser = context.browser
        else:
            logger.info(f"Launching real Chrome: {chrome_exe}")
            browser = pw_instance.chromium.launch(
                headless=False,
                executable_path=chrome_exe,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                ],
            )
            context = browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/125.0.0.0 Safari/537.36"
                ),
            )

            # Inject cookies if provided
            if cookies:
                cookie_list = [
                    {
                        "name": k, "value": v,
                        "domain": ".whiskybase.com",
                        "path": "/",
                        "httpOnly": False,
                        "secure": True,
                    }
                    for k, v in cookies.items()
                ]
                context.add_cookies(cookie_list)
                logger.info(f"Injected {len(cookie_list)} cookies")

        page = context.new_page()

        for idx, url in enumerate(urls[:max_pages]):
            logger.info(f"[{idx+1}/{len(urls[:max_pages])}] {url}")
            try:
                body_text = ""
                # Retry loop: Cloudflare challenge may require a settle.
                for attempt in range(3):
                    page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    try:
                        page.wait_for_load_state("networkidle", timeout=15000)
                    except Exception:
                        pass
                    time.sleep(3)
                    title = page.title()
                    body_text = page.evaluate("() => document.body?.innerText || ''")
                    logger.info(f"  [attempt {attempt+1}] Title: {title[:80]}  Body: {len(body_text)} chars")
                    if is_real_bottle_page(body_text):
                        break
                    logger.warning(f"  -> Challenge/ToS page detected, retrying ({attempt+1}/3)")
                    time.sleep(CRAWL_DELAY)

                # Check if real bottle page
                if not is_real_bottle_page(body_text):
                    logger.warning(f"  -> Skipped (ToS/login/challenge page)")
                    stats["skipped_tos"] += 1
                    continue

                # Parse with adapter
                envelopes = extract_bottle_data(body_text, url)
                if envelopes:
                    all_envelopes.extend(envelopes)
                    stats["parsed_fields"] += len(envelopes)
                    logger.info(f"  -> Extracted {len(envelopes)} evidence fields")
                else:
                    logger.warning(f"  -> Adapter returned zero fields")

                stats["scraped"] += 1

                # Crawl delay
                time.sleep(CRAWL_DELAY)

            except Exception as e:
                logger.error(f"  FAILED: {e}")
                stats["failed"] += 1

        context.close()

    except Exception as e:
        logger.exception(f"Scraper error: {e}")
    finally:
        pw_instance.stop()

    logger.info(f"\nScrape complete: {stats['scraped']} pages, {stats['parsed_fields']} evidence fields, "
                f"{stats['skipped_tos']} skipped, {stats['failed']} failed")
    return all_envelopes


# ── URL discovery ───────────────────────────────────────────────────


def search_whiskybase(query: str, cookies: Dict[str, str], max_results: int = 30) -> List[str]:
    """Search Whiskybase internal search, return bottle page URLs."""
    pw_mod = _import_playwright()
    sync_pw = pw_mod.sync_playwright()
    pw_instance = sync_pw.start()

    urls = []
    try:
        browser = pw_instance.chromium.launch(headless=True)
        context = browser.new_context()
        # Inject cookies
        cookie_list = [
            {"name": k, "value": v, "domain": ".whiskybase.com", "path": "/", "httpOnly": False, "secure": True}
            for k, v in cookies.items()
        ]
        context.add_cookies(cookie_list)
        page = context.new_page()

        search_url = f"https://www.whiskybase.com/search?q={requests.utils.quote(query)}"
        page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
        time.sleep(2)

        # Extract all links containing /whisky/
        links = page.evaluate("""
            () => Array.from(document.querySelectorAll('a[href*="/whisky/"]'))
                .map(a => a.href)
                .filter(h => h.match(/whiskybase\.com\/whisky\/\d+/))
        """)
        urls = list(set(links))
        logger.info(f"Search '{query}': {len(urls)} bottle URLs found")

        browser.close()
    except Exception as e:
        logger.exception(f"Search error: {e}")
    finally:
        pw_instance.stop()

    return urls


# ── CLI ─────────────────────────────────────────────────────────────


def main():
    import argparse

    parser = argparse.ArgumentParser(description="P96-live Whiskybase Cookie Scraper")
    parser.add_argument("--interactive-login", action="store_true", help="Open browser, login manually, save cookies")
    parser.add_argument("--use-profile", action="store_true",
                        help="Use real Chrome profile (launch_persistent_context) instead of cookie injection. "
                             "Required for cf_clearance to work (TLS fingerprint binding).")
    parser.add_argument("--profile-dir", type=str, default="",
                        help="Chrome user data dir. Default: auto-detect from %%LOCALAPPDATA%%")
    parser.add_argument("--urls-file", type=str, default="", help="File with one bottle URL per line")
    parser.add_argument("--search", type=str, default="", help="Search Whiskybase for bottles matching query")
    parser.add_argument("--output", type=str, default=str(OUTPUT_STAGING / "whiskybase_scraped_evidence.jsonl"),
                        help="Output evidence JSONL path")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be scraped, don't write")
    args = parser.parse_args()

    # Step 1: Interactive login
    if args.interactive_login:
        interactive_login()
        return 0

    # Step 2: Load cookies.
    # Cookie injection is required only on the cookie-injection path.
    # --use-profile supplies auth via a real Chrome profile, so it must
    # not incorrectly require cookie injection first.
    cookies = None
    if not args.use_profile:
        cookies = load_cookies()
        if not cookies:
            logger.error("No cookies found. Run with --interactive-login first.")
            return 1

    # Step 3: Gather URLs
    urls = []
    if args.urls_file:
        with open(args.urls_file) as f:
            urls.extend(line.strip() for line in f if line.strip())

    if args.search:
        found = search_whiskybase(args.search, cookies)
        urls.extend(found)

    if not urls:
        logger.error("No URLs provided. Use --urls-file or --search.")
        return 1

    logger.info(f"Total URLs to scrape: {len(urls)}")

    if args.dry_run:
        for u in urls:
            print(f"  {u}")
        logger.info(f"DRY RUN — would scrape {len(urls)} pages")
        return 0

    # Step 4: Scrape
    envelopes = scrape_urls(
        urls, cookies,
        use_profile=args.use_profile,
        profile_dir=args.profile_dir,
    )
    logger.info(f"Total evidence envelopes: {len(envelopes)}")

    # Step 5: Dedup by evidence_id
    seen = set()
    unique = []
    for env in envelopes:
        eid = env["evidence_id"]
        if eid not in seen:
            seen.add(eid)
            unique.append(env)

    logger.info(f"After dedup: {len(unique)} unique evidence records")

    # Step 6: Write output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for env in unique:
            f.write(json.dumps(env, ensure_ascii=False) + "\n")

    logger.info(f"Evidence written to {output_path}")
    return 0 if unique else 1


if __name__ == "__main__":
    import requests as _
    sys.exit(main())
