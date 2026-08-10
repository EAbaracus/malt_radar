"""seo/verify.py — deploy öncesi uyum denetimi (spec §9, test matrisi).

verify() boş liste döndürürse geçti; her ihlal tek satır metin.
"""
import re, xml.etree.ElementTree as ET
from pathlib import Path

from seo.templates import PRICE_PATTERN, FORBIDDEN_RE  # tek kaynak (templates._e ile aynı)

BASE = "https://maltradar.com"


def verify(build_dir: str, expected_pages: int | None = None) -> list[str]:
    d = Path(build_dir)
    violations: list[str] = []

    html_files = sorted(d.rglob("*.html"))
    if expected_pages is not None and len(html_files) != expected_pages:
        violations.append(f"sayfa sayısı: {len(html_files)} != beklenen {expected_pages}")

    urls = {}  # url -> dosya (iç link doğrulaması için)
    cache: dict = {}  # performans: her dosya 1× okunur (14k+ sayfa)

    def _text(f) -> str:
        if f not in cache:
            cache[f] = f.read_text(encoding="utf-8")
        return cache[f]

    for f in html_files:
        txt = _text(f)
        rel = f.relative_to(d).as_posix()
        url = f"{BASE}/{rel[:-len('index.html')]}" if rel.endswith("index.html") else ""
        if url:
            urls[url] = f
        if PRICE_PATTERN.search(txt):
            violations.append(f"PRICE LEAK: {rel}")
        if FORBIDDEN_RE.search(txt):
            violations.append(f"TR mevzuat ihlali: {rel}")
        if not re.search(r'rel="canonical"', txt):
            violations.append(f"canonical yok: {rel}")

    # sitemap
    sm = d / "sitemap.xml"
    if not sm.exists():
        violations.append("sitemap.xml yok")
    else:
        try:
            root = ET.fromstring(sm.read_text(encoding="utf-8"))
            locs = [e.text for e in root.iter("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")]
            if not locs:
                violations.append("sitemap boş")
            seen = set()
            for loc in locs:
                if loc not in urls:
                    violations.append(f"sitemap hedefi yok: {loc}")
                if loc in seen:
                    violations.append(f"sitemap çift URL: {loc}")
                seen.add(loc)
                # R3: noindex sayfası sitemap'te olmamalı (spec §3)
                target = urls.get(loc)
                if target is not None:
                    if "noindex, follow" in _text(target):
                        violations.append(f"sitemap'te noindex sayfa: {loc}")
        except ET.ParseError as e:
            violations.append(f"sitemap XML bozuk: {e}")

    # R3: hreflang bütünlüğü (spec test #4) — çift yönlü + x-default
    for f in html_files:
        txt = _text(f)
        rel = f.relative_to(d).as_posix()
        if "noindex, follow" in txt:
            continue  # noindex sayfalar hreflang denetiminden muaftır
        hreflangs = dict(re.findall(r'hreflang="([a-z-]+)" href="([^"]+)"', txt))
        if "x-default" not in hreflangs:
            violations.append(f"hreflang x-default yok: {rel}")
        for lang in ("tr", "en"):
            target = hreflangs.get(lang)
            if target is None:
                violations.append(f"hreflang {lang} yok: {rel}")
                continue
            norm = target.rstrip("/") + "/"
            if norm not in urls:
                violations.append(f"hreflang hedefi yok: {rel} -> {target}")
                continue
            back = _text(urls[norm])
            # tek capture grubu -> set (dict() string listesinde patlar)
            back_hrefs = {u.rstrip("/") + "/" for u in re.findall(r'hreflang="[a-z-]+" href="([^"]+)"', back)}
            self_url = f"{BASE}/{rel[:-len('index.html')]}" if rel.endswith("index.html") else ""
            if self_url and self_url.rstrip("/") + "/" not in back_hrefs:
                violations.append(f"hreflang geri-dönüş yok: {rel} -> {target}")

    # iç link hedefleri
    for f in html_files:
        txt = _text(f)
        for href in re.findall(r'href="(https://maltradar\.com[^\"]+)"', txt):
            target = href.rstrip("/") + "/"
            if target not in urls and not target.endswith("/w/"):
                violations.append(f"bozuk link: {f.relative_to(d)} -> {href}")
    return violations


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(prog="seo.verify")
    ap.add_argument("--dir", required=True, help="build dizini")
    ap.add_argument("--expected", type=int, default=None, help="beklenen html sayısı (opsiyonel)")
    args = ap.parse_args()
    v = verify(args.dir, args.expected)
    print("IHLAL" if v else "TEMIZ")
    for x in v:
        print(" -", x)
    raise SystemExit(1 if v else 0)