"""P96 Discovery layer — controlled proof (URL seeding / discovery reliability).

Read-only discovery against SearXNG. Deterministic, no production writes.
NO entity resolution here (separate module). NO Hound fetch here (separate task).

Strategy (improves on unscoped bare-name queries that returned off-topic junk
on the dev SearXNG instance):
  1. site:masterofmalt.com "<product name>"
  2. site:whiskynotes.be "<product name>"
  3. Whiskybase is discoverable but MUST be marked CF_BLOCKED_LIVE_SOURCE
     (never bypassed).

Each discovered URL is:
  * normalized (strip tracking params, trailing slash, lowercase host)
  * validated against supported domains
  * classified: FOUND_SUPPORTED | FOUND_CF_BLOCKED | UNSUPPORTED_SOURCE
                | NO_SUPPORTED_RESULT | DISCOVERY_ERROR
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import List, Optional
from urllib.parse import urlparse

SEARXNG = "http://localhost:8090/search"

SUPPORTED = {
    "masterofmalt.com": "masterofmalt",
    "www.masterofmalt.com": "masterofmalt",
    "whiskynotes.be": "whiskynotes",
    "www.whiskynotes.be": "whiskynotes",
    "whiskybase.com": "whiskybase",
    "www.whiskybase.com": "whiskybase",
}
# Whiskybase is CF-blocked in live fallback -> discovered but flagged.
CF_BLOCKED = {"whiskybase.com", "www.whiskybase.com"}

SEARCH_PATH_MARKERS = ("/search", "/Search", "q=", "query=")
NON_PRODUCT_HINTS = ("/category/", "/categories/", "/blog/", "/article/", "/news/",
                     "/about/", "/contact/", "/tag/", "/tags/", "/author/",
                     "/distilleries/", "/distillery/", "/shop?", "/search?")


@dataclass
class DiscoveryResult:
    pilot_case_id: str
    production_candidate_id: str
    production_candidate_name: str
    query_strategy_used: str = ""
    discovered_url: Optional[str] = None
    normalized_url: Optional[str] = None
    discovered_source: Optional[str] = None
    discovery_status: str = "NO_SUPPORTED_RESULT"
    reason: str = ""
    rejected_results_count: int = 0
    candidate_urls: List[str] = field(default_factory=list)


def _normalize_url(u: str) -> str:
    p = urlparse(u)
    host = p.netloc.lower()
    # strip common tracking params
    q = urllib.parse.parse_qs(p.query)
    keep = {k: v for k, v in q.items()
            if k.lower() not in ("utm_source", "utm_medium", "utm_campaign",
                                 "ref", "fbclid", "gclid", "whiskynote", "language")}
    path = p.path.rstrip("/") or "/"
    new_q = urllib.parse.urlencode(keep, doseq=True)
    return f"{p.scheme}://{host}{path}" + (f"?{new_q}" if new_q else "")


def _is_product_page(norm_url: str) -> bool:
    for m in NON_PRODUCT_HINTS:
        if m in norm_url:
            return False
    for m in SEARCH_PATH_MARKERS:
        if m in norm_url:
            return False
    return True


def _classify_host(host: str):
    host = host.lower()
    if host in CF_BLOCKED:
        return "whiskybase", "CF_BLOCKED"
    if host in SUPPORTED:
        return SUPPORTED[host], "SUPPORTED"
    return None, "UNSUPPORTED"


def _searx_site(host: str, name: str) -> List[str]:
    q = f'"{name}" site:{host}'
    eq = urllib.parse.quote(q)
    try:
        with urllib.request.urlopen(f"{SEARXNG}?q={eq}&format=json", timeout=12) as r:
            data = json.load(r)
    except Exception:
        return []
    urls = []
    for res in data.get("results", []):
        u = res.get("url", "")
        if host in u:
            urls.append(u)
    return urls


def _searx_broad(name: str) -> List[str]:
    """Broad hinted fallback: '\"name\" masterofmalt whiskynotes whiskybase'.
    Used when site:-scoped queries return nothing (some hosts aren't
    site-indexable on the dev SearXNG). WB hits are classified CF_BLOCKED.
    """
    q = f'"{name}" masterofmalt whiskynotes whiskybase'
    eq = urllib.parse.quote(q)
    try:
        with urllib.request.urlopen(f"{SEARXNG}?q={eq}&format=json", timeout=12) as r:
            data = json.load(r)
    except Exception:
        return []
    urls = []
    for res in data.get("results", []):
        u = res.get("url", "")
        if any(h in u for h in SUPPORTED):
            urls.append(u)
    return urls


def discover(case: dict) -> DiscoveryResult:
    """Discover a supported source URL for one pilot case.

    case keys: pilot_case_id, production_candidate_id, production_candidate_name
    """
    dr = DiscoveryResult(
        pilot_case_id=case.get("pilot_case_id", ""),
        production_candidate_id=case.get("production_candidate_id", ""),
        production_candidate_name=case.get("production_candidate_name", ""),
    )
    name = dr.production_candidate_name
    rejected = 0
    all_candidates: List[str] = []

    # Phase A: precise site:-scoped queries (MoM, then WN)
    for host in ("masterofmalt.com", "whiskynotes.be"):
        found = _searx_site(host, name)
        all_candidates.extend(found)
        if found:
            chosen = None
            for u in found:
                nu = _normalize_url(u)
                src, kind = _classify_host(urlparse(nu).netloc)
                if kind == "SUPPORTED" and _is_product_page(nu):
                    chosen = (nu, src)
                    break
            # only accept if the result is a SUPPORTED live source
            if chosen is not None:
                dr.query_strategy_used = f'site:{host} "{name}"'
                dr.discovered_url = found[0]
                dr.normalized_url = chosen[0]
                dr.discovered_source = chosen[1]
                dr.discovery_status = "FOUND_SUPPORTED"
                dr.reason = f"scoped {host} query returned product page"
                dr.candidate_urls = [_normalize_url(x) for x in found[:3]]
                return dr
            # else: scoped query returned off-topic/unsupported -> fall through

    # Phase B: broad hinted fallback (capture hosts not site-indexable)
    broad = _searx_broad(name)
    all_candidates.extend(broad)
    if broad:
        # Prefer a live source (MoM/WN); else WB -> CF_BLOCKED
        for u in broad:
            nu = _normalize_url(u)
            src, kind = _classify_host(urlparse(nu).netloc)
            if kind == "SUPPORTED" and _is_product_page(nu):
                dr.query_strategy_used = f'broad hint "{name}"'
                dr.discovered_url = u
                dr.normalized_url = nu
                dr.discovered_source = src
                dr.discovery_status = "FOUND_SUPPORTED"
                dr.reason = "broad hinted query returned live-source product page"
                dr.candidate_urls = [_normalize_url(x) for x in broad[:3]]
                return dr
        # only WB present -> CF_BLOCKED
        for u in broad:
            nu = _normalize_url(u)
            src, kind = _classify_host(urlparse(nu).netloc)
            if kind == "CF_BLOCKED":
                dr.query_strategy_used = f'broad hint "{name}"'
                dr.discovered_url = u
                dr.normalized_url = nu
                dr.discovered_source = "whiskybase"
                dr.discovery_status = "FOUND_CF_BLOCKED"
                dr.reason = "Whiskybase discoverable but CF-blocked in live fallback (not fetched)"
                dr.candidate_urls = [_normalize_url(x) for x in broad[:3]]
                return dr

    dr.rejected_results_count = len(all_candidates)
    dr.candidate_urls = [_normalize_url(x) for x in all_candidates[:3]]
    dr.discovery_status = "NO_SUPPORTED_RESULT"
    dr.reason = "no supported-source URL found via scoped or broad queries"
    return dr


__all__ = ["discover", "DiscoveryResult", "SUPPORTED", "CF_BLOCKED"]
