"""P201 — Editorial adapter factory + concrete GO-source adapters (production-safe).

All adapters are CONCRETE skeletons:
- `discover_listing` is deterministic (real pagination patterns observed in the audit).
- `parse_article` extracts title/author/date/body via BeautifulSoup. Source-specific
  selectors are documented inline; the LLM Knowledge Extractor (not the adapter) owns
  identity/score/flavor derivation. Adapters do NOT open production.db and perform NO
  network calls by themselves (fetching is injected by the pipeline / fixtures).

NO-GO sources (scotchwhisky.com, thewhiskeyjug.com, whisky.com) are intentionally absent.
whiskycast.com is EXCLUDED here (conditional — add only after a human verifies robots.txt).
"""
from __future__ import annotations
import re
from typing import Dict, List, Optional, Type
from bs4 import BeautifulSoup

from .editorial_base_adapter import (
    EditorialBaseAdapter, ArticleParse, ListingResult, CANONICAL_AXES,
)


def _post_links(html: str, base: str, pattern: str = r'/20\d\d/') -> List[str]:
    """Collect in-site article links matching a year-path pattern (WordPress/Hugo blogs)."""
    from urllib.parse import urljoin
    soup = BeautifulSoup(html, "html.parser")
    out: List[str] = []
    seen = set()
    for a in soup.find_all("a", href=True):
        href = str(a["href"])
        if re.search(pattern, href):
            u = urljoin(base, href)
            if u not in seen:
                seen.add(u)
                out.append(u)
    return out


# P203C-FIX: hardened discovery. Excludes category/tag/author/nav/feed/asset URLs and
# the listing page itself, so only article permalinks are returned. Deterministic, no crawling.
_EXCLUDE_RE = re.compile(
    r"(/category/|/tag/|/author/|/page/|/feed|/comments|/trackback|/\?s=|/search|"
    r"/about|/contact|/privacy|/imprint|/wp-json|/cdn-cgi|/cgi-bin|/cart|/checkout|"
    r"/login|/wp-admin|/wp-content|/wp-includes|/xmlrpc|/sitemap|/archives|/amp/|"
    r"/wp-register|/trackback|\.xml|\.json|\.css|\.js|\.png|\.jpg|\.jpeg|\.gif|\.pdf|\.ico)",
    re.I,
)


def _discover_articles(html: str, listing_url: str, include: str, cap: int = 20, min_parts: int = 2,
                       exclude_last: str = r"(-reviews|-category|-tag|-author|-archive)$") -> List[str]:
    """Return in-site article permalinks only.

    - include: positive pattern (e.g. r'/20\\d\\d/' or r'/whisky/whisky-reviews/')
    - exclude: nav/category/tag/author/feed/asset URLs + the listing page itself
    - min_parts: minimum non-empty path segments after the domain. Filters out
      intermediate section/region pages (e.g. /tastings/region/ is 2 parts -> excluded
      when min_parts=3, while /tastings/region/slug/ is 3 -> kept).
    - exclude_last: final path segment matching this regex is a section/category, not an
      article. Plural '-reviews' (e.g. american-whiskey-reviews) is a section; singular
      '-review' (e.g. laphroaig-10-review) is a real article and must be kept.
    - deterministic, deduped, capped
    """
    from urllib.parse import urljoin, urlparse
    soup = BeautifulSoup(html, "html.parser")
    out: List[str] = []
    seen = set()
    for a in soup.find_all("a", href=True):
        href = str(a["href"])
        if not re.search(include, href):
            continue
        u = urljoin(listing_url, href)
        if u in seen or u.rstrip("/") == listing_url.rstrip("/"):
            continue
        if _EXCLUDE_RE.search(u):
            continue
        parts = [p for p in urlparse(u).path.split("/") if p]
        if len(parts) < min_parts:
            continue
        if exclude_last and re.search(exclude_last, parts[-1].lower()):
            continue
        seen.add(u)
        out.append(u)
        if len(out) >= cap:
            break
    return out


# Site-title tokens that must never be used as a whisky_name.
# Compared space-insensitively (the rendered "The Whiskyphiles" has no space).
_SITE_TITLE_TOKENS = {
    "whiskynotes", "whiskynotes.be", "the dramble", "thedramble",
    "the whiskey wash", "thewhiskeywash", "the whisky philes", "thewhiskyphiles",
    "wordsofwhisky", "whisky monster", "whiskymonster", "reviews", "latest reviews",
    "whiskey reviews", "whisky reviews",
}
_SITE_TITLE_NORM = {re.sub(r"\s+", "", t.lower()) for t in _SITE_TITLE_TOKENS}


