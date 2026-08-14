"""Whisky Saga (whiskysaga.com) — English editorial whisky review adapter.

Source profile:
- Squarespace site (same platform as Dramface). robots.txt `User-agent: *`
  disallows only /config, /search, /account$ — blog is fully crawlable
  (re-verified live 2026-08-03; AI-bot UAs are blocked separately, a generic
  descriptive research UA is allowed).
- Sitemap: single flat urlset (2.3 MB) with 4,937 URLs, of which ~4,903 are
  `/blog/<slug>` article permalinks.
- Page structure (verified live 2026-08-03 on Yoichi 13 YO 1989/2003):
  - `<h1>` = review title (e.g. "Yoichi 13 YO (1989/2003) cask #228276").
  - `.blog-item-top-wrapper` holds: country ("Japan"), type ("Single Malt"),
    date ("22 Jul"), author ("Written By Thomas Øhrbom").
  - Body `.blog-item-inner-wrapper` contains a lead line with ABV
    ("Yoichi 13 YO (1989/2003) cask #228276, 62.3 %"), then sections:
    `Nose:` / `Taste:` / `Finish:` / `Comment:` and a final
    `Score NN/100`.
  - Tag list at the end (distillery / brand / vintage / age / bottler).
- EXCERPT_POLICY: store only Nose/Taste/Finish section text (short), the
  /100 score, facts (ABV/vintage/age/cask), author, source_url. No raw HTML.
"""
from __future__ import annotations
import re
from typing import List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .editorial_base_adapter import EditorialBaseAdapter, ArticleParse, ListingResult


