"""Turkish flavor lexicon — TR tasting-note tokens -> English FlavorMapper descriptors.

Restored from the compiled module (mr-kep/editorial/adapters/__pycache__/
tr_flavor_lexicon.cpython-311.pyc) whose .py source was lost. Behavior is
byte-compatible with the original:

- tr_lower('I') -> 'ı', tr_lower('İ') -> 'i' (dotted/dotless I is NOT handled
  by plain str.lower()).
- map_tr_token(token) -> English descriptor or None. Single tokens only;
  bigrams ('kuru üzüm', 'deniz tuzu', ...) are matched by normalize_tr_prose
  before tokenization.
- normalize_tr_prose(prose) -> tr_lowercased, token-preserving string ready
  for bigram + token scanning.

Used by the Turkish editorial adapters (meleklerinpayi, ficisertligi,
theviskici) to bridge TR descriptors into the canonical English FlavorMapper
7-axis lexicon. NEVER a parallel axis vocabulary.
"""
from __future__ import annotations
import re
from typing import Optional

# TR token -> English FlavorMapper descriptor (canonical, from original module)
TR_TO_EN = {
    "duman": "smoke", "dumanlı": "smoky", "dumansı": "smoky", "is": "smoke",
    "isli": "smoky", "füme": "smoke", "kül": "ash", "közlenmiş": "charred",
    "tütsü": "smoke", "tütsülü": "smoky", "turba": "peat", "turbalı": "peaty",
    "turbamsı": "peaty", "iyot": "iodine", "iyotlu": "iodine", "tıbbi": "medicinal",
    "ilaçsı": "medicinal", "fenolik": "phenolic", "toprak": "earthy",
    "topraksı": "earthy", "meyve": "fruity", "meyvemsi": "fruity",
    "meyveli": "fruity", "elma": "apple", "armut": "pear", "narenciye": "citrus",
    "limon": "lemon", "portakal": "orange", "mandalina": "orange",
    "greyfurt": "citrus", "tropikal": "tropical", "tropik": "tropical",
    "şeftali": "fruity", "kayısı": "fruity", "kiraz": "cherry", "vişne": "cherry",
    "çilek": "berry", "böğürtlen": "berry", "ahududu": "berry",
    "yabanmersini": "berry", "muz": "banana", "üzüm": "fruity", "erik": "fruity",
    "ananas": "tropical", "mango": "tropical", "tatlı": "sweet", "tatlımsı": "sweet",
    "bal": "honey", "ballı": "honey", "vanilya": "vanilla", "karamel": "caramel",
    "karamelize": "caramel", "şeker": "sugar", "şekerli": "sugar", "şurup": "syrup",
    "pekmez": "syrup", "çikolata": "chocolate", "kek": "cake", "pasta": "cake",
    "baharat": "spice", "baharatlı": "spicy", "tarçın": "cinnamon",
    "tarçınsı": "cinnamon", "tarçınlı": "cinnamon", "biber": "pepper",
    "karabiber": "pepper", "karanfil": "clove", "zencefil": "ginger",
    "muskat": "nutmeg", "deniz": "sea", "denizel": "maritime", "tuz": "salt",
    "tuzlu": "salty", "salamura": "brine", "yosun": "seaweed", "sahil": "coastal",
    "kıyı": "coastal", "okyanus": "ocean", "şeri": "sherry", "fındık": "nutty",
    "fındıklı": "nutty", "ceviz": "nutty", "badem": "nutty", "acıbadem": "nutty",
    "incir": "fig", "hurma": "fig", "porto": "port", "keçiboynuzu": "fig",
}

# Multi-word tokens checked BEFORE single-token scanning.
TR_BIGRAMS = {
    "kuru meyve": "dried fruit", "kuru üzüm": "raisin", "deniz yosunu": "seaweed",
    "deniz tuzu": "salt", "bitter çikolata": "chocolate",
}

TR_TOKEN_RE = re.compile(r"[a-zçğıöşü]+(?:['-][a-zçğıöşü]+)*")


def tr_lower(s: str) -> str:
    """Turkish-aware lowercase: I->ı, İ->i (plain .lower() corrupts both)."""
    return (s or "").replace("İ", "i").replace("I", "ı").lower()


def map_tr_token(token: str) -> Optional[str]:
    """Map a single TR token to its English FlavorMapper descriptor (or None)."""
    t = tr_lower(token)
    return TR_TO_EN.get(t)


def normalize_tr_prose(prose: str) -> str:
    """Normalize TR prose: Turkish-aware lowercase, preserve tokens."""
    return tr_lower(prose)
