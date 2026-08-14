# Resolver Consolidation Plan — P121

## 1. Current State: 4+ Entity Resolution Implementations

| # | Location | Purpose | Resolution Method | Success Rate |
|---|---|---|---|---|
| 1 | `evidence_engine/engine.py` `resolve_source()` | Maps `source_key` → `authority_tier`/`evidence_type` | YAML config lookup (source_priority.yaml + source_resolution_model.yaml) | N/A — config only |
| 2 | `book_enrichment_sprint01/enrich_mw_yearbook_2019.py` `load_production_lexicon()` + `extract_entities()` | Match entity names in book text to production.db whisky_ids | Regex substring match against production.db names + partials | ~95% resolved (1K+ entities across 6 books) |
| 3 | `p96_pipeline/entity_resolver.py` | Resolve raw names to canonical IDs | Hardcoded lookup table (1 entity) | ~0% — mock only |
| 4 | P119 SMWS Extraction (external script, not committed) | Match SMWS code names to production.db | Cross-ref cask_no against whiskies.name + original_name | 1/792 (0.1%) — catastrophic failure |
| — | `structured_source_intake/` (unknown script) | Match retail CSV names to production.db | Unknown (no scripts committed, only CSV output) | ~97% (39/40 entities resolved) |

### The Core Problem

Entity resolution is implemented differently in every location, with different:
- **Input format**: `source_key` string vs `raw text` vs `CSV row`
- **Resolution strategy**: YAML config lookup vs regex substring match vs mock table vs unknown
- **Output format**: authority tier dict vs `{whisky_id, ...}` record
- **Accuracy**: 95% (books) vs 0.1% (SMWS) — same problem, two orders of magnitude difference

---

## 2. Target: Single Canonical EntityResolver

### Interface

```python
class EntityResolver:
    def __init__(self, production_db_path: str):
        """Load lexicon from production.db once, cache it."""
        self.lexicon = self._load_lexicon(production_db_path)
    
    def resolve(self, entity_hint: str, context: dict = None) -> ResolutionResult:
        """
        Try multiple strategies in order:
        1. Exact name match (whiskies.name)
        2. Normalized name match (whiskies.name normalized)
        3. Fuzzy substring match (whiskies.name partials)
        4. SMWS code match (cask_no → whisky map)
        5. Distillery name → fallback
        6. Unresolved (return None)
        """
        pass
    
    def _load_lexicon(self, db_path: str) -> Lexicon:
        """Load whiskies + distilleries from production.db into optimized lookup structures."""
        pass

@dataclass
class ResolutionResult:
    whisky_id: str | None
    entity_name: str
    matched_name: str | None
    match_type: str  # 'exact' | 'normalized' | 'fuzzy' | 'smws_code' | 'distillery_only' | 'unresolved'
    confidence: float
```

### Resolution Strategies (in order of precedence)

| Strategy | Source Data | Example | Confidence |
|---|---|---|---|
| 1. Exact | `whiskies.name` == `entity_hint` | "Springbank 10 Year Old" | 1.0 |
| 2. Normalized | normalized(name) == norm(entity_hint) | "springbank-10-year-old" | 0.95 |
| 3. Partial match | name substring in entity_hint or vice versa | "Springbank 10" in "Springbank 10 Year Old (2020)" | 0.85 |
| 4. SMWS code | cask_no map → whisky | "127.9" → W001645 | 0.90 |
| 5. Distillery only | distillery name match, no specific whisky | "Glenfarclas" → no single whisky | 0.40 |
| 6. Unresolved | No match found | "Custom IB #1234" | 0.0 |

---

## 3. Reusable Code Inventory

### Code to KEEP and REFACTOR into the shared resolver

| File | Lines | What to Extract |
|---|---|---|
| `book_enrichment_sprint01/enrich_mw_yearbook_2019.py:139-182` | `load_production_lexicon()` | Lexicon builder — reads whiskies + distilleries from production.db |
| `book_enrichment_sprint01/enrich_mw_yearbook_2019.py:208-291` | `extract_entities()` | Entity matching against lexicon (greedy longest-first substring match) |
| `book_enrichment_sprint01/enrich_mw_yearbook_2019.py:113-129` | `classify_flavor()` + `compute_confidence()` | Confidence computation |

### Code to REPLACE (inline with new resolver)

| File | Reason |
|---|---|
| `p96_pipeline/entity_resolver.py` | Mock only; contains no real logic |
| P119 SMWS external script | Not committed; impossible to reuse |
| `evidence_engine/engine.py:139-176` `resolve_source()` | This is a SOURCE resolver (maps source_key → authority), not an ENTITY resolver (maps name → whisky_id). Keep as-is under different name. |

### Code to DEPRECATE (inline entity resolution in book enrichment)

