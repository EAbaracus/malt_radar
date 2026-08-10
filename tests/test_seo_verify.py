"""Uyum denetimi — ihlal yakalama + temiz dizin geçişi."""
import tempfile
from pathlib import Path
from seo.verify import verify

def _write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

def test_verify_catches_price_and_broken_link():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        _write(d / "tr/w/W1/index.html", '<html><head><title>X</title></head><body>₺199 fiyat</body></html>')
        _write(d / "sitemap.xml", '<?xml version="1.0"?><urlset><url><loc>https://maltradar.com/tr/w/W1/</loc></url></urlset>')
        _write(d / "tr/w/W2/index.html", '<html><head></head><body><a href="https://maltradar.com/tr/w/W1/">W1</a><a href="https://maltradar.com/tr/w/MISSING/">x</a></body></html>')
        violations = verify(str(d), expected_pages=2)
        assert any("price" in v.lower() for v in violations)
        assert any("MISSING" in v for v in violations)

def test_verify_clean_dir_passes():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        _write(d / "tr/w/W1/index.html",
               '<html><head><title>W1</title><link rel="canonical" href="https://maltradar.com/tr/w/W1/"></head><body><a href="https://maltradar.com/tr/w/W1/">self</a></body></html>')
        _write(d / "en/w/W1/index.html",
               '<html><head><title>W1</title><link rel="canonical" href="https://maltradar.com/en/w/W1/"></head><body></body></html>')
        _write(d / "sitemap.xml",
               '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://maltradar.com/tr/w/W1/</loc></url><url><loc>https://maltradar.com/en/w/W1/</loc></url></urlset>')
        assert verify(str(d), expected_pages=2) == []