"""Controlled live crawl: Fıçı Sertliği (ficisertligi.com) + The Viskici (theviskici.com).

STAGING-ONLY. Never writes production.db / knowledge.db.

- robots: both sources fully open (fici: no Disallow; theviskici: only
  /wp-admin/ disallowed). Re-verified live 2026-08-03.
- Discovery: deterministic from each source's sitemap (robots-sanctioned
  index), NOT homepage scraping.
- Bounded: min 2s delay, concurrency 1, descriptive UA.
- EXCERPT_POLICY: stores only score, nose/palate/finish section text (short),
  facts + metadata, author, source_url; raw HTML is hashed (content_hash),
  never stored.
- Flavor vector: TR tokens -> English descriptor (tr_flavor_lexicon) ->
  canonical FlavorMapper axis; +0.2 per mention, clamped to 1.0. R4 [0,1].

Usage:
  python mr-kep/editorial/scripts/crawl_fici_theviskici.py --limit N --source fici
  python mr-kep/editorial/scripts/crawl_fici_theviskici.py            # full crawl
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(r"C:/Users/eltun/Documents/malt radar CLEAN")
ADAPTERS = ROOT / "mr-kep" / "editorial" / "adapters"
sys.path.insert(0, str(ROOT / "mr-kep"))
sys.path.insert(0, str(ADAPTERS))

import requests  # noqa: E402

from tr_flavor_lexicon import TR_BIGRAMS, TR_TOKEN_RE, map_tr_token, tr_lower  # noqa: E402
from d4_reducer.flavor_mapper import FlavorMapper  # noqa: E402

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 MaltRadarBot/1.0")
# NOTE: keyifadami.net's WAF 403s any UA containing "research" (verified live
# 2026-08-03: same UA with/without the word -> 403 vs 200). Keep UA word-free.
DELAY_S = 2.0

SOURCES = {
    "fici": {
        "source_id": "ficisertligi",
        "sitemap": "https://ficisertligi.com/sitemap.xml",
        "adapter": None,  # set below to avoid circular import
    },
    "theviskici": {
        "source_id": "theviskici",
        "sitemap": "https://theviskici.com/sitemap.xml",
    },
    "whiskysaga": {
        "source_id": "whiskysaga",
        "sitemap": "https://www.whiskysaga.com/sitemap.xml",
    },
    "viskibilgi": {
        "source_id": "viskibilgi",
        # Direct blog-posts sitemap (the index's `-post-` sub-sitemap filter does
        # not match `blog-posts-sitemap.xml`).
        "sitemap": "https://www.viskibilgi.com/blog-posts-sitemap.xml",
    },
    "keyifadami": {
        "source_id": "keyifadami",
        "sitemap": "https://keyifadami.net/post-sitemap.xml",
        "include_pattern": r"viski-tadimi",
        "sitemap_cache": "C:/Users/eltun/Documents/malt radar CLEAN/.tmp_fici/ka_posts.xml",
    },
    "scotchnoob": {
        "source_id": "scotchnoob",
        "sitemap": "https://scotchnoob.com/sitemap.xml",
        "include_pattern": r"/20\d\d/\d\d/\d\d/",
    },
    "bourbonculture": {
        "source_id": "thebourbonculture",
        "sitemap": "https://thebourbonculture.com/post-sitemap.xml",
        # joint-reviews/ = multi-taster compilation pages (Score: 98/100),
        # not single-whisky reviews — exclude from discovery.
        "include_pattern": r"whiskey-reviews/(?!joint-reviews/)",
    },
    "rumhowler": {
        "source_id": "therumhowlerblog",
        "sitemap": "https://therumhowlerblog.com/sitemap.xml",
        "include_pattern": r"/whisky-reviews/",
    },
    "greatdrams": {
        "source_id": "greatdrams",
        "sitemap": "https://greatdrams.com/post-sitemap.xml",
        "include_pattern": r"-review",
    },
}

DDL = """
CREATE TABLE IF NOT EXISTS staging_editorial_reviews (
    evidence_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    source_url TEXT NOT NULL UNIQUE,
    authority_tier TEXT NOT NULL,
    author TEXT,
    published_date TEXT,
    content_hash TEXT NOT NULL,
    raw_name TEXT NOT NULL,
    normalized_name TEXT NOT NULL,
    matched_master_whisky_id TEXT,
    match_status TEXT NOT NULL DEFAULT 'unmatched',
    match_confidence REAL,
    score_value REAL,
    score_scale_max REAL,
    score_normalized REAL,
    nose TEXT, palate TEXT, finish TEXT, conclusion TEXT,
    flavor_vector_json TEXT NOT NULL,
    metadata_json TEXT,
    evidence_confidence REAL NOT NULL,
    extraction_method TEXT NOT NULL,
    provenance_state TEXT NOT NULL DEFAULT 'staging_unverified',
    ingested_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def norm_name(name: str) -> str:
    """Canonical MR-KEP name normalization (plain lower — NOT tr_lower, whose
    I->ı rule corrupts English names like 'Irish Whiskey')."""
    s = (name or "").lower().replace("'", "").replace("\u2019", "")
    if s.startswith("the "):
        s = s[4:]
    return "".join(ch for ch in s if ch.isalnum())


def sitemap_urls(sitemap: str, source_id: str, include_pattern: str | None = None,
                 cache_file: str | None = None) -> list[str]:
    """Fetch sitemap (or sitemap index -> post sitemaps) and return article URLs.

    Falls back to a local cached sitemap when the live fetch is blocked (WAF
    403s are transient; a cached copy keeps runs deterministic — P9 pattern).
    """
    xml = ""
    try:
        r = requests.get(sitemap, headers={"User-Agent": UA}, timeout=30)
        r.raise_for_status()
        if "<loc>" not in r.text and "urlset" not in r.text and "sitemapindex" not in r.text:
            # 202/captcha/HTML shell — not a sitemap.
            raise ValueError("response is not a sitemap (captcha/HTML)")
        xml = r.text
    except Exception:
        if cache_file and Path(cache_file).exists():
            xml = Path(cache_file).read_text(encoding="utf-8", errors="replace")
            print(f"  [sitemap] live fetch blocked; using cache {cache_file}")
        else:
            raise
    # Sitemap index -> sub-sitemaps (theviskici monthly post files). Only
    # follow article-post sitemaps; page/misc sitemaps are static pages, not
    # whisky reviews.
    subs = re.findall(r"<loc>\s*(https?://[^<]*sitemap[^<]*)</loc>", xml)
    locs: list[str] = []
    if subs:
        for s in subs:
            # Only article-post sitemaps carry whisky reviews; page/misc
            # sitemaps are static pages (skip them).
            if "-post-" not in s:
                continue
            rr = requests.get(s, headers={"User-Agent": UA}, timeout=30)
            locs += re.findall(r"<loc>\s*(https?://[^<]*)</loc>", rr.text)
            time.sleep(DELAY_S)
    else:
        locs = re.findall(r"<loc>\s*(https?://[^<]*)</loc>", xml)

    out, seen = [], set()
    for u in locs:
        u = u.strip()
        path = urlparse(u).path.rstrip("/")
        if not path or path == "/":
            continue
        if path == "/blog" or path.endswith("/blog"):
            continue  # blog listing page, not an article
        if include_pattern and not re.search(include_pattern, u, re.I):
            continue  # per-source include filter (e.g. keyifadami: viski-tadimi)
        if any(x in path for x in ("/category/", "/tag/", "/author/", "/page/", "/feed",
                                   "/wp-", "/sitemap", "/about", "/contact", "/privacy",
                                   "/assets/", "/images/", "/cdn-cgi")):
            continue
        if "." in path.rsplit("/", 1)[-1] and not path.rsplit("/", 1)[-1].endswith((".html",)):
            continue  # asset files
        if u in seen:
            continue
        seen.add(u)
        out.append(u)
    return out


def _is_captcha(html: str) -> bool:
    """SiteGround/Cloudflare challenge shells: tiny HTML with a meta-refresh."""
    low = html.lower()
    return ("sgcaptcha" in low or "cf-chl" in low or "just a moment" in low
            or ("meta http-equiv=\"refresh\"" in low and "captcha" in low))


def fetch(url: str) -> str:
    """Fetch with requests; fall back to curl subprocess on 403 (some WAFs
    fingerprint python-requests' TLS — keyifadami.net blocks it while curl
    succeeds; robots stays respected, no spoofing)."""
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=30)
        if r.status_code == 200 and not _is_captcha(r.text):
            return r.text
        if r.status_code != 403 and r.status_code != 202:
            r.raise_for_status()
    except requests.RequestException:
        pass
    import subprocess
    out = subprocess.run(
        ["curl", "-sL", "--compressed", "-A", UA, "-m", "30",
         "-w", "\n__HTTP_CODE__%{http_code}", url],
        capture_output=True, text=True, timeout=40,
    )
    body = out.stdout
    code = None
    if "__HTTP_CODE__" in body:
        body, _, code_str = body.rpartition("__HTTP_CODE__")
        code = int(code_str.strip())
    if out.returncode != 0 or not body or code == 403 or code == 429:
        raise RuntimeError(
            f"curl fallback failed rc={out.returncode} http={code} for {url}")
    return body


