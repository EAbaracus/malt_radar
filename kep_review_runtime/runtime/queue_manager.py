"""KEP Autonomous Runtime — Queue Manager.

Computes review queues from existing staging + production state.
Read-only — never writes to staging or production databases.
All queries use mode=ro (read-only) SQLite connections.
"""

import sqlite3
import datetime
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ── Data contracts ──────────────────────────────────────────────────

@dataclass
class QueueItem:
    """A candidate in the review queue."""
    evidence_id: str
    whisky_id: Optional[str]
    normalized_name: str
    raw_name: str
    match_status: str
    provenance_state: str
    source_id: str
    evidence_confidence: float
    authority_tier: str
    extraction_method: str
    score_value: Optional[float]
    ingested_at: str

    # Computed
    queue_type: str = ""             # human_review | automatic | drift | closed
    priority_score: float = 0.0
    priority_level: str = "LOW"      # CRITICAL | HIGH | MEDIUM | LOW
    days_in_queue: float = 0.0
    escalation_level: int = 0
    already_promoted: bool = False
    pending_decisions: list[str] = field(default_factory=list)


@dataclass
class QueueReport:
    """A snapshot of all queues at a point in time."""
    generated_at: str
    total_candidates: int
    human_review: list[QueueItem]
    automatic: list[QueueItem]
    drift: list[QueueItem]
    closed: list[QueueItem]
    production_sha: str = ""
    integrity_ok: bool = False
    flavor_evidence_count: int = 0
    tasting_notes_count: int = 0
    promotion_audit_log_count: int = 0
    whiskies_count: int = 0

    @property
    def summary(self) -> dict:
        return {
            "generated_at": self.generated_at,
            "total_candidates": self.total_candidates,
            "human_review": len(self.human_review),
            "automatic": len(self.automatic),
            "drift": len(self.drift),
            "closed": len(self.closed),
            "production_sha": self.production_sha[:16] if self.production_sha else "",
            "integrity_ok": self.integrity_ok,
        }


# ── Priority calculation (P323 §4) ─────────────────────────────────

def calculate_priority(
    ingested_at: str,
    match_status: str,
    provenance_state: str,
    has_whisky_id: bool,
    is_promoted: bool,
) -> tuple[float, str, int]:
    """Calculate priority score, level, and escalation.

    Formula (P323 §4):
      priority_score = (urgency_weight × time_factor)
                     + (impact_weight × impact_factor)
                     + (blocker_weight × blocker_factor)
                     - (new_weight × freshness_boost)

    Returns (score, level, escalation_level).
    """
    # Urgency factor
    try:
        ingested = datetime.datetime.fromisoformat(ingested_at)
    except (ValueError, TypeError):
        ingested = datetime.datetime.now()
    now = datetime.datetime.now()
    aging_days = max(0.0, (now - ingested).total_seconds() / 86400.0)

    urgency_weight = 3.0
    impact_weight = 2.0
    blocker_weight = 1.5
    new_weight = 1.0

    time_factor = min(aging_days / 30.0, 1.0)

    impact_factor = 0.0
    if has_whisky_id:
        impact_factor += 0.6
    if match_status in ("exact", "normalized_exact", "fuzzy"):
        impact_factor += 0.2
    if provenance_state in ("APPROVED",):
        impact_factor += 0.2
    impact_factor = min(impact_factor, 1.0)

    blocker_factor = 0.0
    if not is_promoted and has_whisky_id and provenance_state == "APPROVED":
        blocker_factor = 0.8  # Ready for promotion, being blocked
    elif match_status == "manual_review":
        blocker_factor = 0.4  # Needs human match decision
    elif provenance_state == "HOLD":
        blocker_factor = 0.4
    elif provenance_state == "staging_unverified" and is_promoted:
        blocker_factor = 0.1  # Staging sync only (low impact)

    freshness_boost = max(1.0 - aging_days / 7.0, 0.0)

    score = max(0.0, (
        urgency_weight * time_factor
        + impact_weight * impact_factor
        + blocker_weight * blocker_factor
        - new_weight * freshness_boost
    ))

    # Escalation level
    if aging_days >= 30:
        escalation = 3
    elif aging_days >= 21:
        escalation = 2
    elif aging_days >= 14:
        escalation = 1
    elif aging_days >= 7:
        escalation = 1
    else:
        escalation = 0

    # Adjust score for escalation
    score += escalation * 0.5

    # Priority level
    if score >= 8.0:
        level = "CRITICAL"
    elif score >= 5.0:
        level = "HIGH"
    elif score >= 2.0:
        level = "MEDIUM"
    else:
        level = "LOW"

    return round(score, 2), level, escalation


