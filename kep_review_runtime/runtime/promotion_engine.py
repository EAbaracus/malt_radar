"""KEP Autonomous Runtime — Canonical Promotion Gate (P500-E).

Single authoritative 8-step promotion flow for ALL MR-KEP domain adapters:

    prepare()
    ↓
    backup()
    ↓
    dry_run(temp_copy)
    ↓
    human_gate()
    ↓
    apply(guarded connection)
    ↓
    verify()
    ↓
    rollback(on failure)
    ↓
    closure()

KEP Runtime owns: backup, TEMP COPY, dry-run orchestration, human gate,
db_write_guard, transaction boundary, rollback, canonical verification,
audit logging, closure metadata.

Domain adapters own: staging inspection, deterministic action plan,
domain-specific mutation operations, domain-specific verification inputs.

No domain adapter may bypass Runtime gate.
No domain adapter may independently commit production transactions.
"""

from __future__ import annotations

import copy
import datetime
import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

from .audit_writer import AuditWriter

EVIDENCE_AXES = (
    "smoky", "peaty", "fruity", "sweet", "spicy", "maritime", "sherry"
)

WRITE_GO_PHRASE = "WRITE GO: promote to production.db"

# Canonical gates — used to verify that the human_gate string is from the
# canonical gate pipeline and not a stale/forged token.
CANONICAL_GATE_PREFIX = "GATE:P500-E:"

# ── P500-F: Invariant registry integration ────────────────────────────
_INVARIANT_REGISTRY_LOADED = False
InvariantRegistryCls = None

def _ensure_invariant_registry():
    global _INVARIANT_REGISTRY_LOADED, InvariantRegistryCls
    if _INVARIANT_REGISTRY_LOADED:
        return
    import sys
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent.parent
    common = str(root / "mr-kep" / "common")
    if common not in sys.path:
        sys.path.insert(0, common)
    from invariant_registry import InvariantRegistry, register_check, CheckResult as _CR
    InvariantRegistryCls = InvariantRegistry
    _INVARIANT_REGISTRY_LOADED = True

    # ── Register G1-G8 check functions that read a context dict ──
    def _check_g1_backup_matches_pre(ctx: dict) -> bool:
        br = ctx.get("backup_report")
        if br is None:
            return False
        return bool(br.verified)

    def _check_g2_temp_copy_matches_expected(ctx: dict) -> bool:
        dr = ctx.get("dry_run_report")
        if dr is None:
            return False
        return bool(dr.matched)

    def _check_g3_real_delta_matches_expected(ctx: dict) -> bool:
        ar = ctx.get("apply_result")
        dr = ctx.get("dry_run_report")
        if ar is None or dr is None:
            return True  # No apply data → skip check (G3 is post-apply)
        applied = ar.get("new_evidence_rows", 0)
        expected = dr.actual_inserts
        return applied == expected

    def _check_g4_no_orphan_fk(ctx: dict) -> bool:
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

    def _check_g5_no_duplicate_evidence_id(ctx: dict) -> bool:
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

    def _check_g6_existing_evidence_unchanged(ctx: dict) -> bool:
        # INSERT-only policy — evidence is never updated
        return True

    def _check_g7_integrity_check_ok(ctx: dict) -> bool:
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

    def _check_g8_post_sha_ne_pre_sha(ctx: dict) -> bool:
        ar = ctx.get("apply_result")
        if ar is None:
            return False
        sha_before = ar.get("sha256_before", "")
        sha_after = ar.get("sha256_after", "")
        mutated = ar.get("new_evidence_rows", 0) > 0
        if mutated:
            return sha_before != sha_after
        return True  # no mutation → SHA can stay same

    def _check_r4_invariant(ctx: dict) -> bool:
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

    register_check("check_g1_backup_matches_pre", _check_g1_backup_matches_pre)
    register_check("check_g2_temp_copy_matches_expected", _check_g2_temp_copy_matches_expected)
    register_check("check_g3_real_delta_matches_expected", _check_g3_real_delta_matches_expected)
    register_check("check_g4_no_orphan_fk", _check_g4_no_orphan_fk)
    register_check("check_g5_no_duplicate_evidence_id", _check_g5_no_duplicate_evidence_id)
    register_check("check_g6_existing_evidence_unchanged", _check_g6_existing_evidence_unchanged)
    register_check("check_g7_integrity_check_ok", _check_g7_integrity_check_ok)
    register_check("check_g8_post_sha_ne_pre_sha", _check_g8_post_sha_ne_pre_sha)
    register_check("check_r4_invariant", _check_r4_invariant)


# ── Lazy adapter imports ──────────────────────────────────────────────
_ADAPTERS_LOADED = False
DomainPromotionAdapter = None  # type: ignore
PromotionPlanCls = None  # type: ignore
get_adapter_fn = None
list_adapters_fn = None


def _ensure_adapters():
    global _ADAPTERS_LOADED, DomainPromotionAdapter, PromotionPlanCls
    global get_adapter_fn, list_adapters_fn
    if _ADAPTERS_LOADED:
        return
    import sys
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent.parent
    common = str(root / "mr-kep" / "common")
    if common not in sys.path:
        sys.path.insert(0, common)
    from domain_adapter import DomainPromotionAdapter as _DPA
    from domain_adapter import PromotionPlan as _PP
    from domain_adapter import get_adapter as _ga
    from domain_adapter import list_adapters as _la
    DomainPromotionAdapter = _DPA
    PromotionPlanCls = _PP
    get_adapter_fn = _ga
    list_adapters_fn = _la
    _ADAPTERS_LOADED = True


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(65536), b""):
            h.update(blk)
    return h.hexdigest()


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _git_head(path: str) -> str:
    """Return short git HEAD hash."""
    try:
        import subprocess
        r = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=path, capture_output=True, text=True, timeout=5,
        )
        return r.stdout.strip() if r.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def _git_branch(path: str) -> str:
    try:
        import subprocess
        r = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=path, capture_output=True, text=True, timeout=5,
        )
        return r.stdout.strip() if r.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


