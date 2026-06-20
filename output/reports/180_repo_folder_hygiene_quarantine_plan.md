# 180 Repo Folder Hygiene Quarantine Plan

* KEEP_TRACKED:
  - `backend/`, `frontend/`, `scripts/` (tracked), `tests/`, `etl/`, `schema/`, `data/`
  - `.github/`, `.gitignore`, `README.md`, `find_dups.py`
* KEEP_LOCAL_UNTRACKED:
  - `dist/` ve `dist/manual-apk-beta/` (Beta APK dağıtım paketi)
* GENERATED_IGNORE:
  - `build/`, `frontend/build/`
  - `frontend/.dart_tool/`, `frontend/android/.gradle/`
  - `.pytest_cache/`, `backend/.pytest_cache/`, `__pycache__/` ve alt dizinleri
  - `.flutter-plugins-dependencies`, `.idea/`
* ARCHIVE_CANDIDATE:
  - `output/` içerisindeki tüm alt dizinler (harici: `output/import/production.db` ve güncel CSV seed'ler)
  - `tracked_files*.txt`
  - `00_api_feasibility_report.txt`, `hata_analizi.md`, `test_agent.py`, `repair_agent.py`, `investigate*.py`, `test_row.py`, `verify_db_api.py`
  - `claude database/`
* REVIEW_BEFORE_DELETE:
  - `raw_sources/`
  - `scripts/generate_flavor_gap_candidates.py` (Untracked, branch ile uyumlu değilse quarantine)
  - `tests/test_flavor_gap_enrichment.py` (Untracked, incele)
* DO_NOT_TOUCH:
  - `output/import/production.db`
  - Frontend asset CSV'leri (`frontend/assets/**/*.csv`)
  - Backend/data master dosyaları (`data/**/*.csv`)
  - APK dosyaları
* Proposed .gitignore updates:
  - Sadece `.fallow` veya quarantine dizinini ignore listesine eklemek. `dist/` halihazırda takip edilmiyor, ignore listesine açıkça eklenebilir.
* Proposed archive folder:
  - Yeni bir `.fallow` veya `output/archive_old_runs/` dizini altına alınması önerilir.
* Proposed next commands:
  - Yeni klasörleri archive'a taşımak için PowerShell scriptleri.
  - `git gc --prune=now` (.git boyutunu küçültmek için)
* Files safe to stage: YOK. Sadece raporlar.
* Files not safe to stage: `dist/`, `.pytest_cache/`, `build/`, `output/` vb.
* Commit readiness: NO
