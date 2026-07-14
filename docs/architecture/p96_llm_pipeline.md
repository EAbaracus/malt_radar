# P96-R1 LLM Knowledge Extraction Pipeline Architecture

## 1. Overview
The P96-R1 pipeline replaces the legacy pypdf/regex-oriented book extraction with a robust, semantic LLM-first architecture. It maximizes the extraction of structured whisky knowledge from unstructured book text while strictly maintaining deterministic execution, full provenance traceability, and a staging-only boundary. 

Books remain Authority Tier 3 (T3), meaning their data is merged only according to the established canonical rules and is never permitted to overwrite T1/T2 primary sources.

## 2. Pipeline Stages

### P96-R1-A: Document Preparation
- **Input:** Raw PDF / OCR text.
- **Operations:** Validates source documents, detects OCR confidence, and preserves structural metadata (page numbers, section hierarchy).
- **Output:** Cleaned text array with metadata sidecars.

### P96-R1-B: Semantic Chunking
- **Operations:** Replaces arbitrary page scanning with semantic text chunking. Generates stable, deterministic `chunk_id`s with configurable token overlap to ensure tasting notes spanning pages are not orphaned.
- **Output:** Array of Semantic Chunks.

### P96-R1-C: LLM Knowledge Extraction
- **Operations:** A structured JSON schema is enforced on the LLM. It extracts entities including whisky identity, distillation/bottling metadata (vintage, age, ABV, cask type), and a comprehensive set of sensory descriptors (nose, palate, finish, smoke, peat, maritime, sweetness, fruit, spice, floral, herbal, sulfur, oak, texture).
- **Output:** Raw JSON knowledge objects.

### P96-R1-D: Provenance Model
- **Operations:** Every extracted fact is attached to an immutable provenance object containing `book_id`, `file_id`, `page`, `chunk_id`, original `source text`, and an initial `extraction_confidence` score.

### P96-R1-E: Cross-Book Reconciliation
- **Operations:** Groups facts across multiple books for the same canonical whisky. Identifies identical, complementary, and conflicting statements. Generates weighted consensus candidates while enforcing the T3 ceiling.

### P96-R1-F & G: Descriptor Normalization & Canonical Preparation
- **Operations:** Resolves synonyms, normalizes spelling, handles intensity modifiers and negations against a controlled vocabulary. Prepares the final intermediate representation for the future D4 (NotebookLM/Book Promotion) phase without actually executing D4.

### P96-R1-H & I: Confidence & Conflict Engines
- **Operations:** Calculates modular confidence scores (extraction, normalization, provenance, reconciliation, overall). Automatically traps conflicting metadata (e.g., Book A says 46% ABV, Book B says 43% ABV) and diverts them to unresolved/manual review queues.

### P96-R1-J: Manual Review Queue
- **Operations:** Enqueues ambiguous products, low-confidence scores, and anomalies for human intervention.

## 3. Storage and Promotion Strategy
Outputs remain isolated in `output/p96_r1/staging/`. No mutation occurs in `production.db`.
