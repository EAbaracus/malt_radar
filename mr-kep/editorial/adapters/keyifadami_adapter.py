"""Keyif Adamı (keyifadami.net) — Turkish editorial whisky review adapter.

Source profile:
- WordPress site; robots.txt `User-agent: *` disallows only /wp-admin/
  (re-verified live 2026-08-03). Sitemap: `sitemap_index.xml` ->
  `post-sitemap.xml` (367 posts, 155 with `viski-tadimi` in the slug).
- Article permalinks are root slugs (`/aberfeldy-12-viski-tadimi/`).
- Page structure (verified live 2026-08-03 on Aberfeldy 12):
  - `<h1>` = review title; Yoast JSON-LD `@graph` Article node
    (headline, datePublished, author "Keyif Adamı").
  - Metadata table: `Ülke – Bölge:` / `Damıtımevi:` / `Tür:` / `Yaş:` /
    `Fıçı:` / `Alkol:` (e.g. "40.0%").
  - Tasting sections `Burun:` / `Damak:` / `Bitiş:` (inline labels).
  - A rating widget shows `NN/25` per koku/damak/bitiş/genel and `NN/100`
    TOPLAM — the widget is JS-rendered and often shows 0 in static HTML;
    only take a score when a real value is present (never fabricate).
- EXCERPT_POLICY: store only Burun/Damak/Bitiş section text (short), score
  when present, metadata facts, author, source_url. No raw HTML.
"""
from __future__ import annotations
import json
import re
from typing import List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .editorial_base_adapter import EditorialBaseAdapter, ArticleParse, ListingResult


