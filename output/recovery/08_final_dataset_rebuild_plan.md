# FINAL DATASET REBUILD PLAN

## 1. Eksik Kritik Dosyalar
- final whisky import CSV
- final distillery import CSV
- final import manifest
- production seeder script
- staging DB
- distillery patch diff
- orphan bulk patch
- flavor cleaned import CSV
- source verified tasting notes CSV

## 2. Mevcut Bulunan Dosyalar
- `output/flavor/30_HIGH_CONFIDENCE_flavor_profiles_WDB_MAPPED.csv`
- `output/malt_list/12_malt_list_tasting_notes_patch_preview.csv`
- Diğer `output/malt_list/` klasörü altındaki candidate dosyaları

## 3. Rebuild İçin Gereken Minimum Kaynaklar
- `whisky_database_merged_max.csv` veya orijinal merged source
- final distillery source
- flavor mapping source
- source verified tasting notes source
- Varsa previous reports

## 4. Güvenli Rebuild Sırası
A) whisky master rebuild
B) distillery master rebuild
C) distillery-only kayıtları ayır
D) whisky product count doğrula
E) orphan distillery patch yeniden üret
F) final whisky CSV üret
G) final distillery CSV üret
H) flavor import-ready dosyasını yeniden üret
I) tasting notes source verified dosyasını yeniden üret
J) manifest oluştur
K) dry-run validator oluştur
L) staging import test
M) production seeder dry-run

## 5. Kesin Yasaklar
- Eski `merged_max` doğrudan production final kabul edilmeyecek.
- Fallback master ile patch yapılmayacak.
- Candidate dosyaları production’a yazılmayacak.
- Manual review kayıtlar otomatik uygulanmayacak.

## 6. Kullanıcıdan İstenecek Dosyalar
Lütfen mevcutsa aşağıdaki dosyaları sisteme/projeye dahil edin:
- final CSV yedeği (varsa)
- yoksa ham kaynak dosyaları
- önceki `output/final` klasörü yedeği (varsa)
- `scripts` klasörü yedeği (varsa)

## 7. Son Öneri
Eğer final dosyalar bulunamıyorsa, production import süreci sıfırdan **rebuild edilmelidir**.
