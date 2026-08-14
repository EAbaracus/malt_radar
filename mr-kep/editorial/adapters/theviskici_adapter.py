"""The Viskici (theviskici.com) — Turkish editorial whisky review adapter.

Source profile:
- WordPress site; robots.txt allows everything except /wp-admin/ (Sitemap:
  declared). Google XML sitemap index with monthly `sitemap-pt-post-*.xml`
  files; 19 post sitemaps, 374 article URLs (2020-02 .. 2021-12; the site
  appears dormant after 2021-12).
- Page structure (verified live 2026-08-03):
  - `<h1>` = review title; JSON-LD BlogPosting block (headline, datePublished,
    author).
  - Metadata table in `.entry-content`: `Viski:` / `Alkol Oranı:` (e.g. %40) /
    `Damıtım Evi:` / `Şişeleyici:` / `Köken:` / `Tip:` / `Yaş:` (YBV = yaş
    belirtilmemiş / no age statement).
  - Tasting notes: `Ege Aslan Tadım Notu` section with `Burun` / `Damak` /
    `Bitiş` blocks, each followed by `Skor: NN` (0-100), and a `Genel`
    (overall) block with its own `Skor: NN` — use the Genel score as the
    review score (scale 100).
  - Author: "Ege Aslan" appears in the body ("Ege Aslan Tadım Notu"); the
    JSON-LD author is "theviski" (site account). Prefer Ege Aslan.
- EXCERPT_POLICY: store only nose/palate/finish section text (short), the
  /100 score, metadata facts, author, source_url. No raw HTML.
"""
from __future__ import annotations
import json
import re
from typing import List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .editorial_base_adapter import EditorialBaseAdapter, ArticleParse, ListingResult


