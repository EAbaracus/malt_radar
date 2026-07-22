"""Canonical Invariant Registry — P500-F.

Single source of truth for all promotion invariants.

Usage:
    registry = InvariantRegistry("mr-kep/common/invariant_registry.yaml")
    results = registry.run_all(context)  # list of CheckResult
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional


# ── Check function registry ──────────────────────────────────────────

_CHECKERS: dict[str, Callable] = {}


def register_check(name: str, fn: Callable) -> None:
    """Register a check function by name so InvariantRegistry can resolve it."""
    _CHECKERS[name] = fn


# ── Result type ──────────────────────────────────────────────────────

@dataclass
class CheckResult:
    """Result of a single invariant check."""
    invariant_id: str
    description: str
    fail_action: str
    severity: str
    passed: bool = False
    detail: str = ""
    error: Optional[str] = None


# ── Schema validation error ──────────────────────────────────────────

class RegistryValidationError(ValueError):
    """Raised when registry YAML violates the schema contract."""
    pass


# ── InvariantRegistry ────────────────────────────────────────────────

class InvariantRegistry:
    """Loads, validates, and runs canonical promotion invariants.

    The registry YAML defines WHICH invariants exist and their metadata.
    The actual check callables are registered via register_check() from
    the code that implements them (promotion_engine.py, domain_adapter.py).
    """

    REQUIRED_FIELDS = {"id", "type", "category", "description",
                       "check_method", "fail_action", "severity"}
    VALID_TYPES = {"canonical", "domain"}
    VALID_FAIL_ACTIONS = {"NO_GO", "ROLLBACK"}
    VALID_SEVERITIES = {"critical", "warning", "info"}

    def __init__(self, yaml_path: Optional[str] = None):
        self._invariants: list[dict] = []
        self._yaml_path: Optional[str] = None
        self._loaded: bool = False
        self._schema_errors: list[str] = []

        # Auto-resolve yaml_path relative to this file's project root
        if yaml_path:
            self.load(yaml_path)
        else:
            # Default: look for invariant_registry.yaml next to this file
            default = str(Path(__file__).resolve().parent / "invariant_registry.yaml")
            if os.path.exists(default):
                self.load(default)

    @property
    def invariants(self) -> list[dict]:
        return list(self._invariants)

    @property
    def loaded(self) -> bool:
        return self._loaded

    @property
    def count(self) -> int:
        return len(self._invariants)

    def load(self, yaml_path: str) -> None:
        """Load and validate YAML registry. Raises RegistryValidationError on schema violation."""
        self._yaml_path = yaml_path
        self._schema_errors = []

        if not os.path.exists(yaml_path):
            raise RegistryValidationError(f"Registry file not found: {yaml_path}")

        try:
            import yaml
        except ImportError:
            raise RegistryValidationError(
                "PyYAML required. Install: uv pip install pyyaml"
            )

        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not isinstance(data, dict):
            raise RegistryValidationError("Registry root must be a mapping (dict)")

        # Validate version
        if "version" not in data:
            self._schema_errors.append("Missing top-level 'version' field")

        # Validate invariants list
        raw = data.get("invariants", [])
        if not isinstance(raw, list):
            raise RegistryValidationError("'invariants' must be a list")
        if not raw:
            raise RegistryValidationError("'invariants' list is empty — must contain at least one invariant")

        seen_ids: set[str] = set()
        parsed: list[dict] = []

        for i, entry in enumerate(raw):
            if not isinstance(entry, dict):
                self._schema_errors.append(f"invariant[{i}]: must be a mapping")
                continue

            record = dict(entry)

            # Reject duplicate IDs
            inv_id = record.get("id", "")
            if not inv_id:
                self._schema_errors.append(f"invariant[{i}]: missing required 'id' field")
                continue
            if inv_id in seen_ids:
                self._schema_errors.append(f"invariant[{i}]: duplicate id={inv_id!r}")
                continue
            seen_ids.add(inv_id)

            # Validate required fields
            missing = self.REQUIRED_FIELDS - set(record.keys())
            if missing:
                self._schema_errors.append(
                    f"invariant[{i}] id={inv_id!r}: missing required fields: {sorted(missing)}"
                )
                continue

            # Validate enum fields
            if record["type"] not in self.VALID_TYPES:
                self._schema_errors.append(
                    f"invariant[{i}] id={inv_id!r}: invalid type={record['type']!r} "
                    f"(valid: {sorted(self.VALID_TYPES)})"
                )
            if record["fail_action"] not in self.VALID_FAIL_ACTIONS:
                self._schema_errors.append(
                    f"invariant[{i}] id={inv_id!r}: invalid fail_action={record['fail_action']!r} "
                    f"(valid: {sorted(self.VALID_FAIL_ACTIONS)})"
                )
            if record["severity"] not in self.VALID_SEVERITIES:
                self._schema_errors.append(
                    f"invariant[{i}] id={inv_id!r}: invalid severity={record['severity']!r} "
                    f"(valid: {sorted(self.VALID_SEVERITIES)})"
                )

            # Check that check_method is registered (warn only — may be
            # lazy-loaded by promotion_engine.py at runtime)
            method = record["check_method"]
            if method not in _CHECKERS:
                pass  # Not an error — caller must ensure registration before run()

            parsed.append(record)

        if self._schema_errors:
            raise RegistryValidationError(
                f"Registry schema validation failed ({len(self._schema_errors)} error(s)):\n" +
                "\n".join(f"  - {e}" for e in self._schema_errors)
            )

        self._invariants = parsed
        self._loaded = True

    def get_invariant(self, inv_id: str) -> Optional[dict]:
        """Look up an invariant by ID."""
        for inv in self._invariants:
            if inv["id"] == inv_id:
                return inv
        return None

    def get_invariants_by_category(self, category: str) -> list[dict]:
        """Filter invariants by category (backup, dry_run, apply, data_integrity, data_quality)."""
        return [inv for inv in self._invariants if inv.get("category") == category]

    def run_check(self, invariant: dict, context: dict) -> CheckResult:
        """Run a single invariant check given the context dictionary.

        context keys depend on the invariant type:
        - backup_report / dry_run_report / apply_result / verification_report
        - conn (sqlite3.Connection for DB-level checks)
        - check_db (path to the DB to query)
        - production_db (path to production.db)
        """
        inv_id = invariant["id"]
        method_name = invariant["check_method"]
        fn = _CHECKERS.get(method_name)

        if fn is None:
            return CheckResult(
                invariant_id=inv_id,
                description=invariant.get("description", ""),
                fail_action=invariant.get("fail_action", "ROLLBACK"),
                severity=invariant.get("severity", "critical"),
                passed=False,
                error=f"check_method {method_name!r} not registered",
            )

        try:
            passed = fn(context)
            return CheckResult(
                invariant_id=inv_id,
                description=invariant.get("description", ""),
                fail_action=invariant.get("fail_action", "ROLLBACK"),
                severity=invariant.get("severity", "critical"),
                passed=bool(passed),
                detail=str(passed) if not isinstance(passed, bool) else "",
            )
        except Exception as e:
            return CheckResult(
                invariant_id=inv_id,
                description=invariant.get("description", ""),
                fail_action=invariant.get("fail_action", "ROLLBACK"),
                severity=invariant.get("severity", "critical"),
                passed=False,
                error=str(e),
            )

    def run_all(self, context: dict) -> list[CheckResult]:
        """Run all loaded invariants against context. Returns ordered list of CheckResult."""
        if not self._loaded:
            raise RuntimeError("InvariantRegistry not loaded. Call load() first.")
        results: list[CheckResult] = []
        for inv in self._invariants:
            result = self.run_check(inv, context)
            results.append(result)
        return results

    def to_dict(self) -> dict:
        """Serialize registry metadata for reporting."""
        return {
            "loaded": self._loaded,
            "yaml_path": self._yaml_path,
            "invariant_count": len(self._invariants),
            "invariants": [
                {
                    "id": inv["id"],
                    "type": inv["type"],
                    "category": inv["category"],
                    "fail_action": inv["fail_action"],
                    "severity": inv["severity"],
                    "check_method": inv["check_method"],
                }
                for inv in self._invariants
            ],
        }


__all__ = [
    "InvariantRegistry", "CheckResult", "RegistryValidationError",
    "register_check", "_CHECKERS",
]
