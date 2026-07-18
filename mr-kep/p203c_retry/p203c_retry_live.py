"""P203C-RETRY — Controlled Live Editorial Capture (bounded, offline-destructive-free).

Policy:
- Live HTTP only for approved sources: thewhiskyphiles, thedramble, whiskynotes_be,
  thewhiskeywash, wordsofwhisky. whiskymonster EXCLUDED (403 anti-bot, pending).
- robots.txt re-checked at runtime (wildcard-aware); only allowed URLs fetched.
- Descriptive UA, concurrency 1, min 5s delay, max 1 listing + 5 articles per source.
- EXCERPT_POLICY: NO raw HTML / full text persisted. Raw HTML kept in memory only;
  staging stores metadata + normalized facts + <=15-word attributed excerpt + 7-axis vector.
- Staging-only: data/p203c_staging/editorial_staging_retry.db. production.db/knowledge.db read-only.
"""
from __future__ import annotations
import os, sys, json, sqlite3, re, time, ssl, hashlib, urllib.request, urllib.error, urllib.parse, urllib.robotparser
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "mr-kep"))
from editorial.adapters import editorial_adapter_factory as factory
from editorial.editorial_knowledge_extractor import extract, CANONICAL_AXES
from editorial.matching import WhiskyRegistryMatcher

PROD = os.path.join(ROOT, "output", "import", "production.db")
KB   = os.path.join(ROOT, "output", "import", "knowledge.db")
STAGING_DIR = os.path.join(ROOT, "data", "p203c_staging")
STAGING_DB  = os.path.join(STAGING_DIR, "editorial_staging_retry.db")
MANIFEST    = os.path.join(ROOT, "mr-kep", "p203c_retry", "capture_manifest.json")
RUNRESULTS  = os.path.join(ROOT, "mr-kep", "p203c_retry", "run_results.json")
SCHEMA = json.load(open(os.path.join(ROOT, "mr-kep", "editorial", "schema", "editorial_review.schema.json"), encoding="utf-8"))

APP_SRC = ["thewhiskyphiles", "thedramble", "whiskynotes_be", "thewhiskeywash", "wordsofwhisky"]
EXCLUDED = {"whiskymonster"}
UA = "MaltRadar-EditorialResearchBot/0.1 (+https://example.com/bot; research crawl of approved editorial sources, respects robots.txt; contact editor@example.com)"
DELAY = 5.0
MAX_ARTICLES = 5
ctx = ssl.create_default_context()

os.makedirs(STAGING_DIR, exist_ok=True)
os.makedirs(os.path.dirname(MANIFEST), exist_ok=True)

import jsonschema


def fetch(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30, context=ctx) as r:
        data = r.read()
        return {"status": r.status, "content_type": r.headers.get("Content-Type", ""),
                "content_length": len(data), "html": data.decode("utf-8", "replace")}


def robots_rules(url: str):
    """Return (allow, matched_rule) using wildcard-aware prefix matching."""
    base = "https://" + urllib.parse.urlparse(url).netloc
    try:
        req = urllib.request.Request(base + "/robots.txt", headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=20, context=ctx) as r:
            txt = r.read().decode("utf-8", "replace")
    except Exception:
        return True, "robots-unreadable-allow"
    rules = []  # (type, regex)
    agent_block = False
    for line in txt.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        if line.lower().startswith("user-agent:"):
            agent = line.split(":", 1)[1].strip().lower()
            agent_block = (agent == "*" or agent in UA.lower())
            continue
        if not agent_block:
            continue
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        k = k.strip().lower(); v = v.strip()
        if k == "disallow":
            if not v:
                continue
            pat = re.escape(v).replace(r"\*", ".*").replace(r"\$", "$")
            rules.append(("disallow", re.compile(pat)))
        elif k == "allow":
            if not v:
                continue
            pat = re.escape(v).replace(r"\*", ".*").replace(r"\$", "$")
            rules.append(("allow", re.compile(pat)))
    path = urllib.parse.urlparse(url).path or "/"
    # most specific (longest pattern) wins; allow overrides disallow on tie
    best = None
    for typ, rg in rules:
        if rg.search(path):
            if best is None or len(rg.pattern) > len(best[1].pattern):
                best = (typ, rg)
    if best is None:
        return True, "no-rule"
    return (best[0] == "allow"), f"{best[0]}:{best[1].pattern}"


