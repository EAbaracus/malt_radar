"""KEP Autonomous Runtime — Scheduler CLI.

Commands:
  python -m kep_runtime.runtime.scheduler scan   — scan staging, generate report
  python -m kep_runtime.runtime.scheduler report  — regenerate report from existing data

Output: runtime/reports/queue_report.json + queue_report.md
"""

import json
import sys
import datetime
from pathlib import Path

from .audit_writer import AuditWriter
from .queue_manager import QueueManager


# ── Paths ───────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent.parent.parent  # malt radar CLEAN/
REPORTS = Path(__file__).resolve().parent / "reports"


def _get_staging_db() -> str:
    """Find staging DB."""
    p = ROOT / "mr-kep" / "editorial" / "staging_editorial.db"
    if p.exists():
        return str(p)
    raise FileNotFoundError(f"staging DB not found at {p}")


def _get_production_db() -> str:
    """Find production DB."""
    p = ROOT / "output" / "import" / "production.db"
    if p.exists():
        return str(p)
    raise FileNotFoundError(f"production DB not found at {p}")


# ── Report generation ───────────────────────────────────────────────

def generate_report(output_md: bool = True, output_json: bool = True) -> dict:
    """Scan staging, compute queues, write reports. Returns summary dict."""
    staging_path = _get_staging_db()
    prod_path = _get_production_db()

    qm = QueueManager(
        staging_db=staging_path,
        production_db=prod_path,
    )
    report = qm.compute_queues()

    # Create reports directory
    REPORTS.mkdir(parents=True, exist_ok=True)

    now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    # JSON output
    if output_json:
        json_path = REPORTS / f"queue_report_{now}.json"
        json_path.write_text(
            json.dumps(_report_to_dict(report), indent=2, default=str),
            encoding="utf-8",
        )
        # Also write latest copy
        latest_json = REPORTS / "queue_report.json"
        latest_json.write_text(
            json.dumps(_report_to_dict(report), indent=2, default=str),
            encoding="utf-8",
        )

    # Markdown output
    if output_md:
        md_path = REPORTS / f"queue_report_{now}.md"
        md_content = _report_to_md(report)
        md_path.write_text(md_content, encoding="utf-8")
        latest_md = REPORTS / "queue_report.md"
        latest_md.write_text(md_content, encoding="utf-8")

    summary = dict(report.summary)
    summary["json_report"] = str(REPORTS / "queue_report.json")
    summary["md_report"] = str(REPORTS / "queue_report.md")
    return summary


def _report_to_dict(report) -> dict:
    """Convert QueueReport to a JSON-serialisable dict."""
    def item_dict(i):
        return {
            "evidence_id": i.evidence_id,
            "whisky_id": i.whisky_id,
            "normalized_name": i.normalized_name,
            "match_status": i.match_status,
            "provenance_state": i.provenance_state,
            "queue_type": i.queue_type,
            "priority_score": i.priority_score,
            "priority_level": i.priority_level,
            "days_in_queue": round(i.days_in_queue, 1),
            "escalation_level": i.escalation_level,
            "already_promoted": i.already_promoted,
            "pending_decisions": i.pending_decisions,
        }

    return {
        "generated_at": report.generated_at,
        "total_candidates": report.total_candidates,
        "production": {
            "sha256": report.production_sha,
            "integrity_ok": report.integrity_ok,
            "flavor_evidence": report.flavor_evidence_count,
            "tasting_notes": report.tasting_notes_count,
            "promotion_audit_log": report.promotion_audit_log_count,
            "whiskies": report.whiskies_count,
        },
        "queues": {
            "human_review": [item_dict(i) for i in report.human_review],
            "automatic": [item_dict(i) for i in report.automatic],
            "drift": [item_dict(i) for i in report.drift],
            "closed": [item_dict(i) for i in report.closed],
        },
    }


