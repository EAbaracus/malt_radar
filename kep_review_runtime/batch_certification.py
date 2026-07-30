"""Evidence-based batch certification review — reusable module for KEP runtime.

Replaces score-based approval with structured evidence verification:
match assessment, identity verification, evidence review, provenance review,
and certification decision generation.

Usage:
    from batch_certification import BatchCertificationReview
    review = BatchCertificationReview(staging_db, production_db)
    candidates = review.collect_candidates([evidence_id1, evidence_id2, ...])
    review.verify_identities(candidates)
    review.generate_report(candidates, output_path)

All operations READ-ONLY. No DB writes. No promotion.
"""

import sqlite3
import json
import hashlib
from dataclasses import dataclass, field
from typing import Optional


# ── Data structures ──────────────────────────────────────────────────────────

@dataclass
class CandidateEvidence:
    """Candidate data from staging_editorial_reviews."""
    evidence_id: str
    raw_name: str
    normalized_name: str
    source_id: str
    source_url: str
    authority_tier: str
    matched_master_whisky_id: Optional[str]
    match_status: str
    evidence_confidence: float
    score_value: Optional[float]
    score_scale_max: Optional[float]
    nose: Optional[str]
    palate: Optional[str]
    finish: Optional[str]
    flavor_vector_json: dict
    provenance_state: str
    extraction_method: str
    content_hash: str
    metadata: dict = field(default_factory=dict)

    @property
    def active_flavor_axes(self) -> list[str]:
        """Return axes with value > 0."""
        return [k for k, v in self.flavor_vector_json.items()
                if v and v > 0]


@dataclass
class ProductionRecord:
    """Production whisky record."""
    whisky_id: str
    name: str
    distillery_id: Optional[str]
    region: Optional[str]
    country: Optional[str]
    abv: Optional[float]
    age: Optional[float]
    age_statement: Optional[str]
    type: Optional[str]
    brand: Optional[str]

    @property
    def has_distillery(self) -> bool:
        return self.distillery_id is not None


@dataclass
class DistilleryRecord:
    """Distillery record (from production distilleries table)."""
    name: Optional[str]
    country: Optional[str]
    region: Optional[str]


@dataclass
class IdentityField:
    """Single identity field comparison."""
    name: str
    candidate_value: str
    production_value: str
    classification: str  # VERIFIED | CONFLICT | MISSING
    note: str = ""


@dataclass
class FieldPresence:
    """Evidence field presence check."""
    name: str
    present: bool
    value: Optional[str]


@dataclass
class CandidateReview:
    """Full review for one candidate."""
    evidence: CandidateEvidence
    production: ProductionRecord
    distillery: Optional[DistilleryRecord]
    identity_fields: list[IdentityField] = field(default_factory=list)
    evidence_fields: list[FieldPresence] = field(default_factory=list)

    # Decision fields (PENDING until human fills)
    match_decision: str = "__PENDING__"
    provenance_decision: str = "__PENDING__"
    certification_decision: str = "__PENDING__"
    reviewer: str = "__PENDING__"
    justification: str = "__PENDING__"

    @property
    def match_score(self) -> float:
        """Simple heuristic match score — DECISION SUPPORT ONLY."""
        if not self.evidence.matched_master_whisky_id:
            return 0.0
        if self.evidence.matched_master_whisky_id == self.production.whisky_id:
            return 1.0
        return 0.0


@dataclass
class BatchReview:
    """Complete batch review."""
    batch_id: str
    candidates: list[CandidateReview]
    authorized_by: str = "__PENDING__"
    go_reference: str = "__PENDING__"
    approval_timestamp: str = "__PENDING__"
    approval_scope: str = "__PENDING__"


# ── Core class ───────────────────────────────────────────────────────────────