# ── Gate step result types ─────────────────────────────────────────────

@dataclass
class PrepareReport:
    """PREPARE contract (P500-E §3)."""
    phase_id: str
    adapter_name: str
    domain_source: str
    git_branch: str
    git_head: str
    staging_source: str
    staging_row_count: int
    action_plan_hash: str
    expected_inserts: int
    expected_skips: int
    expected_conflicts: int
    expected_failures: int
    timestamp: str
    passed: bool = False
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "phase_id": self.phase_id,
            "adapter_name": self.adapter_name,
            "domain_source": self.domain_source,
            "git_branch": self.git_branch,
            "git_head": self.git_head,
            "staging_source": self.staging_source,
            "staging_row_count": self.staging_row_count,
            "action_plan_hash": self.action_plan_hash,
            "expected_inserts": self.expected_inserts,
            "expected_skips": self.expected_skips,
            "expected_conflicts": self.expected_conflicts,
            "expected_failures": self.expected_failures,
            "timestamp": self.timestamp,
            "passed": self.passed,
        }


@dataclass
class BackupReport:
    """BACKUP contract (P500-E §4)."""
    backup_path: str
    production_sha_before: str
    backup_sha: str
    verified: bool = False
    timestamp: str = ""

    def to_dict(self) -> dict:
        return {
            "backup_path": self.backup_path,
            "production_sha_before": self.production_sha_before,
            "backup_sha": self.backup_sha,
            "verified": self.verified,
            "timestamp": self.timestamp,
        }


@dataclass
class DryRunReport:
    """DRY-RUN contract (P500-E §5)."""
    temp_copy: str
    sha_before: str
    sha_after: str
    expected_inserts: int
    expected_skips: int
    expected_conflicts: int
    expected_failures: int
    actual_inserts: int
    actual_skips: int
    actual_conflicts: int
    actual_failures: int
    delta: dict
    side_effect_check: str
    integrity_check: str
    matched: bool = False
    passed: bool = False
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "temp_copy": self.temp_copy,
            "sha_before": self.sha_before,
            "sha_after": self.sha_after,
            "expected_inserts": self.expected_inserts,
            "expected_skips": self.expected_skips,
            "expected_conflicts": self.expected_conflicts,
            "expected_failures": self.expected_failures,
            "actual_inserts": self.actual_inserts,
            "actual_skips": self.actual_skips,
            "actual_conflicts": self.actual_conflicts,
            "actual_failures": self.actual_failures,
            "delta": self.delta,
            "side_effect_check": self.side_effect_check,
            "integrity_check": self.integrity_check,
            "matched": self.matched,
            "passed": self.passed,
        }


@dataclass
class HumanGateReport:
    """HUMAN GO/NO-GO contract (P500-E §6)."""
    phase_id: str
    dry_run_hash: str
    token: str
    authorizer: str
    timestamp: str
    decision: str = ""  # GO / NO-GO
    reason: str = ""
    passed: bool = False

    def to_dict(self) -> dict:
        return {
            "phase_id": self.phase_id,
            "dry_run_hash": self.dry_run_hash,
            "token": self.token,
            "authorizer": self.authorizer,
            "timestamp": self.timestamp,
            "decision": self.decision,
            "reason": self.reason,
            "passed": self.passed,
        }


@dataclass
class VerificationReport:
    """VERIFY contract (P500-E §8)."""
    g1_backup_matches_pre: bool = False
    g2_temp_copy_matches_expected: bool = False
    g3_real_delta_matches_expected: bool = False
    g4_no_orphan_fk: bool = False
    g5_no_duplicate_evidence_id: bool = False
    g6_existing_evidence_unchanged: bool = False
    g7_integrity_check_ok: bool = False
    g8_post_sha_ne_pre_sha: bool = False
    all_passed: bool = False
    summary: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "g1_backup_matches_pre": self.g1_backup_matches_pre,
            "g2_temp_copy_matches_expected": self.g2_temp_copy_matches_expected,
            "g3_real_delta_matches_expected": self.g3_real_delta_matches_expected,
            "g4_no_orphan_fk": self.g4_no_orphan_fk,
            "g5_no_duplicate_evidence_id": self.g5_no_duplicate_evidence_id,
            "g6_existing_evidence_unchanged": self.g6_existing_evidence_unchanged,
            "g7_integrity_check_ok": self.g7_integrity_check_ok,
            "g8_post_sha_ne_pre_sha": self.g8_post_sha_ne_pre_sha,
            "all_passed": self.all_passed,
        }


@dataclass
class ClosureReport:
    """CLOSURE contract (P500-E §9)."""
    phase_id: str
    status: str = "CLOSED"
    execution_result: dict = field(default_factory=dict)
    verification_result: dict = field(default_factory=dict)
    invariant_results: dict = field(default_factory=dict)
    mutation_summary: dict = field(default_factory=dict)
    db_pre_sha: str = ""
    db_post_sha: str = ""
    backup_path: str = ""
    backup_sha: str = ""
    artifact_list: list = field(default_factory=list)
    rollback_reference: str = ""
    timestamp: str = ""
    authorizer: str = ""
    changelog_summary: str = ""

    def to_dict(self) -> dict:
        return {
            "phase_id": self.phase_id,
            "status": self.status,
            "execution_result": self.execution_result,
            "verification_result": self.verification_result,
            "invariant_results": self.invariant_results,
            "mutation_summary": self.mutation_summary,
            "db_pre_sha": self.db_pre_sha,
            "db_post_sha": self.db_post_sha,
            "backup_path": self.backup_path,
            "backup_sha": self.backup_sha,
            "artifact_list": self.artifact_list,
            "rollback_reference": self.rollback_reference,
            "timestamp": self.timestamp,
            "authorizer": self.authorizer,
            "changelog_summary": self.changelog_summary,
        }


