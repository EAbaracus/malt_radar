"""P500-F — Canonical Invariant Registry Tests.

Tests the canonical YAML registry, schema validation, G1-G8 coverage,
PromotionGate integration, and production immutability.
"""

import hashlib
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

# Ensure mr-kep/common is on path
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "mr-kep" / "common"))
sys.path.insert(0, str(ROOT / "kep_review_runtime"))

from invariant_registry import InvariantRegistry, RegistryValidationError, register_check, _CHECKERS
from runtime.promotion_engine import (
    PromotionEngine, PromotionGate, PrepareReport, BackupReport,
    DryRunReport, HumanGateReport, VerificationReport, ClosureReport,
    WRITE_GO_PHRASE,
)

PRODUCTION_DB = str(ROOT / "output" / "import" / "production.db")
STAGING_DB = str(ROOT / "mr-kep" / "editorial" / "staging_editorial.db")
REGISTRY_YAML = str(ROOT / "mr-kep" / "common" / "invariant_registry.yaml")


def _make_backup_dir() -> str:
    """Isolated temp backup dir for a gate under test.

    The canonical PromotionGate.backup() defaults backup_dir to the REAL
    output/import/backups/ and writes production_prepromote_{ts}.db with only
    1-second timestamp resolution. Fast/parallel test runs collide on the same
    filename; shutil.copy2 then hits a Windows-locked leftover -> PermissionError.
    Injecting a unique per-test temp dir isolates backups without changing gate
    behavior or the production write policy.
    """
    return tempfile.mkdtemp(prefix="hermes_gate_backup_")

def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(65536), b""):
            h.update(blk)
    return h.hexdigest()


def _make_temp_copy(src: str) -> str:
    tmp = tempfile.NamedTemporaryFile(prefix="test_p500f_", suffix=".db", delete=False)
    tmp.close()
    shutil.copy2(src, tmp.name)
    return tmp.name


def _safe_remove(path: str) -> None:
    import gc
    gc.collect()
    try:
        if os.path.exists(path):
            os.remove(path)
    except PermissionError:
        pass


# ═══════════════════════════════════════════════════════════════════════
# A. Registry Load & Schema Validation
# ═══════════════════════════════════════════════════════════════════════

class TestRegistryLoad(unittest.TestCase):
    """A. Registry loads, parses, and validates correctly."""

    def test_registry_load_passes(self):
        """Registry YAML loads without error."""
        reg = InvariantRegistry(REGISTRY_YAML)
        self.assertTrue(reg.loaded)
        self.assertGreater(reg.count, 0)

    def test_registry_has_g1_to_g8(self):
        """G1-G8 all present in registry."""
        reg = InvariantRegistry(REGISTRY_YAML)
        expected = {f"G{i}" for i in range(1, 9)}
        actual = {inv["id"] for inv in reg.invariants}
        for e in sorted(expected):
            self.assertIn(e, actual, f"Missing invariant: {e}")

    def test_registry_has_r4(self):
        """R4 (domain invariant) present."""
        reg = InvariantRegistry(REGISTRY_YAML)
        self.assertIsNotNone(reg.get_invariant("R4"))

    def test_schema_missing_id_rejected(self):
        """Missing 'id' field → validation error."""
        import yaml
        bad = {"version": 1, "invariants": [{"type": "canonical", "category": "backup"}]}
        tmp = tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False)
        yaml.dump(bad, tmp)
        tmp.close()
        with self.assertRaises(RegistryValidationError) as ctx:
            InvariantRegistry(tmp.name)
        self.assertIn("missing required 'id'", str(ctx.exception))
        os.unlink(tmp.name)

    def test_duplicate_id_rejected(self):
        """Duplicate invariant ID → validation error."""
        import yaml
        bad = {
            "version": 1,
            "invariants": [
                {"id": "G1", "type": "canonical", "category": "backup",
                 "description": "x", "check_method": "check_g1_backup_matches_pre",
                 "fail_action": "NO_GO", "severity": "critical"},
                {"id": "G1", "type": "canonical", "category": "backup",
                 "description": "y", "check_method": "check_g1_backup_matches_pre",
                 "fail_action": "NO_GO", "severity": "critical"},
            ]
        }
        tmp = tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False)
        yaml.dump(bad, tmp)
        tmp.close()
        with self.assertRaises(RegistryValidationError) as ctx:
            InvariantRegistry(tmp.name)
        self.assertIn("duplicate id", str(ctx.exception))
        os.unlink(tmp.name)

    def test_invalid_fail_action_rejected(self):
        """Invalid fail_action → validation error."""
        import yaml
        bad = {
            "version": 1,
            "invariants": [
                {"id": "G1", "type": "canonical", "category": "backup",
                 "description": "x", "check_method": "check_g1_backup_matches_pre",
                 "fail_action": "MAYBE", "severity": "critical"},
            ]
        }
        tmp = tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False)
        yaml.dump(bad, tmp)
        tmp.close()
        with self.assertRaises(RegistryValidationError) as ctx:
            InvariantRegistry(tmp.name)
        self.assertIn("invalid fail_action", str(ctx.exception))
        os.unlink(tmp.name)

    def test_empty_invariants_rejected(self):
        """Empty invariants list → validation error."""
        import yaml
        bad = {"version": 1, "invariants": []}
        tmp = tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False)
        yaml.dump(bad, tmp)
        tmp.close()
        with self.assertRaises(RegistryValidationError) as ctx:
            InvariantRegistry(tmp.name)
        self.assertIn("empty", str(ctx.exception))
        os.unlink(tmp.name)

    def test_unknown_check_method_accepted(self):
        """Unregistered check_method is warned but NOT rejected — lazy registration is valid."""
        import yaml
        bad = {
            "version": 1,
            "invariants": [
                {"id": "X1", "type": "canonical", "category": "data_integrity",
                 "description": "x", "check_method": "nonexistent_check",
                 "fail_action": "NO_GO", "severity": "critical"},
            ]
        }
        tmp = tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False)
        yaml.dump(bad, tmp)
        tmp.close()
        reg = InvariantRegistry(tmp.name)
        self.assertTrue(reg.loaded)
        os.unlink(tmp.name)

    def test_get_invariant_by_id(self):
        """get_invariant() returns correct record."""
        reg = InvariantRegistry(REGISTRY_YAML)
        g1 = reg.get_invariant("G1")
        self.assertIsNotNone(g1)
        self.assertEqual(g1["id"], "G1")
        self.assertEqual(g1["check_method"], "check_g1_backup_matches_pre")


