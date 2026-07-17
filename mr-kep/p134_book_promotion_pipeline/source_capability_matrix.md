# P134 — Source Capability Matrix (READ-ONLY Design)

- doc_version: P134-1
- grounded in: real `data/books/` corpus (849 PDF/EPUB), SMWS USA TASTING NOTES ARCHIVE (PDFs),
  `staging_*` tables, knowledge.db `books`/`citations`, NotebookLM outputs, CSV/JSON assets.
- legend: ✓ provides · ✗ cannot provide · ◐ partial/derived

## Sources inventory (actual)
| source | format | volume | authority tier (P128) |
|---|---|---|---|
| Malt Whisky Yearbook | PDF/EPUB | corpus | T2 Reference |
| World Atlas of Whisky | book | corpus | T2 Reference |
| Michael Jackson / Whisky Classified | book | corpus | T2 Reference |
| Whiskypedia, Broom Manual, Complete Whiskey Course | book | corpus | T3 General |
| Japanese Whisky guide | EPUB | corpus | T3 General |
| Whisky Advocate / Whisky Magazine | PDF | corpus | T4 Periodical |
| SMWS USA TASTING NOTES ARCHIVE | PDF (per cask) | 803+ | T3 (society archive) |
| NotebookLM book profiles | JSON/staging | 17 rows | T3 (LLM-derived) |
| staging_book_flavor_profiles | table | 2,577 | derived (books) |
| staging_flavor_profile_candidates(_full) | table | 650 / 6,133 | derived (books) |
| staging_tasting_notes | table | 733 | web/book notes |
| flavor_evidence | table | 791 | SMWS (T3) |

## Field capability per source
| field | Yearbook/Atlas/Jackson (T2) | General book (T3) | Periodical (T4) | SMWS Archive (PDF) | NotebookLM | staging_book_flavor_profiles |
|---|---|---|---|---|---|---|
| distillery | ✓ | ✓ | ✓ | ✗ (implicit) | ✓ | ✓ |
| age | ✓ | ✓ | ◐ | ✓ (on label) | ◐ | ✓ |
| abv | ✓ | ✓ | ◐ | ✓ (on label) | ◐ | ✓ |
| cask_type | ✓ | ✓ | ✗ | ✓ | ◐ | ✓ |
| cask_number | ✗ | ✗ | ✗ | ✓ (cask #) | ✗ | ✗ |
| tasting_notes (nose/palate/finish) | ✓ | ✓ | ✓ | ✓ (verbatim) | ✓ (summary) | ✓ (summary) |
| flavor_vector (7-axis) | ◐ (derived) | ◐ | ◐ | ◐ (from note) | ✓ (0-100 axes) | ✓ (0-100 axes) |
| flavor_tags | ✓ | ✓ | ✓ | ◐ | ✓ | ✓ |
| region | ✓ | ✓ | ✗ | ✗ | ◐ | ◐ |
| country | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ |
| founded_year | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ |
| owner/company | ✓ | ◐ | ✗ | ✗ | ✗ | ✗ |
| bottler | ✗ | ◐ (BOTTLER_RE) | ✗ | ✓ (society=IB) | ✗ | ✗ |
| brand | ✓ | ✓ | ✗ | ✗ | ✗ | ◐ |
| awards | ◐ | ◐ | ✓ | ✗ | ✗ | ✗ |
| price/msrp | ✗ (firewall) | ✗ | ✗ (firewall) | ✗ | ✗ | ✗ |
| image/label | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |

## Key capability findings
1. **No source provides a stable joining key except SMWS (cask #) and book-derived whisky_name.** Distillery name + expression name is the de-facto join key for books; SMWS archive joins on `cask_no`→`smws_code` (via `flavor_evidence`).
2. **Flavor vectors are never direct in any source** — they are *derived* (NotebookLM emits 0-100 axis scores; SMWS emits normalized 0-1 via `flavor_evidence`). All vector promotion must route through knowledge.db consensus (P128 §6, promotion_contract §5).
3. **Price is universally unavailable by policy** — firewall holds for every source.
4. **NotebookLM & staging_book_flavor_profiles already carry the 7-axis schema** (`smoky,peaty,sherry,fruity,spicy,sweet,maritime,rich/oak…`) — this is the canonical extraction target shape; promotion maps to `canonical_vectors` (which uses `maritime` not `rich`).
5. **Periodicals weak on structured facts** (region/country/owner) but strong on tasting notes + awards.

## Source→staging routing (as-built)
- Book PDF/EPUB → OCR → chunk → LLM → `staging_book_flavor_profiles` (+ `staging_flavor_profile_candidates_full`)
- SMWS PDF → regex/structured extract → `flavor_evidence` + `staging_smws_tasting_notes`
- NotebookLM → `staging_notebooklm_flavor_profiles`
- Web notes → `staging_tasting_notes` / `staging_web_tasting_notes`