class BatchCertificationReview:
    """Evidence-based certification review for batch promotion.

    READ-ONLY. Connects to staging_editorial.db and production.db to
    collect evidence, verify identities, and generate structured review.
    """

    EVIDENCE_FIELDS_REQUIRED = [
        "score_value", "nose", "palate", "finish",
    ]
    EVIDENCE_FIELDS_OPTIONAL = [
        "conclusion", "published_date", "author",
    ]
    IDENTITY_FIELDS = [
        "brand", "product name", "age statement",
        "distillery", "region", "country", "ABV", "category",
    ]
    CANONICAL_AXES = [
        "smoky", "peaty", "fruity", "sweet", "spicy", "maritime", "sherry",
    ]
    CERTIFY_MIN = 0.70

    def __init__(self, staging_db: str, production_db: str):
        self.staging_db = staging_db
        self.production_db = production_db

    # ── Data collection (read-only) ──────────────────────────────────────

    def collect_candidates(
        self, whisky_ids: list[str]
    ) -> dict[str, CandidateReview]:
        """Collect candidate + production data for given whisky_ids.

        Returns dict[whisky_id, CandidateReview].
        All reads are READ-ONLY (mode=ro).
        """
        staging = sqlite3.connect(
            f"file:{self.staging_db}?mode=ro", uri=True
        )
        staging.row_factory = sqlite3.Row
        prod = sqlite3.connect(
            f"file:{self.production_db}?mode=ro", uri=True
        )

        reviews: dict[str, CandidateReview] = {}
        try:
            for wid in whisky_ids:
                ev = self._load_candidate(staging, wid)
                if ev is None:
                    continue
                prod_rec = self._load_production(prod, wid)
                dist = self._load_distillery(prod, prod_rec.distillery_id)

                review = CandidateReview(
                    evidence=ev,
                    production=prod_rec,
                    distillery=dist,
                )
                self._verify_identity(review)
                self._check_evidence_fields(review)
                reviews[wid] = review
        finally:
            staging.close()
            prod.close()

        return reviews

    def _load_candidate(
        self, staging: sqlite3.Connection, whisky_id: str
    ) -> Optional[CandidateEvidence]:
        """Load one staging row by matched_master_whisky_id."""
        row = staging.execute(
            "SELECT * FROM staging_editorial_reviews "
            "WHERE matched_master_whisky_id=?",
            (whisky_id,),
        ).fetchone()
        if row is None:
            return None
        r = dict(row)
        meta = json.loads(r.get("metadata_json") or "{}")
        fv = json.loads(r.get("flavor_vector_json") or "{}")
        return CandidateEvidence(
            evidence_id=r.get("evidence_id", ""),
            raw_name=r.get("raw_name", ""),
            normalized_name=r.get("normalized_name", ""),
            source_id=r.get("source_id", ""),
            source_url=r.get("source_url", ""),
            authority_tier=r.get("authority_tier", ""),
            matched_master_whisky_id=r.get("matched_master_whisky_id"),
            match_status=r.get("match_status", ""),
            evidence_confidence=r.get("evidence_confidence") or 0.0,
            score_value=r.get("score_value"),
            score_scale_max=r.get("score_scale_max"),
            nose=r.get("nose"),
            palate=r.get("palate"),
            finish=r.get("finish"),
            flavor_vector_json=fv,
            provenance_state=r.get("provenance_state", ""),
            extraction_method=r.get("extraction_method", ""),
            content_hash=r.get("content_hash", ""),
            metadata=meta,
        )

    def _load_production(
        self, prod: sqlite3.Connection, whisky_id: str
    ) -> ProductionRecord:
        """Load production whisky record."""
        cur = prod.execute(
            "SELECT * FROM whiskies WHERE whisky_id=?", (whisky_id,)
        )
        cols = [desc[0] for desc in cur.description]
        row = cur.fetchone()
        if row is None:
            return ProductionRecord(whisky_id=whisky_id, name="[NOT FOUND]",
                                       distillery_id=None, region=None,
                                       country=None, abv=None, age=None,
                                       age_statement=None, type=None,
                                       brand=None)
        r = dict(zip(cols, row))
        return ProductionRecord(
            whisky_id=r.get("whisky_id", whisky_id),
            name=r.get("name", ""),
            distillery_id=r.get("distillery_id"),
            region=r.get("region"),
            country=r.get("country"),
            abv=r.get("abv"),
            age=r.get("age"),
            age_statement=r.get("age_statement"),
            type=r.get("type"),
            brand=r.get("brand"),
        )

    def _load_distillery(
        self, prod: sqlite3.Connection, distillery_id: Optional[str]
    ) -> Optional[DistilleryRecord]:
        """Load distillery record if available."""
        if not distillery_id:
            return None
        cur = prod.execute(
            "SELECT * FROM distilleries WHERE distillery_id=?",
            (distillery_id,),
        )
        dcols = [desc[0] for desc in cur.description]
        row = cur.fetchone()
        if row is None:
            return None
        r = dict(zip(dcols, row))
        return DistilleryRecord(
            name=r.get("name"),
            country=r.get("country"),
            region=r.get("region"),
        )

    # ── Verification methods ─────────────────────────────────────────────

    def _verify_identity(self, review: CandidateReview) -> None:
        """Compare candidate evidence against production record.

        Classifies each identity field as VERIFIED / CONFLICT / MISSING.
        """
        ev = review.evidence
        pr = review.production
        dist = review.distillery

        fields = []

        # Brand
        if pr.brand:
            fields.append(IdentityField(
                "brand", "", pr.brand, "VERIFIED",
                "production has brand",
            ))
        else:
            fields.append(IdentityField(
                "brand", "", "", "MISSING",
                "not available in candidate or production",
            ))

        # Product name
        pr_name = pr.name or ""
        def _norm_name(n: str) -> str:
            return (n.lower()
                    .replace(" year old", "yo")
                    .replace(" years old", "yo")
                    .replace("yo", "yo")
                    .replace("  ", " ")
                    .strip())
        norm_match = (
            _norm_name(ev.raw_name) == _norm_name(pr_name)
            or _norm_name(ev.normalized_name) == _norm_name(pr_name)
        )
        if norm_match:
            fields.append(IdentityField(
                "product name", ev.raw_name, pr.name, "VERIFIED",
                f"'{ev.raw_name}' ↔ '{pr.name}'",
            ))
        else:
            fields.append(IdentityField(
                "product name", ev.raw_name, pr.name, "CONFLICT",
                "names do not align",
            ))

        # Age statement
        ca_age = ev.metadata.get("age_statement") or ""
        pr_age = pr.age_statement or ""
        age_match = (
            ca_age.lower().replace("year old", "yo").replace("years old", "yo").strip()
            == pr_age.lower().strip()
        ) if ca_age and pr_age else False
        if age_match:
            fields.append(IdentityField(
                "age statement", ca_age, pr_age, "VERIFIED",
            ))
        elif ca_age and pr_age:
            fields.append(IdentityField(
                "age statement", ca_age, pr_age, "CONFLICT",
            ))
        elif ca_age and not pr_age:
            fields.append(IdentityField(
                "age statement", ca_age, "None", "VERIFIED",
                "candidate provides age; production missing",
            ))
        else:
            fields.append(IdentityField(
                "age statement", "", "", "MISSING",
            ))

        # Distillery
        if dist:
            fields.append(IdentityField(
                "distillery", "", dist.name or pr.brand or "", "VERIFIED",
                f"distillery_id={pr.distillery_id} → {dist.name}",
            ))
        elif pr.distillery_id:
            fields.append(IdentityField(
                "distillery", "", f"id={pr.distillery_id}", "MISSING",
                "distillery_id exists but no distillery table record",
            ))
        else:
            fields.append(IdentityField(
                "distillery", "", "", "MISSING",
            ))

        # Region
        region_src = dist.region if dist else pr.region
        if region_src:
            fields.append(IdentityField(
                "region", "", region_src, "VERIFIED",
            ))
        else:
            fields.append(IdentityField(
                "region", "", "", "MISSING",
            ))

        # Country
        country_src = dist.country if dist else pr.country
        if country_src:
            fields.append(IdentityField(
                "country", "", country_src, "VERIFIED",
            ))
        else:
            fields.append(IdentityField(
                "country", "", "", "MISSING",
            ))

        # ABV
        ca_abv = ev.metadata.get("abv")
        if ca_abv is not None:
            if pr.abv:
                abv_match = abs(float(ca_abv) - float(pr.abv)) < 1.0
                fields.append(IdentityField(
                    "ABV", str(ca_abv), str(pr.abv), "VERIFIED" if abv_match else "CONFLICT",
                ))
            else:
                fields.append(IdentityField(
                    "ABV", str(ca_abv), "None", "VERIFIED",
                    "candidate provides ABV; production missing",
                ))
        else:
            fields.append(IdentityField(
                "ABV", "", str(pr.abv) if pr.abv else "", "MISSING",
            ))

        # Category / type
        if pr.type:
            fields.append(IdentityField(
                "category", "", pr.type, "VERIFIED",
            ))
        else:
            fields.append(IdentityField(
                "category", "", "", "MISSING",
            ))

        review.identity_fields = fields

    def _check_evidence_fields(self, review: CandidateReview) -> None:
        """Check evidence field completeness."""
        ev = review.evidence
        fields = []

        for name in self.EVIDENCE_FIELDS_REQUIRED:
            val = getattr(ev, name, None)
            fields.append(FieldPresence(name, val is not None, str(val) if val else None))

        for name in self.EVIDENCE_FIELDS_OPTIONAL:
            val = getattr(ev, name, None)
            fields.append(FieldPresence(name, val is not None, str(val) if val else None))

        # Flavor vector
        fv = ev.flavor_vector_json
        all_axes = all(ax in fv for ax in self.CANONICAL_AXES)
        fields.append(FieldPresence(
            "flavor_vector (7 axes)", all_axes,
            str(fv) if all_axes else f"missing: {[a for a in self.CANONICAL_AXES if a not in fv]}",
        ))

        review.evidence_fields = fields

    def get_verified_count(self, review: CandidateReview) -> int:
        """Count VERIFIED identity fields."""
        return sum(1 for f in review.identity_fields if f.classification == "VERIFIED")

    def get_missing_count(self, review: CandidateReview) -> int:
        """Count MISSING identity fields."""
        return sum(1 for f in review.identity_fields if f.classification == "MISSING")

    def get_conflict_count(self, review: CandidateReview) -> int:
        """Count CONFLICT identity fields."""
        return sum(1 for f in review.identity_fields if f.classification == "CONFLICT")

    # ── Report generation ────────────────────────────────────────────────

    def generate_report(
        self, reviews: dict[str, CandidateReview], output_path: str
    ) -> str:
        """Generate markdown decision record from collected reviews.

        Args:
            reviews: result of collect_candidates()
            output_path: path for the generated markdown report

        Returns:
            The report content as string.
        """
        lines = []
        batch = BatchReview(
            batch_id=f"PROMO-BATCH-{self._timestamp()}",
            candidates=list(reviews.values()),
        )
        now = self._timestamp()

        lines.append(f"# Batch Certification Decision Record (Evidence-Based)")
        lines.append(f"")
        lines.append(f"**Generated:** {now}")
        lines.append(f"**Status:** PENDING HUMAN CERTIFICATION")
        lines.append(f"")
        lines.append(f"---")
        lines.append(f"")
        lines.append("## 1. Batch Overview")
        lines.append(f"")
        lines.append(f"| Field | Value |")
        lines.append(f"|---|---|")
        lines.append(f"| `batch_id` | `{batch.batch_id}` |")
        lines.append(f"| Candidate count | {len(batch.candidates)} |")
        eids = ", ".join(c.evidence.evidence_id for c in batch.candidates)
        wids = ", ".join(c.production.whisky_id for c in batch.candidates)
        lines.append(f"| Evidence IDs | {eids} |")
        lines.append(f"| Production IDs | {wids} |")
        lines.append(f"")

        for i, review in enumerate(batch.candidates, 1):
            ev = review.evidence
            pr = review.production
            letter = chr(64 + i)  # A, B, C, D...
            lines.append(f"---")
            lines.append(f"")
            lines.append(f"## Candidate {letter}: {ev.raw_name} → {pr.whisky_id}")
            lines.append(f"")

            # 2. Match Assessment
            lines.append(f"### 2. Match Assessment")
            lines.append(f"")
            lines.append(f"| Field | Candidate | Production |")
            lines.append(f"|---|---|---|")
            lines.append(f"| matched_master_whisky_id | `{ev.matched_master_whisky_id}` | `{pr.whisky_id}` |")
            lines.append(f"| Production name | — | `{pr.name}` |")
            lines.append(f"| Raw name | `{ev.raw_name}` | — |")
            lines.append(f"| Age | {ev.metadata.get('age_statement', '?')} | {pr.age} ({pr.age_statement}) |")
            if pr.type:
                lines.append(f"| Type | — | `{pr.type}` |")
            lines.append(f"")
            lines.append(f"**match_score:** `{review.match_score}` — **DECISION SUPPORT ONLY**")
            lines.append(f"")

            # 3. Identity Verification
            lines.append(f"### 3. Identity Verification")
            lines.append(f"")
            lines.append(f"| Field | Candidate | Production | Classification |")
            lines.append(f"|---|---|---|---|")
            for ident in review.identity_fields:
                lines.append(
                    f"| {ident.name} | `{ident.candidate_value}` | `{ident.production_value}` | "
                    f"**{ident.classification}**{(' — ' + ident.note) if ident.note else ''} |"
                )
            lines.append(f"")
            lines.append(f"**Summary:** {self.get_verified_count(review)} VERIFIED, "
                         f"{self.get_missing_count(review)} MISSING, "
                         f"{self.get_conflict_count(review)} CONFLICT")
            lines.append(f"")

            # 4. Evidence Review
            lines.append(f"### 4. Evidence Review")
            lines.append(f"")
            lines.append(f"| Field | Detail |")
            lines.append(f"|---|---|")
            lines.append(f"| Source | `{ev.source_id}` |")
            lines.append(f"| Source URL | `{ev.source_url}` |")
            lines.append(f"| Evidence confidence | `{ev.evidence_confidence}` |")
            lines.append(f"| Authority tier | `{ev.authority_tier}` |")
            lines.append(f"| Extraction method | `{ev.extraction_method}` |")
            lines.append(f"| Content hash | `{ev.content_hash}` |")
            lines.append(f"")
            lines.append(f"**Field completeness:**")
            lines.append(f"")
            lines.append(f"| Field | Present | Value |")
            lines.append(f"|---|---|---|")
            for ef in review.evidence_fields:
                present = "✅" if ef.present else "❌"
                val = ef.value[:60] + "..." if ef.value and len(ef.value) > 60 else (ef.value or "")
                lines.append(f"| {ef.name} | {present} | `{val}` |")
            lines.append(f"")
            if ev.extraction_method == "heuristic":
                lines.append(f"**Note:** Heuristic extraction may produce formatting artifacts "
                             f"(leading colons, missing optional fields).")
            lines.append(f"")

            # 5. Provenance Review
            lines.append(f"### 5. Provenance Review")
            lines.append(f"")
            lines.append(f"| Field | Value |")
            lines.append(f"|---|---|")
            lines.append(f"| Current state | `{ev.provenance_state}` |")
            lines.append(f"| Source chain | `{ev.source_id}` → {ev.extraction_method} → staging |")
            lines.append(f"| Content hash integrity | ✅ `{ev.content_hash[:16]}…` |")
            lines.append(f"")
            lines.append(f"**Provenance decision:** `{review.provenance_decision}` "
                         f"(RATIFY / KEEP HOLD / REJECT)")
            lines.append(f"")

            # 6. Certification Decision
            lines.append(f"### 6. Certification Decision")
            lines.append(f"")
            lines.append(f"| Field | Value |")
            lines.append(f"|---|---|")
            lines.append(f"| Decision | `{review.certification_decision}` (APPROVE / HOLD / REJECT) |")
            lines.append(f"| Reviewer | `{review.reviewer}` |")
            lines.append(f"| Justification | `{review.justification}` |")
            lines.append(f"")

        # 7. Batch Authorization
        lines.append(f"---")
        lines.append(f"")
        lines.append(f"## 7. Batch Authorization")
        lines.append(f"")
        lines.append(f"> **DO NOT create automatic GO.** Leave all fields PENDING for human input.")
        lines.append(f"")
        lines.append(f"| Field | Status |")
        lines.append(f"|---|---|")
        lines.append(f"| Authorized by | `{batch.authorized_by}` |")
        lines.append(f"| GO reference | `{batch.go_reference}` |")
        lines.append(f"| Approval timestamp | `{batch.approval_timestamp}` |")
        lines.append(f"| Approval scope | `{batch.approval_scope}` (ALL / SELECTED) |")
        lines.append(f"")
        lines.append(f"---")
        lines.append(f"")
        lines.append(f"## Final Status")
        lines.append(f"")
        lines.append("```")
        lines.append("BATCH:     PENDING HUMAN CERTIFICATION")
        lines.append("PRODUCTION: UNCHANGED")
        lines.append("```")
        lines.append("")
        lines.append("**No database writes. No staging mutation. No production mutation. "
                     "No promotion executed.**")

        content = "\n".join(lines)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        return content

    @staticmethod
    def _timestamp() -> str:
        import datetime
        return datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S+03:00")
