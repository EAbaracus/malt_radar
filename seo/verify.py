"""seo/verify.py — deploy öncesi uyum denetimi (spec §9, test matrisi).

verify() boş liste döndürürse geçti; her ihlal tek satır metin.
"""
import re, xml.etree.ElementTree as ET
from pathlib import Path

BASE = "https://maltradar.com"
PRICE_PATTERN = re.compile(r"production_price|₺|\$|€|£|\bTL\b|\bprice\b", re.IGNORECASE)

# TR mevzuat: social/content.py _FORBIDDEN desenleriyle eşdeğer (spec test 3)
FORBIDDEN = re.compile(r"deneyin|mutlaka|tavsiye|alın|satın|sipariş|kampanya|indirim|fırsat",
                       re.IGNORECASE)


def verify(build_dir: str, expected_pages: int | None = None) -> list[str]:
    d = Path(build_dir)
    violations: list[str] = []

    html_files = sorted(d.rglob("*.html"))
    if expected_pages is not None and len(html_files) != expected_pages:
        violations.append(f"sayfa sayısı: {len(html_files)} != beklenen {expected_pages}")

    urls = {}  # url -> dosya (iç link doğrulaması için)
    for f in html_files:
        txt = f.read_text(encoding="utf-8")
        rel = f.relative_to(d).as_posix()
        url = f"{BASE}/{rel[:-len('index.html')]}" if rel.endswith("index.html") else ""
        if url:
            urls[url] = f
        if PRICE_PATTERN.search(txt):
            violations.append(f"PRICE LEAK: {rel}")
        if FORBIDDEN.search(txt):
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
            for loc in locs:
                if loc not in urls:
                    violations.append(f"sitemap hedefi yok: {loc}")
        except ET.ParseError as e:
            violations.append(f"sitemap XML bozuk: {e}")

    # iç link hedefleri
    for f in html_files:
        txt = f.read_text(encoding="utf-8")
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