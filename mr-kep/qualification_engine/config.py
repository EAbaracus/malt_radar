"""
Configuration Loader (M1) - MR-KEP Qualification Engine
Loads hardcoded constants derived directly from P67 markdown tables.
"""

from typing import Dict, Any

# Classes
CLASS_BOOK = "Book"
CLASS_MAGAZINE = "Magazine"
CLASS_OFFICIAL_PDF = "Official PDF"
CLASS_PRODUCT_SHEET = "Product Sheet"
CLASS_MARKETING_BROCHURE = "Marketing Brochure"
CLASS_AUCTION_CATALOGUE = "Auction Catalogue"
CLASS_ARCHIVED_SNAPSHOT = "Archived Snapshot"
CLASS_RESEARCH_PAPER = "Research Paper"
CLASS_BLOG_ARTICLE = "Blog Article"
CLASS_REVIEW_WEBSITE_EXPORT = "Review Website Export"
CLASS_DATABASE_DUMP = "Database Dump"
CLASS_SCANNED_DOCUMENT = "Scanned Document"
CLASS_UNKNOWN = "unknown"

# Authority Tiers
TIER_T1 = "T1_authoritative"
TIER_T2 = "T2_expert"
TIER_T3 = "T3_community"

# Qualification Score Model Weights (from qualification_score_model.md)
SCORE_WEIGHTS = {
    "authority": 0.20,
    "metadata_density": 0.15,
    "extraction_complexity": 0.10,
    "historical_value": 0.10,
    "flavor_usefulness": 0.10,
    "identity_usefulness": 0.10,
    "expected_noise": 0.10,
    "license_risk": 0.05,
    "ocr_quality": 0.05,
    "expected_evidence_count": 0.05,
}

# Document Classes Attributes (from document_classes.md and score table)
# Expected Noise (inv) is from the score table (e.g. Book Noise(inv)=0.7 => noise=0.3)
DOCUMENT_CLASSES: Dict[str, Dict[str, Any]] = {
    CLASS_BOOK: {
        "authority_tier": TIER_T2,
        "metadata_density": 0.80,
        "flavor_usefulness": 0.85,
        "identity_usefulness": 0.70,
        "ocr_need": True,
        "table_likelihood": 0.40,
        "image_usefulness": 0.20,
        "license_risk": 0.20,
        "extraction_complexity": 0.55,  # 1 - 0.45 (inv)
        "historical_value": 0.90,
        "expected_noise": 0.30,  # 1 - 0.7 (inv)
        "ocr_quality": 0.30,
        "expected_evidence_count": 9,
    },
    CLASS_MAGAZINE: {
        "authority_tier": TIER_T2,
        "metadata_density": 0.60,
        "flavor_usefulness": 0.80,
        "identity_usefulness": 0.60,
        "ocr_need": False,
        "table_likelihood": 0.50,
        "image_usefulness": 0.40,
        "license_risk": 0.15,
        "extraction_complexity": 0.40,
        "historical_value": 0.50,
        "expected_noise": 0.40,
        "ocr_quality": 1.0,
        "expected_evidence_count": 6,
    },
    CLASS_OFFICIAL_PDF: {
        "authority_tier": TIER_T1,
        "metadata_density": 0.90,
        "flavor_usefulness": 0.10,
        "identity_usefulness": 0.95,
        "ocr_need": False,
        "table_likelihood": 0.70,
        "image_usefulness": 0.30,
        "license_risk": 0.10,
        "extraction_complexity": 0.20,
        "historical_value": 0.60,
        "expected_noise": 0.10,
        "ocr_quality": 1.0,
        "expected_evidence_count": 6,
    },
    CLASS_PRODUCT_SHEET: {
        "authority_tier": TIER_T1,
        "metadata_density": 0.85,
        "flavor_usefulness": 0.20,
        "identity_usefulness": 0.95,
        "ocr_need": False,
        "table_likelihood": 0.40,
        "image_usefulness": 0.50,
        "license_risk": 0.05,
        "extraction_complexity": 0.15,
        "historical_value": 0.30,
        "expected_noise": 0.10,
        "ocr_quality": 1.0,
        "expected_evidence_count": 6,
    },
    CLASS_MARKETING_BROCHURE: {
        "authority_tier": TIER_T1,
        "metadata_density": 0.50,
        "flavor_usefulness": 0.10,
        "identity_usefulness": 0.70,
        "ocr_need": False,
        "table_likelihood": 0.30,
        "image_usefulness": 0.70,
        "license_risk": 0.30,
        "extraction_complexity": 0.30,
        "historical_value": 0.20,
        "expected_noise": 0.50,
        "ocr_quality": 1.0,
        "expected_evidence_count": 3,
    },
    CLASS_AUCTION_CATALOGUE: {
        "authority_tier": TIER_T2,
        "metadata_density": 0.75,
        "flavor_usefulness": 0.30,
        "identity_usefulness": 0.85,
        "ocr_need": True,
        "table_likelihood": 0.80,
        "image_usefulness": 0.30,
        "license_risk": 0.10,
        "extraction_complexity": 0.50,
        "historical_value": 0.70,
        "expected_noise": 0.40,
        "ocr_quality": 0.40,
        "expected_evidence_count": 7,
    },
    CLASS_ARCHIVED_SNAPSHOT: {
        "authority_tier": TIER_T2,
        "metadata_density": 0.50,
        "flavor_usefulness": 0.30,
        "identity_usefulness": 0.60,
        "ocr_need": False,
        "table_likelihood": 0.40,
        "image_usefulness": 0.30,
        "license_risk": 0.20,
        "extraction_complexity": 0.50,
        "historical_value": 0.80,
        "expected_noise": 0.30,
        "ocr_quality": 0.90,
        "expected_evidence_count": 4,
    },
    CLASS_RESEARCH_PAPER: {
        "authority_tier": TIER_T2,
        "metadata_density": 0.70,
        "flavor_usefulness": 0.40,
        "identity_usefulness": 0.70,
        "ocr_need": False,
        "table_likelihood": 0.60,
        "image_usefulness": 0.30,
        "license_risk": 0.10,
        "extraction_complexity": 0.40,
        "historical_value": 0.90,
        "expected_noise": 0.20,
        "ocr_quality": 1.0,
        "expected_evidence_count": 4,
    },
    CLASS_BLOG_ARTICLE: {
        "authority_tier": TIER_T3,
        "metadata_density": 0.40,
        "flavor_usefulness": 0.50,
        "identity_usefulness": 0.20,
        "ocr_need": False,
        "table_likelihood": 0.20,
        "image_usefulness": 0.50,
        "license_risk": 0.30,
        "extraction_complexity": 0.20,
        "historical_value": 0.20,
        "expected_noise": 0.50,
        "ocr_quality": 1.0,
        "expected_evidence_count": 4,
    },
    CLASS_REVIEW_WEBSITE_EXPORT: {
        "authority_tier": TIER_T2,
        "metadata_density": 0.70,
        "flavor_usefulness": 0.90,
        "identity_usefulness": 0.40,
        "ocr_need": False,
        "table_likelihood": 0.30,
        "image_usefulness": 0.20,
        "license_risk": 0.20,
        "extraction_complexity": 0.30,
        "historical_value": 0.30,
        "expected_noise": 0.40,
        "ocr_quality": 1.0,
        "expected_evidence_count": 5,
    },
    CLASS_DATABASE_DUMP: {
        "authority_tier": TIER_T2,
        "metadata_density": 0.80,
        "flavor_usefulness": 0.20,
        "identity_usefulness": 0.90,
        "ocr_need": False,
        "table_likelihood": 0.90,
        "image_usefulness": 0.00,
        "license_risk": 0.10,
        "extraction_complexity": 0.60,  # from inv 0.40
        "historical_value": 0.40,
        "expected_noise": 0.20,
        "ocr_quality": 1.0,
        "expected_evidence_count": 7,
    },
    CLASS_SCANNED_DOCUMENT: {
        "authority_tier": TIER_T2,
        "metadata_density": 0.50,
        "flavor_usefulness": 0.40,
        "identity_usefulness": 0.50,
        "ocr_need": True,
        "table_likelihood": 0.50,
        "image_usefulness": 0.20,
        "license_risk": 0.20,
        "extraction_complexity": 0.90,
        "historical_value": 0.70,
        "expected_noise": 0.30,
        "ocr_quality": 0.00,
        "expected_evidence_count": 4,
    },
}

