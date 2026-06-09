# Malt Radar

Malt Radar, Flutter ve Python tabanlı (FastAPI) geliştirilmiş kişisel bir viski veritabanı ve tadım notu uygulamasıdır. Kullanıcıların viski araması yapmasına, kendi 100 üzerinden referans sistemlerine göre puanlama yapmalarına ve yerel kütüphanelerinde viskilerini (fiyatları ve tadım notlarıyla) saklamalarına olanak tanır.

## Özellikler

- **Offline-First Mimari:** Yerel SQLite (Drift) veritabanı sayesinde çevrimdışı çalışabilme.
- **Backend Entegrasyonu:** Web scraping yerine, backend üzerinden çalışan mock API sağlayıcılarla (WhiskyHunter, WhiskyEdition) veri normalizasyonu.
- **Kişisel Skor Sistemi:** Seçtiğiniz 100 puanlık bir referans viskiye göre diğer viskileri puanlama imkanı.
- **Modern Arayüz:** Riverpod State Management ve modern koyu tema tasarımı.
- **Web Desteği:** Drift'in yerel Wasm dosyaları ile hızlı web derleme desteği.

## Proje Yapısı

Proje iki ana klasörden oluşur:
1. `backend/`: Python ve FastAPI ile yazılmış arka plan servisi. Veri kaynaklarını taklit eder ve arama isteklerini yanıtlar.
2. `frontend/`: Dart ve Flutter ile yazılmış mobil/web uygulaması.

---

## Kurulum ve Çalıştırma

Projeyi bilgisayarınızda çalıştırmak için iki terminal sekmesine ihtiyacınız olacak.

### 1. Backend (Python API) Sunucusunu Başlatma

Backend'i çalıştırmak için Python yüklü olmalıdır.

```bash
# Proje dizininden backend klasörüne gidin
cd "malt radar/backend"

# Gerekli bağımlılıkları yükleyin (İlk seferde gereklidir)
pip install -r requirements.txt

# Geliştirici sunucusunu başlatın
python run.py
```
*(Sunucu varsayılan olarak http://localhost:8080 adresinde çalışır)*

### 2. Frontend (Flutter Uygulaması) Sunucusunu Başlatma

Ayrı bir terminal sekmesi açın. Flutter'ın yüklü ve ayarlarının yapılandırılmış olması gerekir.

```bash
# Proje dizininden frontend klasörüne gidin
cd "malt radar/frontend"

# (Opsiyonel) Paketleri indirin
flutter pub get

# Uygulamayı Chrome tarayıcı üzerinde başlatın
flutter run -d chrome --web-port 8888
```

Uygulama başarıyla derlendiğinde tarayıcınızda http://localhost:8888 adresinden kullanmaya başlayabilirsiniz.
