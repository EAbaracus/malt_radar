# =============================================================================
# P53 - Source Authority Matrix (flavor / tasting-note verification)
# -----------------------------------------------------------------------------
# Flavor-specific tiers, confidence model, normalization, manual-only sources.
# This is the SINGLE SOURCE OF TRUTH for the P53 engine. Deterministic.
#
# Flavor source priority (HIGHEST authority first) -- per P53 brief:
#   1. WhiskyFun
#   2. Whisky Advocate
#   3. Official distillery tasting notes
#   4. WhiskyNotes.be
#   5. The Whisky Edition
#   6. Master of Malt
#   7. The Whisky Exchange
#   8. NotebookLM extracted data
#   9. AI / rule-based generated data
# =============================================================================

LIVE_DB = r"C:\Users\eltun\Documents\malt radar CLEAN\output\import\production.db"
P52_LEDGER = r"C:\Users\eltun\Documents\malt radar CLEAN\reports\p52\verification_ledger.csv"
OUT_DIR = r"C:\Users\eltun\Documents\malt radar CLEAN\reports\p53"
RUN_DATE = "2026-07-12"

# Confidence labels (shared vocabulary with P52)
CONFIDENCE_LABELS = {
    "A": "Direct trusted source",
    "B": "Two independent trusted sources agree",
    "C": "Single trusted source",
    "D": "Legacy / imported data (no per-field provenance)",
    "E": "AI extraction or rule-based enrichment",
    "X": "Conflict between authoritative sources",
}

# Flavor source tier: rank 1 = highest authority. Used for tie-break + reporting.
SOURCE_TIER = {
    "whiskyfun": 1,
    "whisky advocate": 2,
    "official": 3,
    "whiskynotes": 4,
    "the whisky edition": 5,
    "master of malt": 6,
    "the whisky exchange": 7,
    "notebooklm": 8,
    "whiskeymapper": 9,
    "structured_ml_whiskey": 9,
    "tasting_note_rule_based": 9,
    "tasting_note_rule_based_backfill": 9,
    "production_data.csv": 9,
    "scotchgit": 9,
}
# Human-authored book/reference sources are treated as tier ~2-4 depending.
BOOK_SOURCES_TIER = 4  # books (Jim Murray, Whiskey Opus, atlas, yearbook...) ~ WhiskyNotes tier

# Sources that require MANUAL review (never auto-confirmed) and are not to be
# treated as ground truth. Per P53: NotebookLM + AI/rule-based are LOWEST tier.
MANUAL_FLAVOR_SOURCES = {
    "notebooklm", "book_notebooklm",
    "structured_ml_whiskey", "whiskeymapper",
    "tasting_note_rule_based", "tasting_note_rule_based_backfill",
}
# AI/rule-based markers (substring match)
AI_FLAVOR_MARKERS = (
    "whiskeymapper", "structured_ml_whiskey", "rule_based",
    "tasting_note_rule_based", "notebooklm", "ml_", "_ml",
)
# Trusted (non-AI) markers
TRUSTED_FLAVOR_MARKERS = (
    "whiskyfun", "whisky advocate", "whiskynotes", "official",
    "the whisky edition", "master of malt", "the whisky exchange",
    "jim murray", "whiskey opus", "world atlas", "yearbook",
    "anna", "libgen", "pdf", "book",
)

# Canonical 7-axis flavor_profile keys (recommendation engine input)
PROFILE_AXES = ["fruity", "sweet", "spicy", "smoky_peaty", "oak_cask", "floral_herbal", "malty_cereal"]
# P53-requested vector-level terms (mapped from flavor_vector)
VECTOR_TERMS = ["smoky", "peaty", "sherry", "fruity", "sweet", "spicy", "maritime"]

# Confidence normalization: DB stores inconsistent casing/junk.
def _norm_conf(v):
    if v is None:
        return None
    s = str(v).strip().lower()
    if s in ("", "nan", "none", "null"):
        return None
    if s in ("high",):
        return "high"
    if s in ("medium", "med"):
        return "medium"
    if s in ("low",):
        return "low"
    # numeric strings like "1.0" are legacy junk -> treat as unknown
    return None


def source_family(src):
    """Collapse a raw flavor_source string into a reportable family + tier."""
    if not src:
        return "unknown", 9
    s = src.lower()
    # exact/known
    if s in SOURCE_TIER:
        return s, SOURCE_TIER[s]
    if "whiskyfun" in s:
        return "whiskyfun", 1
    if "whisky advocate" in s:
        return "whisky advocate", 2
    if "official" in s:
        return "official distillery", 3
    if "whiskynotes" in s:
        return "whiskynotes", 4
    if "the whisky edition" in s:
        return "the whisky edition", 5
    if "master of malt" in s:
        return "master of malt", 6
    if "the whisky exchange" in s:
        return "the whisky exchange", 7
    if "notebooklm" in s:
        return "notebooklm", 8
    if any(m in s for m in ("whiskeymapper", "structured_ml_whiskey", "rule_based", "ml_", "_ml")):
        return "ai/rule-based", 9
    if any(m in s for m in ("jim murray", "whiskey opus", "world atlas", "yearbook", "anna", "libgen", "pdf", "book")):
        return "book/reference", BOOK_SOURCES_TIER
    if "production_data.csv" in s:
        return "legacy production_data.csv", 9
    return "other_legacy_import", 9


def is_ai_source(src):
    if not src:
        return False
    return any(m in src.lower() for m in AI_FLAVOR_MARKERS)


# Confidence assignment for a flavor_profile row given its source + confidence label.
def flavor_confidence(src, conf_label):
    """Return (confidence_letter, status, note).
    Never auto-upgrades AI/low-tier to A/B. AI labelled 'high' -> X (conflict).
    """
    fam, tier = source_family(src)
    ai = is_ai_source(src)
    if ai and conf_label == "high":
        return ("X", "conflict",
                "AI/rule-based source labelled high confidence; tiers say lowest authority -> manual review required")
    if ai:
        return ("E", "unverified", "AI/rule-based extraction; not independently confirmed")
    # trusted human-authored source
    if tier <= 4:  # whiskyfun/advocate/official/whiskynotes/book
        if conf_label == "high":
            return ("A", "verified", f"trusted source (tier {tier}); high confidence")
        if conf_label == "medium":
            return ("C", "verified", f"trusted source (tier {tier}); medium confidence")
        return ("C", "verified", f"trusted source (tier {tier}); confidence unusable -> C")
    # tier 5-7 (retailers)
    if conf_label in ("high", "medium"):
        return ("C", "verified", f"single trusted retailer source (tier {tier})")
    return ("D", "unverified", f"retailer source (tier {tier}); confidence unusable -> D")


# Generic / boilerplate tasting-note detection (batch policy + finish check)
GENERIC_PHRASES = (
    "no official tasting notes", "tasting notes coming soon", "n/a", "na",
    "please drink responsibly", "enjoy responsibly",
)
SHORT_LEN = 25  # notes shorter than this (after strip) are weak/generic candidates

# Batch policy: same product (distillery+age+abv family) should not be split
# unless a real tasting difference exists. We flag profiles that share a
# normalized key but have divergent dominant axes.
