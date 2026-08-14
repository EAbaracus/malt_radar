# Malt Radar — Agent Operating Instructions

## Mission

Maintain and improve Malt Radar while preserving data quality,
traceability, correctness, and evidence-based validation.

---

## Default Mode

Start in **read-only** mode.

Never assume modifications are required.

Inspect before acting.

---

## Canonical Architecture

**MR-KEP + KEP Runtime = CANONICAL.**

Classic P32-P42 is **RETIRED / HISTORICAL ONLY**. It is not runnable and
must not be treated as an active pipeline. See "Classic P32-P42" section below.

The canonical production path is:

```
INGEST → EXTRACT → NORMALIZE → CANONICALIZE → EVIDENCE
→ QA → HUMAN GO/NO-GO → KEP Runtime PromotionGate → VERIFY → CLOSURE
```

---

## Canonical Governance Rules (15 rules — all mandatory)

### 1. MR-KEP + KEP Runtime is canonical
The only authorized pipeline is MR-KEP (domain) + KEP Runtime (execution/safety).
No other pipeline architecture is active or canonical.

### 2. Production promotion MUST use PromotionGate
All production DB mutations must go through `kep_review_runtime/runtime/promotion_engine.py`.
No direct SQL writes to `production.db` under any circumstances.

### 3. No direct production DB writes
Direct modifications to `output/import/production.db` (via sqlite3 CLI,
Python `sqlite3` module outside PromotionGate, or any other tool) are
**prohibited**. Violation is an automatic NO-GO.

### 4. Evidence INSERT-only
`flavor_evidence` rows are **never** UPDATE'd or DELETE'd.
New evidence is always INSERT'd.
Deduplication is handled by deterministic `evidence_id` — if a row already
exists with the same `evidence_id`, the INSERT is a no-op (idempotent).

### 5. Existing evidence is immutable
Once a `flavor_evidence` row is in production, it cannot be modified.
To correct evidence, insert a NEW row with a NEW deterministic `evidence_id`
(new source, new date, or explicit correction provenance).

### 6. Human GO/NO-GO required
Every `PromotionGate.apply()` requires explicit human authorization.
Dry-run output must be presented to the human. The human must respond GO.
No autonomous apply without human confirmation.

### 7. Backup + SHA256 verification required
Before every apply:
1. Create a backup of `production.db`.
2. Record SHA256 of `production.db` BEFORE apply.
3. Apply via PromotionGate.
4. Record SHA256 of `production.db` AFTER apply.
5. If SHA256 AFTER does not match expected delta — ROLLBACK immediately.

### 8. Dry-run before apply
`--dry-run` is the DEFAULT mode for all KEP Runtime operations.
Never call `PromotionGate.apply()` without a preceding dry-run on the
same batch in the same session.

### 9. Verify after apply
After every apply:
- Check row counts match dry-run predictions.
- Check SHA256 matches post-apply expectation.
- Verify no R4 violations (all axis values in `[0.0, 1.0]`).
- Verify no duplicate `(whisky_id, source)` pairs in `flavor_evidence`.
- If any check fails — rollback.

### 10. Failed verification triggers rollback
If post-apply verification fails for any reason:
- Restore from pre-apply backup.
- Verify SHA256 matches pre-apply SHA.
- Record failure in closure report.
- Do NOT retry without a new human GO.

### 11. Closure artifact required
Every phase that executes a production mutation must produce a closure report:
- Phase ID
- Pre-apply SHA256
- Post-apply SHA256
- Row counts (before / promoted / held / skipped / after)
- Verification status
- Human GO record

### 12. Production DB hash captured before/after
SHA256 of `output/import/production.db` must be recorded in the closure
artifact for every production mutation. These hashes are immutable historical
records — do not overwrite or delete them.

### 13. Staging-first workflow
All new data processing starts in a staging DB or staging tables.
Staging results are QA'd before any promotion is proposed.
Never process directly into production tables.

### 14. Temp artifacts must be cleaned
Temporary DB copies, working files, and intermediate artifacts created during
a phase must be cleaned up after the phase closes. Temp files must not be
committed to git.

### 15. Commit/push only with explicit human authorization
No `git commit` or `git push` without explicit human instruction in the
current session. This includes auto-commit patterns and `--amend` on
historical commits.

---

## Evidence Requirements

Every important conclusion must be supported by evidence.

Never trust aggregate parser metrics alone.

Validate using source material whenever possible.

---

## Validation Requirements

Require:

- traceability (every claim has a source)
- random sampling (verify a sample manually, not just counts)
- source verification (check against raw data)
- cross-page / cross-table validation

---

## Database Safety

Before modifying any database:

1. Create backup
2. Record SHA256 before
3. Inspect impact (dry-run)
4. Get human GO
5. Apply change
6. Record SHA256 after
7. Verify results
8. Write closure artifact

---

## Completion Requirements

Before reporting success:

- Verify outputs match dry-run predictions
- Verify consistency (SHA256, row counts, invariants)
- Check git status (no unintended staged changes)
- Check validation results (no R4 violations, no duplicates)

---

## Product Rule

Price information may exist in storage.

Price information must **never** be exposed in UI or API responses.

