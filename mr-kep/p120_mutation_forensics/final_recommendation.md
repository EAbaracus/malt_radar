# Final Recommendation — P120 Mutation Forensics

## Final Decision
# NO-GO

Do **not** start Sprint 08 (or any ingestion sprint) yet. The forensic pass is
complete and the immediate write burst has stopped, but the conditions for safe
ingestion are not met.

## What must STOP / be resolved before further ingestion
1. **Identify and confirm the writer is stopped.** The bulk importer that added
   +1,192 rows is not currently running, but its exact identity was never captured.
   Confirm no scheduled task / IDE run-config / manual shell will re-trigger it.
   (A `schtasks` filter for whisky/import/seed returned nothing, but a one-off
   manual run cannot be excluded — verify with the operator.)
2. **Freeze a clean snapshot.** Take a copy + SHA-256 of the now-stable
   `production.db` (currently `b18c2429…ba25ef1`, 4,749 rows, mtime 21:17:54) and
   record it as the ingestion baseline. Do NOT modify the live file.
3. **Re-baseline the corpus audit.** Regenerate the 6 P103 reports against the
   stable universe = **4,749** (coverage = 1,737 / 4,749 = **36.6%**). The earlier
   48.8 % / 44.8 % figures are superseded.
4. **Add a guard against recurrence.** E.g. make `production.db` read-only (or
   move it to an archive path) during ingestion sprints, or require an explicit
   write-lock token, so a stray bulk import cannot shift the denominator mid-sprint.

## What was done (compliant)
- ✅ Read-only forensic diff, process capture, PRAGMA fingerprint.
- ✅ No database modified, no schema repair, no vacuum/checkpoint.
- ✅ No process killed (the suggested `taskkill python.exe` would have killed the
   agent/desktop app and was rejected as unsafe + unnecessary).
- ✅ No commit, no file rename/move, no Sprint 08 started.

## Suggested next steps (require explicit user go-ahead)
- Regenerate P103 corpus-audit reports against universe 4,749.
- Begin Sprint 08 only after items 1–4 above are satisfied and the user approves.

## STOP.
