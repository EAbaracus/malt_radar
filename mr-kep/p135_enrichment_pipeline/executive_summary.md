# P135 — Executive Summary (READ-ONLY Plan)

- doc_version: P135-1
- one-page brief for the enrichment program.

## Accepted design
P134 (metadata taxonomy, source matrix, extraction, consensus, normalization, confidence, architecture, failure, implementation) is accepted. P135 turns it into an executable enrichment plan focused on **metadata only** — entity resolution is done, UUIDs canonical, identity untouched.

## Current state (measured, 4,749 whiskies)
- cask_type **1.1%**, finish_type 0%, cask_strength 0%, bottle_size 0.8%
- region 8.8%, country 2.8%, nas 3.1%, age 34.3%, abv 46.0%, type 39.1%, brand 39.4%
- tasting_notes: nose 7.2%, finish 7.3% (palate 99.9%)
- completed_fields 0%, notes_for_review 0%
- price firewall intact; user_score untouched.

## Highest-ROI move: SMWS first
SMWS staging (803 rows) + flavor_evidence (791, 100% joinable) carries:
- cask_type 81%, age 99%, abv 97%, region 80% populated, extraction_conf=1.0.
- Single batch lifts cask_type +54pts, age +26pts, abv +24pts, region +26pts, nose/finish +53pts each.
- Deterministic, LOW conflict, FULL automation → start immediately, no prerequisites.

## Source priority
SMWS (P1) > Books + flavor candidates (P2) > NotebookLM (P3, pilot) > knowledge bootstrap (P4, consensus sink).

## Batches
B1 SMWS tech · B2 SMWS notes · B3 books · B4 vectors (consensus, needs D1+D2) · B5 knowledge/descriptions · B6 recompute.

## Prerequisites (from P128/P129, must clear before gate)
- D1 bootstrap target knowledge.db · D2 uuid↔W crosswalk (SMWS backfill) · D3 cite 726 MERGE rows (C1) · D4 schema fixes (aroma_tags/foo/axis scale).

## Risk posture
13 failure modes catalogued (wrong overwrite, expression collision, LLM hallucination, axis mismatch, dup notes, normalization drift, mis-join, citation gap, price leak, NULL corruption, crosswalk gap, non-idempotency, gate bypass) — each with mitigation. Axis scale confirmed NON-0–100 (smoky 0–945, sweet 0–5523) → normalize to 0–100 input; P136 locks direction from real min/max.

## Expected outcome
- whiskies blended technical completion ~46%→~70%.
- tasting_notes nose/finish 7%→60%.
- completed_fields 0→100%, notes_for_review 0→80%.
- 0 identity fields changed, 0 price written, fully reversible via backup + idempotent keys.

## Verdict input
This plan is **design-complete and read-only**. Execution (P136→P139) is deferred to an explicitly-approved promotion task through the P121 gate, after D1–D4 clear. No DB writes performed here.
