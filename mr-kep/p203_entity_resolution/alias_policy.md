# P203 — Alias Policy

## Existing alias infrastructure (reuse, do not replace)
- `production.entity_aliases(alias_id, entity_type, entity_id, alias_name)` — the only
  alias table. **`entity_type` enum is `'brand','bottler','company','distillery'`**
  (verbatim from `schema/schema.sql` line 69). **`whisky` is NOT in the enum.**
- `production.entity_external_links(entity_type, entity_id, url, link_type)` —
  `link_type ∈ 'wikipedia','official','api'`.
- `production.external_entities(entity_id, entity_name UNIQUE, entity_type, base_url)`.
- `production.official_source_references(...)` — provenance-backed official values
  (field_name/field_value + confidence + license/copyright risk). Can anchor *official*
  aliases with citation.

## Policy by alias class
| Class | Definition | Storage | Provenance required? |
|---|---|---|---|
| **official** | Distillery/brand's legal or canonical name variant | `entity_aliases` + `official_source_references` | YES (source_url + confidence) |
| **historical** | Former name / pre-rename / closed-distillery name | `entity_aliases` | YES (dated note) |
| **OCR** | Scanner variation (e.g. `distillenes`, `vvhiskey`) | resolved at ingest via `B4b` OCR rules; if persisted, `entity_aliases` with class tag | NO (deterministic rule) |
| **editorial** | Blogger's casual naming ("the Glenlivet" vs "Glenlivet") | `entity_aliases` (class=editorial) | YES (source_id) |
| **book** | Book-specific spelling from Jim Murray / Malt Whisky Yearbook | `entity_aliases` (class=book) | YES (book_id + page) |
| **CSV** | Spreadsheet variant spellings | `entity_aliases` (class=csv) | YES (source_file) |
| **SMWS** | SMWS code ↔ distillery/expression mapping | `external_entities` + `entity_external_links` (link_type=official) | YES |
| **community** | User/contributor variants | `entity_aliases` (class=community) | YES (source_id, low default confidence) |

## Gaps this policy must fix (implementation phase)
1. **Whisky-level aliases are unsupported** — extend `entity_aliases.entity_type` to
   include `'whisky'` (and optionally `'series'`,`'edition'`). Until then, whisky
   identity has no alias table and depends solely on fuzzy name matching.
2. **No `alias_class` column** — existing `entity_aliases` stores only the raw
   `alias_name`; class must be added (or a parallel `entity_alias_classes` table) so
   the matcher can weight official > OCR > community.
3. **Matcher is alias-blind** — `matching.py` never queries `entity_aliases`
   (grep-confirmed). The canonical matcher must consult aliases BEFORE fuzzy fallback.

## Conflict rules for aliases
- Duplicate `alias_name` across two different canonical entities ⇒ **ambiguous entity**
  → route to `review_queue` (issue_type `identity`).
- An alias that equals another entity's canonical `name` ⇒ candidate **merge** →
  `review_queue` (issue_type `conflict`), never auto-merge.
- OCR aliases are deterministic and low-risk; auto-accept only when the normalized form
  is unique.

## Reuse note
`B4b/classify_unresolved.py` already performs OCR normalization
(`OCR_JUNK_RE = [«@*%=]|vvh|vvhiskey|vvhisky|co oq]`, `DIST_SINGULAR_RE` includes
`distillenes`). That rule set should be promoted into the canonical normalizer, not
rewritten.
