"""social/content.py — Malt Radar resmi tek hesap için yasal-clean post üretici.

İçerik politiği (4250 s.K m.20-21 + AGENTS product rule):
  - Uygulamanın BİLGİ/VERİ aracı olduğunu tanıtır; İÇKİYİ değil uygulamayı anlatır.
  - Fiyat, skor, "denemelisin", "al", "dene" gibi teşvik kelimeleri HİÇ yok.
  - Marka adları sadece terminolojik/katalog referansı; tanıtıcı vurgu yok.
  - "sorumlu tüketim" gibi nötral-editoryal dil. Teşvik yok.
Bu modül hiçbir platforma yayın yapmaz; sadece taslak üretir -> queue'ya yazar.

KAYNAK GİZLİLİĞİ: Veri üretim zincirini (OCR, WhiskyMag, SMWS, kitap vb. menşei)
içeren ham kaynak ADLARI asla post metnine girmez. Yalnız jenerik sayılar
("N kamuya açık kaynak") paylaşılır; belirli tedarikçi/dergi/araç adları açık
edilmez.

Çok günlük takvim (günde 3 X post) için DEĞİŞKENLİK katmanı:
  - Aynı veri anlık görüntüsünden `day` indeksine göre FARKLI dilim üretir
    (rotasyonlu bölge / ülke window'ları).
  - post id'si `day` içerir -> her gün YENİ id -> queue'ya yeni taslak düşer,
    tekrar eden metin -> SPAM/X ban riski olmaz.
  - Her varyant _FORBIDDEN yasal griden geçirilir; geçmezse üretilmez.
"""

from __future__ import annotations

import json as _json
import re as _re
import hashlib as _hl
from dataclasses import dataclass

# Teşvik / reklam işareti sözcükler — kelime sınırlı (word-boundary) eşleşir,
# böylece "Malt" içindeki "al", "için" içindeki "iç" gibi yanlış pozitifler çıkmaz.
# TEK liste: TR + EN reklam kalıpları + kaynak-adı sızıntıları. Her dildeki
# her post bu listenin TAMAMINA karşı gate'lenir (TR postta EN kelime geçmez,
# EN postta TR kelime geçmez -> tek liste basit ve güvenli).
_FORBIDDEN = [
    # --- TR reklam/teşvik ---
    r"\btavsiye",
    r"\bkaçırma",
    r"\bdeneyin\b",
    r"\bdenemeli",
    r"\bmutlaka\b",
    r"\bsatın al",
    r"\bsipariş",
    r"\bindirim",
    r"\bkampanya",
    r"\bpromosyon",
    r"\bsepete",
    r"\breferans kodu",
    r"\btavsiye ederiz",
    r"\ben iyisi\b",
    r"\bkeyfini\b",
    # --- EN reklam/teşvik ---
    r"\bprice\b",
    r"\bbuy\b",
    r"\border\b",
    r"\bdiscount",
    r"\bcampaign",
    r"\bpromotion",
    r"\bsale\b",
    r"\bdeal\b",
    r"\boffer\b",
    r"\bbest\b",
    r"\bmust have\b",
    r"\bnumber one\b",
    r"\benjoy\b",
    r"\btry\b",
    r"\brecommend",
    r"\bdon't miss",
    r"\bfree\b",
    r"\bwin\b",
    r"\bgift\b",
    # --- evrensel para/bayi işaretleri ---
    r"\bsponsor",
    r"\baffiliate",
    r"\breferral",
    r"\bfiyat",
    r"\b₺\b",
    r"\busd\b",
    r"\beuro\b",
    r"\$",
    r"€",
    r"£",
    # --- KAYNAK ADI SIZINTILARI (skill pitfall #4): tedarikçi/araç/tür adı
    #     asla post metnine girmez; yalnız jenerik "N kamuya açık kaynak".
    r"\bwhisky magazine\b",
    r"\bwhiskymag\b",
    r"\bannuals?\b",
    r"\bsmws\b",
    r"\btesseract\b",
    r"\bocr\b",
    r"\beditorial\b",
    r"\bbook\b",
    r"\bscrape",
    r"\bcrawl",
]
# Marka adları: sadece terminolojik referansta geçebilir; tanıtıcı bağlam yok.
_BRAND_ONLY = ["lagavulin", "macallan", "bruichladdich", "highland park",
               "bowmore", "caol ila", "laphroaig"]  # örnek; tam bloklist eklenebilir


