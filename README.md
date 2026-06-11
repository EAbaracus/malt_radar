# Malt Radar

Malt Radar is a professional, offline-first personal whisky database and tasting library application. It features a robust **Flutter** mobile/web client powered by a highly optimized **Python (FastAPI)** backend and a local SQLite-backed data layer used outside the tracked repository.

## Architecture & Tech Stack

- **Frontend:** Flutter (Dart) with Riverpod for state management, delivering a seamless offline-first experience via a local Drift SQLite integration.
- **Backend:** Python (FastAPI), providing scalable API aggregation and robust local database orchestration.
- **Database:** Local SQLite (Production DB) structured for maximum data integrity.

## Strict Data Security & Ingestion Workflow

To protect the Golden Dataset (the master tables containing curated whiskies and distilleries), Malt Radar employs a strict, production-grade ingestion pipeline:

1. **Master Tables Are Protected:** Direct automated insertions (`INSERT`/`UPDATE`/`DELETE`) to the master `whiskies` or `distilleries` tables are strictly prohibited.
2. **Staging Isolation:** All new incoming data (API fetches, historical PDF menu parsing, external knowledge) is securely routed to isolated `staging_*` tables first.
3. **Mandatory Manual Review:** Candidate data is never automatically promoted. Everything flows into a `staging_manual_review_queue` where it awaits explicit human approval before being merged into the master library.

## Project Roadmap / Status

- ✅ **Phase 3 (Schema Migration):** Migrated to a normalized Entity Architecture. Staging and knowledge tables securely deployed to the production database environment via zero-downtime, non-destructive SQL migrations.
- ✅ **Phase 4 (Candidate Dry-Run):** Successfully mapped and simulated the ingestion of offline candidates (Whisky Edition API, The Malt List PDF, WhiskeyFYI) into preview staging matrices without touching production records.
- ⚠️ **Phase 5 (Staging Import & Execution):** Initial execution attempt was safely rolled back after schema mismatch detection. Master tables remained unchanged. The next step is Phase 5A — staging schema reconciliation.
- ⏳ **Phase 5A (Staging Schema Reconciliation):** Align staging table schemas with Phase 4 preview CSV columns before retrying staging import.

## Current Data Pipeline Status
The robust ETL pipeline consists of the following key scripts:
- **`pre_pipeline_merge.py`**: Pre-processes raw master data, merges Claude-repaired datasets safely without overriding confirmed fields, handles alias mapping, and produces final consolidated inputs.
- **`ingest_whisky_database.py`**: The main ETL script. Safely imports consolidated data into the SQLite database enforcing schema validation, mapping foreign keys, and capturing failed rows.
- **`inspect_whisky_db.py`**: Quality assurance script. Examines the generated database to generate high-level integrity metrics (FK violations, fill rates, missing dependencies).
- **`freeze_checkpoint.py`**: Safely archives a successful output and creates time-stamped, unalterable database backups for production candidate states.
- **`apply_review_fix_42_checkpoint.py`**: Automates safe transitions of experimental patches (like triage auto-fixes) into the main production inputs, running full verification pipelines before finalizing a checkpoint.

---

## Installation & Running Locally

### 1. Backend (FastAPI) Setup
```bash
# Navigate to the backend directory
cd backend

# Create and activate a virtual environment
python -m venv venv
# On Windows: venv\Scripts\activate
# On Mac/Linux: source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the FastAPI server
uvicorn run:app --host 0.0.0.0 --port 8080 --reload
# (Or alternatively use: python run.py)
```

### 2. Frontend (Flutter) Setup
```bash
# In a new terminal tab, navigate to the frontend directory
cd frontend

# Fetch packages
flutter pub get

# Run the application (e.g., on Chrome)
flutter run -d chrome --web-port 8888
```

---

*Note: For a clean repository history, all massive data ingestion reports, temporary staging outputs (`output/`), database backups, and compiled `build/` files are explicitly excluded via `.gitignore`.*