def derive_vector(prose_blocks: list[str], mapper: FlavorMapper) -> dict:
    """Prose (TR or EN) -> canonical 7-axis vector (0..1).

    +0.2 per mapped mention, clamp 1.0. Token resolution order: (1) TR token
    -> English descriptor (tr_flavor_lexicon) -> axis; (2) the token itself as
    an English descriptor -> axis (English sources like Whisky Saga). A token
    counts once (TR match wins when both would hit).
    """
    counts = {ax: 0.0 for ax in mapper.CANONICAL_AXES}
    text = " ".join(b for b in (prose_blocks or []) if b)
    low = " " + tr_lower(text) + " "
    # Bigrams first (TR only; kuru üzüm, deniz tuzu, ...).
    for bg, en in TR_BIGRAMS.items():
        if bg in low:
            ax = mapper.get_axis(en)
            if ax:
                counts[ax] = min(1.0, counts[ax] + 0.2 * low.count(bg))
    for tok in TR_TOKEN_RE.findall(low):
        en = map_tr_token(tok)
        ax = mapper.get_axis(en) if en else mapper.get_axis(tok)
        if ax:
            counts[ax] = min(1.0, counts[ax] + 0.2)
    return counts


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="cap per source (0 = all)")
    ap.add_argument("--source", choices=["fici", "theviskici", "whiskysaga", "viskibilgi",
                                         "keyifadami", "scotchnoob", "bourbonculture",
                                         "rumhowler", "greatdrams"], default=None)
    ap.add_argument("--staging", default=str(ROOT / "output" / "staging" / "fici_theviskici_staging.db"))
    ap.add_argument("--urls-file", default=None,
                    help="file with one URL per line; overrides sitemap discovery "
                         "(targeted re-crawl of failed URLs)")
    ap.add_argument("--dry", action="store_true", help="discover only, no fetch")
    args = ap.parse_args()

    sys.path.insert(0, str(ADAPTERS))
    import importlib
    import types as _t
    pkg = _t.ModuleType("adapters")
    pkg.__path__ = [str(ADAPTERS)]
    sys.modules["adapters"] = pkg
    import adapters.editorial_base_adapter as base_mod
    sys.modules["adapters.editorial_base_adapter"] = base_mod
    import adapters.ficisertligi_adapter as fici_mod
    sys.modules["adapters.ficisertligi_adapter"] = fici_mod
    import adapters.theviskici_adapter as tv_mod
    sys.modules["adapters.theviskici_adapter"] = tv_mod
    import adapters.whiskysaga_adapter as ws_mod
    sys.modules["adapters.whiskysaga_adapter"] = ws_mod
    import adapters.viskibilgi_adapter as vb_mod
    sys.modules["adapters.viskibilgi_adapter"] = vb_mod
    import adapters.keyifadami_adapter as ka_mod
    sys.modules["adapters.keyifadami_adapter"] = ka_mod
    import adapters.scotchnoob_adapter as sn_mod
    sys.modules["adapters.scotchnoob_adapter"] = sn_mod
    import adapters.bourbonculture_adapter as bc_mod
    sys.modules["adapters.bourbonculture_adapter"] = bc_mod
    import adapters.rumhowler_adapter as rh_mod
    sys.modules["adapters.rumhowler_adapter"] = rh_mod
    import adapters.greatdrams_adapter as gd_mod
    sys.modules["adapters.greatdrams_adapter"] = gd_mod

    adapters = {
        "fici": fici_mod.FicisertligiAdapter(),
        "theviskici": tv_mod.TheViskiciAdapter(),
        "whiskysaga": ws_mod.WhiskySagaAdapter(),
        "viskibilgi": vb_mod.ViskiBilgiAdapter(),
        "keyifadami": ka_mod.KeyifAdamiAdapter(),
        "scotchnoob": sn_mod.ScotchNoobAdapter(),
        "bourbonculture": bc_mod.BourbonCultureAdapter(),
        "rumhowler": rh_mod.RumHowlerAdapter(),
        "greatdrams": gd_mod.GreatDramsAdapter(),
    }
    mapper = FlavorMapper()

    targets = ["fici", "theviskici"] if args.source is None else [args.source]
    results = {}
    staging = None
    inserted = 0
    skipped = 0
    for key in targets:
        src = SOURCES[key]
        if args.urls_file:
            urls = [ln.strip() for ln in Path(args.urls_file).read_text(
                encoding="utf-8", errors="replace").splitlines() if ln.strip()]
            print(f"[{key}] targeted re-crawl: {len(urls)} URLs from {args.urls_file}")
        else:
            urls = sitemap_urls(src["sitemap"], src["source_id"], src.get("include_pattern"),
                                src.get("sitemap_cache"))
        if args.limit:
            urls = urls[: args.limit]
        results[key] = {"source_id": src["source_id"], "total": len(urls), "parsed": 0,
                        "errors": 0}
        print(f"[{key}] {src['source_id']}: {len(urls)} URLs discovered")
        if args.dry:
            continue

        # Open the staging DB and write incrementally per article
        # (idempotent INSERT OR REPLACE by deterministic evidence_id). A crash
        # mid-crawl then loses at most the in-flight article, never the run.
        staging = Path(args.staging)
        staging.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(staging))
        conn.executescript(DDL)
        inserted = skipped = 0

        def insert_row(source_id: str, parsed, u: str, html: str, vec: dict) -> tuple:
            """INSERT OR REPLACE one row; commit immediately. Returns (ins, skp)."""
            c_hash = hashlib.sha256(html.encode("utf-8", "replace")).hexdigest()
            eid = "EDR-" + hashlib.sha256(f"{source_id}|{u}".encode()).hexdigest()[:16]
            score_norm = (parsed.score_value / parsed.score_scale_max) if (
                parsed.score_value is not None and parsed.score_scale_max
            ) else None
            vec_json = json.dumps(vec, ensure_ascii=False)
            meta_json = json.dumps(parsed.metadata, ensure_ascii=False) if parsed.metadata else None
            try:
                conn.execute(
                    """INSERT OR REPLACE INTO staging_editorial_reviews (
                        evidence_id, source_id, source_url, authority_tier, author,
                        published_date, content_hash, raw_name, normalized_name,
                        matched_master_whisky_id, match_status, match_confidence,
                        score_value, score_scale_max, score_normalized,
                        nose, palate, finish, conclusion, flavor_vector_json,
                        metadata_json, evidence_confidence, extraction_method,
                        provenance_state)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (eid, source_id, u, "T2_expert", parsed.author,
                     parsed.published_date, c_hash, parsed.raw_name,
                     norm_name(parsed.raw_name), None, "unmatched", None,
                     parsed.score_value, parsed.score_scale_max, score_norm,
                     parsed.nose, parsed.palate, parsed.finish, parsed.conclusion,
                     vec_json, meta_json, 0.8, "heuristic_tr_lexicon",
                     "staging_unverified"),
                )
                conn.commit()
                return 1, 0
            except sqlite3.IntegrityError:
                return 0, 1

        for i, u in enumerate(urls, 1):
            try:
                html = fetch(u)
                parsed = adapters[key].parse_article(u, html)
                if not parsed.raw_name:
                    results[key]["errors"] += 1
                    print(f"  [{i}/{len(urls)}] SKIP no-name {u}")
                    time.sleep(DELAY_S)
                    continue
                if not (parsed.nose or parsed.palate or parsed.finish):
                    # Not a tasting review (interview/news/listing/glossary page):
                    # no tasting sections -> no value for staging. Skip, don't
                    # stage an empty row.
                    results[key]["skipped_no_sections"] = results[key].get("skipped_no_sections", 0) + 1
                    print(f"  [{i}/{len(urls)}] SKIP no tasting sections {parsed.raw_name[:40]} | {u}")
                    time.sleep(DELAY_S)
                    continue
                vec = derive_vector([parsed.nose, parsed.palate, parsed.finish], mapper)
                results[key]["parsed"] += 1
                ins, skp = insert_row(src["source_id"], parsed, u, html, vec)
                inserted += ins
                skipped += skp
                print(f"  [{i}/{len(urls)}] OK {parsed.raw_name[:48]} | score={parsed.score_value}")
            except Exception as e:  # noqa: BLE001
                results[key]["errors"] += 1
                print(f"  [{i}/{len(urls)}] ERR {type(e).__name__}: {e} ({u})")
            time.sleep(DELAY_S)

        conn.close()
        results[key]["inserted"] = inserted
        results[key]["skipped_db"] = skipped

    if args.dry:
        for key, r in results.items():
            print(f"[{key}] dry: {r['total']} URLs, no fetch")
        return 0

    total = sum(r["parsed"] for r in results.values())
    errs = sum(r["errors"] for r in results.values())
    skips = sum(r.get("skipped_no_sections", 0) for r in results.values())
    print(f"\n=== STAGING SUMMARY ===")
    print(f"DB: {staging}")
    for key, r in results.items():
        print(f"{r['source_id']}: total={r['total']} parsed={r['parsed']} "
              f"errors={r['errors']} skips_no_sections={r.get('skipped_no_sections', 0)}")
    print(f"inserted={inserted} skipped={skipped} total_parsed={total} "
          f"total_errors={errs} total_skips_no_sections={skips}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