def robots_allows(url: str):
    allow, rule = robots_rules(url)
    return allow


def discover_via_sitemap(listing_url: str):
    """Fallback discovery using the source sitemap (robots-sanctioned index)."""
    base = "https://" + urllib.parse.urlparse(listing_url).netloc
    try:
        req = urllib.request.Request(base + "/robots.txt", headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=20, context=ctx) as r:
            txt = r.read().decode("utf-8", "replace")
        sm = [l.split(":", 1)[1].strip() for l in txt.splitlines()
              if l.lower().startswith("sitemap:") and l.split(":", 1)[1].strip()]
        urls = []
        for s in sm[:1]:
            with urllib.request.urlopen(urllib.request.Request(s, headers={"User-Agent": UA}), timeout=30, context=ctx) as r:
                smtxt = r.read().decode("utf-8", "replace")
            for m in re.findall(r"<loc>(.*?)</loc>", smtxt):
                if re.search(r"/20\d\d/", m):
                    urls.append(m)
        return urls[:MAX_ARTICLES]
    except Exception:
        return []


def crosswalk_lookup(dist: str):
    kc = sqlite3.connect(f"file:{KB}?mode=ro", uri=True); kc.execute("PRAGMA query_only=ON;")
    row = kc.execute("SELECT entity_id,canonical_name,confidence,match_method FROM distillery_crosswalk WHERE lower(external_name)=?", (dist.lower(),)).fetchone()
    kc.close()
    if row:
        return {"canonical_distillery_id": row[0], "canonical_name": row[1], "method": row[3], "conf": row[2], "unknown": False, "review_required": False}
    return {"canonical_distillery_id": None, "canonical_name": None, "method": None, "conf": 0.0, "unknown": True, "review_required": True}


def derive_all(name: str):
    toks = re.sub(r"[^a-z0-9 ]", " ", name.lower()).split(); found = []
    for i in range(len(toks), 0, -1):
        for j in range(0, len(toks) - i + 1):
            cand = " ".join(toks[j:j + i])
            if len(cand) >= 3:
                r = crosswalk_lookup(cand)
                if not r["unknown"]:
                    found.append((cand, r))
    if found:
        best = max(found, key=lambda x: len(x[0]))
        return best[0], best[1]
    return (toks[0] if toks else name), crosswalk_lookup(toks[0] if toks else name)


def build_record(adapter, url: str, html: str, content_hash: str):
    parsed = adapter.parse_article(url, html)
    res = extract(article=parsed, source_id=adapter.source_id, source_url=url,
                  content_hash=content_hash, authority_tier=adapter.authority_tier,
                  author=parsed.author, published_date=parsed.published_date)
    rec = res.record
    m = WhiskyRegistryMatcher(production_db=PROD)
    m.load_registry()
    mm = m.match(rec["whisky_identity"]["raw_name"])
    rec["whisky_identity"]["matched_master_whisky_id"] = mm.matched_master_whisky_id
    rec["whisky_identity"]["match_status"] = mm.match_status
    rec["whisky_identity"]["match_confidence"] = mm.match_confidence
    dr, cw = derive_all(rec["whisky_identity"]["raw_name"])
    rec["whisky_identity"]["distillery_raw"] = dr
    rec["distillery_crosswalk"] = cw
    # <=15-word attributed excerpt (quote only; attribution appended separately)
    concl = (rec["tasting_notes"].get("conclusion") or "")[:400]
    words = concl.split()
    quote = " ".join(words[:15])
    rec["excerpt_quote"] = quote
    rec["excerpt"] = f'{quote} — {rec["source"].get("author") or "Unknown"} ({url})'
    return rec, mm, cw


def schema_validate(rec):
    try:
        jsonschema.validate(instance=rec, schema=SCHEMA)
        return True, None
    except jsonschema.ValidationError as e:
        return False, f"{e.message} @ {'/'.join(map(str, e.path))}"


