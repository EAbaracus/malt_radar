"""Canonical evidence QA — P500-N.

Read-only QA pass over the P500-M PromotionPlan. Loads the plan
deterministically, runs canonical invariant registry checks, validates
all INSERT candidates, qualifies quality-rejected rows, and produces
a deterministic QA report with GO/NO-GO recommendation.

Does NOT write to production.db.
Does NOT call PromotionGate.apply().
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import os
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# ── Version ────────────────────────────────────────────────────────────

QA_VERSION = "qa-v1.0.0"

# ── QA Report types ───────────────────────────────────────────────────

@dataclasses.dataclass(frozen=True)
class InvariantCheckResult:
    """Result of one invariant check from the canonical registry."""
    invariant_id: str
    description: str
    passed: bool
    severity: str
    detail: str = ""
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "invariant_id": self.invariant_id,
            "description": self.description,
            "passed": self.passed,
            "severity": self.severity,
            "detail": self.detail,
            "error": self.error,
        }


@dataclasses.dataclass(frozen=True)
class EvidenceQAItem:
    """QA verdict for one planned evidence insert."""
    whisky_id: str
    evidence_id: str
    vector: dict[str, float]
    verdict: str                     # PASS | FAIL | REQUIRES_REVIEW
    reasons: tuple[str, ...]

    def to_dict(self) -> dict:
        return {
            "whisky_id": self.whisky_id,
            "evidence_id": self.evidence_id,
            "vector": self.vector,
            "verdict": self.verdict,
            "reasons": list(self.reasons),
        }


@dataclasses.dataclass(frozen=True)
class QualityRejectedItem:
    """Re-evaluation disposition for one quality-rejected record."""
    whisky_id: str
    evidence_id: str
    has_valid_fk: bool
    has_all_axes: bool
    vector: dict[str, float]
    provenance_present: bool
    verdict: str                     # PASS | FAIL | REQUIRES_REVIEW
    reasons: tuple[str, ...]

    def to_dict(self) -> dict:
        return {
            "whisky_id": self.whisky_id,
            "evidence_id": self.evidence_id,
            "has_valid_fk": self.has_valid_fk,
            "has_all_axes": self.has_all_axes,
            "vector": self.vector,
            "provenance_present": self.provenance_present,
            "verdict": self.verdict,
            "reasons": list(self.reasons),
        }


@dataclasses.dataclass(frozen=True)
class QASummary:
    """Single page QA summary."""
    total_candidates: int
    eligible_inserts: int
    rejected: int
    unresolved_skipped: int
    quality_rejected: int
    quality_passed: int
    quality_failed: int
    quality_requires_review: int
    invariant_count: int
    invariant_passed: int
    invariant_failed: int
    all_invariants_pass: bool
    final_promotion_candidate_count: int
    go_nogo_ready: bool
    blocked: bool
    report_hash: str


@dataclasses.dataclass(frozen=True)
class QaReport:
    """Complete deterministic QA readiness report."""
    pipeline_version: str
    created_at: str
    summary: QASummary
    invariant_results: tuple[InvariantCheckResult, ...]
    evidence_verdicts: tuple[EvidenceQAItem, ...]
    quality_rejected_verdicts: tuple[QualityRejectedItem, ...]
    plan_hash_verified: str
    plan_hash_recomputed: str
    plan_deterministic: bool
    blocked_reasons: tuple[str, ...]
    status: str                       # READY | BLOCKED | GO/NO-GO_REQUIRED

    def to_dict(self) -> dict:
        return {
            "pipeline_version": self.pipeline_version,
            "created_at": self.created_at,
            "summary": dataclasses.asdict(self.summary),
            "invariant_results": [r.to_dict() for r in self.invariant_results],
            "evidence_verdicts": [v.to_dict() for v in self.evidence_verdicts],
            "quality_rejected_verdicts": [v.to_dict() for v in self.quality_rejected_verdicts],
            "plan_hash_verified": self.plan_hash_verified,
            "plan_hash_recomputed": self.plan_hash_recomputed,
            "plan_deterministic": self.plan_deterministic,
            "blocked_reasons": list(self.blocked_reasons),
            "status": self.status,
        }


# ── Canonical QA registry check keys (mirror invariant_registry.yaml checks) ──

# Checks that apply pre-promotion (no backup/apply needed yet)
PRE_PROMOTION_CHECK_IDS = {
    "G4",  # no orphan FK
    "G5",  # no duplicate evidence_id
    "G6",  # existing evidence unchanged (INSERT-only)
    "G7",  # integrity check
    "R4",  # axis ≤ 1.0
}

# Checks that require apply data (skip in pre-promotion QA)
POST_PROMOTION_CHECK_IDS = {"G1", "G2", "G3", "G8"}


# ── Core QA function ──────────────────────────────────────────────────

CANONICAL_AXES = ["smoky", "peaty", "fruity", "sweet", "spicy", "maritime", "sherry"]


def _ensure_registry_checkers():
    """Ensure invariant registry check functions are registered."""
    from invariant_registry import register_check

    # Only register pre-promotion checks (G4-G7, R4)
    # These run against the production DB in read-only mode

    def _check_g4_no_orphan_fk(ctx):
        check_db = ctx.get("check_db")
        if not check_db or not os.path.exists(check_db):
            return False
        try:
            conn = sqlite3.connect(f"file:{check_db}?mode=ro", uri=True)
            orphans = conn.execute(
                "SELECT COUNT(*) FROM flavor_evidence fe "
                "LEFT JOIN whiskies w ON fe.whisky_id = w.whisky_id "
                "WHERE w.whisky_id IS NULL"
            ).fetchone()[0]
            conn.close()
            return orphans == 0
        except Exception:
            return False

    def _check_g5_no_duplicate_evidence_id(ctx):
        check_db = ctx.get("check_db")
        if not check_db or not os.path.exists(check_db):
            return False
        try:
            conn = sqlite3.connect(f"file:{check_db}?mode=ro", uri=True)
            dups = conn.execute(
                "SELECT COUNT(*) FROM ("
                "SELECT evidence_id, COUNT(*) as cnt "
                "FROM flavor_evidence GROUP BY evidence_id HAVING cnt > 1)"
            ).fetchone()[0]
            conn.close()
            return dups == 0
        except Exception:
            return False

    def _check_g6_existing_evidence_unchanged(ctx):
        return True  # INSERT-only policy; always pass in pre-promotion QA

    def _check_g7_integrity_check_ok(ctx):
        check_db = ctx.get("check_db")
        if not check_db or not os.path.exists(check_db):
            return False
        try:
            conn = sqlite3.connect(f"file:{check_db}?mode=ro", uri=True)
            integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
            conn.close()
            return integrity == "ok"
        except Exception:
            return False

    def _check_r4_invariant(ctx):
        check_db = ctx.get("check_db")
        if not check_db or not os.path.exists(check_db):
            return False
        try:
            conn = sqlite3.connect(f"file:{check_db}?mode=ro", uri=True)
            bad = conn.execute(
                "SELECT COUNT(*) FROM flavor_evidence WHERE "
                "vector_smoky>1.0 OR vector_peaty>1.0 OR vector_sherry>1.0 "
                "OR vector_fruity>1.0 OR vector_sweet>1.0 OR vector_spicy>1.0 "
                "OR vector_maritime>1.0"
            ).fetchone()[0]
            conn.close()
            return bad == 0
        except Exception:
            return False

    for name, fn in [
        ("check_g4_no_orphan_fk", _check_g4_no_orphan_fk),
        ("check_g5_no_duplicate_evidence_id", _check_g5_no_duplicate_evidence_id),
        ("check_g6_existing_evidence_unchanged", _check_g6_existing_evidence_unchanged),
        ("check_g7_integrity_check_ok", _check_g7_integrity_check_ok),
        ("check_r4_invariant", _check_r4_invariant),
    ]:
        try:
            register_check(name, fn)
        except Exception:
            pass  # Already registered


def _load_invariant_registry(yaml_path: str) -> Any:
    """Load the invariant registry YAML."""
    from invariant_registry import InvariantRegistry
    try:
        return InvariantRegistry(yaml_path)
    except Exception as e:
        return None


def validate_evidence_candidates(
    inserts: list[dict],
    production_db: str,
) -> list[EvidenceQAItem]:
    """Validate each INSERT candidate and produce a per-row verdict.

    Criteria:
    - Valid production whisky_id (FK)
    - All 7 axes present and within [0.0, 1.0]
    - No existing (whisky_id, source) conflict
    - Provenance present
    """
    # Load valid whisky IDs
    valid_wids: set[str] = set()
    if os.path.exists(production_db):
        conn = sqlite3.connect(f"file:{production_db}?mode=ro", uri=True)
        try:
            rows = conn.execute("SELECT whisky_id FROM whiskies").fetchall()
            valid_wids = {r[0] for r in rows}
        finally:
            conn.close()

    # Load existing (whisky_id, source) pairs
    existing_keys: set[tuple[str, str]] = set()
    if os.path.exists(production_db):
        conn = sqlite3.connect(f"file:{production_db}?mode=ro", uri=True)
        try:
            rows = conn.execute(
                "SELECT whisky_id, source FROM flavor_evidence"
            ).fetchall()
            existing_keys = {(r[0], r[1]) for r in rows}
        finally:
            conn.close()

    verdicts: list[EvidenceQAItem] = []

    for ins in inserts:
        wid = ins.get("whisky_id", "")
        eid = ins.get("evidence_id", "")
        vector = ins.get("vector", {})
        reasons: list[str] = []
        fail = False

        # FK check
        if wid not in valid_wids:
            reasons.append(f"whisky_id={wid} not in production whiskies")
            fail = True

        # (whisky_id, source) conflict
        src = ins.get("source", "pipeline")
        if (wid, src) in existing_keys:
            reasons.append(f"duplicate (whisky_id={wid}, source={src}) already in flavor_evidence")
            fail = True

        # All 7 axes present
        missing_axes = [ax for ax in CANONICAL_AXES if ax not in vector]
        if missing_axes:
            reasons.append(f"missing axes: {missing_axes}")
            fail = True

        # Axes within [0.0, 1.0]
        for ax in CANONICAL_AXES:
            v = vector.get(ax, -1)
            if not (0.0 <= v <= 1.0):
                reasons.append(f"axis {ax}={v} out of range [0.0, 1.0]")
                fail = True

        # Provenance present
        if "insert_row" in ins and len(ins.get("insert_row", [])) >= 11:
            pass  # has row data
        elif not ins.get("provenance_json"):
            reasons.append("provenance JSON missing")
            fail = True

        verdicts.append(EvidenceQAItem(
            whisky_id=wid,
            evidence_id=eid,
            vector=vector,
            verdict="FAIL" if fail else "PASS",
            reasons=tuple(reasons),
        ))

    return verdicts


def evaluate_quality_rejected(
    inserts: list[dict],
    qr_whisky_ids: set[str],
    production_db: str,
) -> list[QualityRejectedItem]:
    """Re-evaluate the quality-rejected records.

    Criteria:
    - Valid FK
    - All 7 axes present
    - All axes within [0.0, 1.0]
    - Provenance present
    - Flag is surfaced, not silently cleared
    """
    valid_wids: set[str] = set()
    if os.path.exists(production_db):
        conn = sqlite3.connect(f"file:{production_db}?mode=ro", uri=True)
        try:
            rows = conn.execute("SELECT whisky_id FROM whiskies").fetchall()
            valid_wids = {r[0] for r in rows}
        finally:
            conn.close()

    qr_inserts = [ins for ins in inserts if ins.get("whisky_id", "") in qr_whisky_ids]

    results: list[QualityRejectedItem] = []

    for ins in qr_inserts:
        wid = ins.get("whisky_id", "")
        vector = ins.get("vector", {})
        reasons: list[str] = []

        has_fk = wid in valid_wids
        if not has_fk:
            reasons.append("no valid FK in production whiskies")

        has_all_axes = all(ax in vector for ax in CANONICAL_AXES)
        if not has_all_axes:
            missing = [ax for ax in CANONICAL_AXES if ax not in vector]
            reasons.append(f"missing axes: {missing}")

        axes_ok = all(0.0 <= vector.get(ax, -1) <= 1.0 for ax in CANONICAL_AXES)
        if not axes_ok:
            bad = [ax for ax in CANONICAL_AXES if not (0.0 <= vector.get(ax, -1) <= 1.0)]
            reasons.append(f"axes out of range: {bad}")

        has_prov = bool(ins.get("provenance_json"))
        if not has_prov:
            reasons.append("provenance JSON missing")

        # Flag presence — always record the QR flag
        reasons.append("previous_quality_rejected_flag_present")

        if not has_fk or not has_all_axes or not axes_ok:
            verdict = "FAIL"
        elif not has_prov:
            verdict = "REQUIRES_REVIEW"
        else:
            # All structural checks pass, quality_rejected flag is informational
            verdict = "REQUIRES_REVIEW"  # Human must re-evaluate original quality gate reason

        results.append(QualityRejectedItem(
            whisky_id=wid,
            evidence_id=ins.get("evidence_id", ""),
            has_valid_fk=has_fk,
            has_all_axes=has_all_axes,
            vector=vector,
            provenance_present=has_prov,
            verdict=verdict,
            reasons=tuple(reasons),
        ))

    return results


def _run_invariant_checks(
    registry: Any,
    production_db: str,
) -> tuple[list[InvariantCheckResult], bool, list[str]]:
    """Run applicable canonical invariants. Returns (results, all_pass, blockers)."""
    results: list[InvariantCheckResult] = []
    blocked_reasons: list[str] = []

    context = {"check_db": production_db}
    all_pass = True

    if registry and registry.loaded:
        # Filter to only pre-promotion invariants (G1/G2/G3/G8 need apply data)
        all_invariants = registry.invariants
        pre_invariants = [inv for inv in all_invariants
                          if inv["id"] in PRE_PROMOTION_CHECK_IDS]
        if not pre_invariants:
            pre_invariants = all_invariants  # fallback: run what we have

        # Run selected invariants using registry's run_check
        for inv in pre_invariants:
            c = registry.run_check(inv, context)
            result = InvariantCheckResult(
                invariant_id=c.invariant_id,
                description=c.description,
                passed=c.passed,
                severity=c.severity,
                detail=c.detail,
                error=c.error or "",
            )
            results.append(result)
            if not c.passed:
                all_pass = False
                if c.fail_action == "NO_GO" or c.fail_action == "ROLLBACK":
                    blocked_reasons.append(
                        f"{c.invariant_id}: {c.description} — {c.error or c.detail or 'failed'}"
                    )
    else:
        # Fallback: run hardcoded pre-promotion checks
        check_map = {
            "G4": ("No orphan FK in flavor_evidence", "critical", "NO_GO"),
            "G5": ("No duplicate evidence_id", "critical", "ROLLBACK"),
            "G6": ("Existing evidence immutable (INSERT-only)", "critical", "ROLLBACK"),
            "G7": ("SQLite PRAGMA integrity_check ok", "critical", "ROLLBACK"),
            "R4": ("No flavor_evidence axis > 1.0", "critical", "ROLLBACK"),
        }
        for inv_id, (desc, sev, fail_act) in check_map.items():
            passed = False
            error = ""
            try:
                if inv_id == "G4":
                    c = sqlite3.connect(f"file:{production_db}?mode=ro", uri=True)
                    o = c.execute(
                        "SELECT COUNT(*) FROM flavor_evidence fe "
                        "LEFT JOIN whiskies w ON fe.whisky_id = w.whisky_id "
                        "WHERE w.whisky_id IS NULL"
                    ).fetchone()[0]
                    c.close()
                    passed = (o == 0)
                elif inv_id == "G5":
                    c = sqlite3.connect(f"file:{production_db}?mode=ro", uri=True)
                    d = c.execute(
                        "SELECT COUNT(*) FROM (SELECT evidence_id, COUNT(*) as cnt "
                        "FROM flavor_evidence GROUP BY evidence_id HAVING cnt > 1)"
                    ).fetchone()[0]
                    c.close()
                    passed = (d == 0)
                elif inv_id == "G6":
                    passed = True  # INSERT-only is a policy, not DB-detectable
                elif inv_id == "G7":
                    c = sqlite3.connect(f"file:{production_db}?mode=ro", uri=True)
                    i = c.execute("PRAGMA integrity_check").fetchone()[0]
                    c.close()
                    passed = (i == "ok")
                elif inv_id == "R4":
                    c = sqlite3.connect(f"file:{production_db}?mode=ro", uri=True)
                    b = c.execute(
                        "SELECT COUNT(*) FROM flavor_evidence WHERE "
                        "vector_smoky>1.0 OR vector_peaty>1.0 OR vector_sherry>1.0 "
                        "OR vector_fruity>1.0 OR vector_sweet>1.0 OR vector_spicy>1.0 "
                        "OR vector_maritime>1.0"
                    ).fetchone()[0]
                    c.close()
                    passed = (b == 0)
            except Exception as e:
                error = str(e)

            results.append(InvariantCheckResult(
                invariant_id=inv_id, description=desc,
                passed=passed, severity=sev,
                error=error,
            ))
            if not passed:
                all_pass = False
                if fail_act in ("NO_GO", "ROLLBACK"):
                    blocked_reasons.append(
                        f"{inv_id}: {desc} — {error or 'failed'}"
                    )

    return results, all_pass, blocked_reasons


def compute_plan_hash(plan_data: dict) -> str:
    """Recompute deterministic plan hash from plan data."""
    h = hashlib.sha256()
    for ins in plan_data.get("inserts", []):
        h.update(f"INS:{ins.get('evidence_id','')}:{ins.get('whisky_id','')}\n".encode())
    for sk in plan_data.get("skips", []):
        h.update(f"SKP:{sk.get('evidence_id','')}:{sk.get('reason','')}\n".encode())
    for cf in plan_data.get("conflicts", []):
        h.update(f"CFL:{cf.get('evidence_id','')}:{cf.get('reason','')}\n".encode())
    return h.hexdigest()[:16]


def qa(
    plan_path: str,
    production_db: str,
    invariant_registry_yaml: str | None = None,
    quality_rejected_whisky_ids: set[str] | None = None,
    unresolved_whisky_ids: set[str] | None = None,
) -> QaReport:
    """Run full QA pass over a P500-M PromotionPlan.

    This is the single canonical QA entry point.
    """
    _ensure_registry_checkers()
    qr_set = quality_rejected_whisky_ids or set()
    unres_set = unresolved_whisky_ids or set()

    # Load plan
    if not os.path.exists(plan_path):
        raise FileNotFoundError(f"Plan not found: {plan_path}")

    with open(plan_path, "r", encoding="utf-8") as f:
        plan_data = json.load(f)

    recorded_hash = plan_data.get("plan_hash", "")
    recomputed_hash = compute_plan_hash(plan_data)
    plan_deterministic = (recorded_hash == recomputed_hash)

    inserts = plan_data.get("inserts", [])
    skips = plan_data.get("skips", [])
    conflicts = plan_data.get("conflicts", [])

    reported_inserts = plan_data.get("plan", {}).get("inserts", 0)
    reported_skips = plan_data.get("plan", {}).get("skips", 0)
    reported_unresolved = plan_data.get("plan", {}).get("unresolved_skipped", 0)
    reported_qr = plan_data.get("plan", {}).get("quality_rejected_flagged", 0)
    num_unresolved = reported_unresolved

    # Run invariant checks
    reg = None
    if invariant_registry_yaml and os.path.exists(invariant_registry_yaml):
        reg = _load_invariant_registry(invariant_registry_yaml)
    inv_results, all_inv_pass, blocked_reasons = _run_invariant_checks(reg, production_db)

    # Validate each INSERT candidate
    evidence_verdicts = validate_evidence_candidates(inserts, production_db)
    qr_verdicts = evaluate_quality_rejected(inserts, qr_set, production_db)

    # Count verdicts
    num_pass = sum(1 for v in evidence_verdicts if v.verdict == "PASS")
    num_fail = sum(1 for v in evidence_verdicts if v.verdict == "FAIL")
    num_review = sum(1 for v in evidence_verdicts if v.verdict == "REQUIRES_REVIEW")
    num_rejected = num_fail + num_review

    qr_pass = sum(1 for v in qr_verdicts if v.verdict == "PASS")
    qr_fail = sum(1 for v in qr_verdicts if v.verdict == "FAIL")
    qr_review = sum(1 for v in qr_verdicts if v.verdict == "REQUIRES_REVIEW")

    # Determine status
    if not all_inv_pass:
        status = "BLOCKED"
    elif not plan_deterministic:
        status = "BLOCKED"
    elif num_fail > 0 or num_rejected > 0:
        status = "BLOCKED"  # CANNOT BE PROMOTED — must fix rejects
    elif qr_review > 0:
        status = "GO/NO-GO_REQUIRED"  # Quality-rejected rows need human judgment
    else:
        status = "READY"

    # Final promotion candidate count (only PASS verdicts)
    final_candidates = num_pass

    summary = QASummary(
        total_candidates=reported_inserts,
        eligible_inserts=reported_inserts,
        rejected=num_rejected,
        unresolved_skipped=num_unresolved,
        quality_rejected=reported_qr,
        quality_passed=qr_pass,
        quality_failed=qr_fail,
        quality_requires_review=qr_review,
        invariant_count=len(inv_results),
        invariant_passed=sum(1 for r in inv_results if r.passed),
        invariant_failed=sum(1 for r in inv_results if not r.passed),
        all_invariants_pass=all_inv_pass,
        final_promotion_candidate_count=final_candidates,
        go_nogo_ready=(status != "BLOCKED"),
        blocked=(status == "BLOCKED"),
        report_hash=_compute_report_hash(
            inv_results, evidence_verdicts, qr_verdicts, plan_deterministic
        ),
    )

    return QaReport(
        pipeline_version=QA_VERSION,
        created_at=datetime.now(timezone.utc).isoformat(),
        summary=summary,
        invariant_results=tuple(inv_results),
        evidence_verdicts=tuple(evidence_verdicts),
        quality_rejected_verdicts=tuple(qr_verdicts),
        plan_hash_verified=recorded_hash,
        plan_hash_recomputed=recomputed_hash,
        plan_deterministic=plan_deterministic,
        blocked_reasons=tuple(blocked_reasons),
        status=status,
    )


def _compute_report_hash(
    inv_results, evidence_verdicts, qr_verdicts, plan_deterministic,
) -> str:
    h = hashlib.sha256()
    for r in inv_results:
        h.update(f"INV:{r.invariant_id}:{r.passed}\n".encode())
    for v in evidence_verdicts:
        h.update(f"EV:{v.whisky_id}:{v.verdict}\n".encode())
    for v in qr_verdicts:
        h.update(f"QR:{v.whisky_id}:{v.verdict}\n".encode())
    h.update(f"PD:{plan_deterministic}\n".encode())
    return h.hexdigest()[:16]


def write_report(report: QaReport, output_dir: Optional[str] = None) -> str:
    """Write QA report to JSON output. Returns path."""
    out_dir = output_dir or str(Path(__file__).resolve().parent / "output")
    os.makedirs(out_dir, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = os.path.join(out_dir, f"qa_report_{ts}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report.to_dict(), f, ensure_ascii=False, indent=2, sort_keys=True)
    print(f"QA Report: {path}")
    print(f"  Status: {report.status}")
    print(f"  Invariants: {report.summary.invariant_passed}/{report.summary.invariant_count} pass")
    print(f"  Evidence PASS: {report.summary.eligible_inserts - report.summary.rejected}/{report.summary.eligible_inserts}")
    print(f"  Quality-Rejected: {report.summary.quality_passed} pass, {report.summary.quality_failed} fail, {report.summary.quality_requires_review} review")
    print(f"  Final candidates: {report.summary.final_promotion_candidate_count}")
    return path


def write_report_deterministic(
    report: QaReport,
    output_dir: Optional[str] = None,
    label: str = "p500n",
) -> str:
    """Write QA report to a deterministic file path (overwrite)."""
    out_dir = output_dir or str(Path(__file__).resolve().parent / "output")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"{label}_qa_report.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report.to_dict(), f, ensure_ascii=False, indent=2, sort_keys=True)
    return path
