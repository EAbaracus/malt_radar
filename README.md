# Malt Radar

Whisky discovery platform combining flavor intelligence with a structured whisky database. Explore distilleries, search the catalog, inspect detailed whisky profiles, and visualize each expression on a Flavor Radar with similar-whisky recommendations.

## ✨ Features

- **Whisky discovery** — browse and surface whiskies from a structured catalog.
- **Distillery exploration** — inspect distilleries and their expressions.
- **Search** — find whiskies by name, distillery, or attribute.
- **Whisky profiles** — detailed per-expression data and metadata.
- **Flavor Radar** — visualize a whisky's flavor signature across its axes.
- **Similar whisky recommendations** — find expressions that taste alike.

### Flavor Radar axes

The radar charts each whisky across seven normalized flavor dimensions:

- Fruity
- Sweet
- Spicy
- Smoky / Peaty
- Oak / Cask
- Malty / Cereal
- Floral / Herbal

### Similarity model

Similar whisky recommendations are ranked from a whisky's flavor profile and catalog attributes. The scoring blends flavor proximity with region and category signals. (Exact weights live in the recommendation code; not hard-coded as a single fixed split.)

## 🏗 Architecture

| Layer | Technology |
|-------|------------|
| Frontend | Flutter |
| State management | Riverpod |
| Local database | Drift (SQLite) |
| Backend API | FastAPI (Python) |
| Data pipelines | Python ETL scripts |

The Flutter app ships the structured database locally via Drift/SQLite, while Python pipelines and a FastAPI backend support ingestion and data services.

## 📊 Data Pipeline

External sources are processed through a staged flow:

```
External Sources
        ↓
   Extraction
        ↓
  Normalization
        ↓
  Validation
        ↓
    Staging
        ↓
  Production
```

Principles:

- **Staging-first** — experimental work lands in staging before production.
- **Production DB protection** — the production database is not mutated by ad-hoc or experimental runs.
- **Audit reports** — data changes are recorded and reviewable.
- **Validation gates** — data must pass validation before promotion.

## 🔒 Data Safety

- The production database is never modified directly by experimental operations.
- Import and merge work proceeds through staging.
- Data changes are audited and traceable.

## 🚀 Development

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

Backend serves on port `8080` by default (override with the `PORT` environment variable).

## 📦 Release Pipeline

CI runs on push to `main` and on version tags (`v*`):

```
push main / tag v*
        ↓
  flutter pub get
        ↓
   flutter test
        ↓
  flutter build apk --release
        ↓
  GitHub Artifact
        ↓
  GitHub Release (tag)
        ↓
  Google Drive upload (when configured)
```

See `.github/workflows/android-release.yml`. The Drive upload step runs only when `GOOGLE_DRIVE_CREDENTIALS` and `GOOGLE_DRIVE_FOLDER_ID` secrets are set.

## 📁 Repository Structure

```
malt radar CLEAN/
├── frontend/        # Flutter app (Riverpod + Drift)
├── backend/         # FastAPI backend
├── etl/             # Python ETL pipelines
├── src/             # book ingestion sources
├── data/            # datasets and working data
├── schema/          # database schema definitions
├── docs/            # pipeline & project documentation
├── scripts/         # utility scripts
├── reports/         # audit / validation reports
├── tests/           # backend & pipeline tests
├── memory/          # project memory
├── rules/           # operating rules
├── workflows/       # workflow definitions
└── production.db    # production SQLite database
```

Only folders present in the repository are listed.

## 🗺 Roadmap

Current focus areas:

- Data quality improvements
- Flavor profile expansion
- UI refinement
- Release automation

## 📚 Documentation

See the `docs/` folder for pipeline documentation, project maps, and reports:

- `docs/PIPELINE.md`
- `docs/PROJECT_MAP.md`
- `docs/pipeline/`
- `docs/reports/`
