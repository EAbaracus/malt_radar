# 166 10K i18n Duplicate Key Test Conversion

**Mevcut find_dups.py durumu:**
Manuel olarak stdout'a çıktı basan yapıda tutulmuştur.

**Teste dönüştürülen mantık:**
`app_translations.dart` dosyasındaki TR ve EN anahtarları regex ile okunarak bir `set` içerisinde toplanıp duplicate olup olmadığı kontrol edilmektedir. Bu mantık `tests/test_i18n_duplicate_keys.py` içerisine taşınarak, testin assert üzerinden çalışması sağlanmıştır.

**Duplicate bulunup bulunmadığı:**
Sistemde duplicate bulunmamaktadır (veya var olanlar giderilmiştir). Test başarıyla geçmektedir.

**Komut çıktısı:**
```powershell
$env:PYTHONPATH="backend"
python -m pytest tests/test_i18n_duplicate_keys.py -v
```
Result: `PASSED`

**Karar:**
GO