@dataclass
class Post:
    id: str
    handle: str        # tek resmi hesap
    platform: str
    template: str
    body: str          # yayınlanacak metin (yasal-clean)
    created_utc: str
    source_sha256: str
    day: int = 0
    lang: str = "tr"   # "tr" | "en" — id seed'ine girer, TR/EN ayrı post
    status: str = "draft"


def _post_id(seed: str) -> str:
    return _hl.sha256(seed.encode()).hexdigest()[:12]


def _clean_forbidden(text: str) -> tuple[bool, list[str]]:
    """Metinde yasaklı teşvik/reklam deseni var mı? (product+4250 koruması)"""
    hits = [p for p in _FORBIDDEN if _re.search(p, text, _re.IGNORECASE)]
    return (len(hits) == 0, hits)


def _gate(body: str) -> tuple[bool, str]:
    ok, hits = _clean_forbidden(body)
    if not ok:
        return False, f"YASAKLI ifade: {hits}"
    return True, "OK"


def _tags(row) -> str:
    return f"{row['name']} ({row['count']})"


def _rot(rows: list[dict], day: int, k: int | None = None) -> list[dict]:
    """day indeksine gore doner: day adim kayarak ilk k öğeyi seç.
    Boş liste -> bos. k None -> hepsi (adim yine kayar)."""
    if not rows:
        return []
    k = k if k is not None else len(rows)
    n = len(rows)
    return [rows[(day + i) % n] for i in range(k)]


# --- Template'ler: hepsi editoryal / app-bilgi odaklı, içki teşviki yok ---
# {var} dilimleri varyant başına doldurulur; day'e göre farklı metin çıkar.
# Her template TR + EN çifti taşır; lang seçimi DraftBuilder'da yapılır.
TEMPLATE_FNS = {
    "coverage": lambda m, day, lang: (_coverage_tr if lang == "tr" else _coverage_en)(m, day),
    "flavor_evidence": lambda m, day, lang: (_flavor_tr if lang == "tr" else _flavor_en)(m, day),
    "origins_story": lambda m, day, lang: (_origins_tr if lang == "tr" else _origins_en)(m, day),
}


def _fmt_total(m):
    s = m["totals"]
    return f"{s['whiskies']} viski, {s['distilleries']} damıtım evi, {s['brands']} marka"


def _fmt_total_en(m):
    s = m["totals"]
    return f"{s['whiskies']} whiskies, {s['distilleries']} distilleries, {s['brands']} brands"


def _coverage_tr(m, day):
    s = m["totals"]
    regions = _rot(m["regions"], day, 3)
    if regions:
        body = (
            "Malt Radar'ın veri seti: {totals} indexlendi.\n"
            "Her girdi kaynaklı tadım notu/kanıtla doğrulanıyor.\n"
            "Bölge öne çıkanlar: {regions}."
        ).format(totals=_fmt_total(m), regions=", ".join(_tags(r) for r in regions))
    else:
        body = (
            "Malt Radar'ın veri seti: {totals} indexlendi.\n"
            "Her girdi kaynaklı tadım notu/kanıtla doğrulanıyor."
        ).format(totals=_fmt_total(m))
    return body


def _coverage_en(m, day):
    regions = _rot(m["regions"], day, 3)
    if regions:
        body = (
            "Malt Radar's dataset: {totals} indexed.\n"
            "Every entry is verified against sourced tasting notes.\n"
            "Regional highlights: {regions}."
        ).format(totals=_fmt_total_en(m), regions=", ".join(_tags(r) for r in regions))
    else:
        body = (
            "Malt Radar's dataset: {totals} indexed.\n"
            "Every entry is verified against sourced tasting notes."
        ).format(totals=_fmt_total_en(m))
    return body