def _is_site_title(text: str) -> bool:
    return re.sub(r"\s+", "", (text or "").lower()) in _SITE_TITLE_NORM


def _extract_title(soup, url: str) -> str:
    """Robust article title extraction.

    Order: JSON-LD headline -> .entry-title/h1.entry-title -> first <h1> (reject
    site-title tokens) -> <title> tag minus site suffix -> URL.
    This is resilient to interstitial/holding pages where the first <h1> is the
    site name (real-world crawl fragility).
    """
    # 1) JSON-LD headline
    for sc in soup.find_all("script", type="application/ld+json"):
        try:
            import json as _json
            d = _json.loads(sc.string or "{}")
            h = d.get("headline") if isinstance(d, dict) else None
            if isinstance(h, str) and h.strip():
                return h.strip()
        except Exception:
            pass
    # 2) .entry-title / h1.entry-title / h2.entry-title / .post-title
    et = soup.select_one(".entry-title, h1.entry-title, h2.entry-title, .post-title, .post-title a")
    if et and et.get_text(strip=True):
        return et.get_text(strip=True)
    # 3) any <h1> whose text is not a site-title token (handles masthead-then-article dual-h1)
    for h1 in soup.find_all("h1"):
        t = h1.get_text(strip=True)
        if t and not _is_site_title(t):
            return t.strip()
    # 4) <title> minus site suffix (e.g. " | whisky", " - review")
    if soup.title:
        t = soup.title.get_text(strip=True)
        t = re.split(r"\s[|\-–—]\s", t)[0].strip()
        if t and not _is_site_title(t):
            return t
    return url


class WhiskyNotesBeAdapter(EditorialBaseAdapter):
    """GO-6. Confirmed rel=next + page/N pagination during audit."""
    source_id = "whiskynotes_be"
    authority_tier = "T2_expert"
    start_urls = ["https://www.whiskynotes.be/"]

    def discover_listing(self, start_url: str, html: str) -> ListingResult:
        urls = _discover_articles(html, start_url, include=r'/20\d\d/', min_parts=3)
        nxt = self.next_page_url(start_url, html)
        return ListingResult(article_urls=urls, next_page=nxt)

    def parse_article(self, url: str, html: str) -> ArticleParse:
        soup = BeautifulSoup(html, "html.parser")
        title = _extract_title(soup, url)
        content = soup.find("div", class_=re.compile("entry-content|post-content|content"))
        text = content.get_text("\n", strip=True) if content else (soup.get_text("\n", strip=True))
        author = None
        if soup.find(class_=re.compile("author")):
            author = soup.find(class_=re.compile("author")).get_text(strip=True)
        return ArticleParse(raw_name=title, author=author, title=title, conclusion=text)


class TheWhiskyPhilesAdapter(EditorialBaseAdapter):
    """GO-1. WordPress, category/tasting-notes + date archives."""
    source_id = "thewhiskyphiles"
    authority_tier = "T2_expert"
    start_urls = ["https://thewhiskyphiles.com/category/tasting-notes/"]

    def discover_listing(self, start_url: str, html: str) -> ListingResult:
        urls = _discover_articles(html, start_url, include=r'/20\d\d/\d\d/', min_parts=3)
        nxt = self.next_page_url(start_url, html)
        return ListingResult(article_urls=urls, next_page=nxt)

    def parse_article(self, url: str, html: str) -> ArticleParse:
        soup = BeautifulSoup(html, "html.parser")
        title = _extract_title(soup, url)
        content = soup.find("div", class_=re.compile("entry-content|post-content"))
        text = content.get_text("\n", strip=True) if content else soup.get_text("\n", strip=True)
        return ArticleParse(raw_name=title, title=title, conclusion=text)


class WhiskyMonsterAdapter(EditorialBaseAdapter):
    """GO-2. Independent critic; JSON-LD article present."""
    source_id = "whiskymonster"
    authority_tier = "T2_expert"
    start_urls = ["https://www.whiskymonster.com/whisky/whisky-reviews/list-of-whisky-reviews/"]

    def discover_listing(self, start_url: str, html: str) -> ListingResult:
        urls = _discover_articles(html, start_url, include=r'/whisky/whisky-reviews/', min_parts=3)
        nxt = self.next_page_url(start_url, html)
        return ListingResult(article_urls=urls, next_page=nxt)

    def parse_article(self, url: str, html: str) -> ArticleParse:
        soup = BeautifulSoup(html, "html.parser")
        title = _extract_title(soup, url)
        content = soup.find("div", class_=re.compile("entry-content|post-content|content"))
        text = content.get_text("\n", strip=True) if content else soup.get_text("\n", strip=True)
        return ArticleParse(raw_name=title, title=title, conclusion=text)