class WhiskySagaAdapter(EditorialBaseAdapter):
    source_id: str = "whiskysaga"
    authority_tier: str = "T2_expert"
    license: str = "copyright-attribution-required"

    # ---- discovery (Squarespace blog listing) ----
    def discover_listing(self, start_url: str, html: str) -> ListingResult:
        soup = BeautifulSoup(html, "html.parser")
        urls: List[str] = []
        seen = set()
        for a in soup.find_all("a", href=True):
            href = str(a["href"])
            u = urljoin(start_url, href)
            if "/blog/" not in u:
                continue
            if any(x in u for x in ("/category/", "/tag/", "/search", "?",
                                    "#", "squarespace", "static1", "images.squarespace")):
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

        # Top wrapper: country / type / date / author.
        top = soup.find("div", class_=re.compile(r"blog-item-top-wrapper")) or soup.find(
            "div", class_=re.compile(r"blog-item-inner-wrapper")
        )
        top_txt = top.get_text("\n", strip=True) if top else ""

        author: Optional[str] = None
        m = re.search(r"Written\s+By\s*\n?\s*([A-Za-zÀ-ž][A-Za-zÀ-ž' .-]+)", top_txt)
        if m:
            author = m.group(1).strip()
        if not author:
            m = re.search(r"(?:by|By)\s+([A-Za-zÀ-ž][A-Za-zÀ-ž' .-]{2,40})", html)
            if m:
                author = m.group(1).strip()

        published_date: Optional[str] = None
        m = re.search(r"\b(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)", top_txt)
        if m:
            months = {"Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04", "May": "05",
                      "Jun": "06", "Jul": "07", "Aug": "08", "Sep": "09", "Oct": "10",
                      "Nov": "11", "Dec": "12"}
            published_date = f"2026-{months[m.group(2)]}-{int(m.group(1)):02d}"
        # Prefer explicit JSON-LD/datePublished when present.
        for s in soup.find_all("script", type="application/ld+json"):
            try:
                import json as _json
                d = _json.loads(s.string or s.get_text())
                nodes = d if isinstance(d, list) else [d]
                for node in nodes:
                    if isinstance(node, dict) and node.get("@type") in ("BlogPosting", "Article", "Review"):
                        if node.get("datePublished"):
                            published_date = node["datePublished"][:10]
                            if not author:
                                a = node.get("author") or {}
                                if isinstance(a, dict):
                                    author = a.get("name")
            except (ValueError, TypeError):
                continue

        # Body: Nose / Taste / Finish / Comment sections + Score.
        body = soup.find("div", class_=re.compile(r"blog-item-inner-wrapper")) or soup.find(
            "div", class_=re.compile(r"entry-content|blog-item")
        )
        body_txt = body.get_text("\n", strip=True) if body else soup.get_text("\n", strip=True)

        nose, palate, finish, comment = self._sections(body_txt)
        score_value, score_scale = self._score(body_txt)
        abv = self._abv(body_txt)
        vintage, age = self._vintage_age(body_txt, raw_name)
        tags = self._tags(body_txt)

        quote = self._short_excerpt(body_txt)

        return ArticleParse(
            raw_name=raw_name,
            title=raw_name,
            author=author,
            published_date=published_date,
            score_value=score_value,
            score_scale_max=score_scale,
            nose=nose,
            palate=palate,
            finish=finish,
            conclusion=comment,
            metadata={
                "country": self._country(top_txt),
                "type": self._drink_type(top_txt),
                "abv": abv,
                "vintage": vintage,
                "age": age,
                "tags": tags,
                "language": "en",
            },
            quotes=[{"quote": quote, "attribution": f"{author or 'Whisky Saga'} ({url})"}] if quote else [],
        )

    # ---- helpers ----
    @staticmethod
    def _title_fallback(soup: BeautifulSoup) -> str:
        t = soup.title
        if t:
            return re.sub(r"\s*[—–-]\s*.*$", "", t.get_text(strip=True)).strip()
        return ""

    @staticmethod
    def _country(top_txt: str) -> Optional[str]:
        m = re.search(r"^\s*(Japan|Scotland|Ireland|USA|Canada|Taiwan|India|Sweden|Norway|"
                      r"Finland|Denmark|Iceland|France|Germany|Australia|New Zealand|England|"
                      r"Wales|Belgium|Netherlands|Switzerland|Austria|Italy|Spain|Turkey|"
                      r"Czech|South Africa|Israel|Korea|China|Fiji|Wales)\b", top_txt, re.M)
        return m.group(1) if m else None

    @staticmethod
    def _drink_type(top_txt: str) -> Optional[str]:
        m = re.search(r"\b(Single Malt|Blended Malt|Single Grain|Blended|Single Cask|"
                      r"Bourbon|Rye|Single Pot Still|Blended Scotch|Pure Single|"
                      r"Single Cask Rum|Pot Still|Malt Whisky|Single Malt Whisky)\b", top_txt)
        return m.group(1) if m else None

    @staticmethod
    def _sections(text: str):
        def grab(label: str, lookahead: str):
            m = re.search(
                rf"{label}\s*:\s*\n?\s*(.*?)(?=\n\s*(?:{lookahead})\s*:)", text, re.I | re.S
            )
            return m.group(1).strip() if m else None

        nose = grab("Nose", "Taste|Finish|Comment|Score")
        palate = grab("Taste", "Finish|Comment|Score")
        finish = grab("Finish", "Comment|Score")
        # Comment runs to the end of the review prose (before Score / Sláinte).
        comment = None
        m = re.search(r"Comment\s*:\s*\n?\s*(.*?)(?=\n\s*(?:Score\s*\d|Sláinte|Slainte))", text, re.I | re.S)
        if m:
            comment = m.group(1).strip()
        return nose, palate, finish, comment

    @staticmethod
    def _score(text: str):
        m = re.search(r"Score\s*(\d{1,3})\s*/\s*(\d{1,3})", text, re.I)
        if m:
            return float(m.group(1)), float(m.group(2))
        m = re.search(r"Score\s*[:.]?\s*(\d{1,3})(?:\s*/\s*100)?", text, re.I)
        if m:
            return float(m.group(1)), 100.0
        return None, None

    @staticmethod
    def _abv(text: str) -> Optional[float]:
        m = re.search(r"(\d{1,3}(?:[.,]\d{1,2})?)\s*%", text)
        if m:
            return float(m.group(1).replace(",", "."))
        return None

    @staticmethod
    def _vintage_age(text: str, name: str):
        vintage = None
        m = re.search(r"\b(19|20)\d{2}\b", name)
        if not m:
            m = re.search(r"\b(19|20)\d{2}\b", text)
        if m:
            vintage = int(m.group(0))
        age = None
        m = re.search(r"\b(\d{1,2})\s*(?:YO|Y\.O|year[- ]old|years? old|yaş)\b", name, re.I)
        if not m:
            m = re.search(r"\b(\d{1,2})\s*(?:YO|Y\.O)\b", text, re.I)
        if m and int(m.group(1)) > 0:
            age = int(m.group(1))
        return vintage, age

    @staticmethod
    def _tags(text: str) -> List[str]:
        # The trailing tag list (one token per line) after the last section.
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        if len(lines) <= 2:
            return []
        # Look for the tag block: tokens that are single words/numbers.
        tags, seen = [], set()
        for ln in lines[-12:]:
            if re.match(r"^[A-Za-zÀ-ž0-9][A-Za-zÀ-ž0-9 .#&'-]*$", ln) and len(ln) < 60:
                low = ln.lower()
                if low not in seen and low not in ("sláinte!",):
                    seen.add(low)
                    tags.append(ln)
        return tags

    @staticmethod
    def _short_excerpt(text: str) -> str:
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        for i, ln in enumerate(lines):
            if re.match(r"^(Nose|Taste|Finish|Comment)\s*:", ln, re.I):
                for j in range(i + 1, min(i + 2, len(lines))):
                    words = lines[j].split()
                    if len(words) >= 5:
                        return " ".join(words[:15]) + ("…" if len(words) > 15 else "")
        return ""