Each book enrichment sprint has inline entity resolution in its `main()` that reads production.db and matches names. After consolidation:
- All sprints call `EntityResolver.resolve()` instead of their own `extract_entities()`
- Sprint loaders keep their save-to-knowledge.db logic (that part is not duplicated)

---

## 4. Canonical Selection Criteria

The canonical EntityResolver is built on **book enrichment sprint inline resolution** (#2 in the current-state table above). The selection is based on explicit criteria:

| Criterion | Book Sprint (#2) | Structured Source Intake (#5) | SMWS P119 (#4) | P96 (#3) |
|---|---|---|---|---|
| **Source code committed** | ✅ Yes (6 sprint files) | ❌ No scripts in repo | ❌ Not committed | ✅ Yes but mock |
| **Known success rate** | ~95% (1K+ entities) | ~97% (39/40 entities) | 0.1% (1/792) | ~0% (mock) |
| **Resolution method understood** | ✅ Regex substring vs production.db lexicon | ❌ Inferred from CSV only (name matching, 183 matched lines exist) | ✅ cask_no cross-ref | ✅ Mock lookup table |
| **Testable / reproducible** | ✅ Same inputs → same outputs | ❌ Scripts lost; cannot reproduce resolution logic | ❌ Scripts not committed; cannot reproduce | ✅ But worthless |
| **Proven fact volume** | **13,133** facts (6 books) | 39 entities (1 CSV source) | 792 expressions (never reached any DB) | 0 facts |

**Decision: Book sprint inline resolution (#2) is canonical.** Structured Source Intake may have higher accuracy on its specific dataset (39 entities, ~97%), but its resolution logic is **lost** — no Python scripts exist anywhere in the repo, only CSV output files. Book sprint resolution is the best available candidate with committed, auditable, reproducible code.

Structured Source Intake's `existing_matches.csv` (183 entity → whisky_id mappings, lines 1-183) serves as an **additional validation fixture** — the canonical resolver must produce the same `matched_id` for all 183 names to match that implementation's behavior.

### Recovery Attempt: Structured Source Intake (sonuç: KAYIP)

| Attempt | Result |
|---|---|
| `git log --all -- mr-kep/structured_source_intake/` | ⚠️ NO COMMITS — entire directory is untracked |
| Check for `.py` files in directory | ❌ None found — only CSV/JSON/MD output artifacts exist |
| `git status --short mr-kep/structured_source_intake/` | All files marked `??` (untracked) |
| Infer resolution method from CSV outputs | Partial — `existing_matches.csv` has name→whisky_id mapping. `ambiguous_matches.csv` has pipe-delimited alternatives (e.g. `W002411\|W001109`). Pattern suggests NAME-BASED matching against production.db whiskies.name |

**Verdict: Resolution logic cannot be recovered.** The ~97% accuracy figure (39/40) is known from `promotion_statistics.json` but the method is gone. The canonical selection reverts to the next-best option: book sprint resolution, which is fully committed and reproducible.

---

## 5. SMWS Resolution Gap

P119 achieved 1/792 resolution. Root cause analysis:

| Factor | Impact |
|---|---|
| SMWS codes (e.g. "127.9") do not appear in production.db `whiskies.name` or `original_name` | No name-based match possible |
| `cask_no` field in production.db is inconsistently populated | ~60% of SMWS-identified whiskies have no cask_no |
| SMWS distillery codes (first number = distillery) map to distilleries, not to specific whiskies | Distillery-only match gives low confidence |
| No fuzzy matching was attempted | Exact-match-only approach |

### SMWS Resolution Strategy

```
SMWS code "127.9"
  │
  ├── 1. Parse distillery code: 127 → distillery
  │     └── Cragganmore? Glenfarclas? (need distillery→SMWS_code registry)
  │
  ├── 2. Check production.db: cask_no = "127.9"
  │     └── IF found → W001645 (exact match, high confidence)
  │
  ├── 3. Check production.db: distillery + age match
  │     └── "Cragganmore 14" ≈ "127.9" (14yo SMWS) → medium confidence
  │
  └── 4. Unresolved → manual review
        └── P119 had 791 of these
```

The SMWS resolution problem requires either:
(a) An SMWS distillery code→name registry (e.g., 001 = Glenfarclas, 002 = ...)
(b) Fuzzy age+name matching against distillery+age_statement
(c) Both

---

## 6. Regression Golden Set Specification

### Format
**JSON Lines (JSONL)**, one entry per resolved entity in knowledge.db:

```jsonl
{"whisky_id": "W000023", "resolved_name": "Springbank 10 Year Old", "book_source": "MW2019", "pages": [23, 45], "canonical_vector": {"smoky": 20, "peaty": 10, "fruity": 30, "sweet": 40, "spicy": 15, "maritime": 0, "sherry": 5}}
```

### Location
`mr-kep/tests/fixtures/entity_resolution_golden_v1/`
- `golden_set.jsonl` — resolution golden set
- `golden_set.sha256` — integrity hash
- `golden_set.README.md` — generation metadata (date, source book versions, run_id)

### Kapsam
**Tüm 3,077 ACTIVE consensus node.** Her consensus node = 1 resolved entity.
- Tümü dahil edilir (örneklem hatası riski yok).
- 3,077 satır (~500 KB JSONL) — CI'da saniyeler içinde karşılaştırılabilir, repo'da tutulabilir.

### Üretme Komutu

```bash
python -c "
import sqlite3, json
conn = sqlite3.connect('mr-kep/p102_bootstrap/knowledge.db')
c = conn.execute('''
  SELECT c.whisky_id, c.consensus_id, c.algorithm_version,
         v.smoky, v.peaty, v.fruity, v.sweet, v.spicy, v.maritime, v.sherry
  FROM consensus_nodes c
  JOIN canonical_vectors v ON v.consensus_id = c.consensus_id
  WHERE c.status = 'ACTIVE'
''')
with open('mr-kep/tests/fixtures/entity_resolution_golden_v1/golden_set.jsonl', 'w') as f:
  for row in c:
    f.write(json.dumps({
      'whisky_id': row[0],
      'consensus_id': row[1],
      'algorithm_version': row[2],
      'canonical_vector': {'smoky': row[3], 'peaty': row[4], 'fruity': row[5],
                           'sweet': row[6], 'spicy': row[7], 'maritime': row[8], 'sherry': row[9]}
    }) + '\n')
conn.close()
"
```

### Hangi Aşamada Test Edilecek

| Adım | Test | Status |
|---|---|---|
| **STEP 1** (resolver oluşturma) | Yeni EntityResolver, golden_set'teki her entity için **aynı whisky_id**'i döndürmeli. **Bu STEP 1'in kabul kriteridir.** | 🔴 Geçemezse STEP 1 tamamlanmamış sayılır |
| **STEP 4** (kitap sprint'lerini değiştirme) | Yeni adapter (EntityResolver kullanan) → knowledge.db yazdıktan sonra, golden_set'teki consensus_id'ler birebir aynı olmalı | 🟡 Fark sadece ID formatında olabilir (içerik aynı olmalı) |
| **STEP 5** (eski sprint'leri kapatma) | 3 ardışık run'da golden_set'ten sapma = 0 | 🔴 Kapatma öncesi kanıtlanmalı |

### CI Gate
Regression test **manuel adımdır**, CI'da çalıştırılmaz:
- knowledge.db + production.db bağımlılığı (CI ortamında yok)
- Golden set değişmedikçe tekrar koşmaya gerek yok

Her STEP gate'inde manuel çalıştırma:
```bash
python mr-kep/tests/compare_resolution_golden.py \
  --resolver-output /tmp/new_resolver_output.jsonl \
  --golden mr-kep/tests/fixtures/entity_resolution_golden_v1/golden_set.jsonl
```

### Structured Source Intake Validation Fixture (ek)
```bash
python -c "
import csv, json
with open('mr-kep/structured_source_intake/existing_matches.csv') as f:
    reader = csv.DictReader(f)
    for row in reader:
        print(json.dumps({'name': row['name'], 'expected_id': row['matched_id']}))
" > mr-kep/tests/fixtures/entity_resolution_golden_v1/ssi_validation.jsonl
```
Bu fixture ile canonical resolver, Structured Source Intake'in çözdüğü 183 entity'de de aynı sonucu verdiği doğrulanır.

---

## 7. Migration Plan

```
STEP 1: Create mr-kep/resolution/entity_resolver.py
  - Extract load_production_lexicon() from enrichment_sprint01
  - Implement EntityResolver class with strategy chain
  - Add tests — MUST PASS against golden_set.jsonl (kabul kriteri)

STEP 2: Create mr-kep/tests/fixtures/entity_resolution_golden_v1/
  - Generate golden_set.jsonl from live knowledge.db
  - Generate ssi_validation.jsonl from structured_source_intake outputs
  - Commit to repo

STEP 3: Add SMWS resolution support
  - SMWS distillery code→name registry (hardcoded map or CSV)
  - cask_no lookup in production.db
  - Distillery + age fuzzy match

STEP 4: Wire into KEP pipeline
  - EntityResolver called during produce_extracted_evidence()
  - ResolutionResult attached to evidence entries

STEP 5: Replace inline resolution in book enrichment
  - Import shared EntityResolver
  - Remove duplicate load_production_lexicon() from each sprint
  - Verify against golden_set (same whisky_id, same vectors)

STEP 6: Structured Source Intake validation
  - Verify canonical resolver against ssi_validation.jsonl
  - Report any discrepancies (expected: 0 for name-matched entities)

STEP 7: Remove p96_pipeline/entity_resolver.py and deprecate inline book sprint resolution
  - No longer needed; run 3 consecutive golden_set comparisons (sapma=0 required)
```
