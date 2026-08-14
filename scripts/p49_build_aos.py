import datetime
import hashlib
import os
import shutil
import sys

# ROOT is configurable so the generator is not bound to a single hardcoded path.
# Precedence: CLI arg (sys.argv[1]) > env var MALT_RADAR_ROOT > built-in default.
_ROOT_DEFAULT = r"C:\Users\eltun\Documents\malt radar CLEAN"
ROOT = (
    sys.argv[1]
    if len(sys.argv) > 1
    else os.environ.get("MALT_RADAR_ROOT", _ROOT_DEFAULT)
)

def create_dirs():
    dirs = ["rules", "workflows", "memory", "prompts"]
    for d in dirs:
        os.makedirs(os.path.join(ROOT, d), exist_ok=True)
        print(f"Created directory: {d}")

def write_file(rel_path, content):
    full_path = os.path.join(ROOT, rel_path)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content.strip() + "\n")
    print(f"Wrote file: {rel_path}")

def snapshot_existing():
    """Back up the currently-generated AOS tree before overwriting it.

    The generator's own Rule 02 (rules/02-data-integrity.md) requires a pre-write
    backup and SHA256 logging. This makes the generator honor that discipline
    instead of silently clobbering hand-edited files such as AGENTS.md or
    rules/06-product-rules.md when main() is re-run.
    """
    managed = ["AGENTS.md", "rules", "workflows", "memory", "prompts"]
    existing = [p for p in managed if os.path.exists(os.path.join(ROOT, p))]
    if not existing:
        print("No existing AOS tree to snapshot; fresh generation.")
        return
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = os.path.join(ROOT, "output", "aos_backups", f"pre_{stamp}")
    os.makedirs(dest, exist_ok=True)
    manifest_lines = []
    for p in existing:
        src = os.path.join(ROOT, p)
        dst = os.path.join(dest, p)
        if os.path.isdir(src):
            shutil.copytree(src, dst)
            for dirpath, _, filenames in os.walk(dst):
                for fn in filenames:
                    fp = os.path.join(dirpath, fn)
                    rel = os.path.relpath(fp, dest).replace(os.sep, "/")
                    manifest_lines.append(f"{hashlib.sha256(open(fp, 'rb').read()).hexdigest()}  {rel}")
        else:
            shutil.copy2(src, dst)
            manifest_lines.append(f"{hashlib.sha256(open(dst, 'rb').read()).hexdigest()}  {p}")
    with open(os.path.join(dest, "MANIFEST.txt"), "w", encoding="utf-8") as mf:
        mf.write("\n".join(manifest_lines) + "\n")
    print(f"Snapshot of existing AOS tree saved to: {dest}")

