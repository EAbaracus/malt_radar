"""Fıçı Sertliği (ficisertligi.com) — Turkish editorial whisky review adapter.

Source profile:
- Jekyll static site; robots.txt fully open (no Disallow, Sitemap: declared).
- Article permalinks are root slugs (`/glenlivet-rare-cask/`); sitemap.xml
  enumerates 233 article URLs.
- Page structure (verified live 2026-08-03):
  - `<h1 class="posttitle">WHISKY NAME</h1>` — the review title.
  - Region label as first text of `.site-content` (e.g. `speyside`).
  - Author + date: `<a href="https://instagram.com/brutdefut">Brut De Fût</a>
    on <time class="post-date" datetime="2026-07-05">05 Jul 2026</time>`.
  - Rating: `<div class="c-rating c-rating--regular" data-rating-value="3">`
    (1-5 stars). JSON-LD Review block exists but is MALFORMED (missing `{`
    after `"reviewRating":`) — never json.loads it; read `data-rating-value`.
  - Sub-scores: `N Complexity / N Character / N Sweetness / N Smoke-Peat`
    (0-10 each) rendered before the intro prose.
  - Tasting notes are ONE prose paragraph with INLINE TR markers
    (`Burun:` / `Damak:` / `Bitiş:`), then a "Scroll to English" link and the
    English equivalent (`Nose:` / `Palate:` / `Finish:`).
  - ABV in prose: `%40 ABV` (TR) or `40% ABV` (EN); age usually NAS.
- EXCERPT_POLICY: store only nose/palate/finish section text (short), the
  1-5 score, ABV/age/cask facts, author, source_url. No raw HTML.
"""
from __future__ import annotations
import re
from typing import List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .editorial_base_adapter import EditorialBaseAdapter, ArticleParse, ListingResult


