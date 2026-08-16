"""Kanonik whisky isim casing'i — serve-time normalizasyon (read-only).

B1 teşhisi: production'da name=kanonik, original_name=ham küçük ikiz;
147 satırda name de küçük. Tek kural seti: title-case + MEŞRU brand/ürün
yazımları istisna listesinden korunur. B4 audit'i listeyi genişletti ve
possessive "'s" desenini sabitledi (yaş-kısaltması "18yo" zaten rakam-başlı
kelime olduğu için korunuyordu — test ile sabitlendi).
"""
import re

# Production'da hem düz (U+0027) hem curly (U+2019) apostrof geçiyor.
_APOSTROPHES = "'\u2019"


# MEŞRU yazımlar (B4 audit ile genişletildi). Anahtar: küçük harfli biçim
# (apostroflar düz "'" olarak normalize edilir); değer: korunacak kanonik
# yazım. Kelime-bazlı arama sayesinde "BenRiach 18yo ..." gibi tam isim
# içinde geçen markalar da title-case'e bozulmadan korunur.
_WORD_KEEP = {
    "a'bunadh": "A'Bunadh",
    "benriach": "BenRiach",
    # --- B4: production verisinden, resmi yazımı doğrulanmış markalar/ürünler ---
    "impex": "ImpEx",               # The ImpEx Collection (ABD ithalatçı)
    "whistlepig": "WhistlePig",
    "ancnoc": "anCnoc",             # Knockdhu markası, resmi yazım "anCnoc"
    "glendronach": "GlenDronach",
    "glenallachie": "GlenAllachie",
    "kinglassie": "KinGlassie",     # InchDairnie 2. release
    "sirdavis": "SirDavis",
    "santan": "SanTan",             # SanTan Spirits (Arizona)
    "deleón": "DeLeón",             # DeLeón Tequila
    "milhòc": "MilHòc",             # MilHòc single grain (Fransa)
    "peatsmith": "PeatSmith",       # Copperworks ürün serisi
    "farmsmith": "FarmSmith",
    "maltsmith": "MaltSmith",
    "highglen": "HighGlen",         # İsviçre single malt
    "doublewood": "DoubleWood",     # Balvenie DoubleWood
    "smws": "SMWS",                 # Scotch Malt Whisky Society (akronim)
    # Mc/Mac soyadlı markalar (hem Mc/Mac iç büyüğü hem possessive 's korunur):
    "mcconnell's": "McConnell's",
    "mccarthy's": "McCarthy's",
    "macarthur's": "MacArthur's",
    "macnair's": "MacNair's",
}


def _title_word(word: str) -> str:
    """Tek bir kelimeyi title-case yap; MEŞRU yazımları olduğu gibi koru."""
    if not word:
        return word
    key = word.lower().replace("\u2019", "'")
    if key in _WORD_KEEP:
        return _WORD_KEEP[key]
    # Possessive / contraction: sondaki "'s" küçük kalır — "Michter's",
    # "Dewar's", "Maker's", "It's" ... (production'da ~200 isim). "D'Or" gibi
    # apostrof-sonrası büyük harfli elision'lar aşağıdaki genel dala düşer.
    if key.endswith("'s"):
        ap = word[-2]  # düz veya curly — orijinal karakteri koru
        return _title_word(word[:-2]) + ap + "s"
    if "'" in word or "\u2019" in word:
        segments = re.split("['\u2019]", word)
        segments = [s[0].upper() + s[1:].lower() if s else s for s in segments]
        return "'".join(segments)
    return word[0].upper() + word[1:].lower()


def title_case_name(raw: str) -> str:
    """Title-case; apostrof sonrası harf büyür; istisnalar korunur."""
    if not raw or not raw.strip():
        return raw or ""
    s = raw.strip()
    parts = re.split(r"(\s+|\(|\)|-|&|/)", s)
    out = []
    for part in parts:
        if not part or part in ("(", ")", "-", "&", "/") or part.isspace():
            out.append(part)
            continue
        out.append(_title_word(part))
    return "".join(out)
