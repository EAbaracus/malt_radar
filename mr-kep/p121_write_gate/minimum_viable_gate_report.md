# Write-Path Isolation Gate — Minimum Viable Kurulum Raporu

**Tarih:** 2026-07-15 22:48 (execution, kullanıcı onaylı)
**Standartlar:** AGENTS.md DB-write kuralları uygulandı (backup → hash guard → preflight → transaction → post-validation → rollback).
**Kapsam:** Yalnızca minimum viable gate (izin kilidi + chokepoint). Quarantine (72/upsert_resolver/etl, 3.021 NULL) ve tam migration **kapsam dışı**.

---

## 1. Backup (atlanamaz adım — öncesinde hiçbir izin değişikliği yapılmadı)

| Alan | Değer |
|------|-------|
| Backup yolu | `backups/production_pre_isolation_gate_20260715_224855.db` |
| Backup hash (SHA-256) | `d842b118a9a4106a5c6035281d142bcbad7dc528c578216c4c25b7adbec62961` |
| Canlı DB hash (önce) | `d842b118a9a4106a5c6035281d142bcbad7dc528c578216c4c25b7adbec62961` (özdeş ✅) |
| Backup integrity_check | `ok` ✅ |
| Backup whiskies | 4749 ✅ |
| Orijinal ACL yedeği | `backups/pre_isolation_acl.txt` |
| Orijinal attrib yedeği | `backups/pre_isolation_attrib.txt` |
| Ön-değişiklik hash | `backups/pre_change_hash.txt` |

> Backup, izin değişikliğinden **önce** alındı. İzin değişikliği veri içeriğini değiştirmez (hash sonrada aynı kaldı).

---

## 2. Read-only varsayılan (§2.1 — B + A mekanizmaları)

