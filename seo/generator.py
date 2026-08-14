"""seo/generator.py — SSG orkestrasyonu (spec §2, §7, §8).

- production.db salt-okunur (mode=ro URI); db_write_guard'a dokunmaz.
- Full rebuild her koşuda; determinizm: aynı DB + aynı build_date -> aynı çıktı.
- No-op: .build_sha256 marker'ı (deploy_seo.sh).
- R1: flavor_profile ham değil, seo.axes.map_to_app(parse_profile(...)) çıktısı kullanılır.
"""
import hashlib, json, sqlite3
from datetime import date
from pathlib import Path

from seo import axes as _axes
from seo.tiers import tier_map
from seo.templates import (BASE, render_whisky_page, render_list_page,
                           render_landing, render_sitemap, render_robots, render_llms)


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
    seen_entries: set = set()  # R4: sitemap çift URL koruması (slug çakışmalarına karşı)

    def add_entry(url: str, d: str) -> None:
        if url not in seen_entries:
            seen_entries.add(url)
            entries.append((url, d))

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
        region = w.get("region")
        fp = profiles.get(wid)
        profile = _axes.map_to_app(_axes.parse_profile(fp)) if fp else {}
        desc_tr = f"{name} — {region or 'viski'} lezzet profili ve kaynaklı tadım notları."
        desc_en = f"{name} — {region or 'whisky'} flavor profile with sourced tasting notes."
        for lang in ("tr", "en"):
            self_url = f"{BASE}/{lang}/w/{wid}/"
            alt_url = f"{BASE}/{'en' if lang == 'tr' else 'tr'}/w/{wid}/"
            w_data = {**w, "whisky_id": wid,
                      "distillery_name": dists.get(w.get("distillery_id"), ""),
                      "flavor_profile": profile, "evidence_count": ev_counts.get(wid, 0),
                      "tasting_note": notes.get(wid, ""),
                      "seo_description": desc_tr if lang == "tr" else desc_en}
            page(f"{lang}/w/{wid}", render_whisky_page(w_data, tier, lang, self_url, alt_url),
                 noindex=(tier == "C_no"))
            # R3: C_no (noindex) sayfaları sitemap'e GİRMEZ (spec §3)
            if tier != "C_no":
                add_entry(self_url, bd)

    for key, col, tr_label, en_label, tr_path, en_path in (
        ("region", "region", "Bölgeler", "Regions", "bolgeler", "regions"),
        ("country", "country", "Ülkeler", "Countries", "ulkeler", "countries")):
        groups = {}
        for wid, r in rows.items():
            v = r.get(col)
            if v:
                # R4: slug'a göre grupla — "Highlands" ve "Highlands District" aynı
                # sayfaya birleşir (aksi halde sitemap çift URL + sayfa üzerine yazma)
                slug = _slug(v)
                g = groups.setdefault(slug, {"label": v, "items": []})
                g["items"].append((wid, r.get("name") or wid))
        for slug, g in sorted(groups.items()):
            v = g["label"]
            links = [{"name": n, "url": f"{BASE}/tr/w/{i}/"} for i, n in g["items"]]
            for lang, path, label, alt_path in (("tr", tr_path, tr_label, en_path),
                                                 ("en", en_path, en_label, tr_path)):
                self_url = f"{BASE}/{lang}/{path}/{slug}/"
                alt_url = f"{BASE}/{'en' if lang=='tr' else 'tr'}/{alt_path}/{slug}/"
                page(f"{lang}/{path}/{slug}", render_list_page(f"{label}: {v}", links, lang, self_url, alt_url))
                add_entry(self_url, bd)

    for lang, path, label, alt_path in (("tr", "ureticiler", "Damıtım Evleri", "distilleries"),
                                         ("en", "distilleries", "Distilleries", "ureticiler")):
        seen_dists: set = set()  # R4: per-lang slug dedupe (diller arası paylaşma!)
        for did, dname in sorted(dists.items(), key=lambda x: x[1] or ""):
            slug = _slug(dname or did)
            if slug in seen_dists:
                continue
            seen_dists.add(slug)
            self_url = f"{BASE}/{lang}/{path}/{slug}/"
            alt_url = f"{BASE}/{'en' if lang=='tr' else 'tr'}/{alt_path}/{slug}/"
            page(f"{lang}/{path}/{slug}",
                 render_list_page(f"{label}: {dname}", [], lang, self_url, alt_url))
            add_entry(self_url, bd)

    for lang in ("tr", "en"):
        self_url = f"{BASE}/{lang}/"
        alt_url = f"{BASE}/{'en' if lang=='tr' else 'tr'}/"
        page(lang, render_landing(lang))
        add_entry(self_url, bd)

    (out / "sitemap.xml").write_text(render_sitemap(entries), encoding="utf-8")
    (out / "robots.txt").write_text(render_robots(), encoding="utf-8")
    (out / "llms.txt").write_text(render_llms(), encoding="utf-8")
    conn.close()

    return {"tiers": tiers, "pages": pages,
            "sitemap_urls": len(entries), "out_dir": str(out)}


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(prog="seo.generator")
    ap.add_argument("--db", required=True, help="production.db yolu (salt-okunur açılır)")
    ap.add_argument("--out", required=True, help="çıktı dizini (build)")
    ap.add_argument("--build-date", default=None, help="ISO tarih (determinizm için)")
    args = ap.parse_args()
    print(json.dumps(generate(args.db, args.out, args.build_date), ensure_ascii=False))