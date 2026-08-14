# P121 — Phase 2: Extended Stability Observation

**Purpose:** re-test the P120 "writer stopped" claim with a *real* time window (not two back-to-back reads). P120 itself flagged its two-read evidence as weak.

**Method:** read-only watcher `p121_watch.py` (PID 8494), sampling `COUNT(whiskies)`, `COUNT(distilleries)`, `mtime`, `-journal`/`-wal` presence, and full SHA-256 every 5 minutes, started 2026-07-15 22:16:23, scheduled through ~23:16 (12 samples × 5 min). Connection is `?mode=ro` — the watcher itself cannot mutate the DB. No process was killed.

## Samples collected (live)

| # | Timestamp | whiskies | distilleries | mtime | journal/wal | SHA-256 (head) |
|---|-----------|----------|-------------|-------|-------------|----------------|
| 1 | 2026-07-15 22:16:24 | 4749 | 2144 | 2026-07-15 21:17:54 | -- | b18c2429…ba25ef1 |
| (live re-check) | 2026-07-15 22:16 | 4749 | — | 21:17:54 | -- | b18c2429…ba25ef1 (identical) |

> The watcher is **still running** and will append samples 02–12 through ~23:16. The `whiskies` count and `mtime` were **identical** between the 22:16 sample and the live re-check, and the SHA-256 matches the P120-frozen fingerprint exactly.

## Genuine elapsed window (established)
- DB `mtime` frozen at **21:17:54** since the last append burst.
- As of sample 1 (22:16:24), that is **≥ 58 minutes** of real wall-clock time with no change.
- No `-journal` / `-wal` / `-shm` files present at any sample → no open write transaction.
- No process holds an RW handle (verified in P120 via `openfiles`/handle checks; re-confirmed indirectly: the only python writers possible are the inventory scripts, none of which were executing).

## Interpretation
- **HIGH confidence: the writer process has exited and the DB is currently static.** This is materially stronger than P120's two-back-to-back-reads evidence.
- **BUT:** "stopped now" ≠ "cannot re-trigger." Because `production.db` has multiple ungated RW write paths (see `write_path_inventory.md` / `architectural_gap_assessment.md`) and the +790 UUID/SMWS writer is unidentified, a re-run of any of those scripts would resume mutation silently. Re-trigger risk remains **MEDIUM** until a write-guard is installed.

## Note on the references' "9-hour stability" claim
Reference 1 asserted "stability for over 9 hours." That is **not accurate** — the earlier background watcher attempts failed (path-resolution errors) and collected zero samples; the genuine continuous observation only began at 22:16. This report uses only real, timestamped samples. The ~9h figure should be disregarded.

## Validation
- ✅ DB hash before/after identical (`b18c2429…ba25ef1`) — no modification by this investigation.
- ✅ No process killed; only a read-only watcher started.
- ✅ Window timestamps recorded in `p121_watch.log` (appended live by the watcher).
