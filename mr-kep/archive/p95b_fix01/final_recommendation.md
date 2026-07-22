# P95B-FIX-01 — Final Recommendation & Promotion Readiness

**Mode:** READ-ONLY. No DB/code writes. GO/NO-GO below is a recommendation, not an executed action.

---

## Single authoritative schema (defined)
- **Canonical frozen 7 axes @ 0-100:** `smoky, peaty, fruity, sweet, spicy, maritime, sherry`
  (authority: `canonical_flavor_standard.md` + `CANONICAL_SCHEMA.md §5` + `promotion_rulebook.md`).
- **Storage:** `flavor_profiles.flavor_profile` = canonical 7-axis JSON (de-facto source of truth).
  `flavor_profiles.flavor_vector` = raw term-bag (evidence provenance, non-canonical).
- **Evidence:** `flavor_evidence` must carry the 7 canonical axes as scalars; currently missing
  `vector_maritime`, carrying surplus `vector_rich` (legacy). Add `vector_maritime`; keep `vector_rich`
  (deprecated, evidence-only).
- **Reducer:** use ONLY the real `d4_reducer` pipeline (emits canonical 7 incl `maritime`);
  deprecate `d4_reducer/axis_reducer.py` (wrong vocabulary).
- **Client:** `db_read_service` projection is presentation-only and acceptable, BUT must **stop
  dropping `maritime`** (add to `APP_AXES` or map explicitly).

---

## Layer mismatch summary (all explained)
| # | Mismatch | Explained as |
|---|---|---|
| 1 | `flavor_evidence` missing `vector_maritime` | canonical gap → add column (dry-run provided) |
| 2 | `flavor_evidence.vector_rich` surplus | legacy/unmappable evidence → keep, deprecate |
| 3 | `axis_reducer.py` wrong 7 axes | stale stub → deprecate, exclude from promotion |
| 4 | `db_read_service` drops `maritime` | client-compat gap → add to APP_AXES |
| 5 | doc says `flavor_vector`, code uses `flavor_profile` | doc imprecision → correct doc |

---

## Promotion Readiness Verdict

### Phase 10 — Staging Ingestion: **GO** ✅
Editorial/book evidence is captured with the full canonical 7-axis vector (incl. `maritime`) in
staging `flavor_vector_json`. No loss at ingestion. (P203C-RETRY confirmed extraction emits maritime.)

### Phase 11 — Validation: **GO** ✅ (with added check)
Validation can verify `maritime` is present in staging vectors. **Add a gate:** assert the
canonical 7 axes (incl. `maritime`) are all represented in staging before promotion.

### Phase 12 — Production Promotion: **NO-GO** ⛔ (until fixes land)
Maritime is **silently dropped** on the path to production:
- `flavor_evidence` has no `vector_maritime` → maritime evidence cannot be persisted there; AND
- `db_read_service` strips `maritime` → even stored maritime never reaches the app.

Promoting now would lose the canonical 7th axis. **Phase 12 may proceed ONLY after:**
1. `vector_maritime` added to `flavor_evidence` (dry-run provided), AND
2. promotion path maps staging `flavor_vector_json` → `flavor_profiles.flavor_profile`
   (canonical 7-axis JSON) preserving `maritime`, AND
3. `db_read_service.APP_AXES` includes `maritime` (or maps it), AND
4. legacy `axis_reducer.py` excluded from the promotion path, AND
5. pre-migration backup + post-apply row-count assert (per `promotion_rulebook.md §6`).

---

## Concrete next actions (authorized-migration ticket, NOT executed here)
- [ ] Apply `dry_run_migration.sql` FIX (add `vector_maritime`); backup first.
- [ ] Deprecate `d4_reducer/axis_reducer.py`.
- [ ] Patch `db_read_service.APP_AXES` to include `maritime`.
- [ ] Correct `canonical_flavor_standard.md` column name (`flavor_profile`, not `flavor_vector`).
- [ ] Add Phase-11 validation gate for the 7 canonical axes (incl. maritime).
- [ ] Re-run P95B-FIX-01 checks → if all green, Phase 12 → GO.

**This task performed zero mutations.** production.db SHA `8350fe9d…` and knowledge.db SHA
`e4c0d8b…` are unchanged. No commit/push/tag.