# ── Queue Manager ───────────────────────────────────────────────────

class QueueManager:
    """Computed review queues from existing staging + production state.

    All operations read-only (mode=ro). Never writes to staging or production.
    """

    def __init__(
        self,
        staging_db: str,
        production_db: str,
    ):
        self.staging_db = staging_db
        self.production_db = production_db
        self._validate_paths()

    def _validate_paths(self) -> None:
        for name, path in [("staging", self.staging_db),
                           ("production", self.production_db)]:
            if not Path(path).exists():
                raise FileNotFoundError(
                    f"{name} database not found: {path}"
                )

    # ── Database helpers (read-only) ────────────────────────────────

    def _open_staging(self) -> sqlite3.Connection:
        return sqlite3.connect(
            f"file:{self.staging_db}?mode=ro", uri=True
        )

    def _open_production(self) -> sqlite3.Connection:
        return sqlite3.connect(
            f"file:{self.production_db}?mode=ro", uri=True
        )

    def _get_promoted_ids(self, conn: sqlite3.Connection) -> set[str]:
        """Return set of evidence_ids that exist in flavor_evidence."""
        return {
            r[0] for r in conn.execute(
                "SELECT evidence_id FROM flavor_evidence"
            ).fetchall()
        }

    # ── Queue computation ───────────────────────────────────────────

    def compute_queues(self) -> QueueReport:
        """Compute all queues from current state. READ ONLY."""
        staging = self._open_staging()
        production = self._open_production()

        try:
            promoted_ids = self._get_promoted_ids(production)
            rows = staging.execute(
                "SELECT * FROM staging_editorial_reviews "
                "ORDER BY ingested_at DESC"
            )
            all_rows = rows.fetchall()
            cols = [desc[0] for desc in rows.description]

            human: list[QueueItem] = []
            auto: list[QueueItem] = []
            drift: list[QueueItem] = []
            closed: list[QueueItem] = []

            for r in all_rows:
                rd = dict(zip(cols, r))
                eid = rd["evidence_id"]
                wid = rd.get("matched_master_whisky_id")
                is_promoted = eid in promoted_ids

                item = self._build_item(rd, is_promoted)
                item = self._classify(item)

                if item.queue_type == "human_review":
                    human.append(item)
                elif item.queue_type == "automatic":
                    auto.append(item)
                elif item.queue_type == "drift":
                    drift.append(item)
                else:
                    closed.append(item)

            # Sort each queue by priority descending
            human.sort(key=lambda i: i.priority_score, reverse=True)
            auto.sort(key=lambda i: i.priority_score, reverse=True)
            drift.sort(key=lambda i: i.priority_score, reverse=True)

            # Production state
            prod_sha = self._compute_sha(production)
            integrity = production.execute(
                "PRAGMA integrity_check"
            ).fetchone()[0]
            fe_count = production.execute(
                "SELECT COUNT(*) FROM flavor_evidence"
            ).fetchone()[0]
            tn_count = production.execute(
                "SELECT COUNT(*) FROM tasting_notes"
            ).fetchone()[0]
            al_count = production.execute(
                "SELECT COUNT(*) FROM promotion_audit_log"
            ).fetchone()[0]
            wh_count = production.execute(
                "SELECT COUNT(*) FROM whiskies"
            ).fetchone()[0]

            return QueueReport(
                generated_at=datetime.datetime.now().isoformat(),
                total_candidates=len(all_rows),
                human_review=human,
                automatic=auto,
                drift=drift,
                closed=closed,
                production_sha=prod_sha,
                integrity_ok=(integrity == "ok"),
                flavor_evidence_count=fe_count,
                tasting_notes_count=tn_count,
                promotion_audit_log_count=al_count,
                whiskies_count=wh_count,
            )

        finally:
            staging.close()
            production.close()

    # ── Item building ───────────────────────────────────────────────

    def _build_item(
        self, rd: dict, is_promoted: bool
    ) -> QueueItem:
        """Build a QueueItem from a staging row dict."""
        eid = rd["evidence_id"]
        wid = rd.get("matched_master_whisky_id")
        ingested = rd.get("ingested_at") or datetime.datetime.now().isoformat()
        score, level, escalation = calculate_priority(
            ingested_at=ingested,
            match_status=rd.get("match_status", ""),
            provenance_state=rd.get("provenance_state", ""),
            has_whisky_id=(wid is not None),
            is_promoted=is_promoted,
        )

        return QueueItem(
            evidence_id=eid,
            whisky_id=wid,
            normalized_name=rd.get("normalized_name", ""),
            raw_name=rd.get("raw_name", ""),
            match_status=rd.get("match_status", ""),
            provenance_state=rd.get("provenance_state", ""),
            source_id=rd.get("source_id", ""),
            evidence_confidence=rd.get("evidence_confidence") or 0.0,
            authority_tier=rd.get("authority_tier", ""),
            extraction_method=rd.get("extraction_method", ""),
            score_value=rd.get("score_value"),
            ingested_at=ingested,
            priority_score=score,
            priority_level=level,
            escalation_level=escalation,
            already_promoted=is_promoted,
        )

    def _classify(self, item: QueueItem) -> QueueItem:
        """Determine queue type and pending decisions.

        Classification rules:
          - Already promoted + staging clean (match=exact, prov=APPROVED)  → closed
          - Already promoted + staging stale (mismatch)                    → automatic
          - Not promoted + needs human (manual_review / HOLD / unverified) → human_review
          - Not promoted + ready for promotion                             → human_review (needs GO)
          - Production drift                                               → drift
        """
        if item.already_promoted:
            staging_clean = (
                item.match_status in ("exact", "normalized_exact", "fuzzy")
                and item.provenance_state == "APPROVED"
            )
            if staging_clean:
                item.queue_type = "closed"
            else:
                item.queue_type = "automatic"
                item.pending_decisions = []
                if item.match_status not in ("exact", "normalized_exact", "fuzzy"):
                    item.pending_decisions.append("sync_match")
                if item.provenance_state != "APPROVED":
                    item.pending_decisions.append("sync_provenance")
        else:
            # Not promoted — human review needed
            item.queue_type = "human_review"
            if item.match_status == "manual_review":
                item.pending_decisions.append("match")
            if item.provenance_state in ("staging_unverified", "HOLD"):
                item.pending_decisions.append("provenance")
            if item.provenance_state == "HOLD":
                item.pending_decisions.append("certification")
            if not item.pending_decisions:
                # Fully qualified but not yet promoted → ready for batch
                item.pending_decisions.append("promotion_GO")

        return item

    # ── Production helpers ──────────────────────────────────────────

    @staticmethod
    def _compute_sha(conn: sqlite3.Connection) -> str:
        """Compute SHA-256 of the production database file.

        Note: We cannot SHA the file from within a SQLite connection.
        We derive a hash from table-level metadata instead.
        For actual file-level SHA, see P312 pattern (done externally).
        """
        # Table-level checksum: count + length
        parts = []
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ):
            tname = row[0]
            cnt = conn.execute(f'SELECT COUNT(*) FROM "{tname}"').fetchone()[0]
            parts.append(f"{tname}={cnt}")
        return hashlib_sim(parts)

    def get_drift_candidates(self) -> list[dict]:
        """Identify production drift candidates.

        Returns list of drift descriptions.
        """
        production = self._open_production()
        try:
            integrity = production.execute(
                "PRAGMA integrity_check"
            ).fetchone()[0]
            if integrity != "ok":
                return [{
                    "type": "integrity_failure",
                    "detail": f"integrity_check = {integrity}",
                    "severity": "ERROR",
                }]

            # Check baseline-preserved backups
            backup_dir = Path(self.production_db).parent.parent / "backups"
            if backup_dir.exists():
                backups = list(backup_dir.glob("production.pre_*.db"))
                if not backups:
                    return [{
                        "type": "missing_backup",
                        "detail": "No pre-promotion backups found",
                        "severity": "WARNING",
                    }]

            return []  # No drift detected
        finally:
            production.close()


def hashlib_sim(parts: list[str]) -> str:
    """Simple deterministic hash from table metadata.
    Not cryptographic — used for quick change detection only.
    """
    import hashlib
    return hashlib.sha256(
        "|".join(parts).encode()
    ).hexdigest()
