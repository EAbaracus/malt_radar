# Malt Radar - Project State

Bu dosya projenin tek gerçek durum kaydı (single source of truth) olarak kullanılır. Ajanlar kararlarını buradaki kurallara göre alır.

## 1. Aktif Aşama
**Current Phase:** 10G

## 2. Aktif Branch'ler
- **Backend:** master
- **Frontend:** master

## 3. Stabil API Kontratı
- API iletişimleri için geçerli stabil sürüm `/api/v1/*` rotalarıdır.
- DB API entegrasyonu mevcuttur ve `USE_DB_API=true` konfigürasyonu üzerinden test edilir.

## 4. Test Komutları
- **Backend Test:** `python -m pytest tests/ -v`
- **Frontend Linter:** `flutter analyze`
- **Frontend Test:** `flutter test`

## 5. Bilinen ve Kabul Edilmiş Sorunlar
- (Boş) - Yeni bir sorun tespit edildiğinde buraya eklenir.

## 6. Yasaklı Otomatik Değişiklikler
Otomatik stage ve commit süreçlerinde aşağıdaki dosyalara ve yollara DOKUNULAMAZ:
- `production.db`
- `backend/data/*.csv`
- `data/input/*`
- `.env`
- `restore/*` veya `recovery/*` dizinlerindeki script'ler
- `repo_agent.py`'nin `push` yapması veya branch silmesi kesinlikle yasaktır.