# Authority factor mapping
AUTHORITY_FACTORS = {
    TIER_T1: 1.0,
    TIER_T2: 0.7,
    TIER_T3: 0.2,
}

# Gates
GATE_REJECT = "Reject"
GATE_ARCHIVE_ONLY = "Archive Only"
GATE_EXTRACT_LATER = "Extract Later"
GATE_EXTRACT_NORMALLY = "Extract Normally"
GATE_HIGH_PRIORITY = "High Priority"

# Gate logic expects to know what these mean in schemas
# From qualification.schema.json, decisions are: in_scope, out_of_scope, deferred
DECISION_IN_SCOPE = "in_scope"
DECISION_OUT_OF_SCOPE = "out_of_scope"
DECISION_DEFERRED = "deferred"

GATE_TO_DECISION = {
    GATE_REJECT: DECISION_OUT_OF_SCOPE,
    GATE_ARCHIVE_ONLY: DECISION_DEFERRED,
    GATE_EXTRACT_LATER: DECISION_IN_SCOPE,
    GATE_EXTRACT_NORMALLY: DECISION_IN_SCOPE,
    GATE_HIGH_PRIORITY: DECISION_IN_SCOPE,
}

# Expected fields per class
EXPECTED_FIELDS = {
    CLASS_BOOK: ["distillery_name", "region", "country", "nose", "palate", "finish", "flavor_axes", "age_statement", "cask_type"],
    CLASS_MAGAZINE: ["nose", "palate", "finish", "flavor_axes", "score", "region"],
    CLASS_OFFICIAL_PDF: ["distillery_name", "region", "country", "abv", "age_statement", "cask_type"],
    CLASS_PRODUCT_SHEET: ["distillery_name", "region", "country", "abv", "age_statement", "cask_type"],
    CLASS_MARKETING_BROCHURE: ["distillery_name", "region", "country"],
    CLASS_AUCTION_CATALOGUE: ["distillery_name", "region", "country", "abv", "age_statement", "cask_type", "vintage"],
    CLASS_ARCHIVED_SNAPSHOT: ["distillery_name", "region", "country"],
    CLASS_RESEARCH_PAPER: ["region", "country", "cask_type"],
    CLASS_BLOG_ARTICLE: ["nose", "palate", "finish", "flavor_axes"],
    CLASS_REVIEW_WEBSITE_EXPORT: ["nose", "palate", "finish", "flavor_axes", "score"],
    CLASS_DATABASE_DUMP: ["distillery_name", "region", "country", "abv", "age_statement", "cask_type", "score"],
    CLASS_SCANNED_DOCUMENT: ["distillery_name", "region", "country", "abv", "age_statement", "cask_type"], # Fallback standard official fields
}
