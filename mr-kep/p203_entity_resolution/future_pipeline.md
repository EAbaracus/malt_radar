# P203 — Future Compatibility

How the canonical entity model plugs into upcoming epics (P300/P400/P500). Design only.

## P300 — External Source Expansion
- New sources (Whiskybase, MasterOfMalt, WhiskyNotes, future crawls) emit normalized
  entity hints → canonical matcher.
- Each external ID registered in `external_entities` + `entity_external_links`
  (`link_type` per source). Treated as crosswalk entries under the activation gate.
- No source-specific matcher code; all funnel through the ONE canonical matcher.

## P400 — LLM Knowledge Extraction
- The LLM extractor (`editorial_knowledge_extractor.py`) currently derives
  identity/score/flavor. Its `normalized_name` must be fed to the canonical matcher as a
  candidate, and its distillery/bottler guess must be resolved through the multi-entity
  matcher (currently deferred offline).
- Book/NotebookLM extraction (`evidence_engine`) already produces `entity_key` + needs
  the canonical resolver to upgrade UUID→canonical before promotion.

## P500 — Production Quality & Release
- `review_queue` (issue_type `identity|conflict|low_conf|historical`) is the human gate
  for all ambiguous matches.
- `merge_history` + `confidence` ledger provide the audit trail for release sign-off.
- Coverage gaps (distillery_id 59%, country 2.84%, region 20%) are closed by promoting
  high-confidence candidates through `promotion_queue` (field_class gating), reusing the
  P139 harness referenced in `p143`.

## Cross-epic invariants
- **Single matcher:** every ingestion pipeline (SMWS, book, editorial, CSV, NotebookLM,
  P300 crawls) resolves identity through the canonical layer — no per-source matching.
- **Alias-first:** aliases consulted before fuzzy; alias class weights source confidence.
- **No PK churn:** canonical IDs stay `whisky_id`/`distillery_id` TEXT; knowledge.db UUIDs
  bridged via `promotion_queue.entity_key` + activated crosswalk links only.
- **Read-only foundation preserved:** this phase added zero DB writes; implementation
  phase must keep AGENTS.md DB-safety (backup → impact → apply → verify) and the
  price-never-exposed rule.
