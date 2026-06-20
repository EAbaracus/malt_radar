# 168 10M Release Gate Script

**Oluşturulan dosya:**
`scripts/run_release_gate.py`

**İçerik/Kapsam:**
Release öncesi beta kalitesini tek bir CLI üzerinden denetlemek adına aşağıdaki testleri sıralı çalıştıracak Python subprocess mantığı kurgulanmıştır:
- `pytest` (Backend Smoke, Hardening)
- `pytest` (i18n Duplication Test)
- `pytest` (Scraper Contract Test)
- `flutter analyze`
- `flutter test` (Hedeflenmiş 4 ana test dosyası)

Her testin pass/fail durumu yakalanır ve bir test bile patlarsa script **NO-GO** olarak fail döner. Testlerin tamamı başarılı ise **GO** verir.

**Karar:**
Script çalıştırıldı. Sonuçlar `169_10m_release_gate_results.txt` dosyasına yazıldı.
