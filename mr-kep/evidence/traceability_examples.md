# Traceability Examples — MR-KEP P64

> Spec/docs only, deterministic, evidence-first, read-only, **no fabrication**.
> The entries below are ILLUSTRATIVE examples of the ledger CONTRACT. Values,
> hashes, and URLs are placeholders for shape demonstration — no value is
> asserted as a real fact. Hashes shown are stand-ins (real hashes are computed
> per `evidence_lifecycle.md`).

## Example 1 — Expert score (P62 SRC_013 Whisky Mag), certified

A T2 expert score observation, chain: Source → Evidence → (no merge) →
Certification → Final Value.

```json
{
  "schema_version": "1.0.0",
  "evidence_id": "EV-0a1b2c3d4e5f6071",
  "entity_type": "whisky",
  "entity_id": "W001997",
  "field_name": "score",
  "field_value": 88,
  "normalization": "scale_0_to_100",
  "source_class": "expert_review",
  "source_name": "SRC_013",
  "source_url": "https://whiskymag.com/tastings/example-review",
  "source_citation": null,
  "extraction_method": "structured_parse",
  "selector": "text:Overall Score 88",
  "selector_hash": "3b1f...c9a2",
  "retrieval_timestamp": "2026-07-13T10:00:00Z",
  "content_hash": "aa11...ff00",
  "snapshot_hash": null,
  "retrieval_hash": "77cc...12ab",
  "evidence_hash": "0a1b2c3d4e5f6071abcd...ffff",
  "confidence": 0.90,
  "authority_tier": "T2_expert",
  "merge_strategy": null,
  "certification_level": "certified",
  "certification_path": "A",
  "review_status": "auto",
  "provenance_state": "certified",
  "supersedes": null,
  "notes": "Single expert score; scale /10 source normalized to /100 convention."
}
```

**Trace:** `Final Value(score=88)` → certified (path A, ≥0.70) → no merge
(single source) → evidence entry `EV-0a1b…` → source `SRC_013` (Whisky Mag,
expert_review/T2) at the given selector + retrieval hash.

## Example 2 — Official ABV vs expert, merge by authority_wins

Two entries for the same `(whisky, abv)`. Official (T1) wins; the expert entry
is retained as `verified` supporting evidence, not dropped.

- Entry A: `source_class=official`, `authority_tier=T1_authoritative`,
  `field_value=46`, `merge_strategy=authority_wins`,
  `certification_level=certified`, `provenance_state=certified`.
- Entry B: `source_class=expert_review`, `authority_tier=T2_expert`,
  `field_value=46`, `provenance_state=verified` (agrees → corroboration; adds
  agreement bonus per `authority/confidence.yaml`).

**Trace:** `Final Value(abv=46)` → certified (T1, corroborated, path B) → merge
(`authority_wins`, loser kept) → evidence entries A + B → sources official +
expert.

## Example 3 — Superseded expert score (latest_expert_wins)

A newer expert review supersedes an older score; the old entry persists.

- Old: `EV-1111...`, `field_value=85`, `provenance_state=superseded`.
- New: `EV-2222...`, `field_value=88`, `supersedes="EV-1111...aaaa"`,
  `merge_strategy=latest_expert_wins`, `provenance_state=certified`.

**Trace:** current `score=88` (new), history `85` retained via `supersedes` link.
No silent overwrite (AR-4); both rows queryable.

## Example 4 — Uncovered field (no fabrication)

An NAS product has no age statement. The resolver reached no source.

- `field_name=age_statement`, `field_value=null`,
  `provenance_state=discovered`, `certification_level=uncertified`,
  `notes="No age statement (NAS); no source stated a value."`

**Trace:** `age_statement` = UNCOVERED → null, never invented (AR-6).

## Example 5 — Closed distillery via official_wayback

Identity from an archived official page (P63 closed-distillery override).

- `entity_type=distillery`, `field_name=distillery_name`,
  `source_class=official_wayback`, `authority_tier=T1_authoritative`,
  `source_url="https://web.archive.org/web/2005/http://portellen.example/"`,
  `snapshot_hash="<archived-html-sha256>"`, `provenance_state=certified`,
  `certification_path="A"`, `notes="archived_snapshot; live official gone."`

**Trace:** `Final Value` → certified (T1 archived) → evidence entry with
`snapshot_hash` → Wayback snapshot of the official domain.

---

# Definition of Done — P64

| # | Criterion | Status |
|---|-----------|--------|
| 1 | Evidence Ledger model — all 18 required fields defined | ✅ |
| 2 | Provenance lifecycle — 7 states (discovered→…→deprecated) | ✅ |
| 3 | Hash strategy — content / evidence / selector / snapshot (+ retrieval) | ✅ |
| 4 | Evidence chain — Source→Evidence→Merge→Certification→Final Value | ✅ |
| 5 | Audit rules — immutable, append-only, provenance preservation, no silent overwrite, full traceability | ✅ |
| 6 | 6 required outputs produced | ✅ |
| 7 | Compatible with P62 (SRC_011–013) | ✅ |
| 8 | Compatible with P63 (source classes, certification paths, verification source) | ✅ |
| 9 | Compatible with Sprint 1 (authority layer; rollup evidence schema not clobbered) | ✅ |
| 10 | Deterministic (pure-function ids/hashes, fixed enums) | ✅ |
| 11 | Evidence-first + no fabrication (null for absent) | ✅ |
| 12 | No scraper/parser/extractor/import code | ✅ |
| 13 | No production mutation (read-only; promotion deferred to apply gate) | ✅ |
| 14 | AOUS-compatible | ✅ |

---

# GO / NO-GO — P64

## GO requires ALL of:
- [x] 18-field ledger model + JSON Schema (`evidence/evidence_schema.json`,
      valid draft-07, all 18 fields required).
- [x] 7-state provenance model with a deterministic transition machine.
- [x] Four-hash strategy fully specified and deterministic.
- [x] Evidence chain documented end to end.
- [x] Nine audit rules (AR-1…AR-9) covering the 5 required guarantees.
- [x] All 6 outputs produced.
- [x] Full compatibility with P62/P63/Sprint 1 (enums + source ids reused, no
      authority/schema clobber).
- [x] Deterministic, evidence-first, no fabrication, read-only, no code.

## NO-GO if ANY of:
- Ledger allows in-place edit or delete (violates immutability/append-only).
- A value can be overwritten without a superseding entry (silent overwrite).
- A T1-ceiling field certifiable from a T2/T3 entry.
- Any non-null value permitted without selector/quote/source (fabrication).
- ids/hashes non-deterministic.
- Any scraper/parser/extractor/import code written, or production mutated.

## AOUS Compatibility
Machine-readable schema + enumerated fields shared with P63; the ledger feeds
the Sprint 1 six agents (Extraction writes `extracted`, Validation
`normalized`/`verified`, Merge `merge_strategy`/`superseded`, Certification
`certified` + path, Audit enforces AR-1…AR-9). Single-source-of-truth authority
layer referenced, not duplicated. **Verdict: AOUS-compatible.**

## Verdict: **GO** (standard complete; no data resolved, no code written, by design).
