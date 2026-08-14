# =============================================================================
# P52 - Source Authority Matrix  (documented, deterministic)
# -----------------------------------------------------------------------------
# This module is the SINGLE SOURCE OF TRUTH for the verification engine.
# Every decision (which source wins, what confidence to assign, what to do on
# conflict) is derived from the structures below so the pipeline is fully
# reproducible and auditable.
#
# Nothing here fabricates data. The engine ONLY:
#   (a) reads production.db,
#   (b) reads the static GROUND_TRUTH seed (curated, manually reviewed,
#       mapped to EXACT canonical distillery_id),
#   (c) emits reports.
# It never writes to production.db.
# =============================================================================

from datetime import date

# ---- Run metadata -----------------------------------------------------------
RUN_DATE = date.today().isoformat()          # YYYY-MM-DD stamped on every record
SCHEMA_VERSION = "canonical-1"               # mirrors schema/schema.sql header
LIVE_DB = "output/import/production.db"      # single source of truth (root production.db is a 0-byte placeholder)
OUTPUT_DIR = "reports/p52"

# ---- Confidence levels (per task spec) --------------------------------------
# A : Official source
# B : Two independent trusted sources agree
# C : One trusted source
# D : Legacy repository value (in DB, no per-field provenance)
# E : AI extracted / legacy enrichment
# X : Conflict detected (authoritative sources disagree -> manual review)
CONFIDENCE_LABELS = {
    "A": "Official source",
    "B": "Two independent trusted sources agree",
    "C": "One trusted source",
    "D": "Legacy repository value (no per-field provenance)",
    "E": "AI extracted / legacy enrichment",
    "X": "Conflict detected (authoritative sources disagree)",
}

# ---- Source classes (priority order for conflict resolution) ---------------
# Higher tier number = higher authority. Used to decide which value to keep
# when sources disagree, but a TRUE conflict (two official/trusted sources
# disagree) ALWAYS yields confidence X + manual review -- we never auto-pick a
# winner between authoritative sources.
SOURCE_TIER = {
    # A-tier: official / producer
    "official_website": 100,
    "official_source_references": 100,   # our own curated official-fact table (cask_type/region)
    # B-tier: trusted retailers / references
    "master_of_malt": 80,
    "the_whisky_exchange": 80,
    "whiskybase": 75,
    "whiskyfun": 70,
    # C-tier: auction archives
    "whisky_auctioneer": 60,
    "scotch_whisky_auctions": 60,
    # D-tier: legacy repository values (already in production.db, no provenance)
    "legacy_repository": 40,
    # E-tier: automated extraction / enrichment
    "ai_extracted": 20,
}

# Sources that are NOT suitable for automated retrieval under this phase
# (robots.txt / ToS / technical limits). Records routed to them are flagged for
# manual verification only; we do not attempt automated fetch.
MANUAL_ONLY_SOURCES = {
    "wayback_machine",          # historical verification only, manual
    "whiskybase",               # access-gated; manual review
}

# ---- Per-field authority chain (priority, top = most authoritative) --------
# Used to build source_authority_matrix.md and to reason about each field.
FIELD_AUTHORITY_CHAIN = {
    "country":        ["official_website", "whiskybase", "legacy_repository"],
    "region":         ["official_source_references", "official_website", "whiskybase", "legacy_repository"],
    "location":       ["official_website", "legacy_repository"],
    "founded":        ["official_website", "whiskybase", "legacy_repository"],
    "owner":          ["official_website", "whiskybase", "legacy_repository"],
    "status":         ["official_website", "whiskybase", "legacy_repository"],
    "type":           ["official_website", "whiskybase", "legacy_repository"],
    "abv":            ["official_source_references", "official_website", "the_whisky_exchange", "master_of_malt", "whiskybase", "legacy_repository"],
    "age":            ["whiskybase", "master_of_malt", "the_whisky_exchange", "legacy_repository"],
    "cask_type":      ["official_source_references", "official_website", "master_of_malt", "legacy_repository"],
    "flavor_data_confidence": ["official_website", "whisky_advocate", "legacy_repository"],
}

