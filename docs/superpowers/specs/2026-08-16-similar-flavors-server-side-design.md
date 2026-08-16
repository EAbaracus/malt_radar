# Benzer Lezzetler — Server-side Similarity Endpoint (Design Spec)

- **Tarih:** 2026-08-16
- **Durum:** NİHAİ (Spec Review Passed)
- **Kapsam:** `GET /api/db/public/whiskies/{id}/similar` endpoint + `SimilarityService` (tam katalog, read-only) + Flutter repo bağlantısı
- **Mimari Karar:** Option A (Server-side similarity, tam havuz) — kullanıcı GO (2026-08-16)
- **Önceki kararlar:** `2026-08-12-anonymous-read-layer-design.md` — bu spec onun **bilinçli kapsam genişletmesi**dir (G1).

---

## 1. Problem ve Amaç

"Benzer Lezzetler" bölümü yalnızca **A/B harfli viskileri** gösteriyor, benzerlik oranları düşük.

**Kök neden (koddan doğrulandı):**

| Katman | Dosya:satır | Gerçek |
|---|---|---|
| Katalog sıralaması | `backend/app/services/db_read_service.py:238` | `ORDER BY w.name ASC` — alfabetik |
| Benzerlik aday havuzu | `frontend/lib/features/whisky/data/repositories/db_whisky_repository_impl.dart:198-206` | `getSimilarWhiskies` yalnızca page 0-4 (250 satır) çeker = alfabetik ilk 250 = **A/B harfli viskiler** |
| Benzerlik hesabı | aynı dosya `:209-232` | Euclidean mesafe, **sadece o 250 kişilik önyargılı havuzda** client-side |
| Backend endpoint | `backend/app/routers/db_api.py` / `db_public_api.py` | `/similar` endpoint **yok**; P45/P46 motoru (`output/p45/p45_recommendation_engine.py`, GO-gate'li, canonical) API'ye bağlanmamış |

Gerçek benzer profiller 4.409 profilin arasında yaşarken benzerlik yalnızca alfabetik ilk 250'lik dilimde hesaplanıyor → önyargılı sonuç + düşük skor.

**Amaç:** Benzerlik hesabını **tam aktif katalog** üzerinde, **server-side** (read-only) yaparak gerçek benzer profilleri döndürmek. Client-side 250 satırlık bounded-fetch tamamen ortadan kalkar.

---

## 2. Governance Kararları

| # | Karar | Gerekçe |
|---|-------|---------|
| **G1** | **Bilinçli Kapsam Genişletmesi: tam havuz sonuç** | Anonim okuma katmanı (`anonymous_read_layer`) tüm public endpoint'leri `artifacts/anonymous_allowlist.json` (N=150) ile intersect eder. `/similar` **istisnadır**: sonuçlar tam aktif katalogdan top-N döner. Gerekçe: allowlist'e sınırlı bir benzerlik hesabı bug'ı yeniden üretir (gerçek benzer profil allowlist dışında olabilir). Maruziyet artışı **yok**: dönen alanlar (name, distillery, region, type, global_score) SEO statik katmanının 2.483 Tier A viski için **zaten public** yaptığı alanlardır. Evidence/price/tasting-notes/fiyat **ASLA** dönmez. İstisna **yalnızca sonuçlar** içindir; hedef `whisky_id` allowlist intersect'ine tabidir (kardeş endpoint deseni, madde 4.1). |
| **G2** | **Read-only, PromotionGate gerekmez** | Endpoint yalnızca `production_read_adapter` deseniyle okur; production.db'e yazma yok → KEP gözetim ritüeli tetiklenmez. |
| **G3** | **Metrik: Euclidean (mevcut client ile parity)** | Değiştirilen client kodu Euclidean sum-of-squares kullanır. Aynı sıralama semantiği korunur → davranışsal sürpriz yok, mevcut test zihniyetiyle uyumlu. Cosine metrik kapsam dışı (G7). |
| **G4** | **Normalize portu Dart ile birebir** | `frontend/lib/features/flavor/domain/flavor_profile_normalizer.dart`'ın mantığı (7 eksen, `_scale` ≤1→×10, WhiskeyMapper `component_1..3` fallback'i) **birebir** `similarity_service.py`'ye taşınır. Aksi halde client/server skorları kıyaslanamaz. |
| **G5** | **Response shaping parity** | Dönen alanlar mevcut `_shape_whisky` alan setiyle sınırlı (+ `distance`, `similarity`). Ham `flavor_profile` JSON, evidence row, fiyat yok. |
| **G6** | **Fallback: eski backend uyumluluğu** | Flutter repo, endpoint yoksa (404) veya ağ hatasıysa mevcut bounded-fetch'e düşer. Yeni backend'de asla tetiklenmez (doğrulama: test). |
| **G7** | **Cosine metrik / P45 tam bağlanması kapsam dışı** | Daha geniş iş; ayrı spec gerektirir. Bu spec yalnızca top-5 widget'ının doğru havuzda çalışmasını hedefler. |