class TheViskiciAdapter(EditorialBaseAdapter):
    source_id: str = "theviskici"
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
            if "theviskici.com" not in u:
                continue
            path = u.split("theviskici.com", 1)[-1]
            if (
                not path or path == "/" or path.startswith("/wp-") or path.startswith("/category")
                or path.startswith("/tag") or path.startswith("/author") or path.startswith("/page")
                or path.startswith("/feed") or path.startswith("/sitemap") or path.startswith("/about")
                or path.startswith("/contact") or path.startswith("/privacy")
                or "." in path.rsplit("/", 1)[-1]
            ):
                continue
            if u in seen:
                continue
            seen.add(u)
            urls.append(u)
        return ListingResult(article_urls=urls, next_page=self.next_page_url(start_url, html))

    # ---- article parsing ----
    def parse_article(self, url: str, html: str) -> ArticleParse:
        soup = BeautifulSoup(html, "html.parser")

        # Title: JSON-LD BlogPosting headline first, then <h1>, then <title>.
        raw_name = self._jsonld_title(soup) or self._h1_title(soup) or self._title_tag(soup)

        # Author: prefer "Ege Aslan" from the body; JSON-LD author is the site account.
        author = "Ege Aslan" if re.search(r"Ege Aslan", html) else None
        if not author:
            author = self._jsonld_author(soup)

        # Date: JSON-LD datePublished, then <time datetime>, then meta.
        published_date = self._jsonld_date(soup)
        if not published_date:
            t = soup.find("time", datetime=True)
            if t is not None:
                published_date = str(t.get("datetime") or "") or None
        if not published_date:
            m = re.search(r'property="article:published_time"\s+content="([^"]+)"', html)
            if m:
                published_date = m.group(1)

        # Body region.
        body = soup.find("div", class_="entry-content") or soup.find(
            "div", class_=re.compile(r"post-content|article-content", re.I)
        )
        body_txt = body.get_text("\n", strip=True) if body else soup.get_text("\n", strip=True)

        # Metadata table (Viski/Alkol Oranı/Damıtım Evi/Şişeleyici/Köken/Tip/Yaş).
        meta = self._metadata(body_txt)
        abv = meta.get("abv")
        age = meta.get("age")

        # Tasting sections: Burun / Damak / Bitiş (each with Skor: NN).
        nose, palate, finish = self._sections(body_txt)

        # Score: Genel (overall) Skor, else max of section scores (scale 100).
        score_value, overall_txt = self._overall_score(body_txt)

        quote = self._short_excerpt(overall_txt or body_txt)

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
            conclusion=overall_txt,
            metadata={
                "distillery": meta.get("distillery"),
                "bottler": meta.get("bottler"),
                "origin": meta.get("origin"),
                "type": meta.get("type"),
                "abv": abv,
                "age": age,
                "age_statement": meta.get("age_statement"),
                "language": "tr",
            },
            quotes=[{"quote": quote, "attribution": f"{author or 'Ege Aslan'} ({url})"}] if quote else [],
        )

    # ---- helpers ----
    @staticmethod
    def _jsonld_title(soup: BeautifulSoup) -> Optional[str]:
        for s in soup.find_all("script", type="application/ld+json"):
            try:
                d = json.loads(s.string or s.get_text())
            except (ValueError, TypeError):
                continue
            for node in (d if isinstance(d, list) else [d]):
                if isinstance(node, dict) and node.get("@type") in ("BlogPosting", "Article", "Review"):
                    return (node.get("headline") or node.get("name") or "").strip() or None
        return None

    @staticmethod
    def _h1_title(soup: BeautifulSoup) -> Optional[str]:
        h1 = soup.find("h1")
        return h1.get_text(" ", strip=True) if h1 else None

    @staticmethod
    def _title_tag(soup: BeautifulSoup) -> str:
        t = soup.title
        if t:
            return re.sub(r"\s*[|–-]\s*.*$", "", t.get_text(strip=True)).strip()
        return ""

    @staticmethod
    def _jsonld_author(soup: BeautifulSoup) -> Optional[str]:
        for s in soup.find_all("script", type="application/ld+json"):
            try:
                d = json.loads(s.string or s.get_text())
            except (ValueError, TypeError):
                continue
            for node in (d if isinstance(d, list) else [d]):
                if isinstance(node, dict) and node.get("@type") == "BlogPosting":
                    a = node.get("author") or {}
                    if isinstance(a, dict):
                        return a.get("name")
                    if isinstance(a, str):
                        return a
        return None

    @staticmethod
    def _jsonld_date(soup: BeautifulSoup) -> Optional[str]:
        for s in soup.find_all("script", type="application/ld+json"):
            try:
                d = json.loads(s.string or s.get_text())
            except (ValueError, TypeError):
                continue
            for node in (d if isinstance(d, list) else [d]):
                if isinstance(node, dict) and node.get("@type") in ("BlogPosting", "Article"):
                    return node.get("datePublished") or node.get("dateModified")
        return None

    @staticmethod
    def _metadata(text: str) -> dict:
        out = {}
        m = re.search(r"Alkol\s+Oranı\s*:\s*%?\s*(\d{1,3}(?:[.,]\d{1,2})?)", text, re.I)
        if m:
            out["abv"] = float(m.group(1).replace(",", "."))
        m = re.search(r"Damıtım\s+Evi\s*:\s*([^\n]+)", text, re.I)
        if m:
            out["distillery"] = m.group(1).strip() or None
        m = re.search(r"Şişeleyici\s*:\s*([^\n]+)", text, re.I)
        if m:
            out["bottler"] = m.group(1).strip() or None
        m = re.search(r"Köken\s*:\s*([^\n]+)", text, re.I)
        if m:
            out["origin"] = m.group(1).strip() or None
        m = re.search(r"Tip\s*:\s*([^\n]+)", text, re.I)
        if m:
            out["type"] = m.group(1).strip() or None
        m = re.search(r"Yaş\s*:\s*([^\n]+)", text, re.I)
        if m:
            age_raw = m.group(1).strip()
            out["age_statement"] = age_raw or None
            am = re.search(r"\b(\d{1,2})\s*(?:yaş|yıl)?\b", age_raw)
            out["age"] = int(am.group(1)) if am and "YB" not in age_raw.upper() else None
        return out

    @staticmethod
    def _sections(text: str):
        def grab(label: str):
            m = re.search(
                rf"{label}\s*\n\s*(.*?)(?=\n\s*(?:Skor\s*:\s*\d+|Damak|Bitiş|Genel)\b)", text, re.I | re.S
            )
            return m.group(1).strip() if m else None

        return grab("Burun"), grab("Damak"), grab("Bitiş")

    @staticmethod
    def _overall_score(text: str):
        """Return (score, overall_text) from the Genel block (0-100 scale)."""
        m = re.search(r"Genel\s*\n\s*(.*?)\n\s*Skor\s*:\s*(\d{1,3})", text, re.I | re.S)
        if m:
            return float(m.group(2)), m.group(1).strip()
        # Fallback: any Skor NN in the tasting block.
        scores = [float(x) for x in re.findall(r"Skor\s*:\s*(\d{1,3})", text)]
        if scores:
            return max(scores), None
        return None, None

    @staticmethod
    def _short_excerpt(text: str) -> str:
        words = text.split()
        if not words:
            return ""
        return " ".join(words[:15]) + ("…" if len(words) > 15 else "")
