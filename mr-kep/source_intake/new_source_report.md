# P103 Source Intake \u2014 New Source Report

**Book:** The Complete Whiskey Course \u2014 Robin Robinson
**File:** `data/books/The Complete Whiskey Course -- Robin Robinson --.epub`
**Stage:** READ-ONLY PRE-FLIGHT \u2014 no enrichment, no DB writes, no citations/evidence/facts/vectors created.
**Generated:** 2026-07-15T15:40:00Z

---

## 1. Recommendation: **CONDITIONAL GO**

The book is a **unique, clean, extractable** source with **zero collision risk** against the existing
registry, `knowledge.db` book identities, or B1/B2/B3. It is safe to register and queue.
Two conditions must be settled before any enrichment run (Sprint 04): the **EPUB extraction path**
and **formal B8 matrix registration** (see \u00a76).

---

## 2. Source Identity & Metadata (extracted from file)

| Field | Value | Evidence |
|---|---|---|
| Title | The Complete Whiskey Course | EPUB DC:title |
| Author | Robin Robinson | EPUB DC:creator |
| Year | 2019 | DC:rights "Copyright \u00a9 2019" |
| ISBN | **9781454932215** | EPUB DC:identifier `978-1-4549-3221-5` |
| Publisher | Sterling Epicure | EPUB DC:publisher |
| Language | en-US | EPUB DC:language |
| Format | EPUB (reflowable) | file type |
| Size | 23,885,526 bytes | filesystem |
| **SHA256** | `659f2d4cf3c651d6b805c04d204e5acaf4296b5c5fcf6d84240df60f17e3fa2f` | streamed SHA256 (real) |

---

## 3. Extraction Compatibility \u2014 **VERIFIED**

- `ebooklib.read_epub` + `bs4.get_text` parses the file: **20 content documents**, **466,957 characters** extracted.
- This is the **same extraction stack** already used by `scripts/manual_sources/extract_epub_text.py` \u2014 so EPUB is a known-good path in this repo.
- **Caveat:** the book is **EPUB, not PDF**. Sprint 01\u201303 enrichment scripts use `pypdf` (fixed pages). A Sprint 04 loader must swap the text step for EPUB (documents instead of pages). The downstream resolver/consensus/loader are format-agnostic \u2014 **no schema change required**.

---

## 4. Comparison vs Registered Books (B1 / B2 / B3)

| ID | Book | Scope | Overlap with new? |
|---|---|---|---|
| B1 | Malt Whisky Yearbook 2019 (Ronde) | Annual distillery directory, factual metadata | None (different author/title) |
| B2 | World Atlas of Whisky (Broom) | Region structure + distillery profiles + flavor | None (different author/title) |
| B3 | Michael Jackson World Guide (1987) | Historical distillery facts | None (different author/title) |
| **NEW** | **Robin Robinson \u2014 The Complete Whiskey Course (2019)** | **Contemporary educational course book** | **Distinct identity; no collision** |

The new book is a **contemporary educational** source (production, tasting, types, brands) \u2014 distinct in
scope and vintage from the historical (B3) and reference (B1/B2) sources already ingested.

---

## 5. Collision Checks \u2014 **ALL CLEAR**

| Check | Result |
|---|---|
| Content SHA256 already in `book_registry.json` | \u274c No |
| Duplicate filename in registry | \u274c No |
| Duplicate title (registry / knowledge.db) | \u274c No |
| Duplicate author (registry / knowledge.db) | \u274c No |
| Duplicate ISBN (registry / knowledge.db) | \u274c No |
| Proposed `book_id = BK_RR2020_B8` exists in knowledge.db | \u274c No (22 existing identities, none collide) |

No identity, hash, ISBN, title, or author collision. The proposed key `RR2020_B8` is **collision-free by construction**.

---

## 6. Contribution Estimate (READ-ONLY dry-run)

Method: ran the **frozen Sprint 01** extractor + production-lexicon loader **in memory only**
(no `knowledge.db`/`production.db` write), then measured overlap against current `canonical_vectors`
coverage (post S01\u2013S03).

| Metric | Value |
|---|---|
| Lexicon entries (production.db, read-only) | 13,330 |
| EPUB content documents | 20 |
| Entities matched | 389 |
| Resolved to `whisky_id` | 236 |
| Unresolved (distillery/partial) | 153 |
| **Resolution rate** | **60.67%** |
| Distinct whisky_ids touched | 236 |
| Already covered (by S01\u2013S03) | 217 |
| **Estimated net-new coverage** | **~19 whisky_ids** |
| **Estimated net-new flavor vectors** | **~19** |
| Manual review backlog | 153 unresolved entities |

**Interpretation:**
- **Coverage expansion:** *modest* \u2014 only ~19 net-new whisky_ids, because 217/236 touched ids are
  already covered by prior sprints. This is largely an **overlap/corroboration** source, not a big reach.
- **Flavor-vector expansion:** ~19 net-new vectors; the 217 already-covered ids gain a **fresh
  contemporary corroborating source** (raises consensus evidence, does not lower confidence).
- **Historical value:** *LOW as historical grounding* (it is a 2019 educational book, not a foundational
  historical reference like B3). Its value is **contemporary coverage + corroboration + brand/type facts**.
- **Authority tier:** T3_community (frozen contract \u2014 books cannot sole-certify; corroborate only).

---

## 7. Suggested Registration

| Field | Suggested |
|---|---|
| **Source ID** | **B8** (next free slot; B4=Jim Murray, B5=Wishart, B6=SMWS, B7=supplementary \u2014 B8 is new) |
| **Priority** | **P2** (contemporary educational; consistent with the B7 supplementary tier) |
| **Book key** | `RR2020_B8` |
| **algorithm_version** | `rr2020_b8` (isolated namespace; avoids UNIQUE(whisky_id, algorithm_version) clash) |
| **Authority tier** | T3_community |

> Note: Reference discussion suggested "B5" \u2014 that is **incorrect**; B5 is already allocated to David
> Wishart. The next unused key is **B8**.

---

## 8. Conditions Before Any Enrichment (Sprint 04)

1. **EPUB extraction path** \u2014 Sprint 04 must use the verified `ebooklib` step in place of `pypdf`.
   No DB schema change; the resolver/consensus/loader are reused unchanged from S01 (frozen).
2. **Formal B8 registration** \u2014 add B8 to `source_priority_matrix.md` + `book_ingestion_plan.md`
   (net-new matrix entry). This is a write to the frozen plan docs \u2014 **requires your approval**.
3. **T3 constraint** \u2014 book rows corroborate only, never sole-certify (P95 books-tier audit C1/D1).
4. **Modest net-new coverage** \u2014 set expectations: ~19 net-new vectors; main benefit is corroboration.

---

## 9. Status \u2014 STOPPED AT GATE

No ingestion performed. No `knowledge.db` / `production.db` / registry write performed.
Deliverables written: `source_metadata.json`, `new_source_report.md`.
Awaiting your decision on **B8 / P2** and whether to proceed to a Sprint 04 enrichment run.
