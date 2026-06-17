# Gitignore Hardening Plan

## Safe patterns to add
| Pattern | Reason |
|---|---|
| `investigate_*.py` | Developer scratchpad scripts used for temporary debugging. |
| `scratch_*.py` | Temporary code snippets and experiments. |
| `tracked_files*.txt` | Output logs generated locally by tracking scripts. |
| `test_row.py` | Local debugging script. |
| `verify_db_api.py` | Local API verification script, duplicate of proper testing infrastructure. |
| `00_api_feasibility_report.txt` | Temporary or local feasibility report. |
| `etl/experiment_fix_42.py` | Experimental ETL fix script, not part of the active pipeline. |

## Not ignored yet
| Pattern/File | Reason |
|---|---|
| `scripts/run_production_restore_*.py` | Sensitive production DB logic. Must be manually reviewed before being ignored or deleted. |
| `scripts/run_recovery_candidate_*.py` | Recovery related, potentially dangerous. Must be manually reviewed. |
| `schema/` | Confirmed KEEP_AND_COMMIT. Already tracked. |
| `test_agent.py` & `repair_agent.py` | Core autonomous agent scripts. Already tracked. |
| `scripts/run_phase*.py` | Historical pipeline execution scripts. Held back because some might be refactored into generic utilities, or they might be moved to a local archive folder instead of just ignored. |
| `output/filestructure/*.md` | The `output/` directory is already globally ignored by `.gitignore`. Specific reports are force-added (`git add -f`) when they need tracking, no new pattern needed. |

## Risks
- Ignoring files without deleting them leaves them in the working directory indefinitely. If a developer runs them accidentally, they could still affect the system.
- `etl/experiment_fix_42.py` is highly specific; ignoring it leaves an orphaned script in the `etl` folder.
- Phase execution scripts (`scripts/run_phase*.py`) currently clutter the `scripts/` directory and will still show up as untracked until we decide on archiving vs ignoring them.

## Recommended .gitignore patch
```gitignore
# Temporary Scratchpads & Debug Scripts
investigate_*.py
scratch_*.py
test_row.py
verify_db_api.py

# Local Reports & Logs
tracked_files*.txt
00_api_feasibility_report.txt

# Experimental / Deprecated
etl/experiment_fix_42.py
```
