# Malt Radar

Whisky discovery platform combining flavor intelligence with a structured
whisky database. Browse distilleries, search the catalog, inspect detailed
whisky profiles, and visualize each expression on a Flavor Radar with
similar-whisky recommendations.

---

## Features

- **Whisky discovery** — browse and surface whiskies from a structured catalog.
- **Distillery exploration** — inspect distilleries and their expressions.
- **Search** — find whiskies by name, distillery, or attribute.
- **Whisky profiles** — detailed per-expression data and metadata.
- **Flavor Radar** — visualize a whisky's flavor signature across seven axes.
- **Similar whisky recommendations** — find expressions that taste alike.

### Flavor Radar axes

| Axis | Description |
|------|-------------|
| Fruity | Stone fruit, tropical, orchard |
| Sweet | Honey, vanilla, toffee |
| Spicy | Pepper, ginger, spice |
| Smoky / Peaty | Peat, smoke, medicinal |
| Oak / Cask | Wood, tannin, cask influence |
| Malty / Cereal | Grain, biscuit, malt |
| Floral / Herbal | Floral, grassy, herbal |

---

## Technology Stack

| Layer | Technology |
|-------|------------|
| Frontend | Flutter (Riverpod + Drift/SQLite) |
| Backend API | FastAPI (Python) |
| Data pipeline | **MR-KEP** + **KEP Runtime** |
| Production DB | SQLite (`output/import/production.db`) |

---

## Architecture Overview

The MR-KEP + KEP Runtime canonical pipeline processes data from ingestion to closure through the following stages:

* **INGEST & EXTRACT:** Raw whisky data is collected from external sources and parsed to extract key information.
* **NORMALIZE & CANONICALIZE:** The extracted data is cleaned, standardized, and resolved into canonical database records.
* **EVIDENCE:** Flavor profiles and supporting factual data are gathered and attached to the canonical records.
* **QA & Human GO:** Automated quality assurance invariants are checked, followed by a mandatory human review and GO/NO-GO decision.
* **PromotionGate:** The KEP Runtime safely handles the execution and promotion of validated data into the production database.
* **VERIFY & CLOSURE:** Post-promotion validation ensures data integrity, followed by formal pipeline closure.

## Canonical Pipeline — MR-KEP + KEP Runtime

**MR-KEP** (domain pipeline) and **KEP Runtime** (execution / safety layer)
are the canonical production data path. The full stage flow is:

```
INGEST → EXTRACT → NORMALIZE → CANONICALIZE → EVIDENCE → QA
     → HUMAN GO/NO-GO → PromotionGate → VERIFY → CLOSURE
```

All future production promotion **MUST** pass through **KEP Runtime PromotionGate**.
The classic P32–P42 pipeline is **RETIRED** (historical only — see
`docs/ARCHITECTURE.md` Historical section).

---

## Current Status

| Metric | Value |
|--------|-------|
| Production DB SHA | `40b7f71e84f0b5eec750deb0832f197f4eddc51c023bcdc2dde25fde93476ec0` |
| Tables | 37 |
| Whiskies | 4,749 |
| flavor_evidence rows | 3,180 |
| P500-O | **CLOSED** (299 promoted, 72-row queue remaining) |
| Remaining active queue | **72** (60 QR HOLD + 8 unresolved + 4 duplicate/overlap skips) |
| Evidence coverage | 2,924 / 4,749 whiskies (61.6%) |

**P500 canonicalization is COMPLETE** — published on branch
`p500-canonicalization`. Repository documentation is the canonical source
of truth for all operational detail.

---

## Development — Quick Start

### Flutter (frontend)
```bash
flutter pub get
flutter test
flutter build apk --release
```

### Backend (FastAPI)
```bash
cd backend
pip install -r requirements.txt
python run.py
```
Backend serves on port `8080` by default (override with `PORT` env var).

### MR-KEP / KEP Runtime (data pipeline)
```bash
# KEP Runtime dry-run (read-only, no production writes)
cd kep_review_runtime
python run.py --dry-run

# MR-KEP tests
cd mr-kep
python -m pytest tests/ -v

# KEP Runtime tests
cd kep_review_runtime
python -m pytest tests/ -v
```

---

## Testing

- To run backend tests, activate the virtual environment: `source backend/.venv/bin/activate`
- Run pytest without PYTHONPATH: `env -u PYTHONPATH pytest`
- To run frontend tests: `cd frontend && flutter test`

---


## Documentation

| Doc | Scope |
|-----|-------|
| `docs/ARCHITECTURE.md` | Canonical system architecture, responsibilities, production write path |
| `docs/PIPELINE.md` | Canonical pipeline stages (INGEST→…→CLOSURE), PromotionGate, staging-first |
| `AGENTS.md` | Governance rules, NO-GO gates, production DB protection, human GO/NO-GO |
| `ROADMAP.md` | Roadmap — P500-A…O CLOSED, P500-P/Q done, remaining 72-row queue |
| `CHANGELOG.md` | Production-level change history (P500-A…O) |
| `mr-kep/CHANGELOG.md` | MR-KEP pipeline change history |
| `mr-kep/archive/ARCHIVE_MANIFEST.md` | Archived / historical retired phases |
| `mr-kep/common/invariant_registry.yaml` | Canonical QA invariants |

> **Production DB is immutable by policy.** No direct writes. Evidence is
> INSERT-only. Every mutation goes through authorized PromotionGate with
> backup + SHA256 before/after. See `AGENTS.md` and `docs/ARCHITECTURE.md`.
