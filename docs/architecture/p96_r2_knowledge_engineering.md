# P96-R2 Knowledge Engineering Pipeline Enhancement

## 1. Overview
P96-R2 evolves the P96-R1 extraction model into a full-scale Knowledge Engineering Pipeline. It introduces a deterministic entity resolution engine, citation-grade provenance, strict versioned JSON schemas, robust consensus mapping, and a formalized staging Knowledge Graph. 

This architecture guarantees that all book-derived knowledge is traceable down to the exact sentence, strictly evaluated against cache invariants, and isolated from production data until explicitly merged under the P95 canonical rulebook.

## 2. Core Architectural Components

### P96-R2-A: Entity Resolution Engine
Matches raw book extracts to the Malt Radar canonical `production.db` (staging view) using deterministic rules:
- **Alias Resolution:** Standardizes names (e.g., "Lagavulin 16yo" -> "Lagavulin 16 Year Old").
- **Variants Handling:** Resolves bottler variants, batch numbers, and vintages.
- **Queueing:** Ambiguous matches (confidence < 90%) are pushed to the unresolved queue rather than forcing a match.

### P96-R2-B: Citation-Grade Provenance
Upgrades the R1 `chunk_id` model. Every extracted fact must now include:
- `book_id`, `edition`, `page`, `section`, `paragraph`, `sentence`, `chunk_id`.
- `quoted source text`.
- `extraction confidence`.
This supports 100% exact traceability back to the original source passage.

### P96-R2-C: Strict Extraction Schema (Versioned)
Forces the LLM to use a controlled vocabulary and enums. Each descriptor object must contain:
- `descriptor`, `category` (e.g., palate), `section`, `polarity` (positive/negative), `intensity` (1-5), `confidence`, and `provenance`.
- The schema is explicitly versioned (e.g., `schema_version: "v1.2.0"`).

### P96-R2-D: Consensus Engine
Reconciles extracted facts across multiple books for the same canonical entity.
- Detects agreement and disagreement.
- Generates weighted consensus while retaining minority opinions.
- T3 data is *never* promoted; consensus outputs are staged as candidate updates for future review.

### P96-R2-E & F: Extraction Cache & Versioning
Guarantees identical outputs for identical inputs, saving LLM tokens:
- **Cache Key:** `hash(document_hash + chunk_hash + prompt_version + schema_version + model_identifier)`.
- If the PDF chunk hasn't changed, and the pipeline versions haven't changed, extraction is bypassed.

### P96-R2-G: Canonical Knowledge Graph
Models the knowledge as a directed graph in staging:
`Book` -> `Citation` -> `Extracted Fact` -> `Whisky Entity` -> `Descriptor` -> `Canonical Axis` -> `Flavor Profile`.

## 3. Migration Path from P96-R1
- P96-R2 runs parallel to P96-R1 during testing.
- The `chunk_id` system from R1 is retained but wrapped in the new Citation Engine.
- R1's flat JSON is migrated to R2's `Strict Extraction Schema` via an adapter.
- No P95 data is modified. Production DB is strictly prohibited from mutating.
