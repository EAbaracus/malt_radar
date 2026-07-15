# Malt Radar Knowledge Engineering Walkthrough

## P96.5 Extraction Quality Recovery
- Built `noise_filter.py` and `ner_resolver.py`.
- Filtered raw LLM noise out of the extraction candidates.
- Reduced ~7,000 bad entities to exactly 283 verified whisky entries.

## P97-R2 Regeneration
- Regenerated the canonical 7-axis promotion candidates.
- Sanity-checked duplicate keys.
- Resulted in 256 mathematically clean, 7-axis vectors ready for promotion.

## P98-P100 Schema Audit & Architecture
- Audited `production.db` and proved it could not store T3 authority or provenance safely.
- Designed the "Hybrid Snapshot + Evidence" architecture.
- P101 formalized the `knowledge.db` schema.

## P102 KnowledgeDB Bootstrap
- Created `knowledge.db` offline from production.
- Enforced strict state transitions (ACTIVE/SUPERSEDED) instead of cascades.
- Calculated deterministic baseline DDL hash for schema immutability.
- Certified via `P102-CERT` read-only audit.
