# 04 — Integrity Check (P245C-5)

## git fsck --full
- Exit code: **0** (`fsck_ok=True`)
- After `reflog expire --expire=now --all` + `git gc --prune=now` + `commit-graph write --reachable`, re-run fsck reported NO errors.
- First fsck (pre-gc) showed stale `commit-graph` entries referencing pre-rewrite commits; cleared by gc + commit-graph rebuild. Re-fsck clean.
- size-garbage post-gc: 0 bytes.
