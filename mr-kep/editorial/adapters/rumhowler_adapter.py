"""The Rum Howler Blog (therumhowlerblog.com) — English spirits review adapter.

Source profile:
- WordPress.com site; robots.txt disallows only /wp-admin/ etc. (re-verified
  live 2026-08-03). Sitemap: flat urlset (353 KB) with both category URLs
  (`/whisky-reviews/<cat>/<slug>/`) and dated duplicates
  (`/YYYY/MM/DD/review-<slug>/`) — dedupe on the canonical category URL.
- Page structure (verified live on Great Plains Cognac Casks 22):
  - `<h1>` = review title (site title is a separate h1 — pick the second).
  - Lead line: `Review: <Name>  NN/100` (the score, 100-point scale).
  - Author `Review by Chip Dykstra`, `Published <Month> DD, YYYY`.
  - Scored sections: `In the Bottle X/5`, `In the Glass X/5`,
    `In the Mouth X/5`, `The Verdict X/5` — narrative prose (whisky/rum/gins).
- EXCERPT_POLICY: store only short section text, the /100 score, author,
  source_url. No raw HTML.
"""
from __future__ import annotations
import re
from typing import List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .editorial_base_adapter import EditorialBaseAdapter, ArticleParse, ListingResult


class RumHowlerAdapter(EditorialBaseAdapter):
    source_id: str = "therumhowlerblog"
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
            if "therumhowlerblog.com" not in u:
                continue
            # Canonical review URLs: /whisky-reviews/... (skip dated dupes).
            if "/whisky-reviews/" not in u:
                continue
            if any(x in u for x in ("/category/", "/tag/", "/page/", "/wp-",
                                    "/feed", "/author", "?", "#")):
                continue
            if u.rstrip("/") == "https://therumhowlerblog.com/whisky-reviews":
                continue
            if u in seen:
                continue
            seen.add(u)
            urls.append(u)
        return ListingResult(article_urls=urls, next_page=self.next_page_url(start_url, html))

    # ---- article parsing ----
    def parse_article(self, url: str, html: str) -> ArticleParse:
        soup = BeautifulSoup(html, "html.parser")

        h1s = [h.get_text(" ", strip=True) for h in soup.find_all("h1")
               if "navigation" not in h.get_text().lower()]
        raw_name = h1s[-1] if h1s else self._title_fallback(soup)
        # Strip a leading "Review: " if the h1 carries it.
        if raw_name and raw_name.lower().startswith("review: "):
            raw_name = raw_name[8:]

        author: Optional[str] = None
        # Formats seen live: "Reviewed by Chip Dykstra (Aka Arctic Wolf)",
        # "a review by Chip Dykstra (AKA Arctic Wolf)" (og:description),
        # and older "Review, Chip Dykstra." — "by" is mandatory in the main
        # pattern so "review for me" can never match.
        m = re.search(r"review(?:ed)?\s+by\s+([A-Za-zÀ-ž][A-Za-zÀ-ž' .-]{2,40}?)(?=\s*(?:\(|&|<|\.|,|\n|$))", html, re.I)
        if m:
            author = m.group(1).strip()

        published_date: Optional[str] = None
        # Live pages carry the date in a meta tag, not "Published <Month> D, YYYY".
        m = re.search(r'published_time"\s+content="(\d{4}-\d{2}-\d{2})', html)
        if m:
            published_date = m.group(1)
        if not published_date:
            m = re.search(r"Published\s+([A-Za-z]+ \d{1,2}, \d{4})", html)
            if m:
                published_date = self._parse_date(m.group(1))

        body = soup.find("article") or soup.find("div", class_=re.compile(
            r"entry-content|post-content|td-post-content", re.I))
        body_txt = body.get_text("\n", strip=True) if body else soup.get_text("\n", strip=True)

        # Score: "Review: <Name>  NN/100" in the lead line.
        score_value = self._score(body_txt)

        if not author:
            m = re.search(r"review(?:ed)?\s+by\s+([A-Za-zÀ-ž][A-Za-zÀ-ž' .-]{2,40}?)(?=\s*(?:\(|&|<|\.|,|\n|$))", body_txt, re.I)
            if m:
                author = m.group(1).strip()
        if not author:
            # Older posts: "Review, Chip Dykstra."
            m = re.search(r"review\s*,\s*([A-Za-zÀ-ž][A-Za-zÀ-ž' .-]{2,40}?)(?=\s*(?:\(|&|<|\.|,|\n|$))", html, re.I)
            if m:
                author = m.group(1).strip()
        if not author:
            # Sidebar copyright widget on single-author blog:
            # "the permission of the author, Chip Dykstra."
            m = re.search(r"the author,\s*([A-Za-zÀ-ž][A-Za-zÀ-ž' .-]{2,40}?)(?=\s*(?:\(|&|<|\.|,|\n|$))", html, re.I)
            if m:
                author = m.group(1).strip()

        # Narrative sections: In the Bottle / In the Glass / In the Mouth.
        nose = self._grab_section(body_txt, r"In the (?:Glass|Nose)")
        palate = self._grab_section(body_txt, r"In the Mouth|Palate")
        finish = self._grab_section(body_txt, r"The Verdict|Finish")

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
            metadata={"language": "en"},
            quotes=[{"quote": quote, "attribution": f"{author or 'The Rum Howler'} ({url})"}] if quote else [],
        )

    # ---- helpers ----
    @staticmethod
    def _title_fallback(soup: BeautifulSoup) -> str:
        t = soup.title
        if t:
            return re.sub(r"\s*[|–—-]\s*.*$", "", t.get_text(strip=True)).strip()
        return ""

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
    def _score(text: str) -> Optional[float]:
        # Decimal support: "82.5/100" must NOT collapse to "5/100" (5.0).
        m = re.search(r"Review\s*:\s*.*?(\d{1,3}(?:\.\d+)?)\s*/\s*100", text, re.I | re.S)
        if m:
            return float(m.group(1))
        m = re.search(r"(\d{1,3}(?:\.\d+)?)\s*/\s*100", text)
        if m:
            return float(m.group(1))
        return None

    @staticmethod
    def _grab_section(text: str, pattern: str) -> Optional[str]:
        # Section headers carry their score on the SAME line: "In the Bottle 3.5/5".
        m = re.search(rf"(?:{pattern})(?:\s+\d{{1,2}}(?:\.\d)?\s*/\s*\d{{1,2}})?\s*\n(.*?)(?=\n\s*(?:In the|The Verdict)|\Z)", text, re.I | re.S)
        if m and m.group(1):
            seg = m.group(1).strip()
            return seg[:300] if seg else None
        return None

    @staticmethod
    def _short_excerpt(text: str) -> str:
        for para in text.splitlines():
            p = para.strip()
            if len(p) >= 30 and not re.match(r"^(Review|In the|The Verdict|Published)", p, re.I):
                words = p.split()
                return " ".join(words[:15]) + ("…" if len(words) > 15 else "")
        return ""