---

## 3. Mimari ve API Yüzeyi

### Yeni endpoint: `GET /api/db/public/whiskies/{whisky_id}/similar?limit=5`

`backend/app/routers/db_public_api.py` (public namespace — onaylı API tercihi: farklı kontrat → ayrı namespace; anonim kullanıcılar benzer lezzetleri görür, flavor-profile zaten public).

| Parametre | Varsayılan | Sınır |
|---|---|---|
| `whisky_id` | — | path |
| `limit` | 5 | 1-20 (Query ge/le) |

**Yanıt:**
```json
{
  "whisky_id": "W003023",
  "similar": [
    {
      "whisky_id": "W004123",
      "name": "...",
      "distillery": "...",
      "region": "...",
      "type": "...",
      "global_score": 8.2,
      "distance": 0.31,
      "similarity": 0.64
    }
  ]
}
```

- `similarity = 1 / (1 + sqrt(distance))` — monotonik, sıralamayı değiştirmez; UI ileride oran gösterecekse hazır.
- Sıralama: `distance` artan (client'taki mevcut sıralamayla aynı semantik).

### Bileşenler

| Bileşen | Dosya | Sorumluluk |
|---|---|---|
| `SimilarityService` | `backend/app/services/similarity_service.py` (yeni) | 7-eksen normalize portu (Dart parity, G4) + Euclidean; tam aktif katalog; self hariç; superseded hariç |
| Route | `backend/app/routers/db_public_api.py` | `GET /whiskies/{id}/similar`, 120/min rate-limit (kardeş endpoint'lerle aynı), hedef yoksa 404, DB yoksa 503 |
| Delegate | `backend/app/services/anonymous_catalog_service.py` | `get_similar_whiskies(whisky_id, limit)` → `SimilarityService`'e pasla; shaping uygula (G5) |
| Client | `frontend/lib/core/api/db_whisky_api_client.dart` | `getSimilarWhiskies(String whiskyId, {int limit = 5})` — public endpoint |
| Repo | `frontend/lib/features/whisky/data/repositories/db_whisky_repository_impl.dart:184` | Endpoint'i dene; 404/network hatasında bounded-fetch fallback (G6); `similarity` → `styleSimilarity` map |

### Data akışı

```
detail_screen → SimilarFlavorWhiskies (backendId) → backendSimilarWhiskiesProvider
→ repo.getSimilarWhiskies(id, limit:5)
→ GET /api/db/public/whiskies/{id}/similar?limit=5
→ SimilarityService: tam aktif katalog tara (4.409 profil), normalize + Euclidean
→ top-N → shaping → DbWhiskyMapper.toLegacyMap → Whisky → yatay kart listesi
```

---

## 4. SimilarityService Davranış Kuralları

1. **Hedef yok** (whiskies tablosunda bulunamadı) **veya hedef allowlist dışı** (kardeş public endpoint deseni: `get_whisky`/`get_flavor_profile` aynı kontrolü yapar) → route 404 döner.
2. **Hedefin flavor_profile'i yok/boş** → `{"similar": []}` (200) → UI "Benzer lezzet eşleşmesi bulunamadı" gösterir.
3. **Aday taraması:** aktif viskiler (superseded hariç) + `flavor_profiles` JOIN; `flavor_profile` boş/null adaylar atlanır (mevcut client davranışı: `hasData`).
4. **Normalize:** `normalizeFlavorProfileMap` portu — eksen değeri varsa doğrudan, yoksa WhiskeyMapper component fallback; parse hatası olan profil `{}` sayılır (atlanır).
5. **Distance:** hedef eksenleri üzerinden Euclidean sum-of-squares (`target[k] - other[k]`)², ortak eksen yoksa aday atlanır.
6. **Self:** hedef kendi `whisky_id`'si aday listesinden çıkarılır.
7. **Performans:** 4.409 × 7 eksen ≈ ~30K float op/request → altı-ms. Cache/precompute YAGNI (G7 ile birlikte ileride değerlendirilir).

---

## 5. Hata Yönetimi

| Durum | HTTP | UI davranışı |
|---|---|---|
| Hedef yok veya superseded | 404 | "Benzer lezzet eşleşmesi bulunamadı" (repo fallback: boş liste) |
| Hedef profilsiz / aday yok | 200 `{"similar": []}` | "Benzer lezzet eşleşmesi bulunamadı" |
| DB/artifact yok | 503 | Mevcut kardeş endpoint'lerle aynı desen |

> **G1 REV (2026-08-16, `6871ddb`):** Hedef allowlist gate'i kaldırıldı — sonuçlar zaten tam havuz olduğundan gate koruma sağlamıyordu ve allowlist dışı 4.400+ viskide "Benzer Lezzetler" boş dönüyordu (ürün regresyonu). 404 artık yalnızca hedef yoksa/superseded ise. Test: `test_similar_non_allowlist_active_target_200`.
| Rate limit | 429 | Mevcut 120/min limiti |
| Eski backend (endpoint yok) | 404 → fallback | Bounded-fetch eski davranış (G6) |

---

## 6. Testler

### Backend (pytest)
1. Endpoint top-5 döner, `limit=1..20` sınırları çalışır.
2. Self dışlanır.
3. Anonim erişim (auth gerekmez).
4. Bilinmeyen `whisky_id` → 404; profilsiz hedef → boş liste.
5. **Bug regresyon kanıtı:** peated bir Islay hedefinin sonuçları alfabetik A/B dilimiyle sınırlı **olmamalı**; en az bir sonuç `name` ilk harfi > 'B' olmalı (tam havuz kanıtı).
6. Normalize portu Dart referans değerleriyle parity: 7-eksen doğrudan, `component_1..3` fallback, `_scale` ≤1→×10.

### Frontend
7. Mevcut `similar_flavor_test.dart` (lokal mod) dokunulmaz — green kalmalı.
8. Repo `getSimilarWhiskies`: mock client ile endpoint çağrısı + map doğruluğu; endpoint 404 → fallback davranışı.

---

## 7. Kapsam Dışı (Bilinçli)

- Cosine metrik / P45 motorunun tam API bağlanması (ayrı spec; G7).
- UI'da similarity % gösterimi (endpoint `similarity` alanı hazır; ayrı iş).
- Cache / precompute katmanı (ölçek kanıtı olmadan YAGNI).
- Allowlist genişletme / SEO katmanı değişikliği (dokunulmaz).

---

## 8. Doğrulama (Completion)

- Backend pytest green (madde 6.1-6.6).
- Frontend: mevcut + yeni testler green.
- Canlı backend'de manuel: 3 hedef (peated Islay, sherry, bourbon) için `/similar` yanıtında alfabetik önyargı yok, en yakın profiller mantıklı.
- `production.db` SHA256 değişmedi (read-only kanıtı).
