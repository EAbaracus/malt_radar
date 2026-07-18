# P95B-FIX-01 — Client Compatibility Audit

**Mode:** READ-ONLY. Audits `backend/app/services/db_read_service.py` (legacy compatibility layer).

---

## 1. The four requested projections (verified, `db_read_service.py:83-123`)

```python
APP_AXES = ["fruity", "sweet", "spicy", "smoky_peaty", "oak_cask", "malty_cereal", "floral_herbal"]

mapped = {
    "fruity":       g("fruity"),
    "sweet":        g("sweet"),
    "spicy":        g("spicy"),
    "smoky_peaty":  max(g("smoky"), g("peaty")),
    "oak_cask":     max(g("sherry"), g("oak"), g("cask")),
    "malty_cereal": g("malty"),
    "floral_herbal":g("floral"),
}
```

| Projection | Derivation | Canonical axis(es) | Type |
|---|---|---|---|
| `smoky_peaty` | `max(smoky, peaty)` | smoky + peaty | **presentation merge** of 2 canonical axes |
| `oak_cask` | `max(sherry, oak, cask)` | sherry (+ oak/cask tokens) | **presentation merge**; sherry absorbed here |
| `malty_cereal` | `malty` | (none — raw token) | raw term, not a canonical axis |
| `floral_herbal` | `floral` | (none — raw token) | raw term, not a canonical axis |

## 2. Are these presentation-layer projections only? — YES (with one gap)

The read service is **explicitly read-only** (`uri = file:{db}?mode=ro`) and performs **no DB write**.
The `APP_AXES` projection is a *client/Flutter-radar vocabulary* — it re-maps canonical axes into a
fixed 7-slot UI shape. This is a legitimate **presentation projection**, analogous to how
`canonical_flavor_standard.md` permits deterministic remapping.

**However, two real issues:**
1. **`maritime` is dropped.** Lines 74-81: *"maritime exists [in pilot rows] but is not one of the
   app axes … maritime is dropped as it is not an app axis."* So even when `maritime` is present in
   stored `flavor_profile` (1942/3467 rows), the client never receives it. This is a
   **client-compat gap**, not a corruption — but it means canonical maritime is invisible in the app.
2. **`malty_cereal` / `floral_herbal` are raw tokens**, not canonical axes. They are harmless
   presentation slots but should not be confused with the canonical 7.

## 3. Column-name nuance (verified)
The read service queries **`flavor_profile`** (the canonical 7-axis JSON column), while the canonical
standard doc names **`flavor_vector`** (the raw term-bag column). Both columns exist in
`flavor_profiles`; the read service correctly uses `flavor_profile`. The doc naming is stale (see
canonical_authority_audit §1) but the code is correct.

## 4. Compatibility verdict
- Projections `smoky_peaty` / `oak_cask` / `malty_cereal` / `floral_herbal` are **presentation-only** ✅.
- **`maritime` is dropped by the client layer** ❌ — recommend adding `maritime` to `APP_AXES`
  (or mapping it explicitly) so the canonical 7th axis survives to the UI. This is a client fix,
  independent of the evidence-schema migration.
- Read service performs **no mutation** of stored values ✅ (read-only passthrough + format projection).
