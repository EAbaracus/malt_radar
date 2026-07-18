# P203D — Task 7: pytest Results (read-only execution)

> Real run against the live staging DB, opened in read-only mode (`uri mode=ro`).
> No DB mutated. No production/knowledge DB accessed.

## Command executed
```bash
python -m pytest mr-kep/tests/test_p203d_staging.py -v --tb=short
```

## Result (actual)
```
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0 -- C:\Users\eltun\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: C:\Users\eltun\Documents\malt radar CLEAN
plugins: anyio-4.12.1, cov-7.1.0
collecting ... collected 10 items

mr-kep/tests/test_p203d_staging.py::test_staging_inventory_total PASSED  [ 10%]
mr-kep/tests/test_p203d_staging.py::test_evidence_id_unique PASSED       [ 20%]
mr-kep/tests/test_p203d_staging.py::test_no_duplicate_groups PASSED      [ 30%]
mr-kep/tests/test_p203d_staging.py::test_source_distribution PASSED      [ 40%]
mr-kep/tests/test_p203d_staging.py::test_review_queue_detection PASSED   [ 50%]
mr-kep/tests/test_p203d_staging.py::test_evidence_schema_required_fields PASSED [ 60%]
mr-kep/tests/test_p203d_staging.py::test_whisky_name_not_site_term PASSED [ 70%]
mr-kep/tests/test_p203d_staging.py::test_crosswalk_review_handling PASSED [ 80%]
mr-kep/tests/test_p203d_staging.py::test_flavour_vector_validation PASSED [ 90%]
mr-kep/tests/test_p203d_staging.py::test_staging_db_opens_read_only PASSED [100%]

============================= 10 passed in 0.18s =============================
```

## Coverage (per spec Task 7)
| spec item | test |
|---|---|
| staging inventory validation | `test_staging_inventory_total`, `test_source_distribution` |
| evidence schema validation | `test_evidence_schema_required_fields`, `test_whisky_name_not_site_term` |
| duplicate detection | `test_evidence_id_unique`, `test_no_duplicate_groups` |
| review queue detection | `test_review_queue_detection` |
| crosswalk review handling | `test_crosswalk_review_handling` |
| flavour vector validation | `test_flavour_vector_validation` |
| read-only / offline safeguard | `test_staging_db_opens_read_only` |

## Verification
- All 10 tests passed on the live `editorial_staging_retry.db`, opened read-only.
- No DB mutation possible (uri `mode=ro`); no network.
- `production.db` hash unchanged: `8350fe9de2f1c73d…`
- `knowledge.db` hash unchanged: `e4c0d8b42d2173c3…`
- `knowledge.db.pre_p203b.bak` hash unchanged: `37eed610b4f0ff63…`
- **pytest result: PASS (10/10).**
