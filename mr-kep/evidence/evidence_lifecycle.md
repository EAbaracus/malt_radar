# Evidence Lifecycle & Chain — MR-KEP P64

> Spec/docs only, deterministic, evidence-first, read-only, no fabrication.
> Companion to `evidence_ledger_spec.md`, `provenance_model.md`, and the hash
> strategy below.

## The evidence chain

Every final value MR-KEP emits is the end of an explicit, auditable chain:

```
Source ──▶ Evidence ──▶ Merge ──▶ Certification ──▶ Final Value
  │           │            │            │               │
source_class  ledger      merge_       certification_   current
source_name   entry       strategy     level + path     (latest, non-
source_url    (immutable, (authority_  (P63 A–F)        superseded,
selector      append-only) wins, etc.)                  non-deprecated)
              hashes
```

1. **Source** — a `source_class` + `source_name` located by the P63 resolution
   plan (`discovered`).
2. **Evidence** — an immutable ledger entry captures the observation
   (`extracted` → `normalized`), with `selector`, `retrieval_timestamp`, and
   hashes for re-verification.
3. **Merge** — when multiple entries exist for the same `(entity, field)`, the
   `merge_strategy` (from `authority/merge_policies.yaml`) selects a winner;
   losers are retained (`verified`/`superseded`), never dropped.
4. **Certification** — the winner is evaluated against its
   `certification_source` tier + `certify_min` (0.70) via a P63 path → `certified`.
5. **Final Value** — the current certified entry per `(entity_id, field_name)`.
   Superseding it appends a new entry; the old one becomes `superseded`.

## Hash strategy (four hashes)

All hashes are **SHA-256, deterministic, lowercase hex**. Inputs are UTF-8,
newline-normalized, and field-joined with a `|` separator in a fixed order.

| Hash | Input (fixed order) | Purpose |
|------|---------------------|---------|
| `content_hash` | the retrieved raw content bytes (page/section the value came from) | Detects whether the source content changed between retrievals. |
| `selector_hash` | normalized `selector` string | Detects whether the locator (CSS/XPath/regex/anchor) changed; two entries with the same selector_hash targeted the same spot. |
| `snapshot_hash` | the stored snapshot artifact bytes (archived HTML/PDF), if preserved | Binds an entry to a durable snapshot (esp. `official_wayback`). |
| `retrieval_hash` | `source_url \| retrieval_timestamp \| content_hash` | Proves WHAT was fetched WHEN (retrieval context). Required. |
| `evidence_hash` | all core fields EXCEPT `evidence_hash`/`evidence_id`, joined in schema order | Whole-entry identity. `evidence_id = "EV-" + evidence_hash[:16]`. |

Properties:
- **Idempotent:** re-observing the identical thing yields the identical
  `evidence_id` → duplicate appends are detectable, not silently doubled.
- **Tamper-evident:** any change to a stored entry changes `evidence_hash`,
  which no longer matches `evidence_id` → audit flags it.
- **Deterministic:** fixed input order + normalization ⇒ stable across runs and
  machines. No timestamps other than the recorded `retrieval_timestamp` enter a
  hash's *identity* inputs beyond `retrieval_hash`.

## Re-verification workflow (spec)

To re-verify a value later: re-fetch `source_url` (or open `snapshot_hash`
artifact), re-apply `selector`, recompute `content_hash`. If it matches the
ledger entry → still valid. If not → append a new entry (new observation) and,
if the value changed, mark the old one `superseded`. P64 defines this workflow;
it does not execute any fetch.

## Determinism & read-only

- The chain and hashes are pure functions of recorded inputs.
- No lifecycle step in P64 fetches data or writes production; this is the
  standard the future agents follow.