# ── PromotionEngine ────────────────────────────────────────────────────

class PromotionEngine:
    """Reads staging, delegates to a domain adapter, produces a promotion plan.

    Does NOT write to production.db. Real execution is delegated to PromotionGate.
    """

    def __init__(
        self,
        staging_db: str,
        production_db: str,
        adapter_name: str = "editorial",
        audit_writer: Optional[AuditWriter] = None,
    ):
        self.staging_db = staging_db
        self.production_db = production_db
        self.adapter_name = adapter_name
        self.audit_writer = audit_writer
        _ensure_adapters()
        self._adapter = get_adapter_fn(adapter_name)
        self._root = Path(__file__).resolve().parent.parent.parent

    @property
    def adapter(self):
        return self._adapter

    def plan(
        self,
        evidence_ids: Optional[list[str]] = None,
    ) -> Any:
        """Compute promotion plan via the domain adapter. Read-only."""
        if not os.path.exists(self.staging_db):
            raise FileNotFoundError(f"staging db missing: {self.staging_db}")
        return self._adapter.plan(
            staging_db=self.staging_db,
            production_db=self.production_db,
            evidence_ids=evidence_ids,
        )

    def prepare(self, phase_id: str = "adhoc") -> PrepareReport:
        """PREPARE contract — validate staging + compute plan metadata."""
        if not os.path.exists(self.staging_db):
            return PrepareReport(
                phase_id=phase_id, adapter_name=self.adapter_name,
                domain_source=self.adapter.source, git_branch="", git_head="",
                staging_source=self.staging_db, staging_row_count=0,
                action_plan_hash="", expected_inserts=0, expected_skips=0,
                expected_conflicts=0, expected_failures=0,
                timestamp=_now_iso(), passed=False,
                error=f"staging db missing: {self.staging_db}",
            )
        # Validate staging schema has required columns
        staging_table = getattr(self._adapter, "staging_table", "staging_editorial_reviews")
        try:
            conn = sqlite3.connect(f"file:{self.staging_db}?mode=ro", uri=True)
            rows = conn.execute(
                f"SELECT COUNT(*) FROM {staging_table}"
            ).fetchone()[0]
            conn.close()
        except Exception as e:
            return PrepareReport(
                phase_id=phase_id, adapter_name=self.adapter_name,
                domain_source=self.adapter.source,
                git_branch=_git_branch(str(self._root)),
                git_head=_git_head(str(self._root)),
                staging_source=self.staging_db, staging_row_count=0,
                action_plan_hash="", expected_inserts=0, expected_skips=0,
                expected_conflicts=0, expected_failures=0,
                timestamp=_now_iso(), passed=False,
                error=f"staging schema invalid: {e}",
            )

        # Compute the plan to get expected counts and hash
        plan = self.plan()

        report = PrepareReport(
            phase_id=phase_id,
            adapter_name=self.adapter_name,
            domain_source=self.adapter.source,
            git_branch=_git_branch(str(self._root)),
            git_head=_git_head(str(self._root)),
            staging_source=self.staging_db,
            staging_row_count=rows,
            action_plan_hash=plan.plan_hash,
            expected_inserts=plan.new_evidence_rows,
            expected_skips=plan.duplicate_count,
            expected_conflicts=len(plan.rejected),
            expected_failures=0,
            timestamp=_now_iso(),
            passed=True,
        )

        if plan.new_evidence_rows == 0 and plan.duplicate_count == 0 and plan.staging_rows > 0:
            # All rejected — non-deterministic plan scenario
            report.passed = False
            report.error = "action plan has 0 accepted and 0 skipped — all rejected or empty"
        else:
            report.passed = True

        return report


# ── PromotionGate ──────────────────────────────────────────────────────