def _flavor_tr(m, day):
    s = m["totals"]
    src_count = len(m["evidence_sources"])
    # KAYNAK ADLARI gizli: sadece jenerik sayı. Tedarikçi/dergi/OCR adı paylaşılmaz.
    return (
        "Malt Radar, {evidence} flavor kanıtını {src_count} farklı kamuya açık "
        "kaynaktan derleyip\n{profiles} viski için flavor profili oluşturuyor.\n"
        "Her kanıt kaynak menşeiyle birlikte izlenebilir.\n"
        "Bir viskinin karakterini veriyle okumak üzerine bir proje."
    ).format(evidence=s["flavor_evidence"], src_count=src_count, profiles=s["flavor_profiles"])


def _flavor_en(m, day):
    s = m["totals"]
    src_count = len(m["evidence_sources"])
    # KAYNAK ADLARI gizli: sadece jenerik sayı. Tedarikçi/dergi/OCR adı paylaşılmaz.
    return (
        "Malt Radar compiles {evidence} flavor evidence entries from {src_count} "
        "public sources to build\nflavor profiles for {profiles} whiskies.\n"
        "Every piece of evidence is traceable to its source.\n"
        "A project about reading a whisky's character through data."
    ).format(evidence=s["flavor_evidence"], src_count=src_count, profiles=s["flavor_profiles"])


def _origins_tr(m, day):
    countries = _rot(m["countries"], day, 3)
    if not countries:
        return "Malt Radar veri setinde çok ülkeli bir katalog kapsamı üzerine çalışıyor."
    total = len(m["countries"])
    return (
        "Malt Radar veri setinde {cc} ülke/bölge:\n"
        "{cs}.\n"
        "Coğrafyayı hammaddeden damıtıma kadar kataloglamak."
    ).format(cc=total, cs=", ".join(_tags(r) for r in countries))


def _origins_en(m, day):
    countries = _rot(m["countries"], day, 3)
    if not countries:
        return "Malt Radar works on a multi-country catalog scope."
    total = len(m["countries"])
    return (
        "Malt Radar's dataset spans {cc} countries/regions:\n"
        "{cs}.\n"
        "Cataloguing geography from raw material to distillation."
    ).format(cc=total, cs=", ".join(_tags(r) for r in countries))


PLATFORMS = ["x"]


class DraftBuilder:
    """Metriklerden yasal-clean taslak kümeleri üretir (çok günlük birikimli).

    day: hangi günün diliminin üretileceği (0 = ilk). Her day -> yeni id,
         farklı bölge/ülke vurgusu -> tekrarsız içerik.
    lang: "tr" | "en" — hangi dilde taslak üretileceği. id seed'ine girer,
         böylece aynı day'de TR ve EN postlar FARKLI id alır (queue dedup
         TR'yi EN'yi yutmaz).
    platforms: varsayılan yalnız ['x'] (reddit/forum henüz publish desteklemez).
    """

    def __init__(self, handle: str = "MaltRadar"):
        self.handle = handle

    def build(self, m: dict, platforms: list[str] | None = None,
              day: int = 0, lang: str = "tr") -> list[Post]:
        plats = platforms if platforms is not None else PLATFORMS
        posts = []
        for tpl, fn in TEMPLATE_FNS.items():
            body = fn(m, day, lang)
            ok, why = _gate(body)
            if not ok:
                # yasal griden geçmeyen varyant üretilmez; default atlanır
                continue
            for p in plats:
                pid = _post_id(f"{m['db_sha256']}:{tpl}:{p}:{lang}:day{day}")
                posts.append(Post(
                    id=pid, handle=self.handle, platform=p, template=tpl,
                    body=body, created_utc=_json.dumps(m["generated_utc"]).strip('"'),
                    source_sha256=m["db_sha256"], day=day, lang=lang,
                ))
        return posts


def render_preview(post: Post) -> str:
    return (
        f"[{post.id}] {post.handle} @ {post.platform} | tpl={post.template} "
        f"| lang={post.lang} | day={post.day} | {post.status}\n"
        f"---\n{post.body}\n---"
    )
