"""The Scotch Noob (scotchnoob.com) — English editorial whisky review adapter.

Source profile:
- WordPress-style blog; robots.txt `User-agent: *` allows all (Sitemap:
  https://scotchnoob.com/sitemap.xml — re-verified live 2026-08-03).
- Sitemap: flat urlset, 1,111 URLs in `/YYYY/MM/DD/slug/` date-path format
  (includes month archives `/2010/11/` and the homepage — filter to 4+ path
  segments with a date prefix).
- Page structure (verified live on Lagavulin 16):
  - `<h1>` = review title (e.g. "Lagavulin (16 year)").
  - Narrative review — NO Nose:/Palate:/Finish: labels. Sections are prose
    paragraphs: "The aroma is…", "The mouthfeel is…", "The finish is…".
  - Spec block at the end: `NN.N% ABV` line, `Mark:` (score, often absent),
    tags like `Islay / Lagavulin / Malt / Peat / Scotch / Single Malt`.
  - Date: `<time>` / date line "November 12, 2010".
- EXCERPT_POLICY: store only short section excerpts, ABV/age facts, author,
  source_url. No raw HTML. Never fabricate a score (Mark: often absent).
"""
from __future__ import annotations
import re
from typing import List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .editorial_base_adapter import EditorialBaseAdapter, ArticleParse, ListingResult


class ScotchNoobAdapter(EditorialBaseAdapter):
    source_id: str = "scotchnoob"
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
            if "scotchnoob.com" not in u:
                continue
            if not re.search(r"/20\d\d/\d\d/\d\d/", u):
                continue  # article URLs are /YYYY/MM/DD/slug/
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
            if t and "navigation" not in t.lower() and "search" not in t.lower():
                h1 = t
                break
        raw_name = h1 or self._title_fallback(soup)

        author = "The Scotch Noob"
        published_date: Optional[str] = None
        m = re.search(r"\b([A-Z][a-z]+ \d{1,2}, \d{4})\b", html)
        if m:
            published_date = self._parse_date(m.group(1))

        # Body: longest article block.
        body = self._main_region(soup)
        body_txt = body.get_text("\n", strip=True) if body else soup.get_text("\n", strip=True)

        # Narrative sections: aroma / mouthfeel / finish paragraphs.
        nose = self._grab_para(body_txt, r"(?:The aroma|On the nose|Aroma)")
        palate = self._grab_para(body_txt, r"(?:The mouthfeel|On the palate|The early flavors)")
        finish = self._grab_para(body_txt, r"(?:The finish|On the finish|finish is)")

        abv = self._abv(body_txt)
        age = self._age(raw_name, body_txt)
        tags = self._tags(body_txt)

        score_value = self._mark_score(body_txt)

        quote = self._short_excerpt(body_txt)

        return ArticleParse(
            raw_name=raw_name,
            title=raw_name,
            author=author,
            published_date=published_date,
            score_value=score_value,
            score_scale_max=100.0 if score_value else None,
            nose=nose,
            palate=palate,
            finish=finish,
            metadata={"abv": abv, "age": age, "tags": tags, "language": "en"},
            quotes=[{"quote": quote, "attribution": f"{author} ({url})"}] if quote else [],
        )

    # ---- helpers ----
    @staticmethod
    def _title_fallback(soup: BeautifulSoup) -> str:
        t = soup.title
        if t:
            return re.sub(r"\s*[|–—-]\s*.*$", "", t.get_text(strip=True)).strip()
        return ""

    @staticmethod
    def _main_region(soup: BeautifulSoup):
        best, best_len = None, 0
        for el in soup.find_all(["article", "div"], class_=re.compile(
                r"entry-content|post-content|td-post-content|single-content|ast-article", re.I)):
            t = el.get_text(" ", strip=True)
            if len(t) > best_len:
                best, best_len = el, len(t)
        if best and best_len > 200:
            return best
        return None

    @staticmethod
    def _parse_date(s: str) -> Optional[str]:
        months = {"January": "01", "February": "02", "March": "03", "April": "04",
                  "May": "05", "June": "06", "July": "07", "August": "08",
                  "September": "09", "October": "10", "November": "11", "December": "12"}
        m = re.match(r"([A-Za-z]+) (\d{1,2}), (\d{4})", s)
        if m and m.group(1) in months:
            return f"{m.group(3)}-{months[m.group(1)]}-{int(m.group(2)):02d}"
        return None

    @staticmethod
    def _grab_para(text: str, pattern: str) -> Optional[str]:
        m = re.search(pattern + r"\b[^.\n]*[.:]?\s*(.*?)(?=\n\s*[A-Z]|$)", text, re.I | re.S)
        if m:
            seg = m.group(0).strip()
            return seg[:300] if seg else None
        return None

    @staticmethod
    def _abv(text: str) -> Optional[float]:
        m = re.search(r"(\d{1,3}(?:[.,]\d{1,2})?)\s*%\s*ABV", text, re.I)
        if m:
            return float(m.group(1).replace(",", "."))
        m = re.search(r"(\d{1,3}(?:[.,]\d{1,2})?)\s*%", text)
        if m:
            return float(m.group(1).replace(",", "."))
        return None

    @staticmethod
    def _age(name: str, text: str) -> Optional[int]:
        m = re.search(r"\((\d{1,2})\s*(?:year|yo)\)|(\d{1,2})\s*year\s*[- ]?(?:old|single)", name + " " + text, re.I)
        if m:
            v = int(m.group(1) or m.group(2))
            return v if v > 0 else None
        return None

    @staticmethod
    def _tags(text: str) -> List[str]:
        m = re.search(r"(Islay|Highland|Speyside|Lowland|Campbeltown|Islands|Bourbon|Rye|Malt|Peat|Scotch|Single Malt|Blended)(?:\s*/\s*([A-Za-zÇĞİÖŞÜçğıöşü&' .-]+))+", text)
        if m:
            return [x.strip() for x in re.split(r"\s*/\s*", m.group(0)) if x.strip()]
        return []

    @staticmethod
    def _mark_score(text: str) -> Optional[float]:
        # "ScotchNoob Mark : 92" — the old grading line; often absent.
        m = re.search(r"Mark\s*:?\s*(\d{2,3})(?:\s*/\s*100)?", text)
        if m and 0 < int(m.group(1)) <= 100:
            return float(m.group(1))
        return None

    @staticmethod
    def _short_excerpt(text: str) -> str:
        for para in text.splitlines():
            p = para.strip()
            if len(p) >= 30 and not re.match(r"^(Lagavulin|Mark|Price|Acquired|http|Islay|Share)", p, re.I):
                words = p.split()
                return " ".join(words[:15]) + ("…" if len(words) > 15 else "")
        return ""
