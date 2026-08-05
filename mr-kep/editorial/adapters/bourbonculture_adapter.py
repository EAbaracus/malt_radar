"""The Bourbon Culture (thebourbonculture.com) — English whiskey review adapter.

Source profile:
- WordPress (Yoast). robots.txt carries only content-signal comments (no
  Disallow rules for `*`) — fully crawlable (re-verified live 2026-08-03).
- Sitemap index -> `post-sitemap.xml` (1,001 URLs). Reviews live under
  `/whiskey-reviews/<slug>-review/`.
- Page structure (verified live on Union Horse Reunion Barrel Strength Rye):
  - `<h1>` = review title (ends in "Review").
  - `Nose:` / `Palate:` / `Finish:` labeled sections, then
    `Score: N.N/10` (10-point scale).
  - JSON-LD Review/Article block present.
- EXCERPT_POLICY: store only Nose/Palate/Finish section text (short), the
  /10 score, author, source_url. No raw HTML.
"""
from __future__ import annotations
import json
import re
from typing import List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .editorial_base_adapter import EditorialBaseAdapter, ArticleParse, ListingResult


class BourbonCultureAdapter(EditorialBaseAdapter):
    source_id: str = "thebourbonculture"
    authority_tier: str = "T2_expert"
    license: str = "copyright-attribution-required"

    # ---- discovery ----
    def discover_listing(self, start_url: str, html: str) -> ListingResult:
        soup = BeautifulSoup(html, "html.parser")
        urls: List[str] = []
        seen = set()
        for a in soup.find_all("a", href=True):
            href = str(a["href"])
            u = urljoin(start_url, href)
            if "thebourbonculture.com" not in u or "/whiskey-reviews/" not in u:
                continue
            if any(x in u for x in ("/category/", "/tag/", "/page/", "/wp-", "?", "#", "feed")):
                continue
            if u in seen:
                continue
            seen.add(u)
            urls.append(u)
        return ListingResult(article_urls=urls, next_page=self.next_page_url(start_url, html))

    # ---- article parsing ----
    def parse_article(self, url: str, html: str) -> ArticleParse:
        soup = BeautifulSoup(html, "html.parser")

        h1 = None
        for h in soup.find_all("h1"):
            t = h.get_text(" ", strip=True)
            if t and "navigation" not in t.lower():
                h1 = t
                break
        raw_name = h1 or self._title_fallback(soup)

        author: Optional[str] = None
        published_date: Optional[str] = None
        for s in soup.find_all("script", type="application/ld+json"):
            try:
                d = json.loads(s.string or s.get_text())
            except (ValueError, TypeError):
                continue
            nodes = d.get("@graph", [d]) if isinstance(d, dict) else d
            for node in nodes:
                if isinstance(node, dict) and node.get("@type") in ("Review", "Article", "BlogPosting"):
                    if node.get("datePublished"):
                        published_date = node["datePublished"][:10]
                    a = node.get("author") or {}
                    if isinstance(a, dict):
                        author = a.get("name") or author
        if not author:
            m = re.search(r"\bby\s+([A-Za-zÀ-ž][A-Za-zÀ-ž' .-]{2,40})", html)
            if m:
                author = m.group(1).strip()

        body = soup.find("article") or soup.find("div", class_=re.compile(
            r"entry-content|post-content|td-post-content", re.I))
        body_txt = body.get_text("\n", strip=True) if body else soup.get_text("\n", strip=True)

        nose, palate, finish = self._sections(body_txt)
        score_value = self._score(body_txt)

        quote = self._short_excerpt(body_txt)

        return ArticleParse(
            raw_name=raw_name,
            title=raw_name,
            author=author,
            published_date=published_date,
            score_value=score_value,
            score_scale_max=10.0 if score_value else None,
            nose=nose,
            palate=palate,
            finish=finish,
            metadata={"language": "en"},
            quotes=[{"quote": quote, "attribution": f"{author or 'The Bourbon Culture'} ({url})"}] if quote else [],
        )

    # ---- helpers ----
    @staticmethod
    def _title_fallback(soup: BeautifulSoup) -> str:
        t = soup.title
        if t:
            return re.sub(r"\s*[|–—-]\s*.*$", "", t.get_text(strip=True)).strip()
        return ""

    @staticmethod
    def _sections(text: str):
        def grab(label: str):
            m = re.search(rf"{label}\s*:\s*\n?(.*?)(?=\n\s*(?:Palate|Finish|Score)\s*:)", text, re.I | re.S)
            return m.group(1).strip() if m else None
        return grab("Nose"), grab("Palate"), grab("Finish")

    @staticmethod
    def _score(text: str) -> Optional[float]:
        m = re.search(r"Score\s*:\s*(\d{1,2}(?:[.,]\d{1,2})?)\s*/\s*10", text, re.I)
        if m:
            return float(m.group(1).replace(",", "."))
        m = re.search(r"Score\s*:\s*(\d{1,2}(?:[.,]\d{1,2})?)", text, re.I)
        if m:
            return float(m.group(1).replace(",", "."))
        return None

    @staticmethod
    def _short_excerpt(text: str) -> str:
        for para in text.splitlines():
            p = para.strip()
            if len(p) >= 30 and not re.match(r"^(Nose|Palate|Finish|Score|Rating|Posted)", p, re.I):
                words = p.split()
                return " ".join(words[:15]) + ("…" if len(words) > 15 else "")
        return ""