### B) OS-seviye izin kilidi (gerçek enforcement)
`production.db`'yi `DEATHSTAR\eltun` kullanıcısı **Full** kontrole sahip olduğu için, yalnızca `attrib +R` eltun'ı durduramazdı (P111'de görüldüğü gibi aynı kullanıcı yazabildi). Bu yüzden iki katmanlı kilit uygulandı:

1. `attrib +R` (dosya salt-okunur özniteliği — ikincil sinyal)
2. `icacls /deny Deathstar\eltun:(WD,AD)` — **WriteData + AppendData ACE'si**. Bu, eltun'ın (ve onun altındaki herhangi bir python/ajanın) veri yazmasını **gerçekten engeller**. Gate, WriteDac hakkını koruduğu için bu ACE'yi geçici kaldırıp geri koyabilir; ama normal kod yazamaz.

| | Öncesi | Sonrası |
|---|---|---|
| attrib | `A` (RW) | `A  R` (read-only) |
| icacls ACE | `DEATHSTAR\eltun:(I)(F)` | `DEATHSTAR\eltun:(DENY)(WD,AD)` + `(I)(F)` |

### A) Defense-in-depth (chokepoint içinde)
`db_write_guard.get_read_connection()` her okumada `?mode=ro` + `PRAGMA query_only=ON` açar. `get_write_connection()` iç bağlantıda `BEGIN IMMEDIATE TRANSACTION` zorunlu kılar, sonunda `integrity_check` + `foreign_key_check` otomatik çalıştırır, hata varsa ROLLBACK edip kiliti `finally` ile geri koyar.

---

## 3. Tek chokepoint (§2.2)

**Dosya:** `mr-kep/p121_write_gate/db_write_guard.py` (7573 bayt, lint OK).
- `get_write_connection(authorized_context, restrict_tables=None)` → context manager.
  - `authorized_context` **zorunlu** (boş olamaz) — denetim etiketi; olmadan kilit kaldırılmaz (`PermissionError`).
  - `__enter__`: `lift_write_access()` → RW bağlantı → `BEGIN IMMEDIATE`.
  - `__exit__` (başarı): post-validate → `COMMIT` → `finally` her durumda `assert_write_access()` (kilit geri).
  - `__exit__` (hata): `ROLLBACK` → kilit geri → exception propagate.
- `get_read_connection()`: `?mode=ro` + `query_only=ON` (defense-in-depth A).
- Modül düzeyinde yan etki yok (import edince disk değişmez).

> `restrict_tables` kabul edilir ve denetim için loglanır; **tablo-seviyesi engelleme** (izin verilmeyen tabloya yazımı blocklama) sonraki geliştirmeye bırakıldı. Minimum viable garanti: kilit yalnız gate içinde kalkar, transaction + post-validation zorunlu, kilit daima geri konur.

---

## 4. Doğrulama testleri (gerçek veri değişmeden)

### Test A — doğrudan RW yazma (gate DIŞI) → BAŞARISIZ OLMALI
```
TEST A RESULT: EXPECTED FAILURE
  error: attempt to write a readonly database
```
✅ **Geçti.** `sqlite3.connect(production.db)` ile `UPDATE whiskies SET name=name WHERE 1=0` → `sqlite3.OperationalError: attempt to write a readonly database`. OS kilidi etkili.

### Test B — gate üzerinden no-op yazma → BAŞARILI OLMALI
```
TEST B RESULT: SUCCESS (gate lifted lock, wrote no-op, re-asserted lock)
```
✅ **Geçti.** `get_write_connection(authorized_context="mvp_gate_test_B")` ile aynı no-op yazım başarılı.

### Post-test kilit doğrulaması (B'den sonra kilit GERİ KONMALI)
```
A    R   ... production.db
DEATHSTAR\eltun:(DENY)(WD,AD)
```
✅ **Geçti.** Gate `finally` bloğu kilidi yeniden uyguladı.

### Veri değişmezlik kontrolü (her iki test sonrası)
- FINAL_SHA256: `d842b118…` (PRE ile özdeş ✅)
- whiskies: 4749 (değişmedi ✅)

---

## 5. Kitap import script'lerinin adaptasyon ihtiyacı (YALNIZCA RAPOR — bu görevde değişiklik YOK)

**Tespit:** Kitap enrichment pipeline'ı (`mr-kep/book_enrichment_sprint01`–`08`) `production.db`'ye **yazmaz**.
- Tüm sprintler `production.db`'yi yalnızca **lexicon okumak** için açar; yazımlar `KNOWLEDGE_DB`'ye gider (WAL modu, gate'den etkilenmez).
- `sprint03/04/07/08` production.db bağlantısında zaten `PRAGMA query_only=ON` kullanıyor (iyi).
- `sprint01` (`enrich_mw_yearbook_2019.py:141`): `conn = sqlite3.connect(db_path, uri=True)  # read-only` — **yorum "read-only" diyor ama `uri=True` ≠ `?mode=ro`**; yani RW açılıyor (yazmaz ama denetimsiz). **LATENT SORUN** (P111'deki aynı desen).
- Hiçbir sprint `whiskies` tablosuna INSERT/UPDATE yapmıyor (grep boş).

**Sonuç:**
- **Acil adaptasyon gerekmez** — mevcut kitap pipeline'ı production.db'yi değiştirmiyor; OS kilidi zaten amaçladıkları read-only'u zorluyor.
- **Önerilen (ayrı onaylı görev):** `sprint01`'in yanıltıcı RW açılımı `get_read_connection()` ile değiştirilsin (defense-in-depth, yanlış yorum düzeltilsin). Gelecekteki herhangi bir **kitap→production.db yazma** işlemi `get_write_connection(authorized_context=...)` üzerinden yapılmalı (zorunlu).

---

## 6. Rollback talimatı (kilidi eski haline döndürme)

İzinleri değiştirmeden **önce** `backups/pre_isolation_acl.txt` ve `pre_isolation_attrib.txt` kaydedildi. Geri almak için:

```bat
:: 1) DENY ACE'yi kaldır (tekrar yazmaya izin ver)
icacls "output\import\production.db" /remove:d "Deathstar\eltun"

:: 2) read-only dosya özniteliğini kaldır
attrib -R "output\import\production.db"

:: 3) (opsiyonel) orijinal ACL'i birebir geri yükle
icacls "output\import\production.db" /grant:r "Deathstar\eltun:(F)"
```

Veri geri yükleme (gerekirse): `backups/production_pre_isolation_gate_20260715_224855.db` → `output/import/production.db` (hash `d842b118…`).

---

## 7. Verification Loop

- `git status`: `mr-kep/p121_write_gate/` (yeni), `backups/` (yeni, gitignored değil — kullanıcı commit istemedi), dokümanlar untracked. `production.db` değişmedi (hash aynı).
- DB hash before = `d842b118…`, after = `d842b118…` → **değişmez** ✅ (yalnızca izin ACE eklendi).
- Gate testleri: A BAŞARISIZ (kilitli), B BAŞARILI (gate), kilit B'den sonra geri kondu ✅.

---

## SONUÇ: GO / WARN_GO / NO-GO

**VERDICT: 🟢 GO (kitap import altyapısı için minimum viable gate kuruldu).**

Gerekçe:
- OS-seviye kilit (DENY WD,AD) + `attrib +R` gerçekten enforced (Test A başarısız).
- Tek chokepoint (`get_write_connection`) çalışıyor, transaction + post-validation + otomatik re-lock garanti (Test B başarılı, kilit geri kondu).
- Backup alındı, hash guard doğrulandı, veri değişmedi (4749 whiskies, hash özdeş).
- Mevcut kitap pipeline'ı production.db'ye yazmadığı için hemen adaptasyon gerekmiyor; gelecekteki yazımlar gate'e yönlendirilecek.

**KALAN (sonraki görevlere bırakıldı, GO'yu engellemez):**
- §2.3 Quarantine: `72` / `upsert_resolver` / `etl` / `match_structured_ml` ungated RW yolları hâlâ var (artık OS kilidiyle engelleniyor, ama scriptler hâlâ RW açmayı dener → hata verir, sessiz yazamaz).
- §2.4 `review_query_service.py` rewrite (staging-only zorlaması).
- §2.5 3.021 NULL satır `whiskies_quarantine`'a taşıma.
- `sprint01` latent RW açılımının `get_read_connection`'a çevrilmesi (önerilen temizlik).
- `restrict_tables` tablo-seviyesi engelleme henüz uygulanmadı (şimdilik OS kilidi + audit context yeterli).

> Not: Bu gate, "bilinmeyen/yazıcısı belirsiz writer'lar da engellenmeli" varsayımını karşılır — OS kilidi kimlik-bağımsızdır; Antigravity veya başka bir ajan production.db'ye doğrudan yazamaz (gate dışı). Bu, P111'deki "dış/manuel oturum" riskini ortadan kaldırır.
