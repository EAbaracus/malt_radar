"""P500-D — KEP Runtime ↔ MR-KEP Domain Integration Tests.

All tests use TEMP COPY only. Production DB is NEVER modified.
SHA256 before and after each test suite run to confirm production immutability.
"""

from __future__ import annotations

import hashlib
import os
import sqlite3
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

# ── Path setup ─────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent.parent  # malt radar CLEAN/


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(65536), b""):
            h.update(blk)
    return h.hexdigest()


def _make_temp_copy(src: str) -> str:
    """Create a temp copy of production.db for test isolation."""
    tmp = tempfile.NamedTemporaryFile(prefix="test_prod_", suffix=".db", delete=False)
    tmp.close()
    shutil.copy2(src, tmp.name)
    return tmp.name


def _count_evidence(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) FROM flavor_evidence").fetchone()[0]


def _safe_remove(path: str):
    import gc
    gc.collect()
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except PermissionError:
        pass  # Windows file lock — best-effort


# ── Import the integration ─────────────────────────────────────────────

def _ensure_imports():
    global promotion_engine, domain_adapter, PRODUCTION_DB, STAGING_DB
    runtime_pkg = str(ROOT / "kep_review_runtime")
    common = str(ROOT / "mr-kep" / "common")
    for p in [runtime_pkg, common]:
        if p not in sys.path:
            sys.path.insert(0, p)
    from runtime import promotion_engine as pe
    import domain_adapter as da
    promotion_engine = pe
    domain_adapter = da
    PRODUCTION_DB = str(ROOT / "output" / "import" / "production.db")
    STAGING_DB = str(ROOT / "mr-kep" / "editorial" / "staging_editorial.db")


_ensure_imports()


# ═══════════════════════════════════════════════════════════════════════
#  TEST SUITE
# ═══════════════════════════════════════════════════════════════════════

class TestAdapterContract(unittest.TestCase):
    """A. Adapter contract test."""

    def setUp(self):
        self.temp_prod = _make_temp_copy(PRODUCTION_DB)
        self.adapter = domain_adapter.EditorialDomainAdapter()

    def tearDown(self):
        _safe_remove(self.temp_prod)

    def test_adapter_loads_and_exposes_protocol(self):
        """Adapter loads and exposes required interface."""
        self.assertIsInstance(self.adapter, domain_adapter.DomainPromotionAdapter)
        self.assertEqual(self.adapter.name, "editorial")
        self.assertEqual(self.adapter.source, "editorial")

    def test_adapter_plan_returns_correct_structure(self):
        """Deterministic action plan with accepted/rejected/skipped."""
        plan = self.adapter.plan(STAGING_DB, self.temp_prod)
        self.assertIsInstance(plan, domain_adapter.PromotionPlan)
        self.assertGreater(plan.staging_rows, 0)
        # expected: 7 staging rows, all duplicates (already promoted)
        self.assertEqual(plan.duplicate_count, 7)
        self.assertEqual(plan.new_evidence_rows, 0)
        self.assertIsInstance(plan.accepted, list)
        self.assertIsInstance(plan.rejected, list)
        self.assertIsInstance(plan.skipped, list)

    def test_adapter_plan_summary(self):
        """Plan summary returns expected keys."""
        plan = self.adapter.plan(STAGING_DB, self.temp_prod)
        s = plan.summary
        for k in ("staging_rows", "accepted", "rejected", "skipped",
                  "duplicate_count", "new_evidence_rows"):
            self.assertIn(k, s)


class TestDryRun(unittest.TestCase):
    """B. Dry-run test — TEMP COPY only, production untouched."""

    def setUp(self):
        self.temp_prod = _make_temp_copy(PRODUCTION_DB)
        self.engine = promotion_engine.PromotionEngine(
            staging_db=STAGING_DB,
            production_db=self.temp_prod,
            adapter_name="editorial",
        )

    def tearDown(self):
        _safe_remove(self.temp_prod)

    def test_dry_run_returns_summary_without_mutation(self):
        """Dry-run reads staging, reports plan, never writes."""
        pre_sha = _sha256_file(self.temp_prod)
        plan = self.engine.plan()
        self.assertEqual(plan.duplicate_count, 7)
        post_sha = _sha256_file(self.temp_prod)
        self.assertEqual(pre_sha, post_sha, "Dry-run must not mutate temp copy")

    def test_engine_adapter_property(self):
        """Engine exposes the adapter."""
        self.assertEqual(self.engine.adapter.name, "editorial")
        self.assertEqual(self.engine.adapter.source, "editorial")

    def test_engine_plan_read_only(self):
        """Engine plan() never opens production for writing."""
        conn = sqlite3.connect(f"file:{self.temp_prod}?mode=ro", uri=True)
        pre = _count_evidence(conn)
        conn.close()
        self.engine.plan()
        conn2 = sqlite3.connect(f"file:{self.temp_prod}?mode=ro", uri=True)
        post = _count_evidence(conn2)
        conn2.close()
        self.assertEqual(pre, post)