class FicisertligiAdapter(EditorialBaseAdapter):
    source_id: str = "ficisertligi"
    authority_tier: str = "T2_expert"
    license: str = "copyright-attribution-required"

    # ---- discovery (homepage article cards) ----
    def discover_listing(self, start_url: str, html: str) -> ListingResult:
        soup = BeautifulSoup(html, "html.parser")
        urls: List[str] = []
        seen = set()
        for a in soup.find_all("a", href=True):
            href = str(a["href"])
            # Article cards link to root slugs; filter out nav/asset/about URLs.
            if not href.startswith("/") and "ficisertligi.com/" not in href:
                continue
            u = urljoin(start_url, href)
            path = u.split("//", 1)[-1].split("/", 1)[-1] if "//" in u else u
            if not path or path in ("assets", "images") or "." in path.rsplit("/", 1)[-1]:
                continue
            if u in seen:
                continue
            seen.add(u)
            urls.append(u)
        return ListingResult(article_urls=urls, next_page=None)

    # ---- article parsing ----
    def parse_article(self, url: str, html: str) -> ArticleParse:
        soup = BeautifulSoup(html, "html.parser")

        h1 = soup.find("h1", class_="posttitle")
        raw_name = (h1.get_text(" ", strip=True) if h1 else None) or self._title_fallback(soup)

        # Author + date from the entry-header author box.
        author: Optional[str] = None
        published_date: Optional[str] = None
        time_el = soup.find("time", class_="post-date")
        if time_el is not None:
            published_date = str(time_el.get("datetime") or time_el.get_text(strip=True) or "") or None
        insta = soup.find("a", href=re.compile(r"instagram\.com", re.I))
        if insta is not None:
            author = insta.get_text(" ", strip=True) or None
        if not author:
            m = re.search(r"([A-Za-zÇĞİÖŞÜçğıöşü]+(?:\s+[A-Za-zÇĞİÖŞÜçğıöşü.]+)*)\s+on\s+\d{1,2}\s+[A-Za-z]{3}\s+\d{4}", html)
            if m:
                author = m.group(1).strip()

        # Score: c-rating data-rating-value (1-5 scale).
        score_value: Optional[float] = None
        rating_el = soup.find("div", class_=re.compile(r"c-rating"))
        if rating_el is not None:
            try:
                score_value = float(str(rating_el.get("data-rating-value", "")).strip())
            except ValueError:
                score_value = None

        # Isolate the article body: .article-post (NOT .related-posts).
        body = soup.find("div", class_="article-post") or soup.find("div", class_="main-content")
        body_txt = body.get_text("\n", strip=True) if body else soup.get_text("\n", strip=True)

        # TR sections (Burun/Damak/Bitiş) then EN (Nose/Palate/Finish).
        nose, palate, finish = self._split_sections(body_txt)

        # Region label: first line of site-content before the title.
        region = ""
        sc = soup.find("div", class_="site-content")
        if sc is not None:
            first = sc.get_text(" ", strip=True).split()
            if first and first[0].lower() in (
                "speyside", "highland", "islay", "lowland", "campbeltown", "island",
                "japon", "amerikan", "irlanda", "kanada", "tayvan", "hindistan",
                "dünya", "bourbon", "rye", "single malt", "blended",
            ):
                region = first[0].lower()

        # Facts from prose: ABV, age, cask.
        abv = self._extract_abv(body_txt)
        age = self._extract_age(body_txt)
        cask = self._extract_cask(body_txt)

        # Sub-scores (Complexity/Character/Sweetness/Smoke-Peat 0-10).
        subs = re.findall(
            r"(\d{1,2})\s*(Complexity|Character|Sweetness|Smoke[-\s/]?Peat)", body_txt, re.I
        )
        sub_scores = {k.lower().replace(" ", ""): int(v) for v, k in subs}

        metadata = {
            "region": region,
            "abv": abv,
            "age": age,
            "cask": cask,
            "sub_scores": sub_scores,
            "language": "tr",
            "has_english": "scroll to english" in body_txt.lower(),
        }

        # Short excerpt (<=15 words) from the TR intro prose, attributed.
        quote = self._short_excerpt(body_txt)

        return ArticleParse(
            raw_name=raw_name,
            title=raw_name,
            author=author,
            published_date=published_date,
            score_value=score_value,
            score_scale_max=5.0,
            nose=nose,
            palate=palate,
            finish=finish,
            metadata=metadata,
            quotes=[{"quote": quote, "attribution": f"{author or 'Brut De Fût'} ({url})"}] if quote else [],
        )

    # ---- helpers ----
    @staticmethod
    def _title_fallback(soup: BeautifulSoup) -> str:
        t = soup.title
        if t:
            return re.sub(r"\s*[|–-]\s*.*$", "", t.get_text(strip=True)).strip()
        return ""

    @staticmethod
    def _clean(seg: Optional[str]) -> Optional[str]:
        if not seg:
            return None
        seg = seg.strip().lstrip(";:,").strip()
        return seg or None

    @staticmethod
    def _split_sections(text: str):
        """Return (nose, palate, finish) from TR 'Burun:/Damak:/Bitiş:' markers.

        Falls back to EN 'Nose:/Palate:/Finish:' when TR markers are absent.
        """
        tr = re.search(
            r"Burun\s*:?\s*(.*?)(?:\n|$)Damak\s*:?\s*(.*?)(?:\n|$)Bitiş\s*:?\s*(.*?)(?:\n|$)",
            text, re.I | re.S,
        )
        if tr:
            return (FicisertligiAdapter._clean(tr.group(1)),
                    FicisertligiAdapter._clean(tr.group(2)),
                    FicisertligiAdapter._clean(tr.group(3)))
        en = re.search(
            r"Nose\s*:?\s*(.*?)(?:\n|$)Palate\s*:?\s*(.*?)(?:\n|$)Finish\s*:?\s*(.*?)(?:\n|$)",
            text, re.I | re.S,
        )
        if en:
            return (FicisertligiAdapter._clean(en.group(1)),
                    FicisertligiAdapter._clean(en.group(2)),
                    FicisertligiAdapter._clean(en.group(3)))
        return None, None, None

    @staticmethod
    def _extract_abv(text: str) -> Optional[float]:
        m = re.search(r"(?:%|ABV[:\s]*)\s*(\d{1,3}(?:[.,]\d{1,2})?)\s*%?", text, re.I)
        if m:
            return float(m.group(1).replace(",", "."))
        m = re.search(r"(\d{1,3}(?:[.,]\d{1,2})?)\s*%", text)
        if m:
            return float(m.group(1).replace(",", "."))
        return None

    @staticmethod
    def _extract_age(text: str) -> Optional[int]:
        m = re.search(r"\b(\d{1,2})\s*(?:yaş|years?\s*(?:old)?)\b", text, re.I)
        if m:
            return int(m.group(1))
        if re.search(r"\bNAS\b", text, re.I):
            return None
        return None

    @staticmethod
    def _extract_cask(text: str) -> Optional[str]:
        m = re.search(
            r"(?:first[- ]fill\s+)?(?:ex-)?(?:sherry|bourbon|port|oloroso|px|madeira|rum|virgin oak|"
            r"american white oak|meşe|şeri|porto)\s*(?:cask|fıçı)?", text, re.I,
        )
        return m.group(0).strip().lower() if m else None

    @staticmethod
    def _short_excerpt(text: str) -> str:
        """First real prose sentence after the tasting-note markers, <=15 words."""
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        for i, ln in enumerate(lines):
            if re.match(r"^(Burun|Damak|Bitiş|Nose|Palate|Finish)\s*:", ln, re.I):
                for j in range(i + 1, min(i + 3, len(lines))):
                    if lines[j] and len(lines[j]) > 30 and not re.match(
                        r"^(Su eklemeye|Ödüller|Awards|Viski çoğunlukla|The whisky)", lines[j], re.I
                    ):
                        words = lines[j].split()
                        return " ".join(words[:15]) + ("…" if len(words) > 15 else "")
        return ""
