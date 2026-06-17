# Phase 10G Untracked File Review

Date: 2026-06-17

## Decision

The Phase 10G automated commit flow must not commit remaining untracked operational scripts automatically.

## Current Buckets

### Keep For Manual Review

These files may be useful project history or operational tooling, but they include database access, migration, phase execution, or git workflow behavior. They require explicit human review before tracking:

- `apply_10e_fix.py`
- `run_10f_smoke_test.py`
- `run_10g_dry_run.py`
- `scripts/apply_code_hardening_patches.py`
- `scripts/apply_phase5a_schema_patch.py`
- `scripts/dump_ddl.py`
- `scripts/generate_phase6_design.py`
- `scripts/inspect_master_cols.py`
- `scripts/inspect_phase6_schema.py`
- `scripts/run_code_hardening_analysis.py`
- `scripts/run_db_source_reconciliation.py`
- `scripts/run_phase10a.py`
- `scripts/run_phase10b.py`
- `scripts/run_phase10c.py`
- `scripts/run_phase10d.py`
- `scripts/run_phase5_staging_import_execute.py`
- `scripts/run_phase5a_analysis.py`
- `scripts/run_phase5c_deduplication.py`
- `scripts/run_phase6a_schema_dry_run.py`
- `scripts/run_phase6b_migration_execution.py`
- `scripts/run_phase6c_query_dry_run.py`
- `scripts/run_phase6d_api_dry_run.py`
- `scripts/run_phase6e_dry_run_test.py`
- `scripts/run_phase6f_integration_test.py`
- `scripts/run_phase6g_action_dry_run.py`
- `scripts/run_phase6h_planning.py`
- `scripts/run_phase6i_controlled_write.py`
- `scripts/run_phase6j_planning.py`
- `scripts/run_phase6k_controlled_write.py`
- `scripts/run_phase6l_planning.py`
- `scripts/run_phase6m_api_session.py`
- `scripts/run_phase6n_readiness_assessment.py`
- `scripts/run_phase6p.py`
- `scripts/run_phase6q.py`
- `scripts/run_phase6r.py`
- `scripts/run_phase7a.py`
- `scripts/run_phase7b.py`
- `scripts/run_phase7c.py`
- `scripts/run_phase7d.py`
- `scripts/run_phase7e.py`
- `scripts/run_phase7f.py`
- `scripts/run_phase7g.py`
- `scripts/run_phase7h.py`
- `scripts/run_phase8a.py`
- `scripts/run_phase8b.py`
- `scripts/run_phase8c.py`
- `scripts/run_phase8d.py`
- `scripts/run_phase8e.py`
- `scripts/run_phase8f.py`
- `scripts/run_phase8g.py`
- `scripts/run_phase9a.py`
- `scripts/run_phase9b.py`
- `scripts/run_phase9b_commit.py`
- `scripts/run_phase9c.py`
- `scripts/run_schema_integrity_audit.py`

### Keep Local / Forbidden For Automation

These files are restore or recovery related. They must remain excluded from automated staging and commit:

- `scripts/run_production_restore_dry_run.py`
- `scripts/run_production_restore_execution.py`
- `scripts/run_recovery_candidate_build.py`
- `scripts/run_recovery_candidate_completion.py`
- `scripts/run_recovery_candidate_completion_v2.py`

### Local Report Candidate

This file is a local status snapshot and does not need to be tracked unless explicitly needed for audit history:

- `git_status_before_android_qa.txt`

## Automation Guardrail

`RepoAgent` now preserves leading spaces in `git status --porcelain` output and validates the staged index before commit. If any non-`SAFE_STAGE` file is already staged, the agent removes it from the index and refuses to include it in the auto-commit.
