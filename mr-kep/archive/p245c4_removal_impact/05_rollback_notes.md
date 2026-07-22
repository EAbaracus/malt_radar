# 05 — Rollback Notes (P245C-4)

Existing rollback bundles from prior phases (NOT created in this read-only step):

- `rollback_before_p245c2.bundle` — 19606885 MB (at `C:/Users/eltun/AppData/Local/Temp/`)
- `rollback_before_rewrite.bundle` — 27564938 MB (at `C:/Users/eltun/AppData/Local/Temp/`)

## Rollback procedure (if a future P245C-3 removal rewrite goes wrong)

```bash
# Option A: clone true originals from the earliest bundle
git clone C:/Users/eltun/AppData/Local/Temp/rollback_before_rewrite.bundle recovered_repo

# Option B: in-place restore specific refs from P245C-2 bundle
git fetch C:/Users/eltun/AppData/Local/Temp/rollback_before_p245c2.bundle \
  'refs/heads/feature/editorial-crawl-phase:refs/heads/rollback-target'
git reset --hard rollback-target   # AFTER careful review
```

**Note:** The P245C-2 bundle captures the repo state BEFORE this hidden-data pass,


This step performed NO mutation — bundles were only inspected, not created.