---

## Escalation Rule

When confidence is low:

- Stop
- Explain uncertainty
- Request additional verification or human decision

Never guess or fabricate data.

---

## Classic P32-P42 — HISTORICAL ONLY

**Status: RETIRED. Not runnable. Not canonical.**

- P36-P42 entry point scripts were **never committed** to the repository.
- The pipeline's data formats (CSV staging, manual review CSVs) have been
  superseded by MR-KEP's evidence model.
- No revival planned. P500-A decision (CLOSED/DO-NOT-REOPEN): Classic retired.
- Outputs retained as historical evidence only.

Classic P32-P42 phases **must not** be referenced as active tasks in any
roadmap, sprint, or planning document. If a document references P32-P42 as
active, that document is stale and must be updated.

What remains canonical from the Classic era:
- P44 data quality dashboard — KPI framework still valid as reference.
- P45-P46 similarity engine — GO gate, executable, used by frontend.

---

## KEP Runtime Modules (reference)

| Module | Responsibility |
|--------|----------------|
| `scheduler.py` | Scan queue, orchestrate execution |
| `executor.py` | DryRunExecutor + RealExecutor with SAVEPOINT safety |
| `promotion_engine.py` | **PromotionGate** — ONLY authorized production write path |
| `actions.py` | ActionPlan + domain-specific action wrappers |
| `queue_manager.py` | Computed review queues from staging + production state |
| `audit_writer.py` | Audit table schema + logging |
| `dry_run.py` | Dry-run runner + report printer |
| `db_write_guard.py` | OS lock + write gating |
| `run.py` | Main orchestrator entry point |

---

## MR-KEP Domain Modules (reference)

| Module | Stage | Can Write production? |
|--------|-------|-----------------------|
| `acquisition/` | INGEST | ❌ Never |
| `extraction_engine/` | EXTRACT | ❌ Never |
| `extraction_execution/` | EXTRACT orchestration | ❌ Never |
| `normalize/` | NORMALIZE | ❌ Never |
| `d4_reducer/` | NORMALIZE + CANONICALIZE | ❌ Never |
| `canonicalize/` | CANONICALIZE | ❌ Never |
| `evidence/` | EVIDENCE | ❌ Never |
| `qa/` | QA | ❌ Never |
| `common/` | Shared utilities + invariant_registry.yaml | ❌ Never |

---

## Current Production Baseline (post-Faz 1/2/3/4 Safe-13, updated 2026-08-14)

| Metric | Value |
|--------|-------|
| SHA256 | `cbffd16b29433c983bb113b2e9a9f186dd94c1ff9dc6f5f1b13d97f084386177` |
| Tables | 37 |
| Whiskies | 4,750 (active 4,593 · superseded 157) |
| flavor_evidence | 6,367 |
| flavor_profiles | 4,409 |
| staging_tasting_notes remaining | 7 (staging_hold) |
| Faz 3 canonical merge | 5 variants superseded; evidence rows conserved |
| Faz 1/2/4 Safe-13 | 1 rebind + 12 master-country updates |

> Production mutation QA independently passed for `cbffd16b…`: totals, FK,
> integrity, DENY ACE, and Safe-13 deltas are verified. However, baseline ancestry
> from the last fully retained `70fa9cf0…` state through `9e86cdac…` is **OPEN /
> PROVISIONAL**. The retained `70fa` backup differs from `cbffd` by the five Faz-3
> variant changes plus W003023; no byte-identical `9e86` copy or WAL archive is
> currently retained. Do not describe `70fa -> 9e86` as WAL-only or fully explained.
> Permanent technical record: `docs/superpowers/specs/2026-08-14-faz124-safe13-closure.md`.
> SHA, Production Baseline olarak immutably korunur; yeni mutation ancak yeni closure ile
> bu satırı günceller.

Faz 3 canonical merge and Faz 1/2/4 Safe-13 are **TECHNICALLY VERIFIED / PROVISIONAL**.
This baseline is the immutable starting point for future work only after the ancestry
provenance gap is resolved.

---

## Web Search & Extraction

Three-tier web stack. All sub-agents have the same tools — use them deliberately.

| Tier | Tool | Address | Role |
|------|------|---------|------|
| 1 | SearXNG | `localhost:8090` | Primary search backend. Aggregates Google, DDG, Startpage. Server-side engine filtering. Search-only — no URL extraction. Config: `searxng/settings.yml` (under `search-stack/`). |
| 1 | Firecrawl | `http://localhost:3002` | Primary extraction backend. Handles standard sites, PDFs, structured extraction. |
| 2 | Hound MCP | local MCP server | Anti-bot fallback for sites that block Firecrawl. Registers four tools: `smart_fetch`, `smart_search`, `smart_crawl`, `screenshot`. |

### Escalation path

- **SearXNG + Firecrawl** — always try first. Fast, token-efficient.
- **Hound `smart_fetch`** — when Firecrawl hits 403/CAPTCHA/empty. Handles Cloudflare Turnstile, DataDome.
- **Hound `smart_crawl`** — for deep crawling behind bot protection.
- **Hound `smart_search`** — fallback search if SearXNG is down.