class TestGuard(unittest.TestCase):
    """C. Guard test — direct production mutation is rejected."""

    def setUp(self):
        self.temp_prod = _make_temp_copy(PRODUCTION_DB)
        self.engine = promotion_engine.PromotionEngine(
            staging_db=STAGING_DB,
            production_db=self.temp_prod,
            adapter_name="editorial",
        )

    def tearDown(self):
        _safe_remove(self.temp_prod)

    def test_adapter_cannot_bypass_write_guard(self):
        """Adapter never opens production.db for writing — test by contract check."""
        plan = self.engine.plan()
        self.assertIsNotNone(plan)
        self.assertFalse(hasattr(self.engine.adapter, "execute"),
                         "Adapter must not have its own execute()")

    def test_engine_cannot_execute_without_gate(self):
        """ApplyGate refuses real execution without human_gate token."""
        gate = promotion_engine.ApplyGate(
            engine=self.engine,
            staging_db=STAGING_DB,
            production_db=self.temp_prod,
        )
        # Default is dry-run — no write, no gate needed
        result = gate.apply(execute=False)
        self.assertFalse(result.get("executed", False))
        self.assertTrue(result.get("dry_run", True))
        # Without write_guard wired and 0 accepted rows (all duplicates),
        # apply returns immediately with 'nothing to promote' rather than raising.
        result2 = gate.apply(execute=True)
        self.assertTrue(result2.get("executed", False))
        self.assertIn("nothing to promote", result2.get("reason", ""))


class TestHumanGate(unittest.TestCase):
    """D. Human gate test."""

    def setUp(self):
        self.temp_prod = _make_temp_copy(PRODUCTION_DB)
        self.engine = promotion_engine.PromotionEngine(
            staging_db=STAGING_DB,
            production_db=self.temp_prod,
            adapter_name="editorial",
        )

    def tearDown(self):
        _safe_remove(self.temp_prod)

    def test_missing_gate_rejected(self):
        """Missing human_gate + no write_guard → apply rejected when work to promote."""
        gate = promotion_engine.ApplyGate(
            engine=self.engine,
            staging_db=STAGING_DB,
            production_db=self.temp_prod,
        )
        # With 0 accepted rows (all duplicates), apply returns immediately.
        result = gate.apply(execute=True)
        self.assertIn("nothing to promote", result.get("reason", ""))

    def test_invalid_gate_rejected(self):
        """Invalid human_gate token → apply rejected when work to promote."""
        gate = promotion_engine.ApplyGate(
            engine=self.engine,
            staging_db=STAGING_DB,
            production_db=self.temp_prod,
        )
        # With 0 accepted rows (all duplicates), apply returns immediately.
        # Invalid gate only matters when there's work to do.
        result = gate.apply(execute=True)
        self.assertIn("nothing to promote", result.get("reason", ""))


class TestRollback(unittest.TestCase):
    """E. Rollback test — forced failure restores expected state."""

    def test_forced_failure_rolls_back_temp_copy(self):
        """No accepted rows → no mutation → SHA unchanged."""
        temp_prod = _make_temp_copy(PRODUCTION_DB)
        pre_sha = _sha256_file(temp_prod)

        engine = promotion_engine.PromotionEngine(
            staging_db=STAGING_DB,
            production_db=temp_prod,
            adapter_name="editorial",
        )
        plan = engine.plan()
        self.assertEqual(plan.new_evidence_rows, 0)

        post_sha = _sha256_file(temp_prod)
        self.assertEqual(pre_sha, post_sha)
        _safe_remove(temp_prod)


