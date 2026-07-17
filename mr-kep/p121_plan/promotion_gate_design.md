# Promotion Gate Design — P121

## 1. Design Objective

The Promotion Gate is the missing final stage of the KEP pipeline. It reads
`certification.json` (produced by `certification_engine/`) and writes certified
data to `knowledge.db`. Optionally, after an explicit approval, it writes to
`production.db`.

### Current Gap

```
KEP Pipeline → certification.json → canonical_output.json → [NOTHING]
                                              ↓
                                        13K+ facts sitting in output/ files
                                              ↓
                                    The only write path to knowledge.db is
                                    the book enrichment loaders (standalone bypass)
```

### Target

```
KEP Pipeline → certification.json → Promotion Gate → knowledge.db
                                                         ↓
                                               (future: production.db
                                                with explicit approval)
```

---

## 2. Gate Logic

### Inputs

| Artifact | Source | Contains |
|---|---|---|
| `certification.json` | `certification_engine.certify()` | Per-field certification_level, paths A-F, aggregate state |
| `canonical_output.json` | `pipeline.build_canonical_output()` | entity, metadata, evidence_index, provenance, confidence, flavor_axes |

### Decision Matrix

| certification_state | Promotion Action | knowledge.db Status |
|---|---|---|
| **CERTIFIED** (all fields certified) | Promote ALL fields | `status=ACTIVE` |
| **HOLD** (≥1 field proposed) | Promote certified fields; mark proposed for audit | `status=ACTIVE` for certified; `audit_status=pending_audit` for proposed |
| **REJECTED** (≥1 field rejected) | Do NOT promote rejected fields; route to manual review | Written as `status=ARCHIVED` in audit_logs |

### Design Precedent

The book enrichment sprints' `save_to_knowledge_db()` (lines 382–558 in
`enrich_mw_yearbook_2019.py`) already implements knowledge.db writes with:
- `BEGIN IMMEDIATE TRANSACTION` + rollback on error
- `PRAGMA foreign_keys = ON` + `integrity_check` + `foreign_key_check`
- Pre/post state snapshotting for delta reporting

This function is the canonical template for the Promotion Gate.

---

## 3. Knowledge.db Write Schema

### Tables to Write

| Table | Data Source | Key Field | Write Rule |
|---|---|---|---|
| `citations` | evidence_ledger entries with `provenance_state=extracted` | `citation_id` | INSERT OR IGNORE |
| `evidence_nodes` | evidence_ledger entries | `evidence_id` | INSERT OR IGNORE |
| `extracted_facts` | canonical_output.metadata fields | `fact_id` | INSERT OR IGNORE |
| `consensus_nodes` | certification fields → resolved entity | `consensus_id` | INSERT OR IGNORE |
| `canonical_vectors` | canonical_output.metadata.flavor_axes | `vector_id` | INSERT OR IGNORE |
| `promotion_candidates` | certification → entity | `candidate_id` | INSERT OR IGNORE |
| `audit_logs` | certification paths C/D → reason | `log_id` | Always INSERT |

### ID Convention (following proven book enrichment scheme)

```python
citation_id   = f"CIT_{source_key}_{entity_id}_{page}"
evidence_id   = f"EV_{citation_id}"
fact_id       = f"FACT_{source_key}_{entity_id}_{field_name}"
consensus_id  = f"CONS_{entity_id}_{source_key}"
vector_id     = f"VEC_{entity_id}_{source_key}"
```

### Integrity Guarantees

1. `BEGIN IMMEDIATE TRANSACTION` — blocks concurrent writers
2. `PRAGMA foreign_keys = ON` — cascade/restrict enforced
3. `INSERT OR IGNORE` — idempotent re-runs
4. Post-write: `PRAGMA integrity_check` == "ok"
5. Post-write: `PRAGMA foreign_key_check` == 0 rows
6. Pre/post state capture for delta reporting

---

## 4. Interface

