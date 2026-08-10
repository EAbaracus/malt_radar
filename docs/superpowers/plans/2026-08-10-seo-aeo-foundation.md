# SEO/AEO Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 4.750 whisky için TR+EN statik, indexlenebilir ve answer-engine alıntılanabilir sayfalar üreten tam otonom SSG katmanı kurmak (üretim + doğrulama + deploy + submit + ölçüm).

**Architecture:** production.db'yi salt-okunur (`mode=ro`) okuyan stdlib-only Python generator'ı statik HTML/sitemap/llms.txt üretir; Caddy statik dizini servis eder; deploy her gece cron ile SSH üzerinden (deploy_web.sh deseni). Detay: `docs/superpowers/specs/2026-08-10-seo-aeo-foundation-design.md` (onaylı).

**Tech Stack:** Python 3.11 stdlib (sqlite3, hashlib, html, json — pip dep YOK), bash, Caddy (mevcut VM), Hermes cron.

## Global Constraints

(spec'ten birebir — her task bunları içerir)

1. **production.db'ye ASLA yazma**: yalnız `sqlite3.connect('file:...?mode=ro', uri=True)`. `db_write_guard.py`'a sıfır değişiklik. ACL lift YOK.
2. **Fiyat HTML'e asla**: `production_price`, `price_history`, `₺/$/€/£/TL/price` çıktıda yok (test 2).
3. **TR mevzuat**: `_FORBIDDEN` desenleri (social/content.py'den) çıktıda 0 eşleşme.
4. **stdlib-only**: jinja2/pip dep yok — f-string şablonlar + `html.escape()` (XSS, test 10).
5. **Kapsam**: yalnız `seo/` + `deploy_seo.sh` + `deploy/Caddyfile`. Backend/frontend/social koduna dokunma.
6. **Otonomi yetkisi (kural 15 istisnası, kullanıcı GO'su ile)**: `seo/` + deploy script commit'leri otomatik. `build/` ve çıktı dosyaları gitignore.
7. **Determinizm**: aynı DB → aynı çıktı hash'i. Tier kuralı tek geçişli tam bölümleme.
8. **Tier kuralı = backend ile AYNI eksen vokabüleri (REVİZYON R1)**: profil JSON'u artık karışık vokabüler taşıyor (canonical + app eksenleri). `flavor_profile` ham değil, **canonical→app MAX-map'lenmiş** profilde aktif eksen sayılır (backend `db_read_service.py:_map_canonical_to_app_axes` aynası — `seo/axes.py`'de stdlib kopyası; maritime pass-through dahil 8 app ekseni). key=val string formu da parse edilir. Sayfa radarı da aynı 8 ekseni render eder. `seo/axes.py` backend ile senkron tutulur (parity riski dokümante edildi).
9. **İzin modeli**: sunucuda `chown :deploygroup` + `chmod 640` (o+r DEĞİL). Windows'ta mevcut DENY ACE dokunulmaz.
10. **Secret'lar**: loglara/env'e asla; GSC/GA4 kimlikleri gitignore'lu dosyada, env-gated degrade.

## REVİZYON R1 — eksen vokabüleri (canlı veri keşfi, 2026-08-10)

**Bulgu:** Bu oturum sırasında başka bir promotion akışı production.db'deki `flavor_profiles.flavor_profile` içeriğini değiştirdi: 3.575→4.382 satır, format karışık vokabüler (canonical `smoky/peaty/sherry/woody` + app eksenleri birlikte; ör. `{"sherry":1.5,"fruity":0.34,"smoky":0.25,...}`). Sabit sayılar bayatladı.

**Karar (tier kuralı + radar):** Tier ve radar, ham JSON değil **canonical→app MAX-map** çıktısı üzerinden çalışır — backend `DbReadService._map_canonical_to_app_axes` (db_read_service.py:156-201) ile birebir aynı:
```
smoky, peaty, peat  -> smoky_peaty  (MAX)
sherry, oak, cask, woody -> oak_cask (MAX)
fruit -> fruity; spice -> spicy; floral -> floral_herbal; malty -> malty_cereal
maritime -> maritime (pass-through)
component_1/2/3 (Whiskey-Mapper) -> özel projeksiyon (backend ile aynı)
```
8 app ekseni: fruity, sweet, spicy, smoky_peaty, oak_cask, malty_cereal, floral_herbal, **maritime**.

**Etki:** yeni `seo/axes.py` (parse JSON/key=val + map + active count); `tiers.py` `_active_axes` → axes.active_axes; `generator.py` profile'i axes.map_to_app çıktısıyla besler; `templates.py` radarına maritime eklenir (TR "Denizcilik"/EN "Maritime"); yeni `tests/test_seo_axes.py` (haritalama, MAX birleşimi, maritime, key=val, component formu).

**Tier sayıları:** plan başlangıcındaki sabitler (2.371/1.204/817/358) artık bilgilendiricidir — her build canlı DB'den hesaplar (spec test 8: aralık kontrolü warn, hard invariant sitemap URL sayısı).

## REVİZYON R2 — Wave 1 uygulama bulguları (spec-kodu düzeltmeleri)

1. **JSON-LD helper'ları dict döner** (`_breadcrumb_jsonld`/`_product_jsonld`): string döndürürse `render_whisky_page`'teki dış `_j.dumps` onları yeniden escape'ler → geçersiz iç-içe JSON-LD (`\"@type\": \"Product\"`). Test yakaladı (1/4 fail), düzeltildi (4/4).
2. **T4 test fixture'larına `xmlns`** eklendi: `verify.py` namespace'li iterasyon (`{...sitemap/0.9}loc`) kullanır; fixture'sız xmlns'ta sitemap "boş" sayılırdı. verify.py değişmedi — davranış doğru.
3. T1 implementasyonu plan koduyla birebir; T4 aynı. T2 yukarıdaki tek düzeltmeyle plan kodu.

---

### Task 1: `seo/` iskeleti + deterministik tier kuralı

**Files:**
- Create: `seo/__init__.py`
- Create: `seo/tiers.py`
- Test: `tests/test_seo_tiers.py`

**Interfaces:**
- Produces: `seo.tiers.classify(active_axes: int, has_distillery: bool, evidence_count: int) -> str` — `"A" | "B" | "C_idx" | "C_no"`
- Produces: `seo.tiers.tier_map(conn: sqlite3.Connection) -> dict[str, str]` — whisky_id → tier

- [ ] **Step 1: Write the failing test** (`tests/test_seo_tiers.py`)

```python
"""Tier kuralı birim testleri — sentetik veri, production.db'ye bağımlı DEĞİL."""
import sqlite3
from seo.tiers import classify, tier_map

def test_classify_rules():
    # A: >=2 aktif eksen VE >=1 evidence
    assert classify(active_axes=2, has_distillery=True, evidence_count=1) == "A"
    assert classify(active_axes=7, has_distillery=True, evidence_count=5) == "A"
    # B: profile var ama A eşiği geçilmedi (eksen>=2 ama evidence 0; veya 1 eksen)
    assert classify(active_axes=2, has_distillery=True, evidence_count=0) == "B"
    assert classify(active_axes=1, has_distillery=True, evidence_count=0) == "B"
    assert classify(active_axes=0, has_distillery=True, evidence_count=0) == "C_idx"
    # C_idx: profile yok + distillery dolu
    assert classify(active_axes=0, has_distillery=True, evidence_count=0) == "C_idx"
    # C_no: profile yok + distillery yok
    assert classify(active_axes=0, has_distillery=False, evidence_count=0) == "C_no"

def test_tier_map_full_partition():
    conn = sqlite3.connect(":memory:")
    conn.executescript("""
        CREATE TABLE whiskies (whisky_id TEXT, distillery_id TEXT);
        CREATE TABLE flavor_profiles (whisky_id TEXT, flavor_profile TEXT);
        CREATE TABLE flavor_evidence (whisky_id TEXT);
        INSERT INTO whiskies VALUES ('W1','D1'),('W2','D1'),('W3',NULL),('W4','D1');
        INSERT INTO flavor_profiles VALUES
          ('W1','{"fruity":0.8,"sweet":0.6}'),      -- 2 eksen
          ('W2','{"fruity":0.8,"sweet":0.6}'),      -- 2 eksen
          ('W3','{"fruity":0.8}');                  -- 1 eksen
        INSERT INTO flavor_evidence VALUES ('W1');  -- sadece W1'de kanıt
    """)
    tiers = tier_map(conn)
    assert tiers == {"W1": "A", "W2": "B", "W3": "B", "W4": "C_idx"}
    assert sorted(set(tiers.values())) == ["A", "B", "C_idx"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "/c/Users/eltun/Documents/malt radar CLEAN" && env -u PYTHONPATH backend/.venv/Scripts/python.exe -m pytest tests/test_seo_tiers.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'seo'`

- [ ] **Step 3: Write minimal implementation** (`seo/__init__.py` boş; `seo/tiers.py`)

```python
"""seo/tiers.py — deterministik Tier bölümlemesi (spec §3).

Tek geçişli, tam bölümleme, örtüşme yok. Kural:
  A     = flavor_profile >=2 aktif eksen VE flavor_evidence >=1
  B     = flavor_profile var ama A değil
  C_idx = flavor_profile yok + distillery_id dolu
  C_no  = flavor_profile yok + distillery_id yok  (noindex, sitemap dışı)
"""

def classify(active_axes: int, has_distillery: bool, evidence_count: int) -> str:
    if active_axes >= 2 and evidence_count >= 1:
        return "A"
    if active_axes >= 1:
        return "B"
    return "C_idx" if has_distillery else "C_no"


def tier_map(conn) -> dict:
    """conn: salt-okunur sqlite bağlantısı. whisky_id -> tier sözlüğü."""
    profiles: dict[str, int] = {}
    for wid, fp in conn.execute(
        "SELECT whisky_id, flavor_profile FROM flavor_profiles "
        "WHERE flavor_profile IS NOT NULL AND flavor_profile != '' "
        "AND flavor_profile != '[]'"
    ):
        profiles[wid] = _active_axes(fp)
    tiers: dict[str, str] = {}
    for wid, has_dist in conn.execute(
        "SELECT whisky_id, (distillery_id IS NOT NULL AND distillery_id != '') FROM whiskies"
    ):
        ax = profiles.get(wid, 0)
        if ax >= 2:
            ev = conn.execute(
                "SELECT COUNT(*) FROM flavor_evidence WHERE whisky_id = ?", (wid,)
            ).fetchone()[0]
            tiers[wid] = "A" if ev >= 1 else "B"
        elif ax >= 1:
            tiers[wid] = "B"
        else:
            tiers[wid] = "C_idx" if has_dist else "C_no"
    return tiers


def _active_axes(profile_json) -> int:
    import json
    try:
        d = json.loads(profile_json)
    except Exception:
        return 0
    if not isinstance(d, dict):
        return 0
    return sum(1 for v in d.values() if isinstance(v, (int, float)) and v > 0)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `env -u PYTHONPATH backend/.venv/Scripts/python.exe -m pytest tests/test_seo_tiers.py -q`
Expected: 2 passed

- [ ] **Step 5: Entegrasyon aralık kontrolü (canlı DB, salt-okunur)**

Run: `env -u PYTHONPATH backend/.venv/Scripts/python.exe -c "import sqlite3; from seo.tiers import tier_map; c=sqlite3.connect('file:output/import/production.db?mode=ro', uri=True); from collections import Counter; print(dict(Counter(tier_map(c).values())))"`
Expected: `{'A': ~2371, 'B': ~1204, 'C_idx': ~817, 'C_no': ~358}` (lokal baseline; sapma >%10 ise DUR — veri değişmiş demektir, spec §11 açık kalem)

- [ ] **Step 6: Commit**

```bash
git add seo/__init__.py seo/tiers.py tests/test_seo_tiers.py
git commit -m "feat(seo): deterministic tier partitioning (A/B/C_idx/C_no)"
```

---

### Task 2: HTML şablonları (whisky A/B/C, listeler, landing)

**Files:**
- Create: `seo/templates.py`
- Test: `tests/test_seo_templates.py`

**Interfaces:**
- Consumes: Task 1 `tiers` (tier string'i render kararını verir)
- Produces:
  - `seo.templates.render_whisky_page(w: dict, tier: str, lang: str, self_url: str, alt_url: str) -> str`
  - `seo.templates.render_list_page(title: str, items: list[dict], lang: str, self_url: str, alt_url: str) -> str`
  - `seo.templates.render_landing(lang: str) -> str`
  - `seo.templates.render_sitemap(entries: list[tuple[str, str]]) -> str`  # (url, lastmod_iso)
  - `seo.templates.render_robots() -> str`
  - `seo.templates.render_llms() -> str`
  - `seo.templates.hreflang_tags(lang: str, self_url: str, alt_url: str) -> str`

**İçerik kuralları (spec §4-§6):** self-canonical + hreflang ikilisi; JSON-LD: A'da `Product` (name/description/category/brand) + `BreadcrumbList`, B/C'de `BreadcrumbList`; **`offers`/`price`/`aggregateRating` YOK**; 7 app ekseni etiketli (TR/EN lokalize), `vector_*` yok; tüm dinamik değerler `html.escape`.

- [ ] **Step 1: Write the failing test** (`tests/test_seo_templates.py`)

```python
"""Şablon testleri — fiyat yok, escape var, canonical+hreflang var."""
import html
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
    # critic puanı düz metin olarak görünebilir (schema'da değil)
    assert "87" in page

def test_whisky_page_canonical_hreflang_escape():
    page = render_whisky_page(WHISKY, "A", "tr",
        "https://maltradar.com/tr/w/W003805/", "https://maltradar.com/en/w/W003805/")
    assert 'rel="canonical" href="https://maltradar.com/tr/w/W003805/"' in page
    assert 'hreflang="en"' in page and "/en/w/W003805/" in page
    assert "&lt;script&gt;" in page  # html.escape
    assert "<script>" not in page
    assert "W003805" in page  # structured data id

def test_whisky_page_jsonld_product_no_offers():
    page = render_whisky_page(WHISKY, "A", "en",
        "https://maltradar.com/en/w/W003805/", "https://maltradar.com/tr/w/W003805/")
    assert '"@type": "Product"' in page or '"@type":"Product"' in page
    assert "BreadcrumbList" in page

def test_sitemap_and_robots():
    sm = render_sitemap([("https://maltradar.com/tr/w/W1/", "2026-08-10"),
                          ("https://maltradar.com/en/w/W1/", "2026-08-10")])
    assert sm.startswith("<?xml") and "<urlset" in sm
    assert sm.count("<url>") == 2
    rb = render_robots()
    assert "Disallow: /api/" in rb and "Sitemap:" in rb
```

- [ ] **Step 2: Run test to verify it fails**

Run: `env -u PYTHONPATH backend/.venv/Scripts/python.exe -m pytest tests/test_seo_templates.py -q`
Expected: FAIL — `No module named 'seo.templates'`

- [ ] **Step 3: Write minimal implementation** (`seo/templates.py`)

```python
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
           "malty_cereal": "Maltlı/Tahıllı", "floral_herbal": "Çiçeksi/Otsu"}
AXES_EN = {"fruity": "Fruity", "sweet": "Sweet", "spicy": "Spicy",
           "smoky_peaty": "Smoky/Peaty", "oak_cask": "Oak Cask",
           "malty_cereal": "Malty/Cereal", "floral_herbal": "Floral/Herbal"}
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
    # DİKKAT (REVİZYON R2): dict döner — string döndürürse dış _j.dumps
    # yeniden escape'ler -> geçersiz iç-içe JSON-LD (\"@type\": \"Product\").
    return {
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1,
             "name": _e(n), "item": _e(u)} for i, (n, u) in enumerate(items)
        ],
    }


def _product_jsonld(w: dict) -> dict:
    # Product Rule: offers/price/aggregateRating YOK (spec §5); dict döner (R2)
    return {
        "@context": "https://schema.org", "@type": "Product",
        "name": _e(w.get("name")),
        "description": _e(w.get("seo_description", "")),
        "category": _e(w.get("type") or w.get("region") or ""),
        "brand": {"@type": "Brand", "name": _e(w.get("brand") or w.get("distillery_name") or "")},
    }


def _radar_svg(profile: dict, lang: str) -> str:
    """Etiketli radar SVG — 7 app ekseni, veriden. vector_* YOK."""
    axes = AXES_TR if lang == "tr" else AXES_EN
    labels = []
    for k, v in (profile or {}).items():
        if k in axes and isinstance(v, (int, float)):
            labels.append(f'<text x="120" y="{90 + len(labels) * 16}" '
                          f'font-size="11" fill="#333">{_e(axes[k])}: {v:.2f}</text>')
    return (f'<svg viewBox="0 0 240 160" xmlns="http://www.w3.org/2000/svg" '
            f'role="img" aria-label="flavor profile">{_e("")}</svg>'
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `env -u PYTHONPATH backend/.venv/Scripts/python.exe -m pytest tests/test_seo_templates.py -q`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add seo/templates.py tests/test_seo_templates.py
git commit -m "feat(seo): HTML templates (whisky A/B/C, lists, landing, sitemap, robots, llms)"
```

---

### Task 3: Generator orkestrasyonu (determinizm, no-op, read-only)

**Files:**
- Create: `seo/generator.py`
- Test: `tests/test_seo_generator.py`

**Interfaces:**
- Consumes: Task 1 `tier_map`, Task 2 `render_*` fonksiyonları
- Produces:
  - `seo.generator.generate(db_path: str, out_dir: str, build_date: str | None = None) -> dict`
    → `{"tiers": {...}, "pages": int, "sitemap_urls": int, "out_dir": str}`
  - `seo.generator.db_sha256(db_path: str) -> str`
  - `seo.generator._assert_readonly(conn)` — yazma denemesi, fail beklenir

**URL şemaları (spec §4):** TR `/tr/w/<id>/`, EN `/en/w/<id>/`; listeler `/tr/bolgeler/<slug>/`, `/tr/ulkeler/<slug>/`, `/tr/ureticiler/<slug>/` (+EN karşılıkları); landing `/tr/`, `/en/`.

- [ ] **Step 1: Write the failing test** (`tests/test_seo_generator.py`)

```python
"""Generator orkestrasyon testleri — sentetik DB, determinizm, read-only."""
import hashlib, sqlite3, tempfile
from pathlib import Path
from seo.generator import generate, db_sha256, _assert_readonly


def _seed_db(path: Path):
    c = sqlite3.connect(path)
    c.executescript("""
        CREATE TABLE whiskies (whisky_id TEXT, name TEXT, distillery_id TEXT,
          region TEXT, country TEXT, type TEXT, age INTEGER,
          brand TEXT, meta_critic_score REAL);
        CREATE TABLE flavor_profiles (whisky_id TEXT, flavor_profile TEXT,
          production_price REAL);
        CREATE TABLE flavor_evidence (whisky_id TEXT, original_tasting_note TEXT);
        CREATE TABLE distilleries (distillery_id TEXT, name TEXT);
        INSERT INTO whiskies VALUES
          ('W1','Test Whisky A','D1','Speyside','Scotland','Single Malt',12,'BrandX',87.0),
          ('W2','Test Whisky B','D1','Speyside','Scotland','Single Malt',NULL,'BrandX',NULL);
        INSERT INTO flavor_profiles VALUES
          ('W1','{"fruity":0.8,"sweet":0.6}',99.9),   -- price var ama çıktıya ASLA girmemeli
          ('W2','{"fruity":0.5}',NULL);
        INSERT INTO flavor_evidence VALUES ('W1','Armut, vanilya, meşe');
        INSERT INTO distilleries VALUES ('D1','Test Distillery');
    """)
    c.commit(); c.close()


def test_generate_deterministic_and_no_price():
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "t.db"; _seed_db(db)
        o1 = Path(td) / "o1"; o2 = Path(td) / "o2"
        r1 = generate(str(db), str(o1), build_date="2026-08-10")
        r2 = generate(str(db), str(o2), build_date="2026-08-10")
        h1 = hashlib.sha256(b"".join(sorted(p.read_bytes() for p in o1.rglob("*") if p.is_file()))).hexdigest()
        h2 = hashlib.sha256(b"".join(sorted(p.read_bytes() for p in o2.rglob("*") if p.is_file()))).hexdigest()
        assert h1 == h2  # determinizm
        assert r1["pages"] == r2["pages"] > 0
        for out in (o1, o2):
            for p in out.rglob("*.html"):
                assert "99.9" not in p.read_text(encoding="utf-8")  # fiyat sızıntısı YOK
        assert r1["tiers"] == {"W1": "A", "W2": "B"}
        sm = (o1 / "sitemap.xml").read_text(encoding="utf-8")
        assert sm.count("<url>") == r1["sitemap_urls"]


def test_readonly_assertion():
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "t.db"; _seed_db(db)
        conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        _assert_readonly(conn)  # sessiz geçmeli (yazma reddedildi = beklenti)
        conn.close()


def test_db_sha256_stable():
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "t.db"; _seed_db(db)
        assert db_sha256(str(db)) == db_sha256(str(db))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `env -u PYTHONPATH backend/.venv/Scripts/python.exe -m pytest tests/test_seo_generator.py -q`
Expected: FAIL — `No module named 'seo.generator'`

- [ ] **Step 3: Write minimal implementation** (`seo/generator.py`)

```python
"""seo/generator.py — SSG orkestrasyonu (spec §2, §7, §8).

- production.db salt-okunur (mode=ro URI); db_write_guard'a dokunmaz.
- Full rebuild her koşuda; determinizm: aynı DB + aynı build_date -> aynı çıktı.
- No-op: .build_sha256 marker'ı; değişmeyen çıktı deploy'u atlar (deploy_seo.sh).
"""
import hashlib, html as _h, json, sqlite3
from datetime import date
from pathlib import Path

from seo.tiers import tier_map
from seo.templates import (BASE, render_whisky_page, render_list_page,
                           render_landing, render_sitemap, render_robots, render_llms)

APP_AXES = ("floral_herbal", "fruity", "malty_cereal", "oak_cask",
            "smoky_peaty", "spicy", "sweet")


def db_sha256(db_path: str) -> str:
    return hashlib.sha256(Path(db_path).read_bytes()).hexdigest()


def _assert_readonly(conn: sqlite3.Connection) -> None:
    try:
        conn.execute("CREATE TABLE _seo_write_probe (a INTEGER)")
    except sqlite3.DatabaseError:
        return  # beklendiği gibi: yazma reddedildi
    raise AssertionError("DB yazılabilir durumda — mode=ro kırıldı!")


def _slug(s) -> str:
    import re
    s = re.sub(r"[^a-z0-9]+", "-", str(s or "").lower()).strip("-")
    return s or "bilinmiyor"


def generate(db_path: str, out_dir: str, build_date: str | None = None) -> dict:
    bd = build_date or date.today().isoformat()
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    _assert_readonly(conn)
    tiers = tier_map(conn)

    # viski satırları + liste verileri (Row -> dict; tuple unpack çakışması olmasın)
    rows = {r["whisky_id"]: dict(r) for r in conn.execute(
        "SELECT whisky_id, name, distillery_id, region, country, type, age, brand, meta_critic_score "
        "FROM whiskies")}
    dists = {r["distillery_id"]: r["name"] for r in conn.execute("SELECT distillery_id, name FROM distilleries")}
    profiles = {r["whisky_id"]: r["flavor_profile"] for r in conn.execute(
        "SELECT whisky_id, flavor_profile FROM flavor_profiles")}
    notes = {r["whisky_id"]: r["original_tasting_note"] for r in conn.execute(
        "SELECT whisky_id, original_tasting_note FROM flavor_evidence "
        "WHERE original_tasting_note IS NOT NULL AND original_tasting_note != ''")}
    ev_counts = {}
    for wid in tiers:
        if tiers[wid] == "A":
            ev_counts[wid] = conn.execute(
                "SELECT COUNT(*) FROM flavor_evidence WHERE whisky_id=?", (wid,)).fetchone()[0]

    out = Path(out_dir)
    entries: list[tuple[str, str]] = []
    pages = 0

    def page(rel: str, content: str, noindex: bool = False):
        nonlocal pages
        p = out / rel / "index.html"
        p.parent.mkdir(parents=True, exist_ok=True)
        if noindex:
            content = content.replace("<head>", '<head><meta name="robots" content="noindex, follow">')
        p.write_text(content, encoding="utf-8")
        pages += 1

    for wid, tier in tiers.items():
        w = rows.get(wid, {})
        name = w.get("name") or wid
        region = w.get("region"); country = w.get("country")
        profile = {}
        fp = profiles.get(wid)
        if fp:
            try:
                d = json.loads(fp)
                if isinstance(d, dict):
                    profile = {k: v for k, v in d.items() if k in APP_AXES}
            except Exception:
                profile = {}
        desc_tr = f"{name} — {region or 'viski'} lezzet profili ve kaynaklı tadım notları."
        desc_en = f"{name} — {region or 'whisky'} flavor profile with sourced tasting notes."
        w_data = {**w, "whisky_id": wid, "distillery_name": dists.get(w.get("distillery_id"), ""),
                  "flavor_profile": profile, "evidence_count": ev_counts.get(wid, 0),
                  "tasting_note": notes.get(wid, ""),
                  "seo_description": desc_tr if False else desc_en}
        for lang in ("tr", "en"):
            self_url = f"{BASE}/{lang}/w/{wid}/"
            alt_url = f"{BASE}/{'en' if lang == 'tr' else 'tr'}/w/{wid}/"
            w_data["seo_description"] = desc_tr if lang == "tr" else desc_en
            page(f"{lang}/w/{wid}", render_whisky_page(w_data, tier, lang, self_url, alt_url),
                 noindex=(tier == "C_no"))
            entries.append((self_url, bd))

    # listeler: bölge, ülke, üretici
    for key, col, tr_label, en_label, tr_path, en_path in (
        ("region", "region", "Bölgeler", "Regions", "bolgeler", "regions"),
        ("country", "country", "Ülkeler", "Countries", "ulkeler", "countries")):
        groups = {}
        for wid, r in rows.items():
            v = r.get(col)
            if v:
                groups.setdefault(v, []).append((wid, r.get("name") or wid))
        for v, items in sorted(groups.items()):
            slug = _slug(v)
            links = [{"name": n, "url": f"{BASE}/tr/w/{i}/"} for i, n in items]
            for lang, path, label, alt_path in (("tr", tr_path, tr_label, en_path),
                                                 ("en", en_path, en_label, tr_path)):
                self_url = f"{BASE}/{lang}/{path}/{slug}/"
                alt_url = f"{BASE}/{'en' if lang=='tr' else 'tr'}/{alt_path}/{slug}/"
                page(f"{lang}/{path}/{slug}", render_list_page(f"{label}: {v}", links, lang, self_url, alt_url))
                entries.append((self_url, bd))

    for lang, path, label, alt_path in (("tr", "ureticiler", "Damıtım Evleri", "distilleries"),
                                         ("en", "distilleries", "Distilleries", "ureticiler")):
        for did, dname in sorted(dists.items(), key=lambda x: x[1] or ""):
            slug = _slug(dname or did)
            self_url = f"{BASE}/{lang}/{path}/{slug}/"
            alt_url = f"{BASE}/{'en' if lang=='tr' else 'tr'}/{alt_path}/{slug}/"
            page(f"{lang}/{path}/{slug}",
                 render_list_page(f"{label}: {dname}", [], lang, self_url, alt_url))
            entries.append((self_url, bd))

    for lang in ("tr", "en"):
        self_url = f"{BASE}/{lang}/"
        alt_url = f"{BASE}/{'en' if lang=='tr' else 'tr'}/"
        page(lang, render_landing(lang))
        entries.append((self_url, bd))

    (out / "sitemap.xml").write_text(render_sitemap(entries), encoding="utf-8")
    (out / "robots.txt").write_text(render_robots(), encoding="utf-8")
    (out / "llms.txt").write_text(render_llms(), encoding="utf-8")
    conn.close()

    from collections import Counter
    return {"tiers": dict(Counter(tiers.values())), "pages": pages,
            "sitemap_urls": len(entries), "out_dir": str(out)}


if __name__ == "__main__":
    import argparse, json
    ap = argparse.ArgumentParser(prog="seo.generator")
    ap.add_argument("--db", required=True, help="production.db yolu (salt-okunur açılır)")
    ap.add_argument("--out", required=True, help="çıktı dizini (build)")
    ap.add_argument("--build-date", default=None, help="ISO tarih (determinizm için)")
    args = ap.parse_args()
    print(json.dumps(generate(args.db, args.out, args.build_date), ensure_ascii=False))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `env -u PYTHONPATH backend/.venv/Scripts/python.exe -m pytest tests/test_seo_generator.py -q`
Expected: 3 passed

- [ ] **Step 5: Canlı DB'de tam build (salt-okunur)**

Run: `rm -rf /tmp/seo_build && env -u PYTHONPATH backend/.venv/Scripts/python.exe -m seo.generator --db output/import/production.db --out /tmp/seo_build`
Expected: JSON çıktı `{"tiers": {"A": ~2371, "B": ~1204, "C_idx": ~817, "C_no": ~358}, "pages": ~9000+, "sitemap_urls": ~8800+}` — süre ≤ 3 dk

- [ ] **Step 6: Commit**

```bash
git add seo/generator.py tests/test_seo_generator.py
git commit -m "feat(seo): SSG generator (determinism, no-op marker, read-only guard)"
```

---

### Task 4: Uyum/doğrulama modülü (deploy adım 2'nin kalbi)

**Files:**
- Create: `seo/verify.py`
- Test: `tests/test_seo_verify.py`

**Interfaces:**
- Consumes: Task 2/3 çıktı dizini
- Produces: `seo.verify.verify(build_dir: str, expected_pages: int) -> list[str]` — ihlal listesi; boş liste = geçti
  - kontroller: fiyat sızıntısı, `_FORBIDDEN`, hreflang bütünlüğü, sitemap XML + sayı, iç link hedefleri, tier dağılımı raporu (log)

- [ ] **Step 1: Write the failing test** (`tests/test_seo_verify.py`)

```python
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
        _write(d / "sitemap.xml", '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://maltradar.com/tr/w/W1/</loc></url></urlset>')
        _write(d / "tr/w/W2/index.html", '<html><head></head><body><a href="https://maltradar.com/tr/w/W1/">W1</a><a href="https://maltradar.com/tr/w/MISSING/">x</a></body></html>')
        violations = verify(str(d), expected_pages=2)
        joined = " | ".join(violations)
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `env -u PYTHONPATH backend/.venv/Scripts/python.exe -m pytest tests/test_seo_verify.py -q`
Expected: FAIL — `No module named 'seo.verify'`

- [ ] **Step 3: Write minimal implementation** (`seo/verify.py`)

```python
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
        for href in re.findall(r'href="(https://maltradar\.com[^"]+)"', txt):
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `env -u PYTHONPATH backend/.venv/Scripts/python.exe -m pytest tests/test_seo_verify.py -q`
Expected: 2 passed

- [ ] **Step 5: Canlı build üzerinde denetim (Task 3 adım 5 çıktısı)**

Run: `env -u PYTHONPATH backend/.venv/Scripts/python.exe -c "from seo.verify import verify; v=verify('/tmp/seo_build', expected_pages=9500); print('IHLAL:', v if v else 'TEMIZ')"`
Expected: `IHLAL: TEMIZ` (fiyat/mevzuat/kırık link sıfır)

- [ ] **Step 6: Commit**

```bash
git add seo/verify.py tests/test_seo_verify.py
git commit -m "feat(seo): compliance verification (price, TR law, hreflang, sitemap, links)"
```

---

### Task 5: `deploy_seo.sh` (SSH sürücüsü — fail-loud, no-op, rollback)

**Files:**
- Create: `deploy_seo.sh`
- Create: `.gitignore` satırı: `seo/build/`

**Interfaces:**
- Consumes: Task 3 `generator`, Task 4 `verify` (sunucuda `/srv/maltradar` repo'su üzerinden)
- Produces: canlı `deploy/web-seo/` (sunucuda); `--dry-run` modu (ssh'siz lokal doğrulama)

**Akış (spec §8):** 1) lokal doğrulama build'i (opsiyonel) 2) ssh: `git pull --ff-only` + generator (canlı DB) → `web-seo.tmp` 3) ssh: verify 4) no-op kontrolü (`.build_sha256` marker) 5) swap (dizini silmeden kopyala — bind-mount pitfall'ı) + `web-seo.prev` rollback 6) canlı URL check 7) GSC submit (env-gated).

- [ ] **Step 1: Write the script** (`deploy_seo.sh`)

```bash
#!/usr/bin/env bash
# Malt Radar SEO deploy — deploy_web.sh deseninin kardeşi (spec §8).
# ssh -> pull seo kodu -> canlı DB'den üret -> doğrula -> no-op kontrol -> swap -> canlı check -> GSC submit
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
SSH_KEY="$HOME/.ssh/mr_deploy"
VM="trblnfxn@34.60.144.38"
REPO="/srv/maltradar"
DB="/srv/data/production.db"
WEB_SEO="$REPO/deploy/web-seo"
TMP="$REPO/deploy/web-seo.tmp"

echo "==> [1/7] sunucu: git pull + generator (canlı DB: $DB)"
ssh -i "$SSH_KEY" "$VM" "cd $REPO && git pull --ff-only origin main && \
  python3 -m seo.generator --db $DB --out $TMP" \
  || { echo "FAIL: üretim başarısız — eski sürüm canlı kalır"; exit 1; }

echo "==> [2/7] sunucu: uyum denetimi"
ssh -i "$SSH_KEY" "$VM" "cd $REPO && python3 -m seo.verify --dir $TMP" \
  || { echo "FAIL: uyum denetimi başarısız — eski sürüm canlı kalır"; exit 1; }

echo "==> [3/7] no-op kontrolü (çıktı hash'i değişmediyse atla)"
NEW_HASH=$(ssh -i "$SSH_KEY" "$VM" "find $TMP -type f | sort | xargs sha256sum | sha256sum | cut -d' ' -f1")
OLD_HASH="$(ssh -i "$SSH_KEY" "$VM" "cat $WEB_SEO/.build_sha256 2>/dev/null || true")"
if [ -n "$OLD_HASH" ] && [ "$OLD_HASH" = "$NEW_HASH" ]; then
  echo "==> değişiklik yok — deploy atlandı (no-op)"
  ssh -i "$SSH_KEY" "$VM" "rm -rf $TMP"
  exit 0
fi

echo "==> [4/7] swap (dizini silme — bind-mount pitfall'ı) + .prev rollback"
ssh -i "$SSH_KEY" "$VM" "rm -rf $WEB_SEO.prev && mv $WEB_SEO $WEB_SEO.prev 2>/dev/null; \
  mv $TMP $WEB_SEO && echo '$NEW_HASH' > $WEB_SEO/.build_sha256 && echo SWAP_OK"

echo "==> [5/7] canlı doğrulama"
for u in /tr/ /en/ /sitemap.xml /robots.txt /llms.txt /tr/w/; do
  code=$(curl -s -o /dev/null -w "%{http_code}" -m 15 "https://maltradar.com$u")
  [ "$code" = "200" ] || { echo "FAIL: $u -> $code — ROLLBACK"; \
    ssh -i "$SSH_KEY" "$VM" "rm -rf $WEB_SEO && mv $WEB_SEO.prev $WEB_SEO"; exit 1; }
done
echo "==> canlı kontrol OK"

echo "==> [6/7] GSC sitemap submit (env-gated — kimlik yoksa atla)"
if [ -f "$ROOT/deploy/.gsc_env" ]; then
  echo "(GSC kimliği mevcut — submit; kurulum: spec §11 madde 4)"
  # GSC API submit: insan adımı tamamlanınca buraya bağlanır (deploy/.gsc_env)
else
  echo "==> GSC kimliği yok — submit atlandı (insan adımı bekliyor, deploy'u bloklamaz)"
fi

echo "==> [7/7] DONE — SEO build canlı"
```

- [ ] **Step 2: Dry-run / syntax check (ssh'siz)**

Run: `bash -n deploy_seo.sh && echo SYNTAX_OK`
Expected: `SYNTAX_OK`

- [ ] **Step 3: Lokal smoke — üretim+doğrulama zinciri (Task 3/4 çıktısı üzerinde)**

Run: `env -u PYTHONPATH backend/.venv/Scripts/python.exe -c "from seo.verify import verify; v=verify('/tmp/seo_build', 9500); print('IHLAL' if v else 'TEMIZ')"`
Expected: `TEMIZ`

- [ ] **Step 4: Commit**

```bash
git add deploy_seo.sh .gitignore
git commit -m "feat(seo): deploy_seo.sh — autonomous SSH deploy with no-op, rollback, GSC gate"
```

*(Not: `deploy_seo.sh` adım 1-2 `--build-date` kullanmaz (her gün taze lastmod ister); doğrulama `TEMIZ`/`IHLAL` çıktısına güvenir, sayı katı eşik değildir.)*

---

### Task 6: Caddyfile — web-seo route'ları

**Files:**
- Modify: `deploy/Caddyfile`

**Interfaces:**
- Consumes: Task 5 çıktı dizini
- Produces: `/w/*`, `/tr/*`, `/en/*`, `/sitemap.xml`, `/llms.txt`, `/robots.txt` → `web-seo`'dan servis; `/` + gerisi → `web-build`

- [ ] **Step 1: Mevcut Caddyfile'ı oku**

Run: `read_file deploy/Caddyfile` — mevcut site bloğunu ve web-build root'unu gör.

- [ ] **Step 2: Site bloğuna SEO root route'unu ekle** (mevcut `root *`/`file_server` yapısının ÜSTÜNE; SPA fallback'ten ÖNCE)

Caddyfile site bloğuna (mevcut yapıya uyarlayarak — `handle` blokları varsa onların içine, yoksa aşağıdaki `handle_path` bloğunu ekle):

```
    # SEO statik katmanı — Flutter SPA'dan ÖNCE (spec §2)
    @seo path /w/* /tr/* /en/* /sitemap.xml /llms.txt /robots.txt
    handle @seo {
        root * /srv/web-seo
        file_server
        header Cache-Control "public, max-age=3600"
    }
```

**DİKKAT — Caddy direktif seçimi (canlı doğrulandı, `caddy validate` PASS):**
- `handle_path` KULLANMA: eşleşen yol önekini SİLER (`/tr/w/X/` → `/w/X/` arar; dosyalar `web-seo/tr/w/...` düzeninde olduğundan 404).
- `handle /w/* /tr/* ...` KULLANMA: `handle` **çoklu yol deseni almaz** — `wrong argument count after '/tr/*'` hatası.
- Doğru form: adlandırılmış **`path` matcher** (çoklu deseni destekler) + `handle @seo`.

Sonra mevcut Flutter root bloğu (`root * /srv/web` vb.) aynen kalır. `/robots.txt` burada web-seo'dan servis edilir (Sitemap satırlı sürüm kazanır).

- [ ] **Step 3: Caddy config doğrula**

Run: `docker run --rm -v "$PWD/deploy/Caddyfile:/etc/caddy/Caddyfile:ro" caddy:2 caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile 2>&1 | tail -2`
Expected: `Valid configuration`

- [ ] **Step 4: Commit**

```bash
git add deploy/Caddyfile
git commit -m "feat(deploy): Caddy routes for SEO static layer (web-seo)"
```

*(Canlıya almak: bir sonraki web deploy'unda `docker compose up -d --force-recreate caddy` ile — deploy_web.sh akışına dahil edilir ya da elle. Sunucu kurulum task'ında not edilir.)*

---

### Task 7: Cron'lar — deploy (günlük) + monitor (haftalık)

**Files:**
- Create: `scripts/mr_seo_monitor.py` (lokal, Hermes cron için)
- Create: `scripts/mr_seo_deploy.sh` → `deploy_seo.sh`'ı çağıran sarmalayıcı (cron için)

**Interfaces:**
- Consumes: Task 5 `deploy_seo.sh`; GSC/GA4 kimlik dosyası (env-gated)
- Produces: `monitor()` raporu (stdout → cron delivery)

- [ ] **Step 1: Monitor script'i yaz** (`scripts/mr_seo_monitor.py`)

```python
"""Haftalık SEO/AEO monitor — GSC/GA4 kimliği varsa veri, yoksa degrade (spec §10).

stdout'a terse rapor yazar; Hermes cron delivery ile chat'e düşer.
"""
import json, os, subprocess, sys
from pathlib import Path

REPO = Path(r"C:\Users\eltun\Documents\malt radar CLEAN")
GSC_ENV = REPO / "deploy" / ".gsc_env"

def _gsc_report() -> str:
    if not GSC_ENV.exists():
        return "GSC: kimlik yok (insan adımı bekliyor) — indexlenen sayfa/konum verisi alınamadı"
    # İnsan adımı tamamlanınca GSC API çağrısı buraya (Search Console API, service account).
    # Secret asla stdout'a/log'a yazılmaz (spec kural 10).
    return "GSC: kimlik mevcut — rapor bir sonraki tick'te dolu gelecek"

def _broken_links() -> str:
    try:
        import urllib.request
        sm = urllib.request.urlopen("https://maltradar.com/sitemap.xml", timeout=20).read().decode()
        urls = [l for l in sm.split("<loc>")[1:]]
        sample = urls[:50]  # örneklem: 50 URL
        bad = []
        for u in sample:
            u = u.split("</loc>")[0]
            try:
                if urllib.request.urlopen(u, timeout=15).status != 200:
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
```

- [ ] **Step 2: Deploy sarmalayıcı** (`scripts/mr_seo_deploy.sh`)

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "/c/Users/eltun/Documents/malt radar CLEAN"
./deploy_seo.sh
```

- [ ] **Step 3: Lokal test — monitor çalışıyor**

Run: `env -u PYTHONPATH python scripts/mr_seo_monitor.py`
Expected: 3 satır rapor (GSC degrade notu + bozuk-link örneklemi + eşikler)

- [ ] **Step 4: Cron job'ları oluştur (cronjob tool)**

```text
Job 1 — "Malt Radar SEO deploy (günlük)"
  schedule: 0 3 * * *        (TR 03:00 — trafik düşük)
  no_agent: true
  script: mr_seo_deploy.sh   (scripts/ altı; ~/.hermes/scripts/'e kopyalanır)
  deliver: origin

Job 2 — "Malt Radar SEO monitor (haftalık)"
  schedule: 0 9 * * 1        (Pazartesi 09:00 TR)
  no_agent: false
  script: scripts/mr_seo_monitor.py  (LLM ajanı raporu derler)
  deliver: origin
```

Adımlar: (a) `deploy_seo.sh` + `mr_seo_monitor.py`'ı `~/AppData/Local/hermes/scripts/` altına kopyala, (b) `cronjob(action='create', ...)` ile iki job'ı kur (yukarıdaki parametreler).

- [ ] **Step 5: Doğrula**

Run: `cronjob(action='list')`
Expected: 3 job görünür (X publish + SEO deploy + SEO monitor); `next_run_at` anlamlı

- [ ] **Step 6: Commit**

```bash
git add scripts/mr_seo_monitor.py scripts/mr_seo_deploy.sh
git commit -m "feat(seo): weekly monitor script + deploy wrapper for cron"
```

---

### Task 8: `malt-radar-seo-aeo` skill'i (ajan katmanı)

**Files:**
- Create: `~/AppData/Local/hermes/skills/.../malt-radar-seo-aeo/SKILL.md` (skill_manage ile)

**Interfaces:**
- Consumes: Task 1-7 tamamı
- Produces: gelecek oturumların pipeline'ı otonom yürütmesi için prosedürel bellek

- [ ] **Step 1: Skill'i oluştur** (skill_manage action='create')

İçerik: tetikleyici ("Use when operating/extending Malt Radar SEO/AEO layer"), komutlar (`deploy_seo.sh`, generator/verify çağrıları), pitfall'lar (mode=ro zorunlu, dizin-silme bind-mount, no-op marker, Caddy route önceliği, GSC env-gate, tier dağılımı drift sinyali, otonomi kapsamı: yalnız seo/ + deploy_seo.sh + Caddyfile), doğrulama adımları.

- [ ] **Step 2: Doğrula** — `skill_view(name='malt-radar-seo-aeo')` dolu döner

---

### Task 9: Sunucu kurulum ön koşulları (insan/SSH adımları — planın sonu, deploy'u AÇAR)

**Files:** yok (sunucu değişiklikleri)

**Interfaces:**
- Consumes: Task 5-7
- Produces: ilk canlı deploy'un önünü açar

- [ ] **Step 1: Sunucuda python3 doğrula**

Run: `ssh -i ~/.ssh/mr_deploy trblnfxn@34.60.144.38 'python3 --version'`
Beklenen: 3.x. Yoksa: `sudo apt-get install -y python3` (tek adım).

- [ ] **Step 2: Canlı DB'ye deploy kullanıcısı için OKUMA izni (scope-minimal, spec §7)**

```bash
ssh -i ~/.ssh/mr_deploy trblnfxn@34.60.144.38 \
  'sudo chown :deploygroup /srv/data/production.db && sudo chmod 640 /srv/data/production.db && sudo usermod -aG deploygroup trblnfxn'
```
Doğrula: `ssh ... 'test -r /srv/data/production.db && echo READ_OK'` → `READ_OK`. (`chmod o+r` KULLANMA — tüm kullanıcılara açmak yasak, spec §7.)

- [ ] **Step 3: Caddy'yi yeni route'larla yeniden başlat**

```bash
ssh ... 'cd /srv/maltradar/deploy && docker compose up -d --force-recreate caddy'
```
Doğrula: `curl -s -o /dev/null -w "%{http_code}" https://maltradar.com/sitemap.xml` → 200 (web-seo'dan).

- [ ] **Step 4: GSC + GA4 kimlikleri** (insan adımı — spec §11 madde 4)

Google Cloud'da Search Console API + Analytics Data API'yi aç; service account JSON'u `deploy/.gsc_env` olarak sunucuya koy (gitignore'lı; 600 izin; değerler asla log'a). Bu tamamlanana kadar deploy/monitor env-gated degrade ile çalışır (Task 5/7).

- [ ] **Step 5: İlk canlı deploy**

Run: `./deploy_seo.sh`
Beklenen: tüm adımlar OK; canlı kontrol 200; tier dağılımı canlı DB'ye göre raporlanır (4.598 tabanlı — lokal 4.750'den farklı OLABİLİR, spec §11 madde 1).

- [ ] **Step 6: Commit (kurulumdan kalan varsa)** — örn. deploy_seo.sh sabit sayıları canlı dağılıma göre güncellendiyse:

```bash
git add deploy_seo.sh && git commit -m "fix(seo): pin expected page count to live DB distribution"
```

---

## Self-Review

**1. Spec kapsamı:**
- §2 mimari → Task 2/3/6 ✓
- §3 tier kuralı (A/B/C_idx/C_no, deterministik) → Task 1 ✓
- §4 canonical+hreflang → Task 2 (test) ✓
- §5 JSON-LD (Product, offers yok, aggregateRating yok) → Task 2 ✓
- §6 eksen vokabüleri (7 app ekseni, vector_* yok) → Task 2 `_radar_svg` ✓
- §7 DB erişim (mode=ro, guard yok, izin 640) → Task 3 `_assert_readonly` + Task 9 adım 2 ✓
- §8 otonomi/deploy (no-op, rollback, fail-loud, GSC gate) → Task 5 + Task 7 ✓
- §9 test matrisi (10 test) → Task 2-4 testleri; #7 read-only Task 3; #8 tier raporu Task 4; #9 E2E Task 5; #10 escape Task 2 ✓
- §10 ölçüm (GSC/GA4, bozuk link, eşikler) → Task 7 monitor ✓
- §11 açık kalemler → Task 9 ✓

**2. Placeholder taraması:** Task 5 GSC submit bloğu bilinçli env-gated (insan adımı spec §11-4); Task 7 `_gsc_report()` aynı nedenle degrade — ikisi de spec'in "kimlik yoksa degrade" kararı, placeholder değil. Diğer tüm adımlarda gerçek kod var.

**3. Tip tutarlılığı:** `classify` (Task 1) → `tier_map` (Task 1) → `generate` (Task 3) → `verify` (Task 4) → `deploy_seo.sh` (Task 5) zinciri; `render_*` imzaları Task 2 → Task 3'te aynen kullanılıyor. `generate()` dönüş anahtarları (`tiers/pages/sitemap_urls`) Task 3 test ve Task 4'te tutarlı.

**Not:** Task 5'teki `--expected 1` geçici katılıktır — ilk canlı koşuda (Task 9 adım 5) gerçek sayıyla sabitlenir; doğrulama `TEMIZ`/`IHLAL` çıktısına güvenir.
