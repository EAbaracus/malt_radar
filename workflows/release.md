# Release Workflow

1. **Staging Snapshot:** Extract candidates and freeze staging table state.
2. **Pre-Merge Audit:** Run pre-merge check list.
3. **Transaction Execution:** Run the merge script.
4. **Post-Validation:** Verify counts, verify no leakage, check validation sample.
5. **Release Log:** Create release checklist report and freeze production DB hash.