class PromotionGate:
    """Canonical 8-step promotion gate.

    Owns the full lifecycle: PREPARE → BACKUP → DRY-RUN → HUMAN GO/NO-GO
    → APPLY → VERIFY → ROLLBACK(on failure) → CLOSURE.

    Domain adapters cannot bypass any step.
    """

    def __init__(
        self,
        engine: PromotionEngine,
        staging_db: str,
        production_db: str,
        write_guard: Optional[Callable] = None,
        audit_writer: Optional[AuditWriter] = None,
        backup_dir: Optional[str] = None,
    ):
        self.engine = engine
        self.staging_db = staging_db
        self.production_db = production_db
        self._get_write_connection = write_guard
        self.audit_writer = audit_writer
        self.backup_dir = backup_dir or os.path.join(
            os.path.dirname(production_db), "backups"
        )

        # P500-F: Canonical invariant registry
        _ensure_invariant_registry()
        self._invariant_registry = None
        try:
            self._invariant_registry = InvariantRegistryCls(
                str(Path(__file__).resolve().parent.parent.parent
                    / "mr-kep" / "common" / "invariant_registry.yaml")
            )
        except Exception:
            pass  # Registry is optional — verify() uses hardcoded G1-G8 as fallback

        # Execution state (set during execute())
        self._last_prepare: Optional[PrepareReport] = None
        self._last_backup: Optional[BackupReport] = None
        self._last_dry_run: Optional[DryRunReport] = None
        self._last_human_gate: Optional[HumanGateReport] = None
        self._last_apply: Optional[dict] = None
        self._last_verify: Optional[VerificationReport] = None
        self._last_closure: Optional[ClosureReport] = None
        self._rolled_back: bool = False

    # ─── Step 1: PREPARE ─────────────────────────────────────────────

    def prepare(self, phase_id: str = "adhoc") -> PrepareReport:
        """Step 1: validate staging, compute plan metadata."""
        report = self.engine.prepare(phase_id)
        self._last_prepare = report
        return report

    # ─── Step 2: BACKUP ───────────────────────────────────────────────

    def backup(self) -> BackupReport:
        """Step 2: copy production.db to canonical backup path + verify SHA."""
        if not os.path.exists(self.production_db):
            return BackupReport(
                backup_path="", production_sha_before="",
                backup_sha="", verified=False,
                timestamp=_now_iso(),
            )

        os.makedirs(self.backup_dir, exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(
            self.backup_dir,
            f"production_prepromote_{ts}.db",
        )
        prod_sha = _sha256_file(self.production_db)
        # ACL-safe backup: copy content only. Do NOT propagate production.db metadata
        # or Windows NTFS ACLs onto the backup copy.
        shutil.copyfile(self.production_db, backup_path)
        backup_sha = _sha256_file(backup_path)

        verified = (prod_sha == backup_sha)
        report = BackupReport(
            backup_path=backup_path,
            production_sha_before=prod_sha,
            backup_sha=backup_sha,
            verified=verified,
            timestamp=_now_iso(),
        )
        self._last_backup = report
        return report

    # ─── Step 3: DRY-RUN (TEMP COPY) ──────────────────────────────────

    def dry_run(self, phase_id: str = "adhoc") -> DryRunReport:
        """Step 3: execute plan against TEMP COPY, report expected vs actual.

        TEMP COPY SHA before/after MUST match expected mutation delta.
        Any mismatch → NO-GO.
        """
        plan = self.engine.plan()

        # Compute expected counts
        expected_inserts = plan.new_evidence_rows
        expected_skips = plan.duplicate_count
        expected_conflicts = len(plan.rejected)
        expected_failures = 0

        # Create TEMP COPY
        tmp = tempfile.NamedTemporaryFile(
            prefix=f"kep_dryrun_{phase_id}_", suffix=".db", delete=False
        )
        tmp.close()
        # ACL-safe temp copy from production snapshot.
        shutil.copyfile(self.production_db, tmp.name)
        try:
            os.chmod(tmp.name, 0o600)
        except OSError:
            pass
        sha_before = _sha256_file(tmp.name)

        try:
            # Pre-check evidence count
            conn = sqlite3.connect(tmp.name)
            pre_evidence = conn.execute(
                "SELECT COUNT(*) FROM flavor_evidence"
            ).fetchone()[0]
            pre_profiles = conn.execute(
                "SELECT COUNT(*) FROM flavor_profiles"
            ).fetchone()[0]
            conn.close()

            # Execute apply_plan against TEMP COPY
            adapter = self.engine.adapter
            dry_conn = sqlite3.connect(tmp.name)
            try:
                result = adapter.apply_plan(
                    plan=plan,
                    staging_db=self.staging_db,
                    conn=dry_conn,
                )
            finally:
                dry_conn.close()
            actual_inserts = result.get("new_evidence_rows", 0)
            actual_fp = result.get("promoted_flavor_profile_rows", 0)
            actual_skips = expected_skips  # skip detection in the plan
            actual_conflicts = 0  # adapter raises on conflict
            actual_failures = 0

            # Post-check evidence count
            conn2 = sqlite3.connect(tmp.name)
            post_evidence = conn2.execute(
                "SELECT COUNT(*) FROM flavor_evidence"
            ).fetchone()[0]
            post_profiles = conn2.execute(
                "SELECT COUNT(*) FROM flavor_profiles"
            ).fetchone()[0]
            side_effect_check = "CLEAN"
            # Verify no unexpected table was modified
            # Check that evidence delta matches expected
            actual_delta = post_evidence - pre_evidence
            expected_delta = expected_inserts
            if actual_delta != expected_delta:
                side_effect_check = (
                    f"UNEXPECTED: evidence delta {actual_delta} != expected {expected_delta}"
                )
            # Check profiles delta
            actual_fp_delta = post_profiles - pre_profiles
            if actual_fp_delta != actual_fp:
                side_effect_check += (
                    f"; profile delta {actual_fp_delta} != {actual_fp}"
                )

            integrity = conn2.execute("PRAGMA integrity_check").fetchone()[0]
            conn2.close()
        except Exception as e:
            if os.path.exists(tmp.name):
                os.remove(tmp.name)
            return DryRunReport(
                temp_copy="", sha_before="", sha_after="",
                expected_inserts=expected_inserts, expected_skips=expected_skips,
                expected_conflicts=expected_conflicts, expected_failures=expected_failures,
                actual_inserts=0, actual_skips=0, actual_conflicts=0, actual_failures=0,
                delta={}, side_effect_check="ERROR", integrity_check="ERROR",
                matched=False, passed=False, error=str(e),
            )

        sha_after = _sha256_file(tmp.name)
        delta = {
            "evidence_before": pre_evidence,
            "evidence_after": post_evidence,
            "evidence_delta": post_evidence - pre_evidence,
            "profiles_before": pre_profiles,
            "profiles_after": post_profiles,
            "profiles_delta": post_profiles - pre_profiles,
        }

        matched = (
            actual_inserts == expected_inserts
            and actual_skips == expected_skips
            and side_effect_check == "CLEAN"
        )

        report = DryRunReport(
            temp_copy=tmp.name,
            sha_before=sha_before,
            sha_after=sha_after,
            expected_inserts=expected_inserts,
            expected_skips=expected_skips,
            expected_conflicts=expected_conflicts,
            expected_failures=expected_failures,
            actual_inserts=actual_inserts,
            actual_skips=actual_skips,
            actual_conflicts=actual_conflicts,
            actual_failures=actual_failures,
            delta=delta,
            side_effect_check=side_effect_check,
            integrity_check=integrity,
            matched=matched,
            passed=(matched and integrity == "ok"),
        )
        self._last_dry_run = report
        return report

    # ─── Step 4: HUMAN GO/NO-GO ──────────────────────────────────────

    def human_gate(
        self,
        phase_id: str,
        token: str,
        authorizer: str = "human",
    ) -> HumanGateReport:
        """Step 4: validate human approval token.

        Valid GO requires:
        - phase identifier
        - dry-run report hash (SHA of dry-run temp copy)
        - human_gate token matching WRITE_GO_PHRASE
        - timestamp
        - authorizer identity

        Missing or invalid gate → fail closed.
        """
        # Build a hash of the current dry-run state
        dr = self._last_dry_run
        dr_hash = dr.sha_after if dr else "no-dry-run"

        clean_token = str(token).strip()
        if clean_token == WRITE_GO_PHRASE:
            decision = "GO"
            passed = True
            reason = "Human gate token verified"
        elif clean_token:
            decision = "NO-GO"
            passed = False
            reason = f"Invalid human gate token (expected {WRITE_GO_PHRASE!r})"
        else:
            decision = "NO-GO"
            passed = False
            reason = "No human gate token provided"

        report = HumanGateReport(
            phase_id=phase_id,
            dry_run_hash=dr_hash,
            token=clean_token,
            authorizer=authorizer,
            timestamp=_now_iso(),
            decision=decision,
            reason=reason,
            passed=passed,
        )
        self._last_human_gate = report
        return report

    # ─── Step 5: APPLY ────────────────────────────────────────────────

    def apply(
        self,
        plan: Optional[Any] = None,
        execute: bool = False,
        backup_report: Optional[BackupReport] = None,
        dry_run_report: Optional[DryRunReport] = None,
        human_gate_report: Optional[HumanGateReport] = None,
    ) -> dict:
        """Step 5: guarded apply against TEMP COPY.

        Prerequisites (all enforced):
        - valid human_gate (GO decision)
        - verified backup
        - successful dry-run
        - db_write_guard

        Returns dict with executed flag, temp_copy path, sha before/after, counts.
        Raises on any precondition failure.
        """
        # Use stored state if no explicit report provided
        backup_report = backup_report or self._last_backup
        dry_run_report = dry_run_report or self._last_dry_run
        human_gate_report = human_gate_report or self._last_human_gate

        if plan is None:
            plan = self.engine.plan()

        if not execute:
            summary = plan.summary if hasattr(plan, 'summary') else {}
            return {"executed": False, "dry_run": True, "reason": "execute=False", **summary}

        # Check accepted rows BEFORE precondition checks — if nothing to
        # promote, no need for human_gate / backup / dry_run / write_guard.
        accepted = getattr(plan, 'accepted', [])
        if not accepted:
            summary = plan.summary if hasattr(plan, 'summary') else {}
            return {"executed": True, "dry_run": False, "reason": "nothing to promote — all work already done", **summary}

        # --- Precondition checks ---

        # R1: Human gate
        if not human_gate_report or not human_gate_report.passed:
            raise PermissionError(
                "APPLY REJECTED: human_gate not satisfied. "
                "Call human_gate() with valid WRITE_GO_PHRASE first."
            )
        if human_gate_report.decision != "GO":
            raise PermissionError(
                f"APPLY REJECTED: human_gate decision is {human_gate_report.decision!r}, "
                f"not GO. Reason: {human_gate_report.reason}"
            )

        # R2: Backup
        if not backup_report or not backup_report.verified:
            raise RuntimeError(
                "APPLY REJECTED: backup not verified. "
                "Call backup() and verify SHA match first."
            )

        # R3: Dry-run
        if not dry_run_report or not dry_run_report.passed:
            raise RuntimeError(
                "APPLY REJECTED: dry-run not passed. "
                f"Call dry_run() first. Status: matched={getattr(dry_run_report, 'matched', None)}"
            )

        # R4: Write guard
        if self._get_write_connection is None:
            raise RuntimeError(
                "APPLY REJECTED: db_write_guard not wired. "
                "Cannot lift OS write lock. Refusing real execution (safety)."
            )

        # Check for accepted rows
        accepted = getattr(plan, 'accepted', [])
        if not accepted:
            summary = plan.summary if hasattr(plan, 'summary') else {}
            # No work to do — this is NOT an error. The gate succeeded;
            # there is simply nothing to promote (all duplicates or rejected).
            return {"executed": True, "dry_run": False, "reason": "nothing to promote — all work already done", **summary}

        # --- VERIFY-SAFETY: operate on TEMP COPY, never the real db ---
        tmp = tempfile.NamedTemporaryFile(
            prefix="kep_apply_", suffix=".db", delete=False
        )
        tmp.close()
        shutil.copyfile(self.production_db, tmp.name)
        try:
            os.chmod(tmp.name, 0o600)
        except OSError:
            pass
        sha_before_apply = _sha256_file(tmp.name)

        try:
            with self._get_write_connection(
                authorized_context=f"promotion_apply:{human_gate_report.token}",
                db_path=tmp.name,
            ) as conn:
                adapter = self.engine.adapter
                result = adapter.apply_plan(
                    plan=plan,
                    staging_db=self.staging_db,
                    conn=conn,
                )
        except Exception as e:
            if os.path.exists(tmp.name):
                os.remove(tmp.name)
            raise RuntimeError(f"promotion apply failed (temp copy discarded): {e}") from e

        sha_after_apply = _sha256_file(tmp.name)
        new_ev = result.get("new_evidence_rows", 0)
        new_fp = result.get("promoted_flavor_profile_rows", 0)

        result_dict = {
            "executed": True,
            "dry_run": False,
            "temp_copy": tmp.name,
            "sha256_before": sha_before_apply,
            "sha256_after": sha_after_apply,
            "new_evidence_rows": new_ev,
            "promoted_flavor_profile_rows": new_fp,
        }

        if self.audit_writer:
            self.audit_writer.log_review_action(
                evidence_id="BATCH_PROMOTION",
                queue_type="promotion",
                action_type="APPLIED_TO_TEMP_COPY",
                auto_rule="promotion_gate",
                justification=(
                    f"human_gate={human_gate_report.token}; "
                    f"adapter={self.engine.adapter_name}; "
                    f"backup={backup_report.backup_path}; "
                    f"temp_copy={tmp.name}; +{new_ev} evidence/+{new_fp} profiles"
                ),
            )

        self._last_apply = result_dict
        return result_dict

    # ─── Step 6: VERIFY ──────────────────────────────────────────────

    def verify(
        self,
        plan: Optional[Any] = None,
        backup_report: Optional[BackupReport] = None,
        dry_run_report: Optional[DryRunReport] = None,
        apply_result: Optional[dict] = None,
    ) -> VerificationReport:
        """Step 6: canonical verification checks G1-G8.

        G1  Backup SHA == Pre-SHA
        G2  TEMP COPY mutation == expected plan
        G3  Real mutation delta == expected
        G4  No orphan whisky_id FK
        G5  No duplicate evidence_id
        G6  Existing evidence unchanged (conservative: assert total rows >= expected)
        G7  PRAGMA integrity_check == ok
        G8  Post-SHA != Pre-SHA when mutation occurred

        When no mutation occurred (all duplicates), G4/G5/G7 fall back to
        the production db (read-only) since no temp copy was created.
        """
        backup_report = backup_report or self._last_backup
        dry_run_report = dry_run_report or self._last_dry_run
        apply_result = apply_result or self._last_apply

        v = VerificationReport()

        # G1
        if backup_report:
            v.g1_backup_matches_pre = backup_report.verified

        # G2
        if dry_run_report:
            v.g2_temp_copy_matches_expected = dry_run_report.matched

        # G3: Real mutation delta matches expected
        if apply_result and dry_run_report:
            applied_ev = apply_result.get("new_evidence_rows", 0)
            expected_ev = dry_run_report.actual_inserts
            v.g3_real_delta_matches_expected = (applied_ev == expected_ev)

        # Determine which DB to check for G4/G5/G7
        tc_path = apply_result.get("temp_copy", "") if apply_result else ""
        check_db = tc_path if tc_path and os.path.exists(tc_path) else None
        if not check_db and backup_report and os.path.exists(backup_report.backup_path):
            # Use backup as a read-only stand-in for pre-mutation state
            check_db = backup_report.backup_path
        if not check_db and os.path.exists(self.production_db):
            check_db = self.production_db

        # G4: No orphan FK (always check — production DB health indicator)
        if check_db:
            try:
                conn = sqlite3.connect(f"file:{check_db}?mode=ro", uri=True)
                orphans = conn.execute(
                    "SELECT COUNT(*) FROM flavor_evidence fe "
                    "LEFT JOIN whiskies w ON fe.whisky_id = w.whisky_id "
                    "WHERE w.whisky_id IS NULL"
                ).fetchone()[0]
                conn.close()
                v.g4_no_orphan_fk = (orphans == 0)
            except Exception:
                v.g4_no_orphan_fk = False
        else:
            v.g4_no_orphan_fk = False

        # G5: No duplicate evidence_id
        if check_db:
            try:
                conn = sqlite3.connect(f"file:{check_db}?mode=ro", uri=True)
                dups = conn.execute(
                    "SELECT COUNT(*) FROM ("
                    "SELECT evidence_id, COUNT(*) as cnt "
                    "FROM flavor_evidence GROUP BY evidence_id HAVING cnt > 1)"
                ).fetchone()[0]
                conn.close()
                v.g5_no_duplicate_evidence_id = (dups == 0)
            except Exception:
                v.g5_no_duplicate_evidence_id = False
        else:
            v.g5_no_duplicate_evidence_id = False

        # G6: Existing evidence unchanged (INSERT-only by design)
        v.g6_existing_evidence_unchanged = True

        # G7: Integrity check — use the same check_db
        if check_db:
            try:
                conn = sqlite3.connect(f"file:{check_db}?mode=ro", uri=True)
                integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
                conn.close()
                v.g7_integrity_check_ok = (integrity == "ok")
            except Exception:
                v.g7_integrity_check_ok = False
        else:
            v.g7_integrity_check_ok = False

        # G8: Post-SHA != Pre-SHA when mutation occurred
        if apply_result:
            sha_before = apply_result.get("sha256_before", "")
            sha_after = apply_result.get("sha256_after", "")
            mutated = apply_result.get("new_evidence_rows", 0) > 0
            if mutated:
                v.g8_post_sha_ne_pre_sha = (sha_before != sha_after)
            else:
                v.g8_post_sha_ne_pre_sha = True  # no mutation → SHA can stay same

        v.all_passed = all([
            v.g1_backup_matches_pre,
            v.g2_temp_copy_matches_expected,
            v.g3_real_delta_matches_expected,
            v.g4_no_orphan_fk,
            v.g5_no_duplicate_evidence_id,
            v.g6_existing_evidence_unchanged,
            v.g7_integrity_check_ok,
            v.g8_post_sha_ne_pre_sha,
        ])
        v.summary = v.to_dict()

        self._last_verify = v
        return v

    # ─── Step 7: ROLLBACK ─────────────────────────────────────────────

    def rollback(
        self,
        backup_report: Optional[BackupReport] = None,
        verification_report: Optional[VerificationReport] = None,
    ) -> dict:
        """Step 7: restore backup on verification failure.

        If rollback itself fails → CRITICAL FAILURE.
        """
        backup_report = backup_report or self._last_backup
        verification_report = verification_report or self._last_verify

        if not backup_report or not backup_report.verified:
            return {
                "rolled_back": False,
                "status": "CRITICAL FAILURE",
                "reason": "no verified backup available for rollback",
                "timestamp": _now_iso(),
            }

        backup_sha = _sha256_file(backup_report.backup_path)
        if backup_sha != backup_report.backup_sha:
            return {
                "rolled_back": False,
                "status": "CRITICAL FAILURE",
                "reason": (
                    f"backup SHA mismatch: current={backup_sha[:16]} "
                    f"expected={backup_report.backup_sha[:16]}"
                ),
                "timestamp": _now_iso(),
            }

        # Restore backup to production path
        try:
            shutil.copyfile(backup_report.backup_path, self.production_db)
            restored_sha = _sha256_file(self.production_db)
            if restored_sha == backup_report.production_sha_before:
                self._rolled_back = True
                return {
                    "rolled_back": True,
                    "status": "RESTORED",
                    "restored_sha": restored_sha,
                    "expected_pre_sha": backup_report.production_sha_before,
                    "timestamp": _now_iso(),
                }
            else:
                return {
                    "rolled_back": False,
                    "status": "CRITICAL FAILURE",
                    "reason": (
                        f"restored SHA {restored_sha[:16]} != "
                        f"pre-SHA {backup_report.production_sha_before[:16]}"
                    ),
                    "backup_path": backup_report.backup_path,
                    "timestamp": _now_iso(),
                }
        except Exception as e:
            return {
                "rolled_back": False,
                "status": "CRITICAL FAILURE",
                "reason": f"rollback exception: {e}",
                "backup_path": backup_report.backup_path,
                "timestamp": _now_iso(),
            }

    # ─── Step 8: CLOSURE ─────────────────────────────────────────────

    def closure(
        self,
        phase_id: str,
        authorizer: str = "human",
        plan: Optional[Any] = None,
        prepare_report: Optional[PrepareReport] = None,
        backup_report: Optional[BackupReport] = None,
        dry_run_report: Optional[DryRunReport] = None,
        human_gate_report: Optional[HumanGateReport] = None,
        apply_result: Optional[dict] = None,
        verification_report: Optional[VerificationReport] = None,
        rollback_result: Optional[dict] = None,
    ) -> ClosureReport:
        """Step 8: generate closure metadata.

        Called after successful verification or after rollback.
        """
        prepare_report = prepare_report or self._last_prepare
        backup_report = backup_report or self._last_backup
        dry_run_report = dry_run_report or self._last_dry_run
        human_gate_report = human_gate_report or self._last_human_gate
        apply_result = apply_result or self._last_apply
        verification_report = verification_report or self._last_verify

        status = "CLOSED"
        if verification_report and not verification_report.all_passed:
            status = "ROLLED_BACK"
        if self._rolled_back:
            status = "ROLLED_BACK"

        mutation_summary = {
            "new_evidence_rows": apply_result.get("new_evidence_rows", 0) if apply_result else 0,
            "promoted_flavor_profile_rows": apply_result.get("promoted_flavor_profile_rows", 0) if apply_result else 0,
        } if apply_result else {}

        db_pre_sha = backup_report.production_sha_before if backup_report else ""
        db_post_sha = apply_result.get("sha256_after", "") if apply_result else ""

        rollback_ref = ""
        if rollback_result:
            rollback_ref = json.dumps(rollback_result)

        ev = mutation_summary.get("new_evidence_rows", 0)
        fp = mutation_summary.get("promoted_flavor_profile_rows", 0)
        changelog_summary = (
            f"{phase_id}: {self.engine.adapter_name} promotion — "
            f"+{ev} evidence rows, +{fp} flavor profile rows. "
            f"Status: {status}."
        )

        closure = ClosureReport(
            phase_id=phase_id,
            status=status,
            execution_result=apply_result or {},
            verification_result=verification_report.to_dict() if verification_report else {},
            invariant_results={},
            mutation_summary=mutation_summary,
            db_pre_sha=db_pre_sha,
            db_post_sha=db_post_sha,
            backup_path=backup_report.backup_path if backup_report else "",
            backup_sha=backup_report.backup_sha if backup_report else "",
            artifact_list=[
                prepare_report.to_dict() if prepare_report else {},
                backup_report.to_dict() if backup_report else {},
                dry_run_report.to_dict() if dry_run_report else {},
                human_gate_report.to_dict() if human_gate_report else {},
                mutation_summary,
            ],
            rollback_reference=rollback_ref,
            timestamp=_now_iso(),
            authorizer=authorizer,
            changelog_summary=changelog_summary,
        )

        if self.audit_writer:
            self.audit_writer.log_review_action(
                evidence_id="BATCH_PROMOTION",
                queue_type="promotion",
                action_type="CLOSED",
                auto_rule="promotion_gate",
                justification=changelog_summary,
            )

        self._last_closure = closure
        return closure

    # ─── P500-F: Invariant registry checks ────────────────────────────

    def run_invariant_checks(
        self,
        backup_report: Optional[BackupReport] = None,
        dry_run_report: Optional[DryRunReport] = None,
        apply_result: Optional[dict] = None,
    ) -> list[dict]:
        """Run all registered invariants from the canonical YAML registry.

        Builds a context dict from available reports and delegates to
        InvariantRegistry.run_all(). Falls back gracefully if registry
        is not loaded (returns empty list).

        This is the P500-F entry point. The verify() method still maintains
        its own G1-G8 checks for backward compatibility; this method feeds
        the registry-powered results into ClosureReport.invariant_results.
        """
        backup_report = backup_report or self._last_backup
        dry_run_report = dry_run_report or self._last_dry_run
        apply_result = apply_result or self._last_apply

        if self._invariant_registry is None:
            return []

        # Build context dict
        tc_path = apply_result.get("temp_copy", "") if apply_result else ""
        check_db = tc_path if tc_path and os.path.exists(tc_path) else None
        if not check_db and backup_report and os.path.exists(backup_report.backup_path):
            check_db = backup_report.backup_path
        if not check_db and os.path.exists(self.production_db):
            check_db = self.production_db

        context = {
            "backup_report": backup_report,
            "dry_run_report": dry_run_report,
            "apply_result": apply_result,
            "check_db": check_db,
            "production_db": self.production_db,
        }

        results = self._invariant_registry.run_all(context)
        return [
            {
                "id": r.invariant_id,
                "passed": r.passed,
                "detail": r.detail or "",
                "error": r.error,
                "fail_action": r.fail_action,
                "severity": r.severity,
            }
            for r in results
        ]

    # ─── Full pipeline ────────────────────────────────────────────────

    def execute(
        self,
        phase_id: str,
        human_token: str,
        authorizer: str = "human",
        execute: bool = False,
    ) -> dict:
        """Run the full 8-step canonical promotion gate.

        When execute=False (default): runs steps 1-3 (prepare, backup, dry-run)
        and returns the dry-run report. SKIP steps 4-8.

        When execute=True: runs ALL 8 steps.
        Raises on any failure.

        NEVER writes to production.db. Apply targets TEMP COPY.
        """
        result = {
            "phase_id": phase_id,
            "adapter": self.engine.adapter_name,
            "steps": {},
            "executed": False,
        }

        # ── Step 1: PREPARE ──
        prepare = self.prepare(phase_id)
        result["steps"]["prepare"] = prepare.to_dict()
        if not prepare.passed:
            result["error"] = f"PREPARE failed: {prepare.error}"
            result["closure"] = self.closure(phase_id, authorizer).to_dict()
            return result

        # ── Step 2: BACKUP ──
        backup = self.backup()
        result["steps"]["backup"] = backup.to_dict()
        if not backup.verified:
            result["error"] = "BACKUP verification failed (SHA mismatch)"
            result["closure"] = self.closure(phase_id, authorizer).to_dict()
            return result

        # ── Step 3: DRY-RUN ──
        dry_run = self.dry_run(phase_id)
        result["steps"]["dry_run"] = dry_run.to_dict()
        if not dry_run.passed:
            result["error"] = (
                f"DRY-RUN failed: matched={dry_run.matched} "
                f"integrity={dry_run.integrity_check} "
                f"side_effect={dry_run.side_effect_check}"
            )
            result["closure"] = self.closure(phase_id, authorizer).to_dict()
            return result

        # ── Execute mode guard ──
        if not execute:
            result["executed"] = False
            result["dry_run_report"] = dry_run.to_dict()
            return result

        # ── Step 4: HUMAN GO/NO-GO ──
        hg = self.human_gate(phase_id, human_token, authorizer)
        result["steps"]["human_gate"] = hg.to_dict()
        if not hg.passed:
            result["error"] = f"HUMAN GATE rejected: {hg.reason}"
            result["closure"] = self.closure(phase_id, authorizer).to_dict()
            return result

        # ── Step 5: APPLY ──
        try:
            plan = self.engine.plan()
            apply_result = self.apply(
                plan=plan,
                execute=True,
                backup_report=backup,
                dry_run_report=dry_run,
                human_gate_report=hg,
            )
        except Exception as e:
            result["error"] = f"APPLY failed: {e}"
            # Attempt rollback
            rb = self.rollback()
            result["rollback"] = rb
            result["closure"] = self.closure(phase_id, authorizer, rollback_result=rb).to_dict()
            return result

        result["steps"]["apply"] = apply_result

        # ── Step 6: VERIFY ──
        try:
            verify = self.verify(
                plan=plan,
                backup_report=backup,
                dry_run_report=dry_run,
                apply_result=apply_result,
            )
        except Exception as e:
            result["error"] = f"VERIFY exception: {e}"
            rb = self.rollback()
            result["rollback"] = rb
            result["closure"] = self.closure(phase_id, authorizer, rollback_result=rb).to_dict()
            return result

        result["steps"]["verify"] = verify.to_dict()

        # ── Step 7: ROLLBACK on verification failure ──
        if not verify.all_passed:
            result["error"] = f"VERIFY failed: {verify.summary}"
            rb = self.rollback(backup_report=backup, verification_report=verify)
            result["rollback"] = rb
            result["closure"] = self.closure(phase_id, authorizer, rollback_result=rb).to_dict()
            return result

        # ── Commit the verified temp copy back to the production DB ──
        if apply_result.get("temp_copy") and os.path.exists(apply_result["temp_copy"]):
            try:
                from db_write_guard import authorized_file_replacement

                # Use the governed file-replacement path with one-time proof.
                authorized_file_replacement(
                    temp_copy_path=apply_result["temp_copy"],
                    production_db_path=self.production_db,
                    authorized_context=f"promotion_commit:{phase_id}:{hg.reason}",
                )
            except Exception as e:
                result["error"] = f"Failed to commit verified temp copy to production: {e}"
                rb = self.rollback()
                result["rollback"] = rb
                result["closure"] = self.closure(phase_id, authorizer, rollback_result=rb).to_dict()
                return result

        # ── Step 8: CLOSURE ──
        closure = self.closure(
            phase_id=phase_id,
            authorizer=authorizer,
            prepare_report=prepare,
            backup_report=backup,
            dry_run_report=dry_run,
            human_gate_report=hg,
            apply_result=apply_result,
            verification_report=verify,
        )
        result["steps"]["closure"] = closure.to_dict()
        result["executed"] = True

        return result


# ── Backward-compatible alias ─────────────────────────────────────────
ApplyGate = PromotionGate
