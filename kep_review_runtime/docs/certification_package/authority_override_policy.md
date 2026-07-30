# Authority Override Policy â€” P305

**Source of truth:** `certification_engine/__init__.py` (real, inspected). Constants: `CERTIFY_MIN = 0.70`, `FIELD_CEILING`, `TIER_ORDER = {T1_authoritative: 1, T2_expert: 2, T3_community: 3}`.

---

## T2 Evidence Limitations

- Evidence originating from a `T2_expert` authority can only certify fields whose ceiling is `T2_expert` (nose, palate, finish, flavor_axes, score).
- The six identity fields â€” `distillery_name, region, country, abv, age_statement, cask_type` â€” have a ceiling of `T1_authoritative`.
- Consequently, T2 evidence for those fields can **never** reach `certified` (Path A); it caps at `proposed` (Path C), which forces the aggregate state to **HOLD**.
- The candidate `EDR-b6108f7ac8d252af` carries `authority_tier = T2_expert`, so its six T1-ceiling identity fields are `proposed` â†’ aggregate **HOLD**. This is correct, expected engine behavior.

---

## T1 Field Ceiling Rules

`FIELD_CEILING` (frozen):
- `T1_authoritative`: `distillery_name, region, country, abv, age_statement, cask_type`
- `T2_expert`: `nose, palate, finish, flavor_axes, score`
- `T3_community`: `community_rating`

A field is `certified` (Path A) only if `authority_tier` rank â‰¤ ceiling rank AND confidence â‰¥ `CERTIFY_MIN`.

---

## What Requires Explicit Human Acceptance

- Acceptance of a T2-sourced field for a T1-ceiling attribute (the six identity fields above).
- Promotion of the authority tier for that field (e.g., treating the T2 evidence as `T1_authoritative` for the purpose of this candidate).
- Any move from `HOLD` â†’ approvable state despite `proposed` fields.

---

## What Cannot Be Overridden

- The deterministic rule `confidence < CERTIFY_MIN (0.70)` â†’ **rejected** (Path E).
- The rule that any `rejected` field propagates to aggregate **REJECTED**.
- The immutable ceiling definitions in `FIELD_CEILING`.
- The engine's determinism (same input â†’ same output); no AI/LLM/OCR/scraping is permitted.

---

## Override Mechanism

- An explicit human acceptance recorded in the promotion manifest (P303) that authorizes moving a `proposed` field toward `certified` for the purpose of eventual promotion.
- **No code-level override exists** in the certification engine. The acceptance must be documented externally (manifest + decision form) and exercised via the human `GO` gate.
- Until that acceptance is recorded, the candidate remains **PENDING HUMAN CERTIFICATION**.