def _report_to_md(report) -> str:
    """Generate markdown report."""
    lines = [
        f"# KEP Review Queue Report",
        f"",
        f"**Generated:** {report.generated_at}",
        f"**Total candidates:** {report.total_candidates}",
        f"",
        f"---",
        f"",
        f"## Production State",
        f"",
        f"| Check | Value |",
        f"|---|---|",
        f"| SHA-256 | `{report.production_sha[:16]}...` |",
        f"| integrity_check | {'✅ ok' if report.integrity_ok else '❌ FAILED'} |",
        f"| flavor_evidence | {report.flavor_evidence_count} |",
        f"| tasting_notes | {report.tasting_notes_count} |",
        f"| promotion_audit_log | {report.promotion_audit_log_count} |",
        f"| whiskies | {report.whiskies_count} |",
        f"",
    ]

    def render_queue(title: str, items: list, icon: str):
        nonlocal lines
        lines.append(f"## {icon} {title}")
        lines.append(f"")
        if not items:
            lines.append(f"*Empty — no candidates.*")
            lines.append(f"")
            return
        lines.append(f"| Evidence ID | Product | Status | Score | Level | Esc | Decisions |")
        lines.append(f"|---|---|---|---|---|---|---|")
        for i in items:
            age_str = f"{i.days_in_queue:.0f}d" if i.days_in_queue >= 1 else "<1d"
            pending = ", ".join(i.pending_decisions) if i.pending_decisions else "—"
            lines.append(
                f"| `{i.evidence_id[:20]}...` | {i.normalized_name[:25]} | "
                f"{i.match_status}/{i.provenance_state} | "
                f"{i.priority_score} | {i.priority_level} | "
                f"{i.escalation_level} | {pending} |"
            )
        lines.append(f"")

    render_queue("Human Review Queue", report.human_review, "👤")
    render_queue("Automatic Queue", report.automatic, "🤖")
    render_queue("Drift Queue", report.drift, "⚠️")
    render_queue("Closed Candidates", report.closed, "✅")

    lines.append(f"---")
    lines.append(f"")
    lines.append(f"*Read-only snapshot. No production writes. No certification changes. No promotion.*")

    return "\n".join(lines)


# ── CLI ─────────────────────────────────────────────────────────────

def cmd_scan() -> None:
    """Scan staging, compute queues, write reports."""
    print("KEP Review Scheduler — scan")
    print("=" * 40)

    staging_path = _get_staging_db()
    prod_path = _get_production_db()
    print(f"  Staging:    {staging_path}")
    print(f"  Production: {prod_path}")

    summary = generate_report()
    print(f"\n  Total candidates: {summary['total_candidates']}")
    print(f"  Human review:     {summary['human_review']}")
    print(f"  Automatic:        {summary['automatic']}")
    print(f"  Drift:            {summary['drift']}")
    print(f"  Closed:           {summary['closed']}")
    print(f"  Production SHA:   {summary['production_sha']}")
    print(f"  Integrity:        {'OK' if summary.get('integrity_ok') else '?'}")
    print(f"\n  Reports written:")
    print(f"    {summary['json_report']}")
    print(f"    {summary['md_report']}")


def cmd_report() -> None:
    """Regenerate report from existing data."""
    print("KEP Review Scheduler — report")
    print("=" * 40)
    summary = generate_report()
    print(f"  Report written: {summary['json_report']}")
    print(f"                  {summary['md_report']}")


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python -m kep_runtime.runtime.scheduler <command>")
        print("  Commands:")
        print("    scan          — Scan staging, compute queues, write reports")
        print("    report        — Regenerate report from existing data")
        print("    execute       — Execute automatic queue actions")
        print("    execute --dry-run  — Simulate automatic queue (no writes)")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "scan":
        cmd_scan()
    elif cmd == "report":
        cmd_report()
    elif cmd == "execute":
        cmd_execute()
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


def cmd_execute() -> None:
    """Execute or dry-run automatic queue actions."""
    dry_run = "--dry-run" in sys.argv

    staging_path = _get_staging_db()
    prod_path = _get_production_db()
    audit = AuditWriter()

    if dry_run:
        from .dry_run import run_dry_run, print_dry_run_report
        print("KEP Automatic Executor — DRY-RUN")
        print("=" * 60)
        result = run_dry_run(staging_path, prod_path, audit_writer=audit)
        print_dry_run_report(result)
    else:
        from .executor import RealExecutor
        from .actions import plan_all_actions

        plans = plan_all_actions(staging_path, prod_path)

        if not plans:
            print("Nothing to execute — queue is clean.")
            return

        print(f"KEP Automatic Executor — EXECUTING {len(plans)} actions")
        print("=" * 60)

        executor = RealExecutor(staging_path, prod_path, audit_writer=audit)
        result = executor.execute_batch(plans)

        print(f"\n  Batch ID:   {result.batch_id}")
        print(f"  Total:      {result.total}")
        print(f"  Succeeded:  {result.succeeded}")
        print(f"  Failed:     {result.failed}")
        print(f"  Skipped:    {result.skipped}")
        print(f"  Rollback:   {'YES' if result.rollback_executed else 'NO'}")
        print(f"  Duration:   {result.duration_ms}ms")

        for r in result.results:
            icon = "✅" if r.success else "❌"
            print(f"  {icon} {r.action_type:20s} | {r.evidence_id[:24]:24s} | {r.detail[:60]}")

        if result.failed > 0:
            print(f"\n  ⚠  {result.failed} actions failed. SAVEPOINT rollback executed.")
            for r in result.results:
                if not r.success and r.error:
                    print(f"     Error: {r.error}")



if __name__ == "__main__":
    main()
