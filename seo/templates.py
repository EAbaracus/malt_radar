"""seo/templates.py — f-string HTML şablonları (stdlib-only, spec §4-§6).

Kurallar:
  - Tüm dinamik değerler html.escape() — XSS (test 10)
  - Fiyat/offers/aggregateRating ASLA (Product Rule)
  - 7 app ekseni etiketli, TR/EN lokalize; vector_* yok
"""
import html as _h
import json as _j

BASE = "https://maltradar.com"
AXES_TR = {"fruity": "Meyvemsi", "sweet": "Tatlı", "spicy": "Baharatlı",
           "smoky_peaty": "Dumanlı/Turba", "oak_cask": "Meşe Fıçı",
           "malty_cereal": "Maltlı/Tahıllı", "floral_herbal": "Çiçeksi/Otsu",
           "maritime": "Denizcilik"}
AXES_EN = {"fruity": "Fruity", "sweet": "Sweet", "spicy": "Spicy",
           "smoky_peaty": "Smoky/Peaty", "oak_cask": "Oak Cask",
           "malty_cereal": "Malty/Cereal", "floral_herbal": "Floral/Herbal",
           "maritime": "Maritime"}
_CTA_TR = "Malt Radar'da keşfet — kayıt ol: https://maltradar.com/"
_CTA_EN = "Explore on Malt Radar — sign up: https://maltradar.com/"


def _e(s) -> str:
    return _h.escape(str(s if s is not None else ""), quote=True)


def hreflang_tags(lang: str, self_url: str, alt_url: str) -> str:
    other = "en" if lang == "tr" else "tr"
    return (
        f'<link rel="canonical" href="{_e(self_url)}">\n'
        f'<link rel="alternate" hreflang="{lang}" href="{_e(self_url)}">\n'
        f'<link rel="alternate" hreflang="{other}" href="{_e(alt_url)}">\n'
        f'<link rel="alternate" hreflang="x-default" href="{_e(self_url if lang == "tr" else alt_url)}">'
    )


def _breadcrumb_jsonld(items: list[tuple[str, str]]) -> dict:
    return {
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1,
             "name": _e(n), "item": _e(u)} for i, (n, u) in enumerate(items)
        ],
    }


def _product_jsonld(w: dict) -> dict:
    return {
        "@context": "https://schema.org", "@type": "Product",
        "name": _e(w.get("name")),
        "description": _e(w.get("seo_description", "")),
        "category": _e(w.get("type") or w.get("region") or ""),
        "brand": {"@type": "Brand", "name": _e(w.get("brand") or w.get("distillery_name") or "")},
    }


def _radar_svg(profile: dict, lang: str) -> str:
    """Etiketli radar — 7 app ekseni, veriden. vector_* YOK."""
    axes = AXES_TR if lang == "tr" else AXES_EN
    labels = []
    for k, v in (profile or {}).items():
        if k in axes and isinstance(v, (int, float)):
            labels.append(f'<li><span class="axis">{_e(axes[k])}</span>: {v:.2f}</li>')
    return (f'<svg viewBox="0 0 240 160" xmlns="http://www.w3.org/2000/svg" '
            f'role="img" aria-label="flavor profile"></svg>'
            f'<ul class="flavor-axes">' + "".join(labels) + "</ul>")


def render_whisky_page(w: dict, tier: str, lang: str, self_url: str, alt_url: str) -> str:
    name = _e(w.get("name") or w.get("whisky_id"))
    desc = _e(w.get("seo_description") or f"{name} — {_e(w.get('region') or w.get('type') or 'viski')} lezzet profili.")
    schema = _j.dumps({"@context": "https://schema.org", "@graph": [
        {"@type": "Organization", "name": "Malt Radar", "url": BASE}]
    }, ensure_ascii=False)
    if tier == "A":
        schema = _j.dumps({"@context": "https://schema.org", "@graph": [
            {"@type": "Organization", "name": "Malt Radar", "url": BASE},
            _breadcrumb_jsonld([("Malt Radar", BASE), (name, self_url)]),
            _product_jsonld(w)]}, ensure_ascii=False)
    radar = _radar_svg(w.get("flavor_profile"), lang) if tier == "A" else ""
    note = _e(w.get("tasting_note", "")) if tier == "A" else ""
    score = w.get("meta_critic_score")
    score_html = ""
    if score is not None:
        label = "Kritik puanı" if lang == "tr" else "Critic score"
        score_html = f'<p>{label}: {_e(score)}</p>'
    extra = ("<p>Veri ekleniyor.</p>" if tier in ("B",) else "")
    return f"""<!DOCTYPE html>
<html lang="{lang}"><head><meta charset="utf-8">
<title>{name} — Malt Radar</title>
<meta name="description" content="{desc}">
{hreflang_tags(lang, self_url, alt_url)}
<script type="application/ld+json">{schema}</script>
</head><body>
<nav><a href="{BASE}/{lang}/">Malt Radar</a></nav>
<main>
<h1>{name}</h1>
<p>{desc}</p>
{radar}
{note}
{score_html}
{extra}
<p>{_CTA_TR if lang == 'tr' else _CTA_EN}</p>
</main></body></html>"""


def render_list_page(title, items, lang, self_url, alt_url) -> str:
    rows = "".join(
        f'<li><a href="{_e(it["url"])}">{_e(it["name"])}</a></li>' for it in items)
    return f"""<!DOCTYPE html>
<html lang="{lang}"><head><meta charset="utf-8">
<title>{_e(title)} — Malt Radar</title>
{hreflang_tags(lang, self_url, alt_url)}
</head><body>
<nav><a href="{BASE}/{lang}/">Malt Radar</a></nav>
<main><h1>{_e(title)}</h1><ul>{rows}</ul>
<p>{_CTA_TR if lang == 'tr' else _CTA_EN}</p></main></body></html>"""


def render_landing(lang: str) -> str:
    t = ("Viski lezzet profilleri veriyle okunur. 4.700+ viski, damıtım evleri ve bölgeler — kaynaklı kanıtlarla."
         if lang == "tr" else
         "Whisky flavor profiles, read from data. 4,700+ whiskies, distilleries and regions — with sourced evidence.")
    return f"""<!DOCTYPE html>
<html lang="{lang}"><head><meta charset="utf-8">
<title>Malt Radar — {t.split('.')[0]}</title>
{hreflang_tags(lang, f"{BASE}/{lang}/", f"{BASE}/{'en' if lang=='tr' else 'tr'}/")}
</head><body><main><h1>Malt Radar</h1><p>{_e(t)}</p>
<p>{_CTA_TR if lang == 'tr' else _CTA_EN}</p></main></body></html>"""


def render_sitemap(entries: list[tuple[str, str]]) -> str:
    urls = "".join(
        f"<url><loc>{_e(u)}</loc><lastmod>{_e(d)}</lastmod></url>" for u, d in entries)
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>'


def render_robots() -> str:
    return ("User-agent: *\nDisallow: /api/\n"
            "Sitemap: https://maltradar.com/sitemap.xml\n")


def render_llms() -> str:
    return ("# Malt Radar\n\n> Whisky flavor database with sourced evidence. "
            "4,700+ whiskies across Scotland, Japan, Ireland and more. "
            "Each whisky page lists flavor profile axes and region data.\n\n"
            "## Key pages\n"
            "- Whisky pages: https://maltradar.com/en/w/<whisky_id>/\n"
            "- Regions: https://maltradar.com/en/regions/\n"
            "- Landing: https://maltradar.com/en/\n")