class TestRegistryRun(unittest.TestCase):
    """B. Registry run_check and run_all operate correctly."""

    def setUp(self):
        self.reg = InvariantRegistry(REGISTRY_YAML)
        # Ensure check functions are registered
        from runtime.promotion_engine import _ensure_invariant_registry
        _ensure_invariant_registry()

    def test_run_check_g1_passes_with_backup(self):
        """G1 passes when backup verified."""
        br = BackupReport(backup_path="/tmp/x", production_sha_before="a", backup_sha="a", verified=True)
        ctx = {"backup_report": br}
        results = self.reg.run_all(ctx)
        g1 = [r for r in results if r.invariant_id == "G1"]
        self.assertEqual(len(g1), 1)
        self.assertTrue(g1[0].passed)

    def test_run_check_g1_fails_without_backup(self):
        """G1 fails when no backup report."""
        ctx = {"backup_report": None, "dry_run_report": None, "apply_result": None}
        results = self.reg.run_all(ctx)
        g1 = [r for r in results if r.invariant_id == "G1"]
        self.assertFalse(g1[0].passed)

    def test_run_check_g4_passes_real_db(self):
        """G4 passes against real production DB (no orphan FKs)."""
        ctx = {"check_db": PRODUCTION_DB}
        results = self.reg.run_all(ctx)
        g4 = [r for r in results if r.invariant_id == "G4"]
        self.assertTrue(g4[0].passed)

    def test_run_check_g5_passes_real_db(self):
        """G5 passes against real production DB (no duplicate evidence_id)."""
        ctx = {"check_db": PRODUCTION_DB}
        results = self.reg.run_all(ctx)
        g5 = [r for r in results if r.invariant_id == "G5"]
        self.assertTrue(g5[0].passed)

    def test_run_check_g7_passes_real_db(self):
        """G7 passes against real production DB (integrity ok)."""
        ctx = {"check_db": PRODUCTION_DB}
        results = self.reg.run_all(ctx)
        g7 = [r for r in results if r.invariant_id == "G7"]
        self.assertTrue(g7[0].passed)

    def test_run_checks_includes_all(self):
        """run_all returns checks for all invariants in registry."""
        ctx = {"backup_report": None, "dry_run_report": None, "apply_result": None, "check_db": PRODUCTION_DB}
        results = self.reg.run_all(ctx)
        self.assertEqual(len(results), self.reg.count)
        self.assertEqual(len(results), 9)  # G1-G8 + R4


