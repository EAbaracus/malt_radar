# Field Authority Matrix — MR-KEP P62

For each knowledge field, the **authoritative tier** and the **preferred sources**
that may certify it. Mirrors `mr-kep/authority/field_rules.yaml` authority ceilings.

> Deterministic: a field may only be certified by a source at or above its
> authority ceiling. `Kısmi`-only sources (below ceiling) may supply evidence
> but never the winning value.

| Field | Authority ceiling | Preferred certifying sources | Conflict policy |
|-------|-------------------|------------------------------|-----------------|
| flavor_profile | T1 (reference) / T2 (expert) | World Atlas, Jackson, Broom (ref); WhiskyFun, Whisky Advocate (expert) | consensus_additive (7-axis only) |
| tasting_notes | T2 (expert) | WhiskyFun, Whisky Advocate, Distiller mags, retailers | latest_expert_wins |
| abv | T1 (official) | Official Distillery, SWA (defs); Whiskybase/retailers (verification) | authority_wins (strip-% cast) |
| cask_type | T1 (official) | Official Distillery; Whiskybase/retailers (verification) | authority_wins |
| age | T1 (official) | Official Distillery; Whiskybase/retailers (verification) | authority_wins |
| distillery | T1 (official) | Official Distillery, SWA | reject_on_conflict |
| region | T1 (official/regulatory) | SWA, Official Distillery | reject_on_conflict |
| country | T1 (official/regulatory) | SWA, Official Distillery | reject_on_conflict |
| image | T1 (official) | Official Distillery; retailers (ref by URL) | authority_wins (copyright-gated) |
| awards | T2 (editorial) | Whisky Advocate, Distiller magazines | latest_expert_wins |
| limited_release | T1 (official) / T2 (retail) | Official Distillery; Master of Malt, TWE | authority_wins |
| bottler | T1 (official) | Official Distillery; Whiskybase/retailers (verification) | authority_wins |

## Canonical flavor taxonomy constraint

All `flavor_profile` values MUST use the 7 canonical axes:
`smoky, peaty, fruity, sweet, spicy, maritime, sherry`.
Any non-canonical tag (e.g. legacy 126-tag set) is rejected at validation.

## Authority ceiling recap

- **identity** (distillery/region/country) → T1 only.
- **official_bottling** (abv/cask/age/bottler/limited_release) → T1 only; T2 may verify.
- **sensory** (flavor/tasting) → T1 reference or T2 expert.
- **scored/awards** → T2 expert/editorial.
- **image** → T1 (copyright-gated); reference by URL, never redistribute.
- **verification sources** (T3: Auctioneer, Wayback) → never certify, only confirm.
