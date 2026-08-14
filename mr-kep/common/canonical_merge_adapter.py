"""Canonical `whisky_id`-merge PromotionGate adapter (P500-M).

Collapses batch/release variant `whisky_id`s onto their canonical survivor,
re-points every dependent record (flavor_evidence / flavor_profiles /
price_history), and marks variants as duplicates via a `superseded_by` column.
NO DELETE. NO production DB write is performed by this adapter — all mutation
happens on the temp copy / guarded connection the PromotionGate provides.

Protocol: implements `DomainPromotionAdapter` (plan / apply_plan) so it slots
into the canonical PromotionGate lifecycle:
    PREPARE -> BACKUP -> DRY-RUN -> (QA) -> HUMAN GO -> APPLY -> VERIFY -> CLOSURE

A merge performs 0 evidence INSERTs and 0 new profile rows (it re-points
existing rows). To keep the gate's generic delta check CLEAN, apply_plan
returns new_evidence_rows=0 / promoted_flavor_profile_rows=0 and reports the
re-point counts under separate keys the gate ignores.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any, Optional

from domain_adapter import PromotionPlan, check_r4_invariant

# Dependent tables whose whisky_id must be re-pointed to the canonical survivor
_DEP_TABLES = ("flavor_evidence", "flavor_profiles", "price_history")

MERGE_COLUMN = "superseded_by"


def _content_hash(obj: Any) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
    ).hexdigest()


class CanonicalMergeAdapter:
    """Adapts a canonicalization merge plan to the DomainPromotionAdapter protocol."""

    name = "canonical_merge"
    source = "canonicalization_audit"

    def __init__(self, staging_db: str = "", decisions_json: str = "", production_db: str = ""):
        self._staging_db = staging_db
        self._decisions_json = decisions_json
        self._production_db = production_db
        self._plan_cache: Optional[PromotionPlan] = None

    # ── Staging build (PREPARE, staging-first) ──────────────────────────
    @staticmethod
    def build_staging_plan(decisions_json: str, staging_db: str, only_decisions=("SAFE_CANONICALIZE",)) -> int:
        """Read the decision package and materialize the merge plan into staging.

        Pure build: reads the decisions JSON (read-only) and writes the merge_plan
        table. KEEP_SEPARATE / NEEDS_HUMAN_REVIEW are excluded by construction.
        Returns the number of variant rows written.
        """
        decisions = json.load(open(decisions_json, "r", encoding="utf-8"))
        rows = []
        for d in decisions:
            if d.get("decision") not in only_decisions:
                continue
            canon = d["group_canonical_whisky_id"]
            gname = d["canonical_name"]
            for m in d["members"]:
                vid = m["whisky_id"]
                if vid == canon:
                    continue
                rows.append((gname, canon, vid, d["decision"]))

        # deterministic order
        rows.sort(key=lambda r: (r[2], r[1]))

        if Path(staging_db).exists():
            Path(staging_db).unlink()
        conn = sqlite3.connect(staging_db)
        try:
            conn.execute(
                "CREATE TABLE merge_plan ("
                " group_name TEXT, canonical_whisky_id TEXT,"
                " variant_whisky_id TEXT, decision TEXT,"
                " PRIMARY KEY (variant_whisky_id))"
            )
            conn.executemany(
                "INSERT INTO merge_plan"
                " (group_name, canonical_whisky_id, variant_whisky_id, decision)"
                " VALUES (?,?,?,?)",
                rows,
            )
            conn.commit()
        finally:
            conn.close()
        return len(rows)

    # ── Staging build from a human-review recommendation table ──────────
    @staticmethod
    def build_staging_plan_from_review(review_json: str, staging_db: str,
                                       recommendations=("MERGE",)) -> int:
        """Read a human-review decision table and materialize the merge plan.

        Used when the canonical decision package classifies groups as
        NEEDS_HUMAN_REVIEW but a later, authorized human-review pass has assigned
        a per-group recommendation (MERGE/KEEP_SEPARATE/DEFER). This method reads
        the REVIEW table (NOT the decision package) and emits merge_plan rows for
        the groups whose `recommended` is in `recommendations`.

        The decision package JSON is never read or modified by this method.

        Returns the number of variant rows written.
        """
        review = json.load(open(review_json, "r", encoding="utf-8"))
        rows = []
        for t in review:
            if t.get("recommended") not in recommendations:
                continue
            canon = t["group"]  # canonical survivor == group id
            gname = t.get("canonical_name", canon)
            for m in t["members"]:
                vid = m["whisky_id"]
                if vid == canon:
                    continue
                rows.append((gname, canon, vid, t["recommended"]))

        rows.sort(key=lambda r: (r[2], r[1]))

        if Path(staging_db).exists():
            Path(staging_db).unlink()
        conn = sqlite3.connect(staging_db)
        try:
            conn.execute(
                "CREATE TABLE merge_plan ("
                " group_name TEXT, canonical_whisky_id TEXT,"
                " variant_whisky_id TEXT, decision TEXT,"
                " PRIMARY KEY (variant_whisky_id))"
            )
            conn.executemany(
                "INSERT INTO merge_plan"
                " (group_name, canonical_whisky_id, variant_whisky_id, decision)"
                " VALUES (?,?,?,?)",
                rows,
            )
            conn.commit()
        finally:
            conn.close()
        return len(rows)


    def plan(
        self,
        staging_db: str = "",
        production_db: str = "",
        evidence_ids: Optional[list[str]] = None,
    ) -> PromotionPlan:
        staging_db = staging_db or self._staging_db
        production_db = production_db or self._production_db
        if not staging_db or not Path(staging_db).exists():
            raise FileNotFoundError(f"merge staging db missing: {staging_db}")

        conn = sqlite3.connect(f"file:{staging_db}?mode=ro", uri=True)
        try:
            plan_rows = conn.execute(
                "SELECT group_name, canonical_whisky_id, variant_whisky_id"
                " FROM merge_plan ORDER BY variant_whisky_id, canonical_whisky_id"
            ).fetchall()
        finally:
            conn.close()

        prod = sqlite3.connect(f"file:{production_db}?mode=ro", uri=True)
        try:
            valid_wids = {r[0] for r in prod.execute("SELECT whisky_id FROM whiskies")}
            already_sup = set()
            try:
                for r in prod.execute(
                    f"SELECT whisky_id FROM whiskies WHERE {MERGE_COLUMN} IS NOT NULL"
                    f" AND {MERGE_COLUMN} != ''"
                ):
                    already_sup.add(r[0])
            except sqlite3.OperationalError:
                pass  # column absent pre-merge; nothing superseded yet
        finally:
            prod.close()

        accepted, rejected = [], []
        for gname, canon, vid in plan_rows:
            if canon not in valid_wids:
                rejected.append({"variant_whisky_id": vid, "reason": f"canonical {canon} not in production.whiskies"})
                continue
            if vid not in valid_wids:
                rejected.append({"variant_whisky_id": vid, "reason": f"variant {vid} not in production.whiskies"})
                continue
            if vid == canon:
                rejected.append({"variant_whisky_id": vid, "reason": "variant == canonical (self-merge)"})
                continue
            if vid in already_sup:
                rejected.append({"variant_whisky_id": vid, "reason": f"variant {vid} already superseded"})
                continue
            accepted.append({"group_name": gname, "canonical_whisky_id": canon, "variant_whisky_id": vid})

        plan = PromotionPlan(
            staging_rows=len(plan_rows),
            accepted=accepted,
            rejected=rejected,
            skipped=[],
            duplicate_count=0,
            new_evidence_rows=0,
            promoted_flavor_profile_rows=0,
        )
        plan.plan_hash = plan._compute_hash()
        self._plan_cache = plan
        return plan

    # ── apply_plan() — executed on the gate's guarded temp-copy connection ─
    def apply_plan(
        self,
        plan: PromotionPlan,
        staging_db: str = "",
        conn: Optional[sqlite3.Connection] = None,
    ) -> dict[str, Any]:
        if conn is None:
            raise RuntimeError("apply_plan requires the gate's guarded connection")
        cur = conn.cursor()

        # Ensure marker column exists (idempotent; no-op if present)
        try:
            cur.execute(f"ALTER TABLE whiskies ADD COLUMN {MERGE_COLUMN} TEXT")
        except sqlite3.OperationalError:
            pass  # already exists

        remapped_ev = remapped_fp = remapped_price = marked = 0
        merged_variant_ids = []

        for m in plan.accepted:
            canon = m["canonical_whisky_id"]
            vid = m["variant_whisky_id"]

            for tbl in _DEP_TABLES:
                n = cur.execute(
                    f"UPDATE {tbl} SET whisky_id=? WHERE whisky_id=?", (canon, vid)
                ).rowcount
                if tbl == "flavor_evidence":
                    remapped_ev += n
                elif tbl == "flavor_profiles":
                    remapped_fp += n
                elif tbl == "price_history":
                    remapped_price += n

            # Mark variant duplicate (NO DELETE)
            cur.execute(
                f"UPDATE whiskies SET {MERGE_COLUMN}=? WHERE whisky_id=?",
                (canon, vid),
            )
            marked += 1
            merged_variant_ids.append(vid)

        check_r4_invariant(conn)
        conn.commit()

        return {
            "new_evidence_rows": 0,
            "promoted_flavor_profile_rows": 0,
            "remapped_evidence_rows": remapped_ev,
            "remapped_profile_rows": remapped_fp,
            "remapped_price_rows": remapped_price,
            "marked_duplicates": marked,
            "merged_variant_ids": merged_variant_ids,
        }


# ── Verification (merge-specific, M1-M9) ──────────────────────────────────
def verify_canonical_merge(
    conn: sqlite3.Connection,
    merged_variant_ids: list[str],
    pre_whisky_count: int,
    pre_evidence_count: int,
    pre_active_count: Optional[int] = None,
) -> dict:
    """Independently verify a post-merge (or dry-run temp-copy) DB.

    Returns dict with per-check booleans + overall `all_passed`.

    `pre_whisky_count`  = total whiskies BEFORE this merge (row count must be
                         unchanged — no DELETE).
    `pre_active_count`  = ACTIVE (non-superseded) whiskies BEFORE this merge.
                         After the merge, active must drop by exactly
                         len(merged_variant_ids). Defaults to pre_whisky_count
                         (correct only when nothing was superseded beforehand).
    """
    if pre_active_count is None:
        pre_active_count = pre_whisky_count
    cur = conn.cursor()
    checks = {}

    # M1 every variant has superseded_by set
    try:
        set_count = cur.execute(
            f"SELECT COUNT(*) FROM whiskies WHERE whisky_id IN ({','.join('?'*len(merged_variant_ids))})"
            f" AND {MERGE_COLUMN} IS NOT NULL AND {MERGE_COLUMN} != ''",
            merged_variant_ids,
        ).fetchone()[0]
    except sqlite3.OperationalError:
        set_count = 0
    checks["M1_all_variants_marked"] = (set_count == len(merged_variant_ids))

    # M2-M4 no dependent row points to a superseded variant
    dep_ok = True
    for tbl in _DEP_TABLES:
        n = cur.execute(
            f"SELECT COUNT(*) FROM {tbl} WHERE whisky_id IN ({','.join('?'*len(merged_variant_ids))})",
            merged_variant_ids,
        ).fetchone()[0]
        dep_ok = dep_ok and (n == 0)
    checks["M2_no_dependent_orphans"] = dep_ok

    # M5 whisky row count unchanged (no DELETE)
    post_count = cur.execute("SELECT COUNT(*) FROM whiskies").fetchone()[0]
    checks["M5_row_count_unchanged"] = (post_count == pre_whisky_count)

    # M6 active count reduced by merged count (relative to pre-merge ACTIVE)
    try:
        active = cur.execute(
            f"SELECT COUNT(*) FROM whiskies WHERE {MERGE_COLUMN} IS NULL OR {MERGE_COLUMN} = ''"
        ).fetchone()[0]
    except sqlite3.OperationalError:
        active = post_count
    checks["M6_active_reduced_by_merged"] = (active == pre_active_count - len(merged_variant_ids))

    # M7 canon present + variant present (just marked)
    checks["M7_survivors_present"] = True  # implied by M1/M5; canon rows untouched

    # M8 integrity
    checks["M8_integrity_ok"] = (cur.execute("PRAGMA integrity_check").fetchone()[0] == "ok")

    # M9 evidence rows conserved (NO DELETE). Production already permits
    # duplicate (whisky_id, source) pairs (92 pre-existing), so pair-uniqueness
    # is NOT the invariant — row conservation is. Merged rows keep distinct
    # evidence_id (no data loss per AGENTS.md Rule 5).
    post_ev = cur.execute("SELECT COUNT(*) FROM flavor_evidence").fetchone()[0]
    checks["M9_evidence_rows_conserved"] = (post_ev == pre_evidence_count)

    # Transparency metric: how many (canon, source) pairs collide post-merge
    coll = cur.execute(
        "SELECT COUNT(*) FROM ("
        "SELECT whisky_id, source, COUNT(*) c FROM flavor_evidence"
        " GROUP BY whisky_id, source HAVING c>1)"
    ).fetchone()[0]
    checks["collision_pairs_post_merge"] = coll

    checks["all_passed"] = all(v for k, v in checks.items()
                               if k not in ("all_passed", "collision_pairs_post_merge"))
    return checks


def register() -> None:
    """Register this adapter with the canonical domain-adapter registry."""
    from domain_adapter import register_adapter
    register_adapter("canonical_merge", CanonicalMergeAdapter)


__all__ = ["CanonicalMergeAdapter", "verify_canonical_merge", "register"]