def init_staging(db_path: str):
    if os.path.exists(db_path):
        os.remove(db_path)
    conn = sqlite3.connect(db_path)
    conn.executescript("""
    PRAGMA foreign_keys = OFF;
    CREATE TABLE IF NOT EXISTS staging_editorial_reviews (
        evidence_id TEXT PRIMARY KEY,
        source_id TEXT NOT NULL,
        source_url TEXT NOT NULL UNIQUE,
        authority_tier TEXT NOT NULL,
        author TEXT,
        published_date TEXT,
        content_hash TEXT NOT NULL,
        http_status INTEGER,
        content_type TEXT,
        content_length INTEGER,
        fetched_at TEXT,
        raw_name TEXT NOT NULL,
        normalized_name TEXT NOT NULL,
        distillery_raw TEXT,
        distillery_canonical TEXT,
        canonical_distillery_id TEXT,
        crosswalk_method TEXT,
        crosswalk_confidence REAL,
        review_required INTEGER,
        match_status TEXT NOT NULL,
        match_confidence REAL,
        age TEXT,
        abv REAL,
        score_value REAL,
        score_scale_max REAL,
        score_normalized REAL,
        flavor_vector_json TEXT NOT NULL,
        excerpt_quote TEXT,
        excerpt TEXT,
        evidence_confidence REAL NOT NULL,
        extraction_method TEXT NOT NULL,
        provenance_state TEXT NOT NULL DEFAULT 'staging_unverified',
        ingested_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
    CREATE INDEX IF NOT EXISTS idx_src ON staging_editorial_reviews(source_id);
    CREATE INDEX IF NOT EXISTS idx_matched ON staging_editorial_reviews(canonical_distillery_id);
    """)
    return conn


def upsert(conn, rec, mm, cw, cap):
    src = rec["source"]; meta = rec.get("metadata", {})
    conn.execute("""
        INSERT INTO staging_editorial_reviews (
            evidence_id, source_id, source_url, authority_tier, author, published_date,
            content_hash, http_status, content_type, content_length, fetched_at,
            raw_name, normalized_name, distillery_raw, distillery_canonical, canonical_distillery_id,
            crosswalk_method, crosswalk_confidence, review_required, match_status, match_confidence,
            age, abv, score_value, score_scale_max, score_normalized, flavor_vector_json,
            excerpt_quote, excerpt, evidence_confidence, extraction_method, provenance_state
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(evidence_id) DO UPDATE SET
            match_status=excluded.match_status, match_confidence=excluded.match_confidence,
            distillery_canonical=excluded.distillery_canonical,
            canonical_distillery_id=excluded.canonical_distillery_id,
            crosswalk_method=excluded.crosswalk_method, crosswalk_confidence=excluded.crosswalk_confidence,
            review_required=excluded.review_required,
            ingested_at=datetime('now')
    """, (
        rec["evidence_id"], src["source_id"], src["url"], src["authority_tier"],
        src.get("author"), src.get("published_date"), src["content_hash_sha256"],
        cap["status"], cap["content_type"], cap["content_length"], cap["fetched_at"],
        rec["whisky_identity"]["raw_name"], rec["whisky_identity"]["normalized_name"],
        rec["whisky_identity"].get("distillery_raw"), cw["canonical_name"], cw["canonical_distillery_id"],
        cw["method"], cw["conf"], int(bool(cw["review_required"])), mm.match_status, mm.match_confidence,
        meta.get("age_statement"), meta.get("abv"), rec["score"].get("value"), rec["score"].get("scale_max"), rec["score"].get("normalized"),
        json.dumps(rec["flavor_vector"]), rec.get("excerpt_quote"), rec.get("excerpt"), rec["evidence"]["confidence"],
        rec["evidence"]["extraction_method"], rec["evidence"]["provenance_state"],
    ))
    conn.commit()


FORBIDDEN_NAMES = {"tastings","whiskynotes","whiskey reviews","the whiskyphiles","reviews","latest reviews","home",
                   "whisky notes","the dramble","the whiskey wash","wordsofwhisky"}
def _is_semantic(name):
    return name.strip().lower() not in FORBIDDEN_NAMES and len(name.strip()) > 0


