"""Great Drams (greatdrams.com) — English whisky review adapter.

Source profile:
- WordPress + WooCommerce; robots.txt allows all (only /wp-admin/ and
  woocommerce upload paths disallowed; Yoast block Disallow: empty).
  Re-verified live 2026-08-03. Sitemap index -> post-sitemap*.xml.
- Reviews live at root slugs like `/ardbeg-10-cask-strength-review/` and are
  listed under `/category/whisky-reviews/` (+ subcategories). Many posts are
  news/listicles — keep only URLs with `-review` in the slug.
- Page structure (verified live on Ardbeg 10 Cask Strength Review):
  - `<h1>` = review title (e.g. "Ardbeg 10 Cask Strength Review").
  - Narrative review — "On the nose…", "On the palate…", "The finish…"
    prose paragraphs; ABV inline ("61.7% ABV").
  - JSON-LD is QAPage (not Review) — do not rely on it for the score.
  - No explicit score on most pages (never fabricate).
- EXCERPT_POLICY: store only short section text, ABV/age facts, author,
  source_url. No raw HTML.
"""
from __future__ import annotations
import re
from typing import List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .editorial_base_adapter import EditorialBaseAdapter, ArticleParse, ListingResult


class GreatDramsAdapter(EditorialBaseAdapter):
    source_id: str = "greatdrams"
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
            if "greatdrams.com" not in u:
                continue
            path = u.split("greatdrams.com", 1)[-1].rstrip("/")
            if not re.search(r"-review$|-review/", u, re.I) or "/category/" in u or "/tag/" in u:
                continue
            if any(x in u for x in ("/wp-", "/page/", "/feed", "/shop", "/whisky-shop",
                                    "/author", "?", "#", "/login", "/register")):
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
            if t and "login" not in t.lower() and "navigation" not in t.lower():
                h1 = t
                break
        raw_name = h1 or self._title_fallback(soup)

        author: Optional[str] = None
        m = re.search(r"\b(?:by|By)\s+([A-Za-zÀ-ž][A-Za-zÀ-ž' .-]{2,40}?)(?:\n|$|,)", html)
        if m and not re.search(r"\b(distillery|them|us|the team)\b", m.group(1), re.I):
            author = m.group(1).strip()
        if not author:
            m = re.search(r'"author":\s*\{[^}]*"name":\s*"([^"]+)"', html)
            if m:
                author = m.group(1)

        published_date: Optional[str] = None
        m = re.search(r'property="article:published_time"\s+content="([^"]+)"', html)
        if m:
            published_date = m.group(1)[:10]
        if not published_date:
            m = re.search(r"<time[^>]*datetime=\"([^\"]+)\"", html)
            if m:
                published_date = m.group(1)[:10]

        body = soup.find("article") or soup.find("div", class_=re.compile(
            r"entry-content|post-content|td-post-content", re.I))
        body_txt = body.get_text("\n", strip=True) if body else soup.get_text("\n", strip=True)

        # Narrative sections.
        nose = self._grab(body_txt, r"On the nose[^.]*\.\s*")
        palate = self._grab(body_txt, r"On the palate[^.]*\.\s*")
        finish = self._grab(body_txt, r"(?:The finish|On the finish)[^.]*\.\s*")

        abv = self._abv(body_txt)
        age = self._age(raw_name)

        quote = self._short_excerpt(body_txt)

        return ArticleParse(
            raw_name=raw_name,
            title=raw_name,
            author=author,
            published_date=published_date,
            score_value=None,
            score_scale_max=None,
            nose=nose,
            palate=palate,
            finish=finish,
            metadata={"abv": abv, "age": age, "language": "en"},
            quotes=[{"quote": quote, "attribution": f"{author or 'Great Drams'} ({url})"}] if quote else [],
        )

    # ---- helpers ----
    @staticmethod
    def _title_fallback(soup: BeautifulSoup) -> str:
        t = soup.title
        if t:
            return re.sub(r"\s*[|–—-]\s*.*$", "", t.get_text(strip=True)).strip()
        return ""

    @staticmethod
    def _grab(text: str, pattern: str) -> Optional[str]:
        m = re.search(pattern + r"(.*?)(?=\n\s*(?:On the|The finish|Photo|Share|\w+ \d{1,2}, \d{4})|\Z)", text, re.I | re.S)
        if m:
            seg = (m.group(1) or "").strip()
            return seg[:250] if seg else None
        return None

    @staticmethod
    def _abv(text: str) -> Optional[float]:
        # Only explicit bottle-level phrases are trustworthy in narrative
        # reviews; "NN% ABV" alone can be a process mention ("new make at 70%")
        # or a comparison to a DIFFERENT expression ("comes in at 46% ABV").
        # Return None rather than a wrong value (no fabrication).
        for pat in (r"(?:clocks in at|bottled at|weighs in at)\s+(?:a\s+)?(\d{1,3}(?:[.,]\d{1,2})?)\s*%",
                    r"(?:this|the)\s+(\d{1,3}(?:[.,]\d{1,2})?)\s*%\s*ABV"):
            m = re.search(pat, text, re.I)
            if m:
                return float(m.group(1).replace(",", "."))
        return None

    @staticmethod
    def _age(name: str) -> Optional[int]:
        m = re.search(r"\b(\d{1,2})\s*(?:year|yo|year old|yaş)", name, re.I)
        if m:
            return int(m.group(1))
        return None

    @staticmethod
    def _short_excerpt(text: str) -> str:
        for para in text.splitlines():
            p = para.strip()
            if len(p) >= 30 and not re.match(r"^(Photo|Ardbeg|The |On the|Share|Login)", p, re.I):
                words = p.split()
                return " ".join(words[:15]) + ("…" if len(words) > 15 else "")
        return ""
