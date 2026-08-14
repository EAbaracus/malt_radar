# Book Ingestion Report — B4b: Jim Murray, *The Complete Book of Whiskey*

**Plan ID:** B4b (companion of B4 — Jim Murray *Whisky Bible 2020*, `c0878db8…`)
**Output location:** `mr-kep/book_ingestion/b4b-jim-murray-complete-book-of-whiskey/`
**Mode:** STAGING ONLY — no production.db change, no knowledge.db write, no auto-promotion.
**Registry:** `data/registries/book_registry.json` (SHA `49d1558…`, status `REGISTERED_STAGING_ONLY`)

---

## Phase 1 — Corpus Registration ✅ (done)

| Field | Value |
|-------|-------|
| title | The Complete Book of Whiskey: The Definitive Guide to the World's Whiskies |
| author | Jim Murray |
| publication | London, 1998 (ed. ©1997); Carlton Books |
| isbn13 | 9781858684949 |
| format | PDF |
| source file | `data/books/Jim Murray's complete book of whiskey ; the definitive guide -- Murray, Jim, 1957.pdf` |
| source hash (SHA256) | `49d1558e119fc816d50187d766f3c1da41ebccc9fd00ad395d9feb29c6a05cc3` |
| size | 35,897,472 bytes |
| ingestion timestamp | 2026-07-15T22:55:00 |
| provenance | Anna's Archive mirror; content treated as © regardless of source |
| target tables | `staging_book_flavor_profiles`, `tasting_notes` (attributed), `flavor_profiles` (weighted-avg merge, Dec 3) |
| reliability | 3 (subjective tasting) |
| licensing | © Jim Murray — signal extraction + attribution only; numeric scores are IP → derived axis signals, never verbatim score text |

Stored in corpus registry under existing SHA key (metadata was a placeholder `Unknown Title/Author`; enriched in place, file hash unchanged).

---

## Phase 2 — Extraction 🔲 (skeleton — NOT RUN)

Target entities: whisky entities, distilleries, regions, tasting descriptions, flavor terminology, production methods, historical facts.
Provenance to preserve: page number, chapter, quote location, source reference.

> **Staging-only scope:** extraction not executed this task. When run: pdfplumber text → anchor-regex blocks → CSV in `data/staging/`. Deterministic, local, NO LLM (Rule 08). Numeric scores extracted only as derived 7-axis signals.

---

## Phase 3 — Semantic Normalization 🔲 (skeleton — NOT RUN)

Map flavor language → canonical 7 axes: **smoky, peaty, sherry, fruity, sweet, spicy, maritime**. No new axes created.
Record `original_term → canonical_axis → confidence`.

---

## Phase 4 — Entity Resolution 🔲 (skeleton — NOT RUN)

Match against existing distilleries / whisky products / canonical IDs. No duplicates.
Uncertain matches → `staging_manual_review_queue`.

---

## Phase 5 — Evidence Graph 🔲 (skeleton — NOT RUN)

Staging evidence nodes: source, claim, entity, confidence, citation location. No orphan evidence.
All flows into `staging_*` tables only.

---

## Phase 6 — Validation Report 🔲 (skeleton — NOT RUN)

To include when extraction is approved:
- extracted entity count: _TBD_
- matched entity count: _TBD_
- unresolved entities: _TBD_
- flavor mappings: _TBD_
- evidence count: _TBD_
- promotion readiness: **NOT READY** (no extraction run yet)

---

## Verification Loop (read-only confirmations)

- `git status`: this task added `data/registries/book_registry.json` (enriched record) + `mr-kep/book_ingestion/b4b-…/book_ingestion_report.md`. No other files changed.
- production.db: **untouched** (OS read-only lock + gate; hash `d842b118…` unchanged).
- knowledge.db: **no write** (B4b not loaded; 792 SMWS staging vectors still pending, unrelated).
- No commit performed.

---

## Final Status: 🟡 WARN_GO

**Rationale:** Phase 1 (corpus registration) complete and traced (SHA-anchored). Phases 2–6 are scaffolded but **not executed** (user selected registration-only, safest staging path). No production/knowledge.db mutation, no auto-promotion — evidence requirements and licensing guardrails preserved.

**Promotion readiness:** BLOCKED-pending-extraction. The book is registered and ready for the deterministic extraction pipeline (B4-grouping, signals-only, attributed), but actual staging rows + review queue are empty until extraction is explicitly approved as a separate task.

**Next concrete step (separate task, requires explicit user approval):** run Phase 2–5 extraction into `staging_*` (gate not needed — staging writes go to `output/staging` / `data/staging`, NOT production.db), then Phase 6 validation → promotion gate.
