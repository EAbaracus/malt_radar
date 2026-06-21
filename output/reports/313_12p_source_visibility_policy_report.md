# External Source Public Visibility Policy (AŞAMA 12P)

## Policy Decision
- **Source attribution**: Kept for internal audit ONLY.
- **Public UI**: No external sources will be shown to users.
- **Public API**: No source fields will be returned in public responses.
- **User Uploads**: Documents uploaded by users will still have their source display flag set to false.

## Registry Update
- **Updated Sources**: 11
- **Columns Added**: `public_source_display_allowed`, `public_api_source_fields_allowed`, `internal_audit_only`
- **Whiskyfun Added**: True

## Code Scan (Leakage Risk)
- **Frontend Risk Found**: YES (9 files flagged)
- **Backend/API Risk Found**: YES (5 files flagged)

### Frontend Flagged Files:
- frontend\lib\core\database\database.dart:20
- frontend\lib\core\database\database.g.dart:142
- frontend\lib\core\database\data_seed_service.dart:29
- frontend\lib\features\whisky\data\dto\db_whisky_dto.dart:33
- frontend\lib\features\whisky\data\repositories\whisky_repository_impl.dart:127
- frontend\lib\features\whisky\domain\models\whisky.dart:17
- frontend\lib\features\whisky\domain\repositories\whisky_repository.dart:30
- frontend\lib\features\whisky\presentation\screens\detail_screen.dart:85
- frontend\web\drift_worker.js:4576

### Backend/API Flagged Files:
- backend\app\models\schemas.py:19
- backend\app\providers\csv_provider.py:160
- backend\app\providers\distiller_provider.py:63
- backend\app\providers\mock_providers.py:215
- backend\app\services\review_query_service.py:53

## Integrity Check
- **production.db Hash**: e8f1839e312fe474a43f3f224d5c7d57e213f28db75545516d242788fdcf36a8
- **DB Changed**: False

## Gate Status
**GO_WITH_CODE_GUARD_RECOMMENDED**