class TheDrambleAdapter(EditorialBaseAdapter):
    """GO-4. /tastings/ index."""
    source_id = "thedramble"
    authority_tier = "T2_expert"
    start_urls = ["https://www.thedramble.com/tastings/"]

    def discover_listing(self, start_url: str, html: str) -> ListingResult:
        urls = _discover_articles(html, start_url, include=r'/tastings/', min_parts=3)
        nxt = self.next_page_url(start_url, html)
        return ListingResult(article_urls=urls, next_page=nxt)

    def parse_article(self, url: str, html: str) -> ArticleParse:
        soup = BeautifulSoup(html, "html.parser")
        title = _extract_title(soup, url)
        title = re.sub(r"^\s*Bottle\s*Name\s*:\s*", "", title, flags=re.I).strip()
        content = soup.find("article") or soup.find("div", class_=re.compile("content|entry"))
        text = content.get_text("\n", strip=True) if content else soup.get_text("\n", strip=True)
        return ArticleParse(raw_name=title, title=title, conclusion=text)


class TheWhiskeyWashAdapter(EditorialBaseAdapter):
    """GO-9. /whiskey-reviews/, sitemap_index present."""
    source_id = "thewhiskeywash"
    authority_tier = "T2_expert"
    start_urls = ["https://thewhiskeywash.com/whiskey-reviews/"]

    def discover_listing(self, start_url: str, html: str) -> ListingResult:
        urls = _discover_articles(html, start_url, include=r'/whiskey-reviews/')
        nxt = self.next_page_url(start_url, html)
        return ListingResult(article_urls=urls, next_page=nxt)

    def parse_article(self, url: str, html: str) -> ArticleParse:
        soup = BeautifulSoup(html, "html.parser")
        title = _extract_title(soup, url)
        content = soup.find("div", class_=re.compile("entry-content|post-content"))
        text = content.get_text("\n", strip=True) if content else soup.get_text("\n", strip=True)
        return ArticleParse(raw_name=title, title=title, conclusion=text)


class WordsOfWhiskyAdapter(EditorialBaseAdapter):
    """GO-10. JSON-LD BlogPosting; sitemap_index present."""
    source_id = "wordsofwhisky"
    authority_tier = "T2_expert"
    start_urls = ["https://wordsofwhisky.com/"]

    def discover_listing(self, start_url: str, html: str) -> ListingResult:
        urls = _discover_articles(html, start_url, include=r'/20\d\d/', min_parts=3)
        nxt = self.next_page_url(start_url, html)
        return ListingResult(article_urls=urls, next_page=nxt)

    def parse_article(self, url: str, html: str) -> ArticleParse:
        soup = BeautifulSoup(html, "html.parser")
        title = _extract_title(soup, url)
        content = soup.find("div", class_=re.compile("entry-content|post-content"))
        text = content.get_text("\n", strip=True) if content else soup.get_text("\n", strip=True)
        # JSON-LD BlogPosting sometimes carries author/date
        author = None
        jld = soup.find("script", type="application/ld+json")
        if jld:
            try:
                import json
                data = json.loads(jld.string or "{}")
                author = (data.get("author") or {}).get("name") if isinstance(data.get("author"), dict) else None
            except Exception:
                pass
        return ArticleParse(raw_name=title, author=author, title=title, conclusion=text)


# Registry of GO adapters (NO-GO sources excluded; whiskycast conditional, excluded).
GO_ADAPTERS: Dict[str, Type[EditorialBaseAdapter]] = {
    "thewhiskyphiles": TheWhiskyPhilesAdapter,
    "whiskymonster": WhiskyMonsterAdapter,
    "thedramble": TheDrambleAdapter,
    "whiskynotes_be": WhiskyNotesBeAdapter,
    "thewhiskeywash": TheWhiskeyWashAdapter,
    "wordsofwhisky": WordsOfWhiskyAdapter,
}


def get_adapter(source_id: str) -> EditorialBaseAdapter:
    if source_id not in GO_ADAPTERS:
        raise ValueError(f"No GO adapter for source_id={source_id!r} "
                         f"(NO-GO or conditional source excluded)")
    return GO_ADAPTERS[source_id]()


def all_go_sources() -> List[str]:
    return list(GO_ADAPTERS.keys())


__all__ = [
    "GO_ADAPTERS", "get_adapter", "all_go_sources",
    "WhiskyNotesBeAdapter", "TheWhiskyPhilesAdapter", "WhiskyMonsterAdapter",
    "TheDrambleAdapter", "TheWhiskeyWashAdapter", "WordsOfWhiskyAdapter",
    "CANONICAL_AXES",
]
