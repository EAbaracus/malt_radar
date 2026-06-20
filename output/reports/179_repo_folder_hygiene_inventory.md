# 179 Repo Folder Hygiene Inventory

* Current branch: `maintenance/repo-folder-hygiene`
* Git status: Clean working tree for tracked files.
* Top-level folders: `.fallow`, `.git`, `.github`, `.idea`, `.pytest_cache`, `backend`, `build`, `claude database`, `data`, `dist`, `etl`, `frontend`, `output`, `raw_sources`, `schema`, `scripts`, `tests`, `__pycache__`
* Largest files top 50:
  - 164.2 MB (`.git` cache / objects)
  - 163.7 MB (`.git` cache / objects)
  - 149.9 MB (`.git` cache / objects)
  - 142.7 MB (`frontend/build` artifacts)
  - 60.4 MB (`frontend/build` artifacts)
  - 60.2 MB (`dist/manual-apk-beta/MaltRadar-beta-release-2026-06-18.apk`)
  - 60.2 MB (`frontend/build/app/outputs/flutter-apk/app-release.apk`)
  - 58.0 MB (`frontend/build` artifacts)
  - 51.2 MB (`frontend/build` artifacts)
  - 39.8 MB (`frontend/build` artifacts)
  - 30.9 MB (`frontend/build` artifacts)
* Untracked files: 
  - `dist/`
  - `scripts/generate_flavor_gap_candidates.py`
  - `tests/test_flavor_gap_enrichment.py`
* Ignored files: `output/*`, `raw_sources/*`, `claude database/*`, `tracked_files*.txt`, `investigate*.py`, `test_row.py`, `__pycache__/*`, `.pytest_cache/*`, vb.
* Generated/cache folders: 
  - `.pytest_cache`, `backend/.pytest_cache`, `tests/__pycache__`, `backend/app/__pycache__`, `__pycache__`
  - `build`, `frontend/build`
  - `frontend/.dart_tool`
  - `frontend/android/.gradle`
  - `.idea`
* dist contents: 
  - `dist/manual-apk-beta/INSTALL_NOTES_TR.md` (928 bytes)
  - `dist/manual-apk-beta/MaltRadar-beta-release-2026-06-18.apk` (60.2 MB)
  - `dist/manual-apk-beta/MaltRadar-beta-release-2026-06-18.apk.sha256.txt` (372 bytes)
* output report count: 1121 files
* production.db status: DO NOT TOUCH. Safe.
* Risk notes: 
  - Yüksek hacimli `output/` dizini (1121 dosya, loglar ve eski import verileri).
  - `.git` çok şişmiş durumda (garbage collection gerekebilir).
  - `frontend/build` dizininde büyük boyutlu apk ve cache dosyaları mevcut (silinmesi durumunda flutter build süresi uzar, ancak yer açar).
