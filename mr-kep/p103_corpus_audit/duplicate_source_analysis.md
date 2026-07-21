# Duplicate Source Analysis — P103 Corpus Audit
_Generated 2026-07-15 18:01 UTC_

Detection: full SHA256 (exact) + same-size / name-similarity ≥0.85 (near-dup). Read-only; no files renamed/moved.

## Exact duplicates (identical SHA256)

### DUP-1 — Malt Whisky Yearbook 2019 (misnamed copy)
- `annas-arch-21eb2f4fc714.pdf` ≡ `Malt whisky yearbook 2019 ... -- Ingvar Ronde ....pdf`
- SHA256 `056ab6524af7…`, 27,293,436 bytes.
- **Handling:** `annas-arch` is a byte-identical copy of an already-INGESTED source (B1). DELETE/ignore one copy; do not ingest twice. The misleading `annas-arch` name should be noted as the yearbook.

### DUP-2 — Whisky Advocate Wol 32 No 04 Winter 2023
- `Whisky Advocate - Wol_ 32 No_ 04 [Winter 2023] (TruePDF)...` ≡ `_OceanofPDF.com_Whisky_Advocate_-_Wol_32_No_04_Winter_2023_...`
- SHA256 `8fda7b30798f…`, 87,291,310 bytes.
- **Handling:** identical content, different download names. Keep one (prefer the non-OceanofPDF name); the other is redundant. NOT yet ingested, so no double-ingest risk — just pick one at Sprint 08.

## Near-duplicates (same size, name similarity 0.90)

### NEAR-1 — Scotch Whisky Annual First Edition 2019 (two downloads)
- `[Scotch Whisky The Whisky Magazine Annual First Edition _2019] - - libgen.li.pdf` (2026-07-15) ≡ `[Scotch Whisky The Whisky Magazine Annual First Edition _2019].pdf` (2026-07-07)
- Both 109,203,504 bytes, name ratio 0.90.
- **Handling:** same edition, two acquisition timestamps. Keep one; treat the other as redundant. Verify page-count equal (132 vs 132) before discarding — if identical, one is enough.

## Overlap caveats
- The 803 SMWS PDFs may contain internal near-duplicates (same bottle, multiple scans); recommend a SHA256 de-dup pass *inside* the SMWS group during Sprint 09 before extraction.
- Remaining Whisky Advocate / Magazine issues are distinct editions (different months/years) → NOT duplicates; all should be ingested.
