# Glossary — MR-KEP

Key terms used across MR-KEP standards, schemas, and docs.

| Term | Definition |
|------|------------|
| MR-KEP | Malt Radar Knowledge Extraction Pipeline — extracts & certifies whisky knowledge from external sources. |
| AOUS | Agent Operating / Orchestration System — drives the pipeline stages using the manifests and standards. |
| Sprint 1 | The FOUNDATION sprint: standards, schemas, infrastructure only; no extraction code. |
| Authority tier | Trust ranking of a source (T1 authoritative > T2 expert > T3 community). |
| Source priority | Numeric tie-breaker within a tier; lower number = higher precedence. |
| Field category | Grouping of fields (identity, official_bottling, sensory_evaluation, scored_assessment, supporting_evidence_only). |
| Authority ceiling | Highest tier permitted to certify a given field. |
| Evidence type | Provenance class (`primary_source_quote`, `bottle_print`, `expert_quote`, `aggregated_link`, `inferred`). |
| Confidence | Deterministic score in [0.0, 1.0] for a fact, from `confidence.yaml`. |
| Provenance | Record of where a value came from (source_key, source_url, quote, source_date). |
| Quote | Verbatim source excerpt supporting an extracted value (evidence-first). |
| IoU | Intersection-over-Union match score deciding if two units are the same whisky. |
| Merge policy | Named deterministic rule resolving field conflicts (`authority_wins`, `latest_expert_wins`, `consensus_additive`, `keep_all_supporting`, `reject_on_conflict`). |
| Checkpoint | Per-stage checksummed artifact enabling resumable, verifiable runs. |
| Certification | Attaching an evidence record to every field and enforcing `certify_min` (0.70). |
| Apply gate | Future, explicitly-approved production-write gate (backup + rollback). Not in Sprint 1. |
| 7-axis taxonomy | Canonical flavor axes: smoky, peaty, fruity, sweet, spicy, maritime, sherry. |
| No fabrication | Rule: never invent values/quotes; absent field = null. |
| Evidence-first | Rule: no fact without a quoted source excerpt and URL. |
| Read-only verification | Rule: this foundation writes no production data; verification is non-mutating. |
| Gate | Run verdict: GO / PARTIAL_GO / NO_GO / AWAITING_APPROVAL. |
| Unit | A source granularity (e.g. one review page) considered for qualification. |
| Norm (normalized name) | Deterministic canonical form of a whisky name used for matching. |
