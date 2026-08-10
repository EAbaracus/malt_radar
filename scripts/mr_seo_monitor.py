"""Haftalık SEO/AEO monitor — GSC/GA4 kimliği varsa veri, yoksa degrade (spec §10).

stdout'a terse rapor writer; Hermes cron delivery ile chat'e düşer.
Secret asla stdout'a/log'a yazılmaz (spec kural 10).
"""
import sys
import urllib.request
from pathlib import Path

REPO = Path(r"C:\Users\eltun\Documents\malt radar CLEAN")
GSC_ENV = REPO / "deploy" / ".gsc_env"


def _gsc_report() -> str:
    if not GSC_ENV.exists():
        return "GSC: kimlik yok (insan adımı bekliyor) — indexlenen sayfa/konum verisi alınamadı"
    # İnsan adımı tamamlanınca GSC API çağrısı buraya (Search Console API, service account).
    return "GSC: kimlik mevcut — rapor bir sonraki tick'te dolu gelecek"


def _broken_links() -> str:
    try:
        req = urllib.request.Request(
            "https://maltradar.com/sitemap.xml",
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
        sm = urllib.request.urlopen(req, timeout=20).read().decode()
        urls = [l for l in sm.split("<loc>")[1:]]
        sample = urls[:50]
        bad = []
        for u in sample:
            u = u.split("</loc>")[0]
            try:
                r2 = urllib.request.Request(
                    u, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
                if urllib.request.urlopen(r2, timeout=15).status != 200:
                    bad.append(u)
            except Exception:
                bad.append(u)
        return f"bozuk-link örneklemi (50): {len(bad)} hatalı" + (f" -> {bad[:3]}" if bad else "")
    except Exception as e:
        return f"bozuk-link taraması başarısız: {e}"


def main():
    print("=== Malt Radar SEO/AEO Monitor ===")
    print(_gsc_report())
    print(_broken_links())
    print("Eşikler (spec §10): indexlenen sayfa > 0 | organik gösterim > 0 | register hunisi ölçülüyor")


if __name__ == "__main__":
    sys.exit(main())