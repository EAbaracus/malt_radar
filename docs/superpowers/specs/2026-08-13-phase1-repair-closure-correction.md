# Phase 1 Repair Closure Correction Addendum

**Status:** Independent correction addendum — original repair closure is untouched
**Phase:** AL-MD-01 / Phase 1 identity propagation
**Scope:** Correct the recorded evidence; this document performs no production mutation and grants no apply or baseline GO.
**Prepared:** 2026-08-14

## 1. Purpose

The original repair closure contains an incorrect update arithmetic claim and references backup files whose provenance as the Phase 1 pre-apply backup could not be established. This addendum records the independent evidence and supersedes neither the original closure nor its historical hashes.

## 2. Original claim vs independently verified result

| Item | Original closure claim | Independent result | Verdict |
|---|---|---|---|
| Update arithmetic | `6,332` updates, described through `3,000 + 3,311 + 833` | **4,143 cell updates** = `3,310 country + 833 region` | Original arithmetic is false |
| Row delta | `0` table-row delta | `0` rows for `whiskies`, `distilleries`, `flavor_evidence`, `flavor_profiles` | Confirmed |
| Post-apply production SHA | `70fa9cf0…` | `70fa9cf001c981af991c7382485378ac9caa607b98a7168f54fc9bcfb0f208e3` | Confirmed |
| Referenced backups | `production.db.bak.adhoc_supersede` and `production.db.bak.adhoc_supersede_apply` treated as Phase 1 backup evidence | Both exist, but neither SHA equals the known pre-apply SHA and their Phase 1 provenance is not established | Unresolved / not admissible as Phase 1 backup evidence |
| Verified pre-state copy | Not correctly identified in original closure | `output/import/backups/production_pre_phase1_external_mutation_20260813_234617.db`, SHA `a9960053da30cc8da0897919c5e25392a7fc1c0f5ffed46a0d4325df7eaab6b4` | Independently verified pre-state snapshot |

### Arithmetic detail

The original expression is mathematically inconsistent:

```text
3,000 + 3,311 + 833 = 7,144, not 6,332
```

The independent row-level comparison against the verified pre-state found:

```text
country: 3,310 newly filled cells
region:    833 newly filled cells
-----------------------------------
total:   4,143 cell updates
```

`3,311` is consistent with a post-state total of filled country cells in the closure context; it is not the country update delta. The pre-state country-filled count was `161`, and the post-state count was `3,471`, yielding `3,310` updates.

## 3. Verified pre-state and post-state evidence

### Verified pre-state

```text
Path: C:\Users\eltun\Documents\malt radar CLEAN\output\import\backups\production_pre_phase1_external_mutation_20260813_234617.db
SHA-256: a9960053da30cc8da0897919c5e25392a7fc1c0f5ffed46a0d4325df7eaab6b4
Size: 14,139,392 bytes
```

This file was copied from the previously observed read-only snapshot:

```text
C:\Users\eltun\AppData\Local\Temp\d2_i_both_1zyxrohc\stash_hold.db
```

Source and destination SHA values matched. The destination has a separate inode from the source and was independently re-hashed after copying.

### Current production

```text
Path: C:\Users\eltun\Documents\malt radar CLEAN\output\import\production.db
SHA-256: 70fa9cf001c981af991c7382485378ac9caa607b98a7168f54fc9bcfb0f208e3
PRAGMA integrity_check: ok
Foreign-key violations: 0
```

## 4. Remaining scope — independently recomputed

The current production database was opened with a strict read-only SQLite URI. Candidate predicates were recomputed directly from live rows:

- active whisky: `superseded_by IS NULL OR superseded_by=''`
- target cell: `whiskies.country` or `whiskies.region` is `NULL` or empty
- source: joined `distilleries.<same_column>` is non-empty
- candidate IDs sorted before hashing

| Remaining field | Count | Candidate-set SHA-256 | Duplicate IDs |
|---|---:|---|---:|
| `country` | **434** | `4b68385c1d5766d4a170e0a7588b89484e54f228fccbda144437fb52194a676e` | 0 |
| `region` | **9** | `273bb0855c16965791c029919a5ca678762a28d2cab2051644010588ec96ddd5` | 0 |
| **Total cells** | **443** | N/A | N/A |