def main():
    snapshot_existing()
    create_dirs()

    # 1. AGENTS.md
    write_file("AGENTS.md", """
# Malt Radar Agent Operating Instructions

## Mission

Maintain and improve Malt Radar while preserving data quality,
traceability, correctness, and evidence-based validation.

## Default Mode

Start in read-only mode.

Never assume modifications are required.

Inspect before acting.

## Evidence Requirements

Every important conclusion must be supported by evidence.

Never trust aggregate parser metrics alone.

Validate using source material whenever possible.

## Validation Requirements

Require:

- traceability
- random sampling
- source verification
- cross-page validation

## Database Safety

Before modifying a database:

1. create backup
2. inspect impact
3. apply change
4. verify results

## Completion Requirements

Before reporting success:

- verify outputs
- verify consistency
- check git status
- check validation results

## Product Rule

Price information may exist in storage.

Price information must never be exposed in UI or API.

## Escalation Rule

When confidence is low:

- stop
- explain uncertainty
- request additional verification
""")

    # 2. rules/01-readonly-first.md
    write_file("rules/01-readonly-first.md", """
# Rule 01: Read-Only First Protocol

All agents must default to Read-Only mode at the start of any task.

## Rules of Engagement:
1. Do not modify databases or files on initialization.
2. Read schemas, run count queries, and inspect logs first.
3. Validate environment state and DB hashes before drafting changes.
4. If a task is investigatory or analysis-only, never write files or execute git operations.
""")

    # 3. rules/02-data-integrity.md
    write_file("rules/02-data-integrity.md", """
# Rule 02: Data Integrity & DB Safety

Preserve the integrity of `production.db` at all costs.

## DB Rules:
1. Always create a pre-write backup in `output/import/backups/` named `production_[stage]_pre_[timestamp].db`.
2. Compute and log pre-write and post-write SHA256 hashes.
3. Run all writes inside a transaction (`BEGIN TRANSACTION` / `COMMIT`).
4. Execute `ROLLBACK` immediately if any error occurs.
5. Post-validation must include `PRAGMA integrity_check` and `PRAGMA foreign_key_check`.
""")

    # 4. rules/03-validation.md
    write_file("rules/03-validation.md", """
# Validation Rules

Validation must not rely on aggregate metrics alone.

Minimum process:

1. source review
2. sample validation
3. cross-page validation
4. consistency review

Validation reports must document evidence.
""")

    # 5. rules/04-traceability.md
    write_file("rules/04-traceability.md", """
# Traceability Rules

Every important fact should be linked to:

- source
- extraction path
- validation status

Untraceable information must be flagged.

Do not present assumptions as facts.
""")

    # 6. rules/05-release.md
    write_file("rules/05-release.md", """
# Rule 05: Release & Verification Protocol

Before final delivery or promotion:
1. Run a full verification check (counts, hashes, schema check).
2. Execute automated test suites if available.
3. Log clean workspace status with `git status --short`.
4. Produce a gate report file and release checklists.
""")

    # 7. rules/06-product-rules.md
    write_file("rules/06-product-rules.md", """
# Product Rules

Price data:

Allowed:
- storage
- analysis
- internal processing

Not allowed:
- UI display
- API responses
- recommendation weighting

The user-facing system should remain price-independent.
""")

    # 7b. rules/08-cost-policy.md
    write_file("rules/08-cost-policy.md", """
# Rule 08: AOS Cost Policy

This rule governs how the Agent Operating System (AOS) spends money and compute.
It is mandatory for every gate report and every execution decision.

## Default Execution Policy

Every task MUST start in this mode unless explicitly overridden:

- **Local** — run on the local machine / local compute
- **Offline** — do not require network access to complete standard work
- **Deterministic** — same input produces the same output; no hidden randomness

## LLM Usage Is Optional

LLM usage is **OPTIONAL** and must **never be required** for the standard
Malt Radar pipeline.

The pipeline must be able to complete end-to-end using only local deterministic
processing. Any LLM step is an enhancement, not a dependency.

## Priority Order (strict)

When a task needs computation, select the cheapest viable option in this order:

1. **Local deterministic processing** (regex, SQLite, fuzzy match, rules) — preferred
2. **Local open-source models** (local weights, no API) — if ML is genuinely needed
3. **Free hosted models** (rate-limited free tiers, no spend) — only if local is insufficient
4. **Paid APIs** — ONLY with explicit human approval before any call is made

Do not skip a lower tier to use a higher one. Do not pre-emptively assume a paid
API is required.

## Cost Gate Thresholds

Every execution is classified against its **actual API spend** (USD):

|| Gate | Condition | Meaning |
||------|-----------|---------|
|| `FREE_GO` | Cost == $0.00 | No API spend. Preferred outcome. |
|| `GO` | $0.01 – $0.49 inclusive | Trivial spend, auto-approved. |
|| `WARN_GO` | $0.50 – $1.00 inclusive | Moderate spend, flagged for review. |
|| `NO_GO` | > $1.00 | Blocked. Requires explicit approval before proceeding. |

Boundary convention: at exactly $0.50 the gate is `GO`; at exactly $1.00 the
gate is `WARN_GO`; anything above $1.00 is `NO_GO`.

The **default gate assumption is `FREE_GO`**. A task is only upgraded to a paid
gate when API spend actually occurs.

## Mandatory Gate Report Fields

Every gate report MUST include all four of the following:

- **Estimated API Cost** — predicted API spend before execution (USD)
- **Actual API Cost** — measured API spend after execution (USD)
- **Local Compute Used** — did the task rely on local compute? (Yes / No)
- **Fully Local Execution** — was the task completed with zero API calls? (Yes / No)

For the standard Malt Radar pipeline these default to `Estimated API Cost: $0.00`,
`Actual API Cost: $0.00`, `Local Compute Used: Yes`, `Fully Local Execution: Yes`.

The most desirable outcome is a **fully local execution with zero API cost**
(`FREE_GO`). Every paid-tier choice must be justified against this baseline.
""")

    # 8. workflows/audit.md
    write_file("workflows/audit.md", """
# Audit Workflow

1. **Pre-flight Check:** Get DB hash, verify schema stability, and check git status.
2. **Integrity Check:** Execute SQLite checks.
3. **Traceability Mapping:** Check sources of active database rows.
4. **Discrepancy Identification:** Generate discrepancy logs and delta matrices.
5. **Gate Classification:** Determine GO/NO-GO gate decision based on evidence.
""")

    # 9. workflows/import.md
    write_file("workflows/import.md", """
# Import Workflow

1. Source inventory
2. Import plan
3. Parsing
4. Mapping review
5. Sampling
6. Validation
7. Report
""")

    # 10. workflows/validation.md
    write_file("workflows/validation.md", """
# Validation Workflow

Phase 1
- Read-only inspection

Phase 2
- Source inventory

Phase 3
- Sample review

Phase 4
- Cross-page validation

Phase 5
- Consistency analysis

Phase 6
- Validation report
""")

    # 11. workflows/normalization.md
    write_file("workflows/normalization.md", """
# Normalization Workflow

1. **String Cleaning:** Strip whitespace, lowercase names, and remove extra spaces.
2. **ABV Cleaning:** Extract decimals, strip "%" symbols, and cast to Float.
3. **Age Cleaning:** Standardize "yo", "years old" to numerical format or "NAS" for No Age Statement.
4. **Distillery Matching:** Perform fuzzy match against the master company/distillery dictionary.
""")

    # 12. workflows/release.md
    write_file("workflows/release.md", """
# Release Workflow

1. **Staging Snapshot:** Extract candidates and freeze staging table state.
2. **Pre-Merge Audit:** Run pre-merge check list.
3. **Transaction Execution:** Run the merge script.
4. **Post-Validation:** Verify counts, verify no leakage, check validation sample.
5. **Release Log:** Create release checklist report and freeze production DB hash.
""")

    # 13. memory/flavor-system.md
    write_file("memory/flavor-system.md", """
# Flavor Axes

Current flavor dimensions:

- smoky
- peaty
- fruity
- sweet
- spicy
- maritime
- sherry

New dimensions require justification and validation.
""")

    # 14. memory/architecture.md
    write_file("memory/architecture.md", """
# Architecture Memory

- **Database:** SQLite (`production.db`) containing distilleries, whiskies, tasting_notes, flavor_profiles, and price_history.
- **NLP Flavor Engine:** Uses anchor-guided regex pattern scanners (sliding window around flavor anchors) to assign ratings on 7 flavor dimensions.
- **Identity Resolver:** Employs string normalization and Levenshtein fuzzy matching to resolve new expressions to master products.
""")

    # 15. memory/glossary.md
    write_file("memory/glossary.md", """
# Glossary of Terms

- **Zero-Vector:** A flavor profile where all 7 axes are scored as `0.0`.
- **Low Risk Candidates:** Cleanly matched entities with high confidence and verified source files.
- **Orphans:** Staging records that link to a nonexistent `whisky_id`.
- **Hold Records:** Staging records with medium/high risk that are quarantined from merging.
""")

    # 16. memory/project-principles.md
    write_file("memory/project-principles.md", """
# Malt Radar Principles

Prioritize accuracy over speed.

Prioritize evidence over assumptions.

Prioritize reproducibility over convenience.

Prioritize traceability over volume.

Every dataset should be explainable.

Every recommendation should be traceable.
""")

    # 17. prompts/auditor.md
    write_file("prompts/auditor.md", """
You are the Malt Radar Auditor.

Follow AGENTS.md.

Operate in read-only mode.

Look for:

- data quality issues
- validation gaps
- traceability problems
- normalization inconsistencies

Produce findings only.

Do not modify files.
""")

    # 18. prompts/validator.md
    write_file("prompts/validator.md", """
You are the Malt Radar Validator.

Follow AGENTS.md.

Never rely on aggregate metrics alone.

Require:

- evidence
- traceability
- sample review
- cross-page validation

Provide confidence assessment.
""")

    # 19. prompts/architect.md
    write_file("prompts/architect.md", """
You are the Malt Radar Architect.

Follow AGENTS.md.

Design clean structures, maintain schema integrity, plan refactoring steps, and align directories without corrupting system state.
""")

    # 20. prompts/importer.md
    write_file("prompts/importer.md", """
You are the Malt Radar Importer.

Follow AGENTS.md.

Perform structured mapping, validate keys/FK constraints before merging, enforce transaction safety, and verify after importing.
""")

    print("Malt Radar AOS v1 files generated successfully!")

if __name__ == '__main__':
    main()