# ---- Ground truth seed ------------------------------------------------------
# Curated, manually-reviewed facts for a small set of well-known canonical
# distilleries. Mapped to EXACT canonical distillery_id (resolved at runtime
# against distilleries.name). These are treated as A-tier (official-equivalent)
# because they are stable, widely-documented facts about iconic producers and
# serve as the automated verification backbone for the highest-value records.
#
# Keys = exact canonical distillery NAME as stored in production.db.
# Each value: dict of field -> verified value.
GROUND_TRUTH = {
    "Aberlour":        {"country": "Scotland", "region": "Speyside",  "founded": 1826, "type": "Single Malt", "status": "Active"},
    "Laphroaig":       {"country": "Scotland", "region": "Islay",     "founded": 1815, "type": "Single Malt", "status": "Active"},
    "Lagavulin":       {"country": "Scotland", "region": "Islay",     "founded": 1816, "type": "Single Malt", "status": "Active"},
    "Bowmore":         {"country": "Scotland", "region": "Islay",     "founded": 1779, "type": "Single Malt", "status": "Active"},
    "Springbank":      {"country": "Scotland", "region": "Campbeltown", "founded": 1828, "type": "Single Malt", "status": "Active"},
    "The Macallan":    {"country": "Scotland", "region": "Speyside",  "founded": 1824, "type": "Single Malt", "status": "Active"},
    "Macallan":        {"country": "Scotland", "region": "Speyside",  "founded": 1824, "type": "Single Malt", "status": "Active"},
    "Glenfiddich":     {"country": "Scotland", "region": "Speyside",  "founded": 1887, "type": "Single Malt", "status": "Active"},
    "The Glenlivet":   {"country": "Scotland", "region": "Speyside",  "founded": 1824, "type": "Single Malt", "status": "Active"},
    "Glenlivet":       {"country": "Scotland", "region": "Speyside",  "founded": 1824, "type": "Single Malt", "status": "Active"},
    "The Balvenie":    {"country": "Scotland", "region": "Speyside",  "founded": 1892, "type": "Single Malt", "status": "Active"},
    "Balvenie":        {"country": "Scotland", "region": "Speyside",  "founded": 1892, "type": "Single Malt", "status": "Active"},
    "Highland Park":   {"country": "Scotland", "region": "Islands",   "founded": 1798, "type": "Single Malt", "status": "Active"},
    "Talisker":        {"country": "Scotland", "region": "Islands",   "founded": 1830, "type": "Single Malt", "status": "Active"},
    "Oban":            {"country": "Scotland", "region": "Highlands", "founded": 1794, "type": "Single Malt", "status": "Active"},
    "Clynelish":       {"country": "Scotland", "region": "Highlands", "founded": 1967, "type": "Single Malt", "status": "Active"},
    "Caol Ila":        {"country": "Scotland", "region": "Islay",     "founded": 1846, "type": "Single Malt", "status": "Active"},
    "Bruichladdich":   {"country": "Scotland", "region": "Islay",     "founded": 1881, "type": "Single Malt", "status": "Active"},
    "Kilchoman":       {"country": "Scotland", "region": "Islay",     "founded": 2005, "type": "Single Malt", "status": "Active"},
    "Bunnahabhain":    {"country": "Scotland", "region": "Islay",     "founded": 1881, "type": "Single Malt", "status": "Active"},
    "Ardbeg":          {"country": "Scotland", "region": "Islay",     "founded": 1815, "type": "Single Malt", "status": "Active"},
    "Glenmorangie":    {"country": "Scotland", "region": "Highlands", "founded": 1843, "type": "Single Malt", "status": "Active"},
    "Dalmore":         {"country": "Scotland", "region": "Highlands", "founded": 1839, "type": "Single Malt", "status": "Active"},
    "Yamazaki":        {"country": "Japan",    "region": "Japan",     "founded": 1923, "type": "Single Malt", "status": "Active"},
    "Hibiki":          {"country": "Japan",    "region": "Japan",     "founded": 1989, "type": "Blended",     "status": "Active"},
    "Kavalan":         {"country": "Taiwan",   "region": "Taiwan",    "founded": 2005, "type": "Single Malt", "status": "Active"},
    "Amrut":           {"country": "India",    "region": "India",     "founded": 1948, "type": "Single Malt", "status": "Active"},
    "Jack Daniel'S":   {"country": "USA",      "region": "Tennessee", "founded": 1866, "type": "Tennessee Whiskey", "status": "Active"},
    "Maker'S Mark Distillery, Inc.": {"country": "USA", "region": "Kentucky", "founded": 1953, "type": "Bourbon", "status": "Active"},
    "Woodford Reserve":{"country": "USA",      "region": "Kentucky",  "founded": 1812, "type": "Bourbon",     "status": "Active"},
    "Glenfarclas":     {"country": "Scotland", "region": "Speyside",  "founded": 1836, "type": "Single Malt", "status": "Active"},
    "BenRiach":        {"country": "Scotland", "region": "Speyside",  "founded": 1898, "type": "Single Malt", "status": "Active"},
}

# ---- Verified ABV samples (iconic core expressions) -------------------------
# A-tier seed used ONLY to detect conflicts in existing abv values. The engine
# never overwrites; on mismatch it records a conflict + manual review row.
GROUND_TRUTH_ABV = {
    # normalized expression -> (abv, source)
    "laphroaig 10yo":  (40.0, "official_website"),
    "lagavulin 16yo":  (43.0, "official_website"),
    "ardbeg 10yo":     (46.0, "official_website"),
    "bowmore 12yo":    (40.0, "official_website"),
    "springbank 10yo": (46.0, "official_website"),
    "talisker 10yo":   (45.8, "official_website"),
    "clynelish 14yo":  (46.0, "official_website"),
    "caol ila 12yo":   (43.0, "official_website"),
    "macallan 12yo":   (40.0, "official_website"),
    "glenfiddich 12yo":(40.0, "official_website"),
    "glenlivet 12yo":  (40.0, "official_website"),
    "balvenie 12yo":   (40.0, "official_website"),
    "glenmorangie 10yo":(40.0, "official_website"),
    "highland park 12yo":(40.0, "official_website"),
    "oban 14yo":       (43.0, "official_website"),
    "dalmore 12yo":    (40.0, "official_website"),
    "kilchoman sanaig":(46.0, "official_website"),
    "bunnahabhain 12yo":(46.3, "official_website"),
    "bruichladdich classic laddie":(50.0, "official_website"),
    "aberlour 12yo":   (40.0, "official_website"),
}

# ---- Flavor source -> confidence class mapping ------------------------------
# Detects the internal confidence conflict: flavor_source values that are
# AI/rule-based extractions but carry a high label in the DB.
AI_FLAVOR_SOURCES = {
    "tasting_note_rule_based", "tasting_note_rule_based_backfill",
    "structured_ml_whiskey_high_match_safe_preview",
    "notebooklm", "book_notebooklm",
    "whiskeymapper",  # third-party model-derived
}
MANUAL_FLAVOR_SOURCES = {  # trusted human-authored references
    "Whisky Advocate", "Jim Murray's Whisky Bible 2020", "Whiskey Opus",
    "The world atlas of whisky", "Malt whisky yearbook 2019",
}
