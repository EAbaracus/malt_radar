"""P500-N — Canonical QA Pipeline Tests.

Tests: plan determinism, invariant checks, evidence validation,
quality-rejected evaluation, GO/NO-GO readiness, BLOCKED detection.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_QA_ROOT = _HERE.parent
_ENGINE_ROOT = _QA_ROOT.parent

for _p in [_QA_ROOT, _ENGINE_ROOT / "evidence",
           _ENGINE_ROOT / "canonicalize",
           _ENGINE_ROOT / "common"]:
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from qa import qa, write_report, write_report_deterministic, compute_plan_hash
from qa import QaReport, QASummary, InvariantCheckResult, EvidenceQAItem, QualityRejectedItem

import pytest

ROOT = _ENGINE_ROOT.parent
PROD_DB = os.path.join(ROOT, "output", "import", "production.db")
INV_YAML = os.path.join(ROOT, "mr-kep", "common", "invariant_registry.yaml")
VALID_WID = "21e7ffc0-6813-5c8d-9a31-26a99ca23a6f"
VALID_WID2 = "84b74073-31ee-54c4-b58b-e9f22465b4d4"

# ── Helper ────────────────────────────────────────────────────────────

def _make_plan(
    inserts_count: int = 3,
    include_skips: bool = False,
    include_conflicts: bool = False,
    qr_ids: set | None = None,
) -> str:
    """Write a test plan JSON to temp directory, return path."""
    inserts = []
    for i in range(inserts_count):
        wid = VALID_WID if i == 0 else f"00000000-{i:04d}-{'a'*19}"[:36]
        eid = hashlib.sha256(f"{wid}:pipeline".encode()).hexdigest()[:32]
        vec = {"smoky": 0.5, "peaty": 0.0, "fruity": 0.0, "sweet": 0.0,
               "spicy": 0.0, "maritime": 0.0, "sherry": 0.0}
        ins = {
            "whisky_id": wid,
            "evidence_id": eid,
            "source": "pipeline",
            "insert_row": [eid, wid, "pipeline", 0.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            "vector": vec,
            "confidence": 1.0,
            "provenance_json": '{"pipeline":"evidence-v1.0.0","axis_sources":[]}',
        }
        inserts.append(ins)

    skips = []
    if include_skips:
        wid = f"unresolved-uuid-{'x'*20}"
        eid = hashlib.sha256(f"{wid}:pipeline".encode()).hexdigest()[:32]
        skips.append({
            "whisky_id": wid,
            "evidence_id": eid,
            "reason": "unresolved_whisky_id — no FK in production whiskies table",
        })

    plan = {
        "plan": {
            "inserts": len(inserts),
            "skips": len(skips),
            "conflicts": 0,
            "unresolved_skipped": len(skips),
            "quality_rejected_flagged": len(qr_ids) if qr_ids else 0,
            "plan_hash": "test",
        },
        "inserts": inserts,
        "skips": skips,
        "conflicts": [],
        "plan_hash": "test",
    }
    # Compute actual hash
    plan["plan_hash"] = compute_plan_hash(plan)
    plan["plan"]["plan_hash"] = plan["plan_hash"]

    tmp = tempfile.mkdtemp(prefix="qa-test-")
    path = os.path.join(tmp, "test_plan.json")
    with open(path, "w") as f:
        json.dump(plan, f)
    return path, tmp


# ── 1. Plan determinism ──────────────────────────────────────────────

class TestPlanDeterminism:
    def test_deterministic_hash(self):
        """Same plan content → same plan hash."""
        h1 = compute_plan_hash({"inserts": [{"evidence_id": "abc", "whisky_id": "wid1"}], "skips": [], "conflicts": []})
        h2 = compute_plan_hash({"inserts": [{"evidence_id": "abc", "whisky_id": "wid1"}], "skips": [], "conflicts": []})
        assert h1 == h2
        assert len(h1) == 16

    def test_hash_changes_with_content(self):
        h1 = compute_plan_hash({"inserts": [{"evidence_id": "abc", "whisky_id": "wid1"}], "skips": [], "conflicts": []})
        h2 = compute_plan_hash({"inserts": [{"evidence_id": "def", "whisky_id": "wid2"}], "skips": [], "conflicts": []})
        assert h1 != h2


# ── 2. Invariant checks ──────────────────────────────────────────────

class TestInvariants:
    def test_all_pre_promotion_checks(self):
        inv_reg = os.path.join(ROOT, "mr-kep", "common", "invariant_registry.yaml")
        path, tmp = _make_plan(1)
        try:
            report = qa(path, PROD_DB, inv_reg)
            # Must run G4, G5, G6, G7, R4
            inv_ids = {r.invariant_id for r in report.invariant_results}
            assert "G4" in inv_ids
            assert "G5" in inv_ids
            assert "G6" in inv_ids
            assert "G7" in inv_ids
            assert "R4" in inv_ids
            assert not any(r.invariant_id in ("G1", "G2", "G3", "G8")
                          for r in report.invariant_results)
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)

    def test_invariant_g4_orphan_fk(self):
        """G4 should reflect real production FK status."""
        path, tmp = _make_plan(1)
        try:
            report = qa(path, PROD_DB, INV_YAML)
            g4 = [r for r in report.invariant_results if r.invariant_id == "G4"]
            assert len(g4) == 1
            # Production DB has no orphans
            assert g4[0].passed is True
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)


# ── 3. Evidence validation ───────────────────────────────────────────

class TestEvidenceValidation:
    def test_valid_whisky_pass(self):
        path, tmp = _make_plan(1)
        try:
            report = qa(path, PROD_DB, INV_YAML)
            assert report.summary.eligible_inserts == 1
            assert report.summary.final_promotion_candidate_count == 1
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)

    def test_no_invalid_whisky_ids(self):
        path, tmp = _make_plan(3)
        try:
            report = qa(path, PROD_DB, INV_YAML)
            # First insert has VALID_WID, others are dummy UUIDs
            # Verify at least one passes and at least one fails
            verdicts = report.evidence_verdicts
            vals = {v.verdict for v in verdicts}
            assert "PASS" in vals
            assert "FAIL" in vals
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)


# ── 4. Unresolved ────────────────────────────────────────────────────

class TestUnresolved:
    def test_unresolved_skipped(self):
        path, tmp = _make_plan(1, include_skips=True)
        try:
            report = qa(path, PROD_DB, INV_YAML)
            assert report.summary.unresolved_skipped >= 1
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)


# ── 5. Quality-rejected ──────────────────────────────────────────────

class TestQualityRejected:
    def test_qr_evaluated(self):
        qr_set = {VALID_WID}
        path, tmp = _make_plan(1, qr_ids=qr_set)
        try:
            report = qa(path, PROD_DB, INV_YAML,
                       quality_rejected_whisky_ids=qr_set)
            assert report.summary.quality_rejected >= 1
            qrs = report.quality_rejected_verdicts
            assert len(qrs) >= 1
            # All have VALID_WID and provenance present
            assert qrs[0].has_valid_fk is True
            assert qrs[0].provenance_present is True
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)

    def test_qr_flag_surfaced(self):
        """Quality-rejected flag is always present in reasons."""
        qr_set = {VALID_WID}
        path, tmp = _make_plan(1, qr_ids=qr_set)
        try:
            report = qa(path, PROD_DB, INV_YAML,
                       quality_rejected_whisky_ids=qr_set)
            qr = report.quality_rejected_verdicts[0]
            assert any("quality_rejected_flag_present" in r for r in qr.reasons)
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)


# ── 6. GO/NO-GO readiness ────────────────────────────────────────────

class TestGoNogo:
    def test_clean_plan_is_ready(self):
        """All invariants pass, all inserts valid, no QR → status=READY."""
        path, tmp = _make_plan(1)
        try:
            report = qa(path, PROD_DB, INV_YAML)
            assert report.status == "READY"
            assert report.summary.go_nogo_ready is True
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)

    def test_blocked_on_invariant_fail(self):
        """An invariant failure → BLOCKED."""
        # Use a non-existent DB to force R4/G7 failure
        fake_db = os.path.join(tempfile.gettempdir(), "nonexistent_prod.db")
        path, tmp = _make_plan(1)
        try:
            report = qa(path, fake_db, INV_YAML)
            assert report.status == "BLOCKED"
            assert report.summary.blocked is True
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)

    def test_not_blocked_on_qr_review(self):
        """QR rows requiring review → GO/NO-GO_REQUIRED, not BLOCKED."""
        qr_set = {VALID_WID}
        path, tmp = _make_plan(1, qr_ids=qr_set)
        try:
            report = qa(path, PROD_DB, INV_YAML,
                       quality_rejected_whisky_ids=qr_set)
            assert report.status == "GO/NO-GO_REQUIRED"
            assert report.summary.blocked is False
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)


# ── 7. Report output ─────────────────────────────────────────────────

class TestReport:
    def test_write_report(self):
        path, tmp = _make_plan(1)
        try:
            report = qa(path, PROD_DB, INV_YAML)
            out = tempfile.mkdtemp(prefix="report-test-")
            try:
                result = write_report_deterministic(report, out)
                assert os.path.isfile(result)
                with open(result) as f:
                    data = json.load(f)
                assert data["status"] == report.status
                assert data["summary"]["final_promotion_candidate_count"] >= 0
                assert "invariant_results" in data
                assert "evidence_verdicts" in data
                assert "quality_rejected_verdicts" in data
            finally:
                import shutil
                shutil.rmtree(out, ignore_errors=True)
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)


# ── 8. Production DB ─────────────────────────────────────────────────

class TestProductionImmutable:
    def test_production_unchanged(self):
        import hashlib
        sha = hashlib.sha256(open(PROD_DB, "rb").read()).hexdigest()
        assert sha == "e9ef4702189e6a36f7b5d4efc55124e60667e73491ae9ed55ba06040b3776783"
        c = sqlite3.connect(f"file:{PROD_DB}?mode=ro", uri=True)
        assert c.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'").fetchone()[0] == 37
        assert c.execute("SELECT COUNT(*) FROM whiskies").fetchone()[0] == 4749
        assert c.execute("SELECT COUNT(*) FROM flavor_evidence").fetchone()[0] == 2881
        c.close()