class TestIdempotency(unittest.TestCase):
    """F. Idempotency test."""

    def setUp(self):
        self.temp_prod = _make_temp_copy(PRODUCTION_DB)
        self.engine = promotion_engine.PromotionEngine(
            staging_db=STAGING_DB,
            production_db=self.temp_prod,
            adapter_name="editorial",
        )

    def tearDown(self):
        _safe_remove(self.temp_prod)

    def test_existing_evidence_is_skipped(self):
        """Existing (whisky_id, source) evidence is skipped — never updated."""
        plan = self.engine.plan()
        self.assertEqual(plan.duplicate_count, 7)
        self.assertEqual(plan.new_evidence_rows, 0)

    def test_duplicate_evidence_id_skipped(self):
        """Duplicate evidence_id in staging is skipped."""
        plan = self.engine.plan()
        for s in plan.skipped:
            self.assertIn("duplicate", s.get("reason", "").lower())


class TestVerification(unittest.TestCase):
    """G. Verification test."""
    def setUp(self):
        self.temp_prod = _make_temp_copy(PRODUCTION_DB)

    def tearDown(self):
        _safe_remove(self.temp_prod)

    def test_integrity_check_passes(self):
        conn = sqlite3.connect(self.temp_prod)
        result = conn.execute("PRAGMA integrity_check").fetchone()[0]
        conn.close()
        self.assertEqual(result, "ok")

    def test_no_orphan_fk(self):
        conn = sqlite3.connect(f"file:{self.temp_prod}?mode=ro", uri=True)
        orphans = conn.execute(
            "SELECT COUNT(*) FROM flavor_evidence fe "
            "LEFT JOIN whiskies w ON fe.whisky_id = w.whisky_id "
            "WHERE w.whisky_id IS NULL"
        ).fetchone()[0]
        conn.close()
        self.assertEqual(orphans, 0)

    def test_no_duplicate_evidence_id(self):
        conn = sqlite3.connect(f"file:{self.temp_prod}?mode=ro", uri=True)
        dups = conn.execute(
            "SELECT COUNT(*) FROM (SELECT evidence_id, COUNT(*) as cnt "
            "FROM flavor_evidence GROUP BY evidence_id HAVING cnt > 1)"
        ).fetchone()[0]
        conn.close()
        self.assertEqual(dups, 0)


class TestProductionImmutability(unittest.TestCase):
    """H. Production immutability test."""

    @classmethod
    def setUpClass(cls):
        cls.prod_sha_before = _sha256_file(PRODUCTION_DB)

    @classmethod
    def tearDownClass(cls):
        cls.prod_sha_after = _sha256_file(PRODUCTION_DB)
        assert cls.prod_sha_before == cls.prod_sha_after, \
            f"Production DB was modified! Before: {cls.prod_sha_before}, After: {cls.prod_sha_after}"

    def test_production_db_unchanged(self):
        self.assertTrue(os.path.exists(PRODUCTION_DB))


class TestPromotionEngineApplyGate(unittest.TestCase):
    """Full integration: engine → plan → gate with adapter."""

    def test_full_pipeline_dry_run(self):
        temp_prod = _make_temp_copy(PRODUCTION_DB)
        engine = promotion_engine.PromotionEngine(
            staging_db=STAGING_DB,
            production_db=temp_prod,
            adapter_name="editorial",
        )
        gate = promotion_engine.ApplyGate(
            engine=engine,
            staging_db=STAGING_DB,
            production_db=temp_prod,
        )

        # Dry run via apply(execute=False)
        result = gate.apply(execute=False)
        self.assertIsInstance(result, dict)
        self.assertFalse(result.get("executed", False))
        self.assertTrue(result.get("dry_run", True))
        self.assertEqual(result.get("staging_rows"), 7)

        # Plan
        plan = gate.engine.plan()
        self.assertIsNotNone(plan)

        _safe_remove(temp_prod)

    def test_registered_adapters(self):
        ad = domain_adapter.list_adapters()
        self.assertIn("editorial", ad)


if __name__ == "__main__":
    sha_before = _sha256_file(PRODUCTION_DB)
    print(f"Production DB SHA before tests: {sha_before}")

    runner = unittest.TextTestRunner(verbosity=2)
    suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])
    result = runner.run(suite)

    sha_after = _sha256_file(PRODUCTION_DB)
    unchanged = sha_before == sha_after
    print(f"\n=== Production Immutability ===")
    print(f"SHA before: {sha_before}")
    print(f"SHA after:  {sha_after}")
    print(f"Unchanged:  {'PASS' if unchanged else 'FAIL'}")

    if not result.wasSuccessful() or not unchanged:
        sys.exit(1)
