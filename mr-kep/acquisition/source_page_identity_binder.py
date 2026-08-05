"""P4 — Source-page identity binder (canonical, deterministic, read-only).

Compares a production whisky record against source-page extracted identity
to determine whether the page reviews the exact production expression.

This module is side-effect-free, network-free, and database-write-free.
It sits in the acquisition layer which NEVER writes to production.

Verdicts:
  MATCH                — source page reviews the exact production expression
  NO_MATCH             — source page reviews a demonstrably different product
  INSUFFICIENT_IDENTITY — brand matches but not enough product-level evidence
  AMBIGUOUS            — page reviews multiple products or identity is unclear
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple, Union


class IdentityVerdict(Enum):
    MATCH = "match"
    NO_MATCH = "no_match"
    INSUFFICIENT_IDENTITY = "insufficient_identity"
    AMBIGUOUS = "ambiguous"


@dataclass
class ProductionRecord:
    whisky_id: str
    name: str
    brand: str
    distillery: Optional[str] = None
    age: Optional[Union[int, str, None]] = None  # int = years, "NAS" = no age, None = unknown
    abv: Optional[float] = None
    cask_type: Optional[str] = None
    edition: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = None


@dataclass
class SourcePageIdentity:
    brand: Optional[str] = None
    distillery: Optional[str] = None
    age: Optional[Union[int, str, None]] = None  # None = not found, "NAS" = explicitly NAS
    abv: Optional[float] = None
    cask_type: Optional[str] = None
    edition: Optional[str] = None
    expression: Optional[str] = None  # extracted product name/expression
    multi_product: bool = False


@dataclass
class BindingResult:
    verdict: IdentityVerdict
    reason: str
    matched_attributes: List[str] = field(default_factory=list)
    contradicted_attributes: List[str] = field(default_factory=list)
    source_url: str = ""

    def __bool__(self) -> bool:
        return self.verdict == IdentityVerdict.MATCH


# ---------------------------------------------------------------------------
# Extraction helpers — conservative, title/H1 preferential
# ---------------------------------------------------------------------------

_AGE_PATTERNS = [
    re.compile(r"(\d+)\s*(?:yo|years?\s*old|year)\b", re.I),
    re.compile(r"\b(\d+)\s*Year", re.I),
]

_NAS_KEYWORDS = re.compile(r"\b(?:NAS|no\s+age\s+statement)\b", re.I)

_ABV_PATTERN = re.compile(r"(\d{1,2}(?:\.\d)?)\s*%", re.I)

_CASK_KEYWORDS = [
    "sherry", "bourbon", "port", "wine", "madeira", "sauternes",
    "rum", "cognac", "mizunara", "oak", "cask strength",
    "virgin oak", "first fill", "second fill", "refill",
]

_EDITION_KEYWORDS = [
    "edition", "release", "batch", "limited", "annual",
    "distillery exclusive", "travel retail", "fèis ìle", "feis ile",
]


def _norm(text: str) -> str:
    """Lowercase, strip accents-aware, collapse whitespace."""
    return re.sub(r"\s+", " ", text.lower().strip())


def _extract_age(text: str) -> Optional[Union[int, str]]:
    """Extract age from text. Returns int (years), 'NAS', or None (not found)."""
    if _NAS_KEYWORDS.search(text):
        return "NAS"
    for pat in _AGE_PATTERNS:
        m = pat.search(text)
        if m:
            return int(m.group(1))
    return None


def _extract_abv(text: str) -> Optional[float]:
    """Extract ABV percentage from text."""
    m = _ABV_PATTERN.search(text)
    if m:
        return float(m.group(1))
    return None


def _extract_cask(text: str) -> Optional[str]:
    """Extract cask type from text. Returns first matching keyword or None."""
    t = _norm(text)
    for kw in _CASK_KEYWORDS:
        if kw in t:
            return kw
    return None


def _extract_edition(text: str) -> Optional[str]:
    """Extract edition/release info. Returns first matching keyword or None."""
    t = _norm(text)
    for kw in _EDITION_KEYWORDS:
        if kw in t:
            return kw
    return None


def extract_source_identity(page_title: str, page_content: str = "") -> SourcePageIdentity:
    """Conservatively extract product identity from page title + content.

    Uses title/H1 preferentially. Body text is secondary.
    Returns None for attributes that cannot be determined.
    """
    search_text = page_title + " " + (page_content[:500] if page_content else "")
    return SourcePageIdentity(
        age=_extract_age(search_text),
        abv=_extract_abv(search_text),
        cask_type=_extract_cask(search_text),
        edition=_extract_edition(search_text),
        expression=page_title.strip() if page_title.strip() else None,
        brand=None,       # caller must set from extraction or match logic
        distillery=None,  # caller must set
        multi_product=_detect_multi_product(page_title, page_content[:2000] if page_content else ""),
    )


def _detect_multi_product(title: str, content: str) -> bool:
    """Heuristic: does this page review multiple products?"""
    t = _norm(title)
    multi_title = any(kw in t for kw in ["vs", "compared", "shootout", "tasting", "battle", "head to head"])
    # Count numbered items in first portion
    numbered = len(re.findall(r"(?:^|\n)\s*\d+[\.\)]\s+", content))
    return multi_title or numbered >= 3


# ---------------------------------------------------------------------------
# Core binding logic
# ---------------------------------------------------------------------------

def _age_contradicts(prod_age: Optional[Union[int, str]], src_age: Optional[Union[int, str]]) -> bool:
    """Check if ages explicitly contradict each other."""
    if prod_age is None or src_age is None:
        return False  # can't contradict what we don't know
    # Both are known values
    if isinstance(prod_age, int) and isinstance(src_age, int):
        return prod_age != src_age
    if prod_age == "NAS" and isinstance(src_age, int):
        return True  # production is NAS, source is age-stated
    if isinstance(prod_age, int) and src_age == "NAS":
        return True  # production is age-stated, source is NAS
    return False


def _abv_contradicts(prod_abv: Optional[float], src_abv: Optional[float], tolerance: float = 0.5) -> bool:
    """Check if ABVs contradict beyond tolerance."""
    if prod_abv is None or src_abv is None:
        return False
    return abs(prod_abv - src_abv) > tolerance


def bind(
    prod: ProductionRecord,
    page_identity: SourcePageIdentity,
    page_title: str = "",
    source_url: str = "",
) -> BindingResult:
    """Determine whether source page reviews the exact production expression.

    Args:
        prod: canonical production record (read-only)
        page_identity: extracted source-page identity
        page_title: raw page title for diagnostics
        source_url: source URL for diagnostics

    Returns:
        BindingResult with verdict, reason, matched/contradicted attributes
    """
    matched: List[str] = []
    contradicted: List[str] = []

    # ── Step 1: Brand check ──
    if page_identity.brand and prod.brand:
        if _norm(page_identity.brand) != _norm(prod.brand):
            contradicted.append(f"brand: production='{prod.brand}' source='{page_identity.brand}'")
            return BindingResult(
                verdict=IdentityVerdict.NO_MATCH,
                reason=f"Brand mismatch: production='{prod.brand}' vs source='{page_identity.brand}'",
                matched_attributes=matched,
                contradicted_attributes=contradicted,
                source_url=source_url,
            )
        matched.append("brand")

    # ── Step 2: Multi-product check ──
    if page_identity.multi_product:
        return BindingResult(
            verdict=IdentityVerdict.AMBIGUOUS,
            reason="Page reviews multiple products — cannot isolate single expression",
            matched_attributes=matched,
            contradicted_attributes=contradicted,
            source_url=source_url,
        )

    # ── Step 3: Age contradiction check ──
    if _age_contradicts(prod.age, page_identity.age):
        age_desc = f"production age={prod.age} vs source age={page_identity.age}"
        contradicted.append(age_desc)
        return BindingResult(
            verdict=IdentityVerdict.NO_MATCH,
            reason=f"Age contradiction: {age_desc}",
            matched_attributes=matched,
            contradicted_attributes=contradicted,
            source_url=source_url,
        )

    if prod.age is not None and page_identity.age is not None:
        if (isinstance(prod.age, int) and isinstance(page_identity.age, int) and prod.age == page_identity.age):
            matched.append("age")

    # ── Step 4: Expression/product match check ──
    if page_identity.expression and prod.name:
        prod_norm = _norm(prod.name)
        src_norm = _norm(page_identity.expression)
        if prod_norm in src_norm or src_norm in prod_norm:
            matched.append("expression")

    # ── Step 5: ABV contradiction ──
    if _abv_contradicts(prod.abv, page_identity.abv):
        contradicted.append(f"abv: production={prod.abv}% vs source={page_identity.abv}%")
        return BindingResult(
            verdict=IdentityVerdict.NO_MATCH,
            reason=f"ABV contradiction: production={prod.abv}% vs source={page_identity.abv}%",
            matched_attributes=matched,
            contradicted_attributes=contradicted,
            source_url=source_url,
        )

    if prod.abv and page_identity.abv and abs(prod.abv - page_identity.abv) <= 0.5:
        matched.append("abv")

    # ── Step 6: Cask contradiction ──
    if page_identity.cask_type and prod.cask_type:
        if _norm(page_identity.cask_type) != _norm(prod.cask_type):
            # Only flag if both sides have explicit cask info
            # A generic mention on source is not a contradiction
            if page_identity.cask_type.lower() not in ("oak", "cask strength"):
                contradicted.append(f"cask: production='{prod.cask_type}' source='{page_identity.cask_type}'")
                return BindingResult(
                    verdict=IdentityVerdict.NO_MATCH,
                    reason=f"Cask contradiction: production='{prod.cask_type}' vs source='{page_identity.cask_type}'",
                    matched_attributes=matched,
                    contradicted_attributes=contradicted,
                    source_url=source_url,
                )
        else:
            matched.append("cask")

    # ── Step 7: Edition contradiction ──
    if page_identity.edition and prod.edition:
        if _norm(page_identity.edition) != _norm(prod.edition):
            contradicted.append(f"edition: production='{prod.edition}' source='{page_identity.edition}'")
            return BindingResult(
                verdict=IdentityVerdict.NO_MATCH,
                reason=f"Edition contradiction: production='{prod.edition}' vs source='{page_identity.edition}'",
                matched_attributes=matched,
                contradicted_attributes=contradicted,
                source_url=source_url,
            )
        else:
            matched.append("edition")

    # ── Step 8: Sufficiency gate ──
    # BRAND-ONLY IS NEVER SUFFICIENT.
    # We need at least 2 non-brand corroborating attributes, OR
    # brand + expression match (which implies product-level identity).
    non_brand_matched = [a for a in matched if a != "brand"]

    if len(non_brand_matched) >= 2:
        return BindingResult(
            verdict=IdentityVerdict.MATCH,
            reason=f"Identity corroborated by: {', '.join(matched)}",
            matched_attributes=matched,
            contradicted_attributes=contradicted,
            source_url=source_url,
        )

    if "expression" in matched:
        # Brand + expression is sufficient if no contradiction
        return BindingResult(
            verdict=IdentityVerdict.MATCH,
            reason=f"Identity corroborated by brand + expression match ({page_identity.expression})",
            matched_attributes=matched,
            contradicted_attributes=contradicted,
            source_url=source_url,
        )

    # Not enough evidence
    return BindingResult(
        verdict=IdentityVerdict.INSUFFICIENT_IDENTITY,
        reason=f"Insufficient corroboration. Matched: {matched or ['brand only']}. "
               f"Need age/expression/cask/edition corroboration for product-level binding.",
        matched_attributes=matched,
        contradicted_attributes=contradicted,
        source_url=source_url,
    )


# ---------------------------------------------------------------------------
# Self-test (runs only when executed directly, not on import)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    passed = 0
    failed = 0

    def check(name: str, actual: IdentityVerdict, expected: IdentityVerdict):
        global passed, failed
        ok = actual == expected
        status = "PASS" if ok else "FAIL"
        if not ok:
            failed += 1
            print(f"  FAIL: {name} — expected {expected.value}, got {actual.value}")
        else:
            passed += 1
            print(f"  PASS: {name}")

    print("=== NEGATIVE CONTROLS ===")

    # N1: Amrut 20yo vs NAS Cask Strength
    prod_20 = ProductionRecord("W001835", "Amrut 20 Year Old", "Amrut", age=20)
    src_nas = SourcePageIdentity(brand="Amrut", age="NAS", expression="Amrut Indian Cask Strength")
    r = bind(prod_20, src_nas, page_title="Amrut Indian Cask Strength")
    check("N1: Amrut 20yo vs NAS → NO_MATCH", r.verdict, IdentityVerdict.NO_MATCH)

    # N2: Amrut 8yo vs NAS Cask Strength
    prod_8 = ProductionRecord("W001837", "Amrut 8 Year Old", "Amrut", age=8)
    r = bind(prod_8, src_nas, page_title="Amrut Indian Cask Strength")
    check("N2: Amrut 8yo vs NAS → NO_MATCH", r.verdict, IdentityVerdict.NO_MATCH)

    # N3: Amrut 20yo vs 4 Years
    prod_20b = ProductionRecord("W001835", "Amrut 20 Year Old", "Amrut", age=20)
    src_4 = SourcePageIdentity(brand="Amrut", age=4, expression="Amrut 2020 4 Years")
    r = bind(prod_20b, src_4, page_title="Amrut 2020 4 Years (Whiskybase)")
    check("N3: Amrut 20yo vs 4yo → NO_MATCH", r.verdict, IdentityVerdict.NO_MATCH)

    # N4: Amrut 29yo vs 4 Years
    prod_29 = ProductionRecord("W001836", "Amrut 29 Year Old", "Amrut", age=29)
    r = bind(prod_29, src_4, page_title="Amrut 2020 4 Years (Whiskybase)")
    check("N4: Amrut 29yo vs 4yo → NO_MATCH", r.verdict, IdentityVerdict.NO_MATCH)

    # N5: Brand-only → INSUFFICIENT_IDENTITY
    prod_12 = ProductionRecord("W000100", "Glenfiddich 12 Year Old", "Glenfiddich", age=12)
    src_brand = SourcePageIdentity(brand="Glenfiddich")
    r = bind(prod_12, src_brand, page_title="Glenfiddich Review")
    check("N5: Brand-only → INSUFFICIENT_IDENTITY", r.verdict, IdentityVerdict.INSUFFICIENT_IDENTITY)

    print("\n=== STRICTNESS AUDIT ===")

    # M1: Brand + age only (no expression) — insufficient if expression matters
    prod_m1 = ProductionRecord("W001835", "Amrut 20 Year Old", "Amrut", age=20)
    src_m1 = SourcePageIdentity(brand="Amrut", age=20, expression=None)
    r = bind(prod_m1, src_m1, page_title="Amrut 20 Year Old")
    check("M1: Brand+age only → INSUFFICIENT_IDENTITY (no expression)", r.verdict, IdentityVerdict.INSUFFICIENT_IDENTITY)

    # M2: Brand + expression only (no age on either side)
    prod_m2 = ProductionRecord("W001840", "Amrut Indian Cask Strength", "Amrut", age=None)
    src_m2 = SourcePageIdentity(brand="Amrut", expression="Amrut Indian Cask Strength")
    r = bind(prod_m2, src_m2, page_title="Amrut Indian Cask Strength")
    check("M2: Brand+expression → MATCH (unique expression, no age either side)", r.verdict, IdentityVerdict.MATCH)

    # M3: Brand + cask only
    prod_m3 = ProductionRecord("W001845", "Amrut 20 Year Old", "Amrut", age=20, cask_type="ex-bourbon")
    src_m3 = SourcePageIdentity(brand="Amrut", cask_type="ex-bourbon")
    r = bind(prod_m3, src_m3, page_title="Amrut Review")
    check("M3: Brand+cask only → INSUFFICIENT_IDENTITY", r.verdict, IdentityVerdict.INSUFFICIENT_IDENTITY)

    # M4: Brand + ABV only
    prod_m4 = ProductionRecord("W001850", "Amrut Fusion", "Amrut", abv=46.0)
    src_m4 = SourcePageIdentity(brand="Amrut", abv=46.0)
    r = bind(prod_m4, src_m4, page_title="Amrut Fusion")
    check("M4: Brand+ABV → INSUFFICIENT_IDENTITY (ABV alone not identity)", r.verdict, IdentityVerdict.INSUFFICIENT_IDENTITY)

    # M5: Brand + age + expression
    prod_m5 = ProductionRecord("W001835", "Amrut 20 Year Old", "Amrut", age=20)
    src_m5 = SourcePageIdentity(brand="Amrut", age=20, expression="Amrut 20 Year Old")
    r = bind(prod_m5, src_m5, page_title="Amrut 20 Year Old")
    check("M5: Brand+age+expression → MATCH", r.verdict, IdentityVerdict.MATCH)

    # M6: Brand + expression + ABV
    prod_m6 = ProductionRecord("W001840", "Amrut Indian Cask Strength", "Amrut", abv=57.8)
    src_m6 = SourcePageIdentity(brand="Amrut", abv=57.8, expression="Amrut Indian Cask Strength")
    r = bind(prod_m6, src_m6, page_title="Amrut Indian Cask Strength")
    check("M6: Brand+expression+ABV → MATCH", r.verdict, IdentityVerdict.MATCH)

    # M7: Expression shared across ages — brand+expression but source has no age
    prod_m7 = ProductionRecord("W001837", "Amrut 8 Year Old", "Amrut", age=8)
    src_m7 = SourcePageIdentity(brand="Amrut", age=None, expression="Amrut Indian Cask Strength")
    r = bind(prod_m7, src_m7, page_title="Amrut Indian Cask Strength")
    # Expression "Amrut Indian Cask Strength" != "Amrut 8 Year Old" → expression doesn't match
    check("M7: Shared expression, no age on source → INSUFFICIENT or NO (expr mismatch)", r.verdict, IdentityVerdict.INSUFFICIENT_IDENTITY)

    # M8: Unique expression, brand+expression
    prod_m8 = ProductionRecord("W999001", "Compass Box Orchard House", "Compass Box")
    src_m8 = SourcePageIdentity(brand="Compass Box", expression="Compass Box Orchard House")
    r = bind(prod_m8, src_m8, page_title="Compass Box Orchard House")
    check("M8: Unique expression → MATCH", r.verdict, IdentityVerdict.MATCH)

    print(f"\n=== RESULTS: {passed} PASS, {failed} FAIL ===")
    print("=== BINDER SELF-TEST COMPLETE ===")