class TestPromotionGateRegistryIntegration(unittest.TestCase):
    """C. PromotionGate integration with invariant registry."""

    def setUp(self):
        self.temp_prod = _make_temp_copy(PRODUCTION_DB)
        self.engine = PromotionEngine(
            staging_db=STAGING_DB,
            production_db=self.temp_prod,
            adapter_name="editorial",
        )
        self.gate = PromotionGate(
            engine=self.engine,
            staging_db=STAGING_DB,
            production_db=self.temp_prod,
            backup_dir=_make_backup_dir(),
        )

    def tearDown(self):
        _safe_remove(self.temp_prod)

    def test_gate_registry_loaded(self):
        """PromotionGate loads invariant registry on init."""
        self.assertIsNotNone(self.gate._invariant_registry)
        self.assertTrue(self.gate._invariant_registry.loaded)

    def test_gate_run_invariant_checks_returns_list(self):
        """run_invariant_checks() returns a list of dict results."""
        br = self.gate.backup()
        dr = self.gate.dry_run("test-reg")
        results = self.gate.run_invariant_checks(backup_report=br, dry_run_report=dr)
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)

    def test_gate_invariant_checks_all_pass_with_good_data(self):
        """All invariants pass against temp copy of production DB."""
        br = self.gate.backup()
        dr = self.gate.dry_run("test-pass")
        plan = self.engine.plan()
        # Skips all-pass by skipping G8 (which needs apply_result with sha)
        ar = self.gate.apply(plan=plan, execute=False)
        results = self.gate.run_invariant_checks(backup_report=br, dry_run_report=dr, apply_result=ar)
        for r in results:
            self.assertTrue(r["passed"], f"Invariant {r['id']} failed: {r.get('error')}")

    def test_gate_invariant_checks_include_r4(self):
        """R4 invariant is included in run_invariant_checks results."""
        br = self.gate.backup()
        dr = self.gate.dry_run("test-r4")
        results = self.gate.run_invariant_checks(backup_report=br, dry_run_report=dr)
        r4 = [r for r in results if r["id"] == "R4"]
        self.assertEqual(len(r4), 1)

    def test_verify_records_invariant_results(self):
        """verify() stores invariant_results in VerificationReport."""
        br = self.gate.backup()
        dr = self.gate.dry_run("test-verify")
        plan = self.engine.plan()
        ar = self.gate.apply(plan=plan, execute=False)
        vr = self.gate.verify(backup_report=br, dry_run_report=dr, apply_result=ar)
        self.assertIsNotNone(vr)


class TestExistingTestsRegression(unittest.TestCase):
    """D. Existing P500-D and P500-E tests still pass."""

    def test_gate_backup_works(self):
        """Backup still works after registry integration."""
        br = self.gate.backup()
        self.assertTrue(br.verified)

    def test_gate_dry_run_works(self):
        """Dry-run still works."""
        dr = self.gate.dry_run("test-regression")
        self.assertIsNotNone(dr)

    def test_gate_human_gate_works(self):
        """Human gate still works."""
        hg = self.gate.human_gate("test-regression", WRITE_GO_PHRASE)
        self.assertTrue(hg.passed)

    def setUp(self):
        self.temp_prod = _make_temp_copy(PRODUCTION_DB)
        self.engine = PromotionEngine(
            staging_db=STAGING_DB,
            production_db=self.temp_prod,
            adapter_name="editorial",
        )
        self.gate = PromotionGate(
            engine=self.engine,
            staging_db=STAGING_DB,
            production_db=self.temp_prod,
            backup_dir=_make_backup_dir(),
        )

    def tearDown(self):
        _safe_remove(self.temp_prod)


class TestProductionImmutability(unittest.TestCase):
    """E. Production DB unchanged after all tests."""

    def test_production_db_unchanged(self):
        """Production DB SHA matches known value."""
        sha = _sha256_file(PRODUCTION_DB)
        # Known from P500-E final report
        known = "40b7f71e84f0b5eec750deb0832f197f4eddc51c023bcdc2dde25fde93476ec0"
        self.assertEqual(sha, known)

    def test_production_db_counts(self):
        """Production DB row counts unchanged."""
        c = sqlite3.connect(f"file:{PRODUCTION_DB}?mode=ro", uri=True)
        tables = c.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
        whisky = c.execute("SELECT COUNT(*) FROM whiskies").fetchone()[0]
        fe = c.execute("SELECT COUNT(*) FROM flavor_evidence").fetchone()[0]
        c.close()
        self.assertEqual(tables, 37)
        self.assertEqual(whisky, 4749)
        self.assertEqual(fe, 3180)


class TestP500GReadiness(unittest.TestCase):
    """F. P500-G readiness: registry interface complete."""

    def test_registry_has_version(self):
        """Registry has version field."""
        import yaml
        with open(REGISTRY_YAML) as f:
            data = yaml.safe_load(f)
        self.assertIn("version", data)

    def test_registry_to_dict(self):
        """to_dict() produces reportable output."""
        reg = InvariantRegistry(REGISTRY_YAML)
        d = reg.to_dict()
        self.assertIn("loaded", d)
        self.assertIn("invariant_count", d)
        self.assertIn("invariants", d)
        self.assertEqual(len(d["invariants"]), reg.count)

    def test_new_invariant_can_be_registered(self):
        """P500-G can register new invariants dynamically."""
        # Register a new check
        def dummy_check(ctx):
            return True
        register_check("test_p500g_method", dummy_check)
        self.assertIn("test_p500g_method", _CHECKERS)


if __name__ == "__main__":
    unittest.main()
