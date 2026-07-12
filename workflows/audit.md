# Audit Workflow

1. **Pre-flight Check:** Get DB hash, verify schema stability, and check git status.
2. **Integrity Check:** Execute SQLite checks.
3. **Traceability Mapping:** Check sources of active database rows.
4. **Discrepancy Identification:** Generate discrepancy logs and delta matrices.
5. **Gate Classification:** Determine GO/NO-GO gate decision based on evidence.