```python
def promote(
    certification: dict,
    canonical_output: dict,
    evidence_ledger: list[dict],
    source_key: str,
    knowledge_db_path: str,
    run_id: str,
) -> dict:
    """
    Write KEP pipeline output to knowledge.db.

    Returns:
        {
            "promotion_state": "PROMOTED" | "PARTIAL" | "BLOCKED",
            "tables_written": {
                "citations": N,
                "evidence_nodes": N,
                "extracted_facts": N,
                "consensus_nodes": N,
                "canonical_vectors": N,
            },
            "certified_fields": [...],
            "proposed_fields": [...],
            "rejected_fields": [...],
            "delta": {...},
        }
    """
```

### Called from `pipeline/run.py`

```python
# After build_canonical_output() in run_pipeline():
promotion_result = promote(
    certification=certification,
    canonical_output=canonical,
    evidence_ledger=combined_evidence,
    source_key=source_key,
    knowledge_db_path=KNOWLEDGE_DB,
    run_id=run_id,
)
```

---

## 5. Production DB Promotion (Future Gate)

A separate gate writes from knowledge.db → production.db.
This requires EXPLICIT human approval (confirm phrase pattern from `scripts/apply/*`):

```python
EXPECTED_CONFIRM = "WRITE GO: promote from knowledge.db to production.db"
```

The production promotion gate:
1. Reads `promotion_candidates` where `promotion_status='certified'`
2. Joins with `canonical_vectors` + `consensus_nodes`
3. Writes to `production.db` tables: `whiskies`, `flavor_profiles`, `tasting_notes`, `official_source_references`
4. Updates `promotion_candidates.status = 'promoted'`

### This is NOT implemented in P121. The P121 gate writes ONLY to knowledge.db.

### Relation to Legacy Apply Scripts (TEK YAZMA NOKTASI kararı)

P121 Promotion Gate ve legacy `scripts/apply/*.py` script'leri FARKLI veritabanlarına yazar:
- Promotion Gate → `knowledge.db`
- Legacy apply scripts → `production.db`

Uzun vadede **TEK YAZMA NOKTASI** hedeflenir: bu gate hem knowledge.db'e hem de production.db'e yazar. (Karar gerekçesi için `migration_risk_report.md` Section 6.2.)

P121'de production.db promotion gate'inin yazması gereken tablolar:

| production.db Tablo | İşlem Tipi | Mevcut Apply Script'ler |
|---|---|---|
| `whiskies` | UPDATE (region, cask_type, etc.) | apply_low_risk_official_facts_v{4,6,8,10,12}.py |
| `flavor_profiles` | INSERT | apply_{book,data_coverage,flavor_profile}*.py |
| `flavor_profiles` | UPDATE (flavor_vector) | apply_data_coverage_next_v9_v5_key_fix.py |
| `tasting_notes` | INSERT | apply_{book,remaining_uploaded}*.py |
| `official_source_references` | INSERT | apply_low_risk_official_facts_v{6,8,10,12}.py + apply_official_source_metadata_schema_v3.py |

**P121 kapsamı dışında:** Bu production.db yazma işlevi ayrı bir phase olarak planlanmıştır. P121 Promotion Gate yalnızca knowledge.db'e yazar.

---

## 6. Risk: Duplicate or Conflicting Data

| Scenario | Handling |
|---|---|
| Same entity resolved from 2 different sources | Each gets its own `consensus_id` (source-scoped); app queries `algorithm_version` for latest |
| Same field certified to different values | Both written as separate `extracted_facts`; consensus engine merges on read |
| Re-running pipeline for same source | `INSERT OR IGNORE` prevents duplicates; idempotent |
| Manual correction in knowledge.db | Manual edits have higher `algorithm_version`; pipeline writes do NOT overwrite |

---

## 7. Testing

The Promotion Gate must be tested with:
1. **Dry run** — simulate write, report what WOULD change
2. **Integration test** — run pipeline → gate on a known fixture, verify knowledge.db rows
3. **Idempotency test** — run twice, verify no duplicate rows
4. **Rollback test** — inject constraint violation, verify no partial writes
