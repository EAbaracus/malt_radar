"""Viski Bilgi (viskibilgi.com) — Turkish editorial whisky review adapter (Wix).

Source profile:
- Wix site. robots.txt `User-agent: *` has `Allow: /` (only `*?lightbox=`
  disallowed) — fully crawlable (re-verified live 2026-08-03). Wix serves the
  full article in static HTML (no JS render needed — verified on a live post).
- Sitemap: `sitemap.xml` index -> `blog-posts-sitemap.xml` (329 article URLs,
  `/post/<slug>` permalinks).
- Page structure (verified live 2026-08-03 on Game of Thrones Mortlach 15 YO):
  - `<h1>` = review title; JSON-LD BlogPosting (headline, datePublished,
    author "Viski Bilgi").
  - Metadata table in the body: `Yaşı:` / `Alkol Oranı:` / `Türü:` /
    `Ülkesi / Bölgesi:` / `Ana Fıçı / Bitiş Fıçısı:` / `Renklendirme /
    Soğuk Filtrasyon:` / `Fıçı Sertliği / Tek Fıçı:` / `Limitli Üretim:`.
  - Tasting sections `Burun` / `Damak` / `Bitiş`, each followed by `NN/25`,
    then `Yorum & Kanaat Notum` (NN/25) and `Toplam Puan NN/100` — the
    /100 total is the review score.
  - TR tasting prose — flavor vector via tr_flavor_lexicon -> FlavorMapper.
- EXCERPT_POLICY: store only Burun/Damak/Bitiş section text (short), the
  /100 score, metadata facts, author, source_url. No raw HTML.
"""
from __future__ import annotations
import json
import re
from typing import List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .editorial_base_adapter import EditorialBaseAdapter, ArticleParse, ListingResult


class ViskiBilgiAdapter(EditorialBaseAdapter):
    source_id: str = "viskibilgi"
    authority_tier: str = "T2_expert"
    license: str = "copyright-attribution-required"

    # ---- discovery (Wix blog listing) ----
    def discover_listing(self, start_url: str, html: str) -> ListingResult:
        soup = BeautifulSoup(html, "html.parser")
        urls: List[str] = []
        seen = set()
        for a in soup.find_all("a", href=True):
            href = str(a["href"])
            u = urljoin(start_url, href)
            if "/post/" not in u:
                continue
            if any(x in u for x in ("?lightbox", "#", "static.wixstatic", "_partials")):
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
            if isinstance(d, dict) and d.get("@type") == "BlogPosting":
                if d.get("datePublished"):
                    published_date = d["datePublished"][:10]
                a = d.get("author") or {}
                if isinstance(a, dict):
                    author = a.get("name") or author
        if not author:
            m = re.search(r"\b(Viski Bilgi)\b", html)
            if m:
                author = m.group(1)
        if not published_date:
            m = re.search(r"\b(\d{1,2})\s+(Oca|Şub|Mar|Nis|May|Haz|Tem|Ağu|Eyl|Eki|Kas|Ara)\s+(\d{4})", html)
            if m:
                months = {"Oca": "01", "Şub": "02", "Mar": "03", "Nis": "04", "May": "05",
                          "Haz": "06", "Tem": "07", "Ağu": "08", "Eyl": "09", "Eki": "10",
                          "Kas": "11", "Ara": "12"}
                published_date = f"{m.group(3)}-{months[m.group(2)]}-{int(m.group(1)):02d}"

        # Body text (Wix renders prose directly in the DOM).
        body_txt = soup.get_text("\n", strip=True)

        nose, palate, finish, comment = self._sections(body_txt)
        score_value = self._total_score(body_txt)
        meta = self._metadata(body_txt)

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
            conclusion=comment,
            metadata=meta,
            quotes=[{"quote": quote, "attribution": f"{author or 'Viski Bilgi'} ({url})"}] if quote else [],
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
        """Return (nose, palate, finish, comment) from Burun/Damak/Bitiş blocks.

        Each section runs from its label line to its NN/25 score line; the
        comment runs from 'Yorum & Kanaat Notum' to its NN/25.
        """
        def grab(label: str):
            m = re.search(
                rf"{label}\s*\n(.*?)\n\s*\d{{1,2}}/25", text, re.I | re.S
            )
            return m.group(1).strip() if m else None

        nose = grab("Burun")
        palate = grab("Damak")
        finish = grab("Bitiş")
        comment = None
        m = re.search(r"Yorum\s*&\s*Kanaat\s*Notum\s*\n(.*?)\n\s*\d{1,2}/25", text, re.I | re.S)
        if m:
            comment = m.group(1).strip()
        return nose, palate, finish, comment

    @staticmethod
    def _total_score(text: str) -> Optional[float]:
        m = re.search(r"Toplam\s*Puan\s*\n?\s*(\d{1,3})\s*/\s*100", text, re.I)
        if m:
            return float(m.group(1))
        # Fallback: any NN/100 in the body.
        m = re.search(r"\b(\d{1,3})\s*/\s*100\b", text)
        if m:
            return float(m.group(1))
        return None

    @staticmethod
    def _metadata(text: str) -> dict:
        def field(label: str, rgx: str):
            m = re.search(rf"{label}\s*:\s*({rgx})", text, re.I)
            return m.group(1).strip() if m else None

        meta = {
            "age": None,
            "abv": None,
            "type": field(r"Türü", r"[^\n]+"),
            "origin": field(r"Ülkesi\s*/\s*Bölgesi", r"[^\n]+"),
            "cask": field(r"Ana\s*Fıçı\s*/\s*Bitiş\s*Fıçısı", r"[^\n]+"),
            "coloring_filtration": field(r"Renklendirme\s*/\s*Soğuk\s*Filtrasyon", r"[^\n]+"),
            "cask_strength": field(r"Fıçı\s*Sertliği\s*/\s*Tek\s*Fıçı", r"[^\n]+"),
            "limited": field(r"Limitli\s*Üretim", r"[^\n]+"),
            "language": "tr",
        }
        m = re.search(r"Yaşı\s*:\s*(\d{1,2})", text, re.I)
        if m:
            meta["age"] = int(m.group(1))
        m = re.search(r"Alkol\s*Oranı\s*:\s*%?\s*(\d{1,3}(?:[.,]\d{1,2})?)", text, re.I)
        if m:
            meta["abv"] = float(m.group(1).replace(",", "."))
        return meta

    @staticmethod
    def _short_excerpt(text: str) -> str:
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        for i, ln in enumerate(lines):
            if ln in ("Burun", "Damak", "Bitiş", "Yorum & Kanaat Notum"):
                for j in range(i + 1, min(i + 2, len(lines))):
                    words = lines[j].split()
                    if len(words) >= 5:
                        return " ".join(words[:15]) + ("…" if len(words) > 15 else "")
        return ""
