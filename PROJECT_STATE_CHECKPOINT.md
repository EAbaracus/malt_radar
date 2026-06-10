# Malt Radar - Project State Checkpoint

Bu dosya uygulamanın ve veri boru hatlarının (data pipelines) güncel durumunu, alınan kararları ve bir sonraki aşama olan **AŞAMA 3** planlamasını içerir.

## 1. Veri ve Dosya Yolları (Paths)
- **Production Baseline (Core Data):** `backend/data/whisky_database_merged_max.csv`
- **Final CSV Paths:** 
  - `backend/data/whisky_database_merged_max.csv` (Ana veri)
  - `backend/data/production_data.csv` (Production snapshot)
  - `backend/data/flavor_profiles.csv` (Tadım profilleri)
  - `backend/data/Distillery.csv` (Damıtımevi listesi)
- **Production DB Path:** (Proje şu an ana kaynak olarak CSV Provider kullanmaktadır. Frontend tarafında ise Drift SQLite veritabanı uygulama içi cihaz klasöründe oluşur.)
- **Backup Paths:** 
  - `recovered_from_radiant_bardeen/` (Eski sistem kurtarma yedekleri)
  - `auto_push.ps1` tarafından otomatik alınan GitHub commit/push geçmişi.

## 2. İş Durumları (Task Status)

### 2.1 Tamamlanan İşler
- **Core UI Modernizasyonu:** Glassmorphism arayüzü, Google Fonts (Outfit & Inter) entegrasyonu ve genel premium tasarım iyileştirmeleri tamamlandı.
- **Kaggle Baseline Import:** Temel viski verileri, özellikleri ve tadım profilleri `whisky_database_merged_max.csv` üzerinden sisteme entegre edildi.
- **67_FINAL (Whisky.com) Integration:** Sadece güncelleme (update-only metadata backfill) stratejisiyle çalıştırıldı. Mevcut yapıları bozmadan başarıyla üretim hattına yansıtıldı ve kilitlendi (CLOSED/LOCKED).

### 2.2 Candidate Olarak Bekleyen İşler
- **Malt List Fiyatları:** 23 adet `historical_menu_price` düşük riskli (LOW risk) aday mevcut. `current_price` olarak kullanılamayacağı için beklemeye alındı. Ayrıca 57 aday için manual review (elle kontrol) gerekiyor.
- **Whisky Edition API Tadım Notları:** Çekilen 523 review'dan 522'si tadım notu adayı (tasting note candidate). 5'i manual review statüsünde. 
- **WhiskeyFYI Zenginleştirme:** 19 adet güvenli açıklama zenginleştirmesi (safe description enrichment) adayı bulundu. 

### 2.3 AŞAMA 3'e Devredilen Kaynaklar
- **Malt List:** Mevcut PDF parse işlemi yetersiz kaldığından, tasting note'lar için PDF reparse sistemi kurulacak ve fiyatlar manuel kontrolden geçirilecek.
- **Whisky Edition API:** Yüksek güvenilir eşleşme (high-confidence match) yakalanamadığı için yeni product (ürün) adayları olarak ele alınacak. Bu durum "AŞAMA 3 Entity Model" ve staging (hazırlık) ortamı gerektirdiği için bu aşamaya devredildi.
- **WhiskeyFYI:** Knowledge tables (bölgeler, sözlük, rehberler) ve metadata zenginleştirmeleri AŞAMA 3 Knowledge Pipeline dahilinde incelenecek.

## 3. Korunması Gerekenler (Safety Constraints)

### 3.1 Silinmemesi Gereken Klasörler
- `output/` (Bütün review, match ve candidate closure raporları burada yer almaktadır)
- `backend/data/` (Production datasetleri burada bulunur)
- `scripts/` (Pipeline ve dönüşüm scriptleri)
- `recovered_from_radiant_bardeen/` (Eski versiyon yedekleridir, history için gereklidir)

### 3.2 Yeniden Çalıştırılmaması Gereken Scriptler
- **67_FINAL import scriptleri:** Veri işlendi ve kitlendi. Tekrar çalıştırılması production datasetini gereksiz yere update eder.
- **Whisky Edition API fetch scriptleri:** API limitlerini doldurmamak ve duplicate (çift) veri çekmemek adına tekrar tetiklenmemelidir. Veriler zaten `output` içine çekilmiştir.
- **İlk Kaggle verisi çekme betikleri:** `download_data.py` vb. ana veriyi bozabileceği için yalnızca sıfırdan kurulumlarda çalıştırılmalıdır.

---
**Sonraki Adım:** AŞAMA 3 (Brands / Bottlers / Companies / External Links / Knowledge Tables / Product Candidate Staging) ayrı bir branch/migration olarak tasarlanıp başlatılacaktır. Mevcut çekirdek (core) hattı güvenliğe alınmıştır.
