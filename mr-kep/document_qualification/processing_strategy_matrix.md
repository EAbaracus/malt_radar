# Processing Strategy Matrix — MR-KEP P67

> Design only, deterministic, evidence-first, read-only. Maps each document
> class to its **recommended pipeline** and processing posture. Pipeline stage
> names reuse P66 / Sprint 1 vocabulary; this is orchestration planning, not code.

## Stage vocabulary (from P66 extraction architecture)

`detect_type → qualify → ocr_gate → extract → normalize → evidence_ledger →
validate → merge → certify`

- `ocr_gate` is **blocking** for OCR classes; if it fails, the document drops to
  **Archive Only** and is not extracted.
- `extract` sub-strategies (declarative tags, no implementation): `prose`,
  `table`, `structured_parse`, `image_caption`, `structured/tabular`.

## Matrix

| Class | detect_type signal | ocr_gate | extract strategy | normalize | post-extract gate | Cost |
|-------|--------------------|:---:|------------------|-----------|-------------------|------|
| Book | publisher/ISBN | YES | prose | full-text → fields | validate | High |
| Magazine | ISSN/title | NO | prose + table | field map | validate | Medium |
| Official PDF | .pdf / gov/domain | NO | structured/table | field map | validate | Medium |
| Product Sheet | .pdf / producer domain | NO | structured | field map | validate | Low |
| Marketing Brochure | .pdf / brand domain | NO | text + image_caption | field map | validate | Medium |
| Auction Catalogue | .pdf / auction domain | YES | table | field map | validate | High |
| Archived Snapshot | web.archive.org | NO | prose | field map | validate (Wayback source) | Medium |
| Research Paper | DOI / .pdf | NO | prose + table | field map | validate | Medium |
| Blog Article | blog domain / RSS | NO | prose | field map | validate (T3) | Low |
| Review Website Export | structured export | NO | structured_parse | field map | validate | Low |
| Database Dump | .csv/.sql/.json | NO | structured/tabular | field map | validate | Low |
| Scanned Document | image/scan MIME | YES (blocking) | depends on OCR output | field map | validate | High |

## Pipeline selection rule (deterministic)

```
if class in {Book, Auction Catalogue, Scanned Document}: ocr_gate = required
if table_likelihood >= 0.6: extract_strategy includes table
if image_usefulness >= 0.6: extract_strategy includes image_caption
if source is structured (Database Dump, Review Export, Product Sheet): structured_parse
else: prose
```

## Posture by gate (from score model)

| Gate | Queue posture |
|------|---------------|
| High Priority | front of queue, immediate extract |
| Extract Normally | standard queue |
| Extract Later | deferred queue |
| Archive Only | store, no extract |
| Reject | discard, log only |

## Compatibility
- Stages map to Sprint 1 six agents + P66 architecture (no schema change).
- Source tags reuse P63 classes; structured_metadata/database → T2 per P65.
- Every pipeline ends in `evidence_ledger` (P64) + `validate` (P65
  validation_contract), preserving the evidence-first chain.