class KeyifAdamiAdapter(EditorialBaseAdapter):
    source_id: str = "keyifadami"
    authority_tier: str = "T2_expert"
    license: str = "copyright-attribution-required"

    # ---- discovery (WordPress listing) ----
    def discover_listing(self, start_url: str, html: str) -> ListingResult:
        soup = BeautifulSoup(html, "html.parser")
        urls: List[str] = []
        seen = set()
        for a in soup.find_all("a", href=True):
            href = str(a["href"])
            u = urljoin(start_url, href)
            if "keyifadami.net" not in u or "tadimi" not in u:
                continue
            if any(x in u for x in ("/wp-", "/category", "/tag", "/author", "/page",
                                    "/feed", "/bira", "/sarap", "/likor", "/kokteyl",
                                    "?", "#")):
                continue
            if u in seen:
                continue
            seen.add(u)
            urls.append(u)
        return ListingResult(article_urls=urls, next_page=self.next_page_url(start_url, html))

    # ---- article parsing ----
    def parse_article(self, url: str, html: str) -> ArticleParse:
        soup = BeautifulSoup(html, "html.parser")

        h1 = soup.find("h1")
        raw_name = (h1.get_text(" ", strip=True) if h1 else None) or self._title_fallback(soup)

        author: Optional[str] = None
        published_date: Optional[str] = None
        for s in soup.find_all("script", type="application/ld+json"):
            try:
                d = json.loads(s.string or s.get_text())
            except (ValueError, TypeError):
                continue
            nodes = d.get("@graph", [d]) if isinstance(d, dict) else d
            for node in nodes:
                if isinstance(node, dict) and node.get("@type") == "Article":
                    if node.get("datePublished"):
                        published_date = node["datePublished"][:10]
                    a = node.get("author") or {}
                    if isinstance(a, dict):
                        author = a.get("name") or author
        if not author:
            m = re.search(r"\bby\s+([A-Za-zÇĞİÖŞÜçğıöşü ]{2,30}?)\s*$", html, re.M)
            if m:
                author = m.group(1).strip()

        # Article body: pick the longest <article>/entry-content block (>200
        # chars of visible text) — the first <article> tag can be a nav widget.
        body = self._main_region(soup)
        body_txt = body.get_text("\n", strip=True) if body else soup.get_text("\n", strip=True)

        nose, palate, finish = self._sections(body_txt)
        meta = self._metadata(body_txt)
        score_value = self._total_score(body_txt)

        quote = self._short_excerpt(body_txt)

        return ArticleParse(
            raw_name=raw_name,
            title=raw_name,
            author=author,
            published_date=published_date,
            score_value=score_value,
            score_scale_max=100.0,
            nose=nose,
            palate=palate,
            finish=finish,
            metadata=meta,
            quotes=[{"quote": quote, "attribution": f"{author or 'Keyif Adamı'} ({url})"}] if quote else [],
        )

    # ---- helpers ----
    @staticmethod
    def _main_region(soup: BeautifulSoup):
        """Longest article/entry-content block (P13: isolate the article body)."""
        best, best_len = None, 0
        for el in soup.find_all(["article", "div"], class_=re.compile(
                r"entry-content|post-content|td-post-content|et_pb_post_content|ast-article", re.I)):
            t = el.get_text(" ", strip=True)
            if len(t) > best_len:
                best, best_len = el, len(t)
        if best and best_len > 200:
            return best
        for art in soup.find_all("article"):
            t = art.get_text(" ", strip=True)
            if len(t) > best_len:
                best, best_len = art, len(t)
        return best if best and best_len > 200 else None

    @staticmethod
    def _title_fallback(soup: BeautifulSoup) -> str:
        t = soup.title
        if t:
            return re.sub(r"\s*[|–—-]\s*.*$", "", t.get_text(strip=True)).strip()
        return ""

    @staticmethod
    def _sections(text: str):
        """Return (nose, palate, finish) from `Burun:` / `Damak:` / `Bitiş:`."""
        def grab(label: str):
            m = re.search(
                rf"{label}\s*:\s*\n?(.*?)(?=\n\s*(?:Damak|Bitiş)\s*:)", text, re.I | re.S
            )
            return m.group(1).strip() if m else None

        nose = grab("Burun")
        palate = grab("Damak")
        finish = None
        m = re.search(r"Bitiş\s*:\s*\n?(.*?)(?=\n\s*(?:[A-ZÇĞİÖŞÜ][a-zçğıöşü]+|0\s*/25|$))", text, re.I | re.S)
        if m:
            finish = m.group(1).strip()
        return nose, palate, finish

    @staticmethod
    def _metadata(text: str) -> dict:
        meta: dict = {"language": "tr"}
        m = re.search(r"Ülke\s*[–-]\s*Bölge\s*:\s*([^\n]+)", text, re.I)
        if m:
            meta["origin"] = m.group(1).strip()
        m = re.search(r"Damıtımevi\s*:\s*([^\n]+)", text, re.I)
        if m:
            meta["distillery"] = m.group(1).strip()
        m = re.search(r"Tür\s*:\s*([^\n]+)", text, re.I)
        if m:
            meta["type"] = m.group(1).strip()
        m = re.search(r"Yaş\s*:\s*(\d{1,2})", text, re.I)
        if m:
            meta["age"] = int(m.group(1))
        m = re.search(r"Fıçı\s*:\s*([^\n]+)", text, re.I)
        if m:
            meta["cask"] = m.group(1).strip()
        m = re.search(r"Alkol\s*:\s*%?\s*(\d{1,3}(?:[.,]\d{1,2})?)", text, re.I)
        if m:
            meta["abv"] = float(m.group(1).replace(",", "."))
        return meta

    @staticmethod
    def _total_score(text: str) -> Optional[float]:
        # The rating widget: `NN /100 TOPLAM`. Static HTML often renders 0 —
        # only take a non-zero value (never fabricate a score).
        m = re.search(r"(\d{1,3})\s*/\s*100\s*TOPLAM", text, re.I)
        if m and int(m.group(1)) > 0:
            return float(m.group(1))
        return None

    @staticmethod
    def _short_excerpt(text: str) -> str:
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        for i, ln in enumerate(lines):
            if re.match(r"^(Burun|Damak|Bitiş)\s*:", ln, re.I):
                for j in range(i + 1, min(i + 2, len(lines))):
                    words = lines[j].split()
                    if len(words) >= 5:
                        return " ".join(words[:15]) + ("…" if len(words) > 15 else "")
        return ""