def main():
    cache = {}
    manifest = {"run_at": datetime.now(timezone.utc).isoformat(), "sources": {}, "excluded": list(EXCLUDED)}
    forbidden_re = re.compile(r"/category/|/tag/|/author/|/page/|/about|/contact|/wp-admin", re.I)

    for s in APP_SRC:
        adapter = factory.get_adapter(s)
        listing_url = adapter.start_urls[0]
        entry = {"listing_url": listing_url, "listing_ok": False, "articles": [], "error": None,
                 "discovery_method": "listing"}
        try:
            if not robots_allows(listing_url):
                entry["error"] = "robots disallow listing"; manifest["sources"][s] = entry; continue
            try:
                lh = fetch(listing_url); time.sleep(DELAY)
                entry["listing_ok"] = (lh["status"] == 200)
                d = adapter.discover_listing(listing_url, lh["html"])
                arts = [u for u in d.article_urls if not forbidden_re.search(u)][:MAX_ARTICLES]
                entry["discovered_total"] = len(d.article_urls)
                entry["discovered_after_filter"] = len(arts)
                # sitemap fallback if listing yields nothing
                if not arts:
                    sm = discover_via_sitemap(listing_url); time.sleep(DELAY)
                    arts = [u for u in sm if not forbidden_re.search(u)][:MAX_ARTICLES]
                    if arts:
                        entry["discovery_method"] = "sitemap"
                        entry["discovered_after_filter"] = len(arts)
            except Exception as e:
                # sitemap fallback (robots-sanctioned index) if listing 404s
                if "404" in str(e) or "Not Found" in str(e):
                    sm = discover_via_sitemap(listing_url); time.sleep(DELAY)
                    arts = [u for u in sm if not forbidden_re.search(u)][:MAX_ARTICLES]
                    entry["discovery_method"] = "sitemap"
                    entry["listing_ok"] = bool(arts)
                    entry["discovered_after_filter"] = len(arts)
                else:
                    entry["error"] = str(e)[:200]; manifest["sources"][s] = entry; continue
            cache[s] = {"listing": None, "articles": []}
            for u in arts:
                if not robots_allows(u):
                    entry["articles"].append({"url": u, "skipped": "robots"}); continue
                try:
                    ah = fetch(u); time.sleep(DELAY)
                    cache[s]["articles"].append({"url": u, "status": ah["status"],
                        "content_type": ah["content_type"], "content_length": ah["content_length"], "html": ah["html"]})
                    entry["articles"].append({"url": u, "status": ah["status"], "content_length": ah["content_length"]})
                except Exception as e:
                    entry["articles"].append({"url": u, "error": str(e)[:120]})
        except Exception as e:
            entry["error"] = str(e)[:200]
        manifest["sources"][s] = entry

    json.dump(manifest, open(MANIFEST, "w"), indent=2, default=str)

    conn = init_staging(STAGING_DB)
    run_results = []
    for pass_i in (1, 2):
        for s in APP_SRC:
            if s not in cache: continue
            adapter = factory.get_adapter(s)
            for a in cache[s]["articles"]:
                if "html" not in a: continue
                ch = hashlib.sha256(a["html"].encode("utf-8")).hexdigest()
                rec, mm, cw = build_record(adapter, a["url"], a["html"], ch)
                ok, err = schema_validate(rec)
                cap = {"status": a["status"], "content_type": a["content_type"], "content_length": a["content_length"],
                       "fetched_at": datetime.now(timezone.utc).isoformat()}
                upsert(conn, rec, mm, cw, cap)
                if pass_i == 1:
                    run_results.append({"source": s, "url": a["url"], "evidence_id": rec["evidence_id"],
                        "raw_name": rec["whisky_identity"]["raw_name"], "semantic_ok": _is_semantic(rec["whisky_identity"]["raw_name"]),
                        "schema_ok": ok, "schema_err": err, "match_status": mm.match_status,
                        "crosswalk_unknown": cw["unknown"], "excerpt_quote_words": len(rec.get("excerpt_quote","").split()),
                        "excerpt_ok": len(rec.get("excerpt_quote","").split()) <= 15})
    conn.close()
    json.dump(run_results, open(RUNRESULTS, "w"), indent=2, default=str)

    attempt = len(APP_SRC)
    success = sum(1 for s in APP_SRC if s in cache and (manifest["sources"][s].get("listing_ok") or manifest["sources"][s].get("discovery_method")=="sitemap"))
    arts = sum(len([a for a in cache.get(s,{}).get("articles",[]) if "html" in a]) for s in APP_SRC)
    sem = sum(1 for r in run_results if r["semantic_ok"])
    sch = sum(1 for r in run_results if r["schema_ok"])
    cw = sum(1 for r in run_results if not r["crosswalk_unknown"])
    exc = sum(1 for r in run_results if r["excerpt_ok"])
    print(json.dumps({"attempted": attempt, "listing_ok": success, "articles_captured": arts,
        "semantic_ok": sem, "schema_ok": sch, "crosswalk_resolved": cw, "excerpt_ok": exc,
        "records": len(run_results)}, indent=2))


if __name__ == "__main__":
    main()