Independent structural checks:

```text
whiskies rows: 4,750
active whiskies: 4,598
distilleries rows: 2,144
integrity_check: ok
foreign_key_check: 0
country conflicts: 31
region conflicts: 134
```

The `434/9` values are remaining candidate counts, not filled-cell totals.

## 5. Adhoc backup provenance — forensic status

**Status: RESOLVED FOR PHASE 1 — LOW-PRIORITY REPO-HYGIENE BACKLOG.**

The files are not admissible as Phase 1 backup evidence. Their birth times are 11 days before the Phase 1 mutation window, and the compiled helper is a dry-run artifact with no evidence of a production write. The exact historical operator/source is still unknown, so the source-file gap remains a separate low-priority hygiene item.

Observed facts:

- `production.db.bak.adhoc_supersede`:
  - birth: `2026-08-02 11:58:10.232855500 +0300`
  - mtime: `2026-08-01 18:05:37.081368300 +0300`
  - SHA-256: `dfc26512e3e67f7c7d98a81046ab5616685bc40b98ee3a32b245060063abb56f`
- `production.db.bak.adhoc_supersede_apply`:
  - birth: `2026-08-02 12:00:00.645507200 +0300`
  - mtime: `2026-08-01 18:05:37.081368300 +0300`
  - SHA-256: `dfc26512e3e67f7c7d98a81046ab5616685bc40b98ee3a32b245060063abb56f`
- Neither SHA equals the verified Phase 1 pre-state SHA `a9960053…`.
- Both files are separate regular files with link count `1`.
- No tracked git history entry or repository source/docs match was found for the literal `adhoc_supersede` name.
- `.hermes/` contains no match.
- A compiled, untracked/stale helper artifact exists at `scripts/__pycache__/adhoc_supersede_dry_run.cpython-311.pyc`, with birth/mtime `2026-08-02 11:57:13.756944100 +0300`. Its embedded constants identify `output/import/production.db` and `output/import/production.db.bak.adhoc_supersede`; it performs `shutil.copy2`, opens SQLite, and prints a dry-run report. The source `.py` is absent from the current tree, so the exact historical execution and operator cannot be proven from repository source.
- The nearby `output/import/production_backup_r32.db` has the same size but a different SHA (`1edb0eb3…`), so it is not interchangeable evidence for either adhoc file.

This evidence is sufficient to exclude the files from Phase 1 backup provenance: they pre-date the Phase 1 mutation window by 11 days and the compiled helper is a dry-run artifact with no evidence of a production write. The exact historical operator/source remains unknown and is retained as a separate low-priority repository-hygiene backlog item. The files must not be used as Phase 1 backup evidence.

## 6. Closure and baseline decision

```text
Phase 1 closure: CLOSED — CORRECTED BY THIS ADDENDUM
Post-apply SHA baseline update: COMPLETED
Backup provenance: EXCLUDED FROM PHASE 1; LOW-PRIORITY HYGIENE BACKLOG
Original closure: retained unchanged as historical record
```

This addendum is the authoritative correction record for Phase 1 closure. It does not edit the original closure, production DB, or existing backups. The post-apply SHA is now the production baseline in `AGENTS.md`; historical SHA records remain immutable.

## 7. Evidence commands

The independent checks used:

```text
stat -c 'path=%n inode=%i links=%h size=%s birth=%w mtime=%y ctime=%z' output/import/production.db.bak.adhoc_supersede*
git log --all --full-history --name-status -- '**/*supersede*'
git grep -n -i 'adhoc_supersede' <recent git revisions>
```

All database reads for the recomputation used `file:<absolute-path>?mode=ro`. No production or existing backup write was performed while preparing this addendum.

## 8. Pending forensic action

Optional hygiene follow-up: recover the missing `scripts/adhoc_supersede_dry_run.py` source or record its historical owner from shell/IDE execution history. This follow-up does not block Phase 1 closure or the post-apply baseline update because the artifact is proven to pre-date the Phase 1 mutation window and is excluded from Phase 1 backup evidence.

---

**Addendum verdict:** CORRECTED CLOSURE RECORD — GO EXECUTED.
