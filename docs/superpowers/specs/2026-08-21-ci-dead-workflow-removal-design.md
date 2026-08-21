# CI Dead Workflow Removal — Design

**Date:** 2026-08-21
**Status:** Approved (design), pending implementation
**Scope:** `malt_radar` CI surface only
**Type:** Removal-only change (no new behaviour, no new code)

---

## 1. Problem

Three defects were found in the `malt_radar` CI surface. All three share a
property: they are invisible during normal work, so they persist.

### 1.1 `deploy-pages.yml` deploys to a target that does not exist

The workflow runs on every push to `main`, builds Flutter web, and calls
`cloudflare/pages-action@v1` against Pages project `malt-radar`.

Evidence collected 2026-08-21:

| Check | Result |
|---|---|
| `gh run list --workflow="Deploy to Cloudflare Pages"` | last 3 runs = **failure** |
| Run log (`32466305954`) | `{"success":false,"errors":[{"code":10000,"message":"Authentication error"}]}` then `Error: Failed to get Pages project, API returned non-200` |
| `curl https://malt-radar.pages.dev` | `Could not resolve host` — **NXDOMAIN** |
| `curl -I https://maltradar.com` | `HTTP/1.1 200 OK`, `Server: cloudflare` |
| `deploy_seo.sh` | `ssh -> /srv/maltradar -> docker + Caddy` |

The real production deploy path is the VM (`/srv/maltradar`, Docker + Caddy)
driven by `deploy_seo.sh`. The Cloudflare Pages project was never created.

**The token is not the root cause.** Fixing `CLOUDFLARE_API_TOKEN` would make
the workflow authenticate and then fail on a non-existent project. The
workflow itself is the defect.

Cost per push: ~2-3 min of CI time spent on a Flutter web build whose output
is discarded, plus one failure notification.

### 1.2 Ghost workflow registrations

`gh api repos/EAbaracus/malt_radar/actions/workflows` lists
`webapp-next-deploy.yml` and `golden-regen.yml` as `state: active`, but
neither file exists in `.github/workflows/`. `webapp-next/` does not exist in
the repo either (`404`).

These are residual registrations from deleted workflows. They cannot trigger
(a workflow without a file does not run), so they are noise rather than risk.

### 1.3 Root `tests/` runs in no CI job — the most serious finding

```
Repo Gates  ->  python -m pytest backend/tests     (24 files)
root tests/ ->  19 files, referenced by NO workflow
```

Verified: `grep -rn "pytest" .github/workflows/` returns only the
`backend/tests` invocation.

`docs/KNOWN_ISSUES_pre-existing-test-failures.md` documents three broken tests
"tracked for follow-up". All three live in root `tests/`. Because CI never
runs that directory, their breakage is invisible — they are not "known broken
tests" so much as an **unmonitored test surface**.

`tests/conftest.py` sets `MALT_RADAR_DB_PATH=output/import/production.db`,
which is the likely reason the directory was never wired into CI.

---

## 2. Scope

### In scope

| # | Change | Rationale |
|---|---|---|
| 1 | Delete `.github/workflows/deploy-pages.yml` | Target Pages project does not exist; real deploy is `deploy_seo.sh` |
| 2 | Verify ghost workflow registrations, report only | Files already absent; no safe CLI path to force-remove registrations |
| 3 | Delete `.github/workflows/codeql.yml.disabled` | CodeQL already runs via default setup; a `.disabled` file is dead weight |
| 4 | Update `docs/KNOWN_ISSUES_pre-existing-test-failures.md` | Record *why* the three failures went unnoticed; hand the decision to a separate spec |

### Explicitly out of scope

- **Wiring root `tests/` into CI.** The `conftest.py` -> synthetic-DB migration
  is its own design problem under the standing "production DB is read-only"
  constraint. Deferred to a separate spec (see §6).
- **Fixing the three known-broken tests.** Same spec as above.
- **Root script clutter** (`p95a_certify.py`, `p96_pipeline.py`, `repair_agent.py`,
  `.md.txt` artefacts). Separate work item.
- **`Repo Gates` and `Android Release CI/CD`.** Both green and functioning.
  Not touched.

---

## 3. Architecture impact

None.

Neither deleted workflow is invoked by another workflow, and neither sits on
the production deploy path. The production chain
(`deploy_seo.sh` -> ssh -> `/srv/maltradar` -> Docker + Caddy) is entirely
independent of the GitHub Actions surface being changed.

Active workflow count goes from 4 to 2 — the two that actually work.

---

## 4. Implementation

### Step 0 — Pre-flight verification (before any deletion)

```bash
curl -sSI https://maltradar.com
nslookup malt-radar.pages.dev
grep -rn "deploy-pages" --include="*.yml" --include="*.sh" --include="*.md" .
```

The `grep` is the gate. If any script, document, or workflow references
`deploy-pages.yml`, **stop and report** — that dependency is resolved first.
Expected result: zero references.

If `maltradar.com` returns anything other than a healthy 200, **stop** and
investigate before deleting anything.

### Step 1 — Delete (single commit)

- `.github/workflows/deploy-pages.yml`
- `.github/workflows/codeql.yml.disabled`

### Step 2 — Ghost registrations

Query the workflows API and confirm current state. Do **not** attempt forced
removal via API — there is no safe `gh` path for this and the registrations
are inert. Report whatever remains.

### Step 3 — Documentation

Update `docs/KNOWN_ISSUES_pre-existing-test-failures.md` with:
- the finding that root `tests/` executes in no CI job,
- the resulting conclusion that the three failures were never being observed,
- an explicit handoff to the follow-up spec.

No new document is created; the existing one is amended.

---

## 5. Error handling and rollback

| Scenario | Behaviour |
|---|---|
| Step 0 finds a `deploy-pages` reference | **STOP.** Report. No deletion. |
| `maltradar.com` returns an unexpected response | **STOP.** Investigate first. |
| `Repo Gates` breaks after the commit | `git revert <sha>` — single commit, single operation |

Deleted files remain in git history; nothing is unrecoverable.

---

## 6. Verification

This change contains no code, so there are no unit tests. Verification is
observational, and every item must be evidenced:

1. `deploy-pages.yml` and `codeql.yml.disabled` absent — confirmed via `git log`
2. After the next push, `gh run list` shows **no** "Deploy to Cloudflare Pages" entry
3. `Repo Gates` = success **and** `Android Release CI/CD` = success (no regression)
4. `curl https://maltradar.com` = 200 (production unaffected)
5. `docs/KNOWN_ISSUES_pre-existing-test-failures.md` contains the handoff record

### Measurable gain

- ~2-3 min of CI time reclaimed per push
- One failure notification per push eliminated
- Active workflow surface: 4 -> 2

---

## 7. Deferred decision (separate spec)

> The 19 files in root `tests/` run in no CI job. `tests/conftest.py` depends on
> `production.db`. Wiring these into CI with a synthetic database requires its
> own design under the standing "production DB is read-only" constraint. The
> three broken tests recorded in `KNOWN_ISSUES_pre-existing-test-failures.md`
> fall within that spec's scope, not this one.

---

## 8. Commit discipline

Single atomic commit. The commit message carries the evidence for *why* each
file was removed (NXDOMAIN result and the real deploy path), so the reasoning
survives without this document.

Per standing user preference, `push` requires explicit GO.
