"""Kanonik whisky isim casing'i — serve-time normalizasyon (read-only).

B1 teşhisi: production'da name=kanonik, original_name=ham küçük ikiz;
147 satırda name de küçük. Tek kural seti: title-case + MEŞRU brand/ürün
yazımları istisna listesinden korunur. B4 audit'i listeyi genişletir.
"""
import re

# MEŞRU yazımlar (B4 audit öncesi minimum set; tam liste audit'ten gelir).
# Anahtar: küçük harfli biçim; değer: korunacak kanonik yazım. Kelime-bazlı
# arama sayesinde "BenRiach 18yo ..." gibi tam isim içinde geçen markalar da
# title-case'e bozulmadan korunur (tam-eşleşme _EXACT_KEEP YETMEZ).
_WORD_KEEP = {
    "a'bunadh": "A'Bunadh",
    "benriach": "BenRiach",
}


def _title_word(word: str) -> str:
    """Tek bir kelimeyi title-case yap; MEŞRU yazımları olduğu gibi koru."""
    if not word:
        return word
    key = word.lower()
    if key in _WORD_KEEP:
        return _WORD_KEEP[key]
    if "'" in word:
        segments = word.split("'")
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
