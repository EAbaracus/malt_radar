# Test Hata Analizi

## Özet
Testler `2` çıkış kodu ile başarısız oldu. Lütfen logları inceleyin.

## Çalıştırılan Komut
```bash
python -m pytest
```

## Exit Code
2

## Kırılan Testler
* ____________ ERROR collecting backend/tests/test_db_api_adapter.py ____________
* ERROR backend/tests/test_db_api_adapter.py

## Muhtemel Kök Nedenler
* E   ModuleNotFoundError: No module named 'app'

## Çözüm Önerileri
* Kırılan testlerle ilgili kod bloklarını gözden geçirin.
* Hata loglarındaki çağrı yığınını (stack trace) takip edin.

## Ham Log Özeti
```text
============================= test session starts =============================
platform win32 -- Python 3.13.13, pytest-9.0.3, pluggy-1.6.0
rootdir: C:\Users\eltun\Documents\malt radar
plugins: anyio-4.13.0
collected 28 items / 1 error

=================================== ERRORS ====================================
____________ ERROR collecting backend/tests/test_db_api_adapter.py ____________
ImportError while importing test module 'C:\Users\eltun\Documents\malt radar\backend\tests\test_db_api_adapter.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
C:\Program Files\Python313\Lib\importlib\__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
backend\tests\test_db_api_adapter.py:4: in <module>
    from app.main import app
E   ModuleNotFoundError: No module named 'app'
============================== warnings summary ===============================
..\..\AppData\Roaming\Python\Python313\site-packages\fastapi\testclient.py:1
  C:\Users\eltun\AppData\Roaming\Python\Python313\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ===========================
ERROR backend/tests/test_db_api_adapter.py
!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
========================= 1 warning, 1 error in 7.21s =========================

```
