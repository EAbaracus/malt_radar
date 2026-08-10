"""Şablon testleri — fiyat yok, escape var, canonical+hreflang var."""
from seo.templates import render_whisky_page, render_sitemap, render_robots

WHISKY = {
    "whisky_id": "W003805", "name": "Glenfiddich 12", "brand": "Glenfiddich",
    "distillery_name": "Glenfiddich", "region": "Speyside", "country": "Scotland",
    "age": 12, "type": "Single Malt", "meta_critic_score": 87.0,
    "flavor_profile": {"fruity": 0.8, "sweet": 0.6, "oak_cask": 0.5},
    "evidence_count": 3, "tasting_note": "Armut, vanilya, meşe <script>",
}

def test_whisky_page_no_price_no_rating():
    page = render_whisky_page(WHISKY, "A", "tr",
        "https://maltradar.com/tr/w/W003805/", "https://maltradar.com/en/w/W003805/")
    for bad in ("production_price", "price", "₺", "$", "€", "£", "TL", "aggregateRating",
                '"offers"', "meta_critic_score"):
        assert bad not in page, f"YASAK içerik sızdı: {bad}"
    assert "87" in page

def test_whisky_page_canonical_hreflang_escape():
    page = render_whisky_page(WHISKY, "A", "tr",
        "https://maltradar.com/tr/w/W003805/", "https://maltradar.com/en/w/W003805/")
    assert 'rel="canonical" href="https://maltradar.com/tr/w/W003805/"' in page
    assert 'hreflang="en"' in page and "/en/w/W003805/" in page
    assert "&lt;script&gt;" in page
    assert "<script>" not in page
    assert "W003805" in page

def test_whisky_page_jsonld_product_no_offers():
    page = render_whisky_page(WHISKY, "A", "en",
        "https://maltradar.com/en/w/W003805/", "https://maltradar.com/tr/w/W003805/")
    assert '"@type": "Product"' in page
    assert "BreadcrumbList" in page

def test_sitemap_and_robots():
    sm = render_sitemap([("https://maltradar.com/tr/w/W1/", "2026-08-10"),
                          ("https://maltradar.com/en/w/W1/", "2026-08-10")])
    assert sm.startswith("<?xml") and "<urlset" in sm
    assert sm.count("<url>") == 2
    rb = render_robots()
    assert "Disallow: /api/" in rb and "Sitemap:" in rb
