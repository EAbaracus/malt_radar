# B+C Design Spec — Read Seam + Write Guard Enforcement

- **Tarih:** 2026-08-11
- **Durum:** TASLAK — insan onayı bekliyor (spec review gate)
- **Kapsam:** Faz 0 (P0 fix) + Faz B (ProductionReadAdapter) + Faz C (guard CI enforcement)
- **Sözlük:** /codebase-design — module, interface, depth, seam, adapter, leverage, locality

---

## 1. Problem

Üç ayrı sqlite okuyucusu, ikisi canlı (`DbReadService` catalog, `ReviewQueryService` admin queue), biri dead (`SqliteReadAdapter` + `db_read.py` — mount edilmemiş, sadece testler import ediyor). Fiyat redaction'ı merkezi değil: canlı servis açık kolon listesi kullanıyor, dead adapter `SELECT *` ile `production_price`/`price_value` sızdırabilir (şu an dead olduğu için aktif sızıntı yok). Guard (`db_write_guard.py`) var ama zorunlu değil — `review_query_service.execute_action()` (canlı admin API write'ı) ve `p95b_phase12_execute.py` + `scripts/apply/apply_low_risk_official_facts_v4..v12.py` doğrudan `sqlite3.connect(production.db)` yapıyor. Commit mesajı "guarded apply" diyen `apply_v12.py` guard'ı çağırmıyor (kendi ad-hoc `--confirm` string'i).

**Kök neden:** zorunlu olmayan chokepoint. Disiplin kod incelemesine/hafızaya bağımlı kalmış.

## 2. Governance kararları (bu spec)

| # | Karar | Gerekçe |
|---|-------|---------|
| G1 | Guard = production yüzeyinin (backend) parçası. Canonical konum: `backend/app/db/write_guard.py` | Guard zaten production.db'nin bekçisi; backend = production yüzeyi, mr-kep = orchestration/forensic. mr-kep → backend bağımlılık yönü governance sınırıyla hizalı |
| G2 | `execute_action` mutasyon sınıfı: staging-scope'lu queue aksiyonu → **otomatik backup+SHA, senkron insan GO yok** | Order 7'nin amacı (geri alınabilirlik, iz) korunur; harfi (senkron onay) bu sınıf için gevşetilir çünkü varsayımı (toplu promotion) geçerli değil. API key = zaten insan tetiklemesi. Production canonical promotion değişmez: insan-GO'lu kalır (PromotionGate / identity-backfill sınıfı) |
| G3 | `restrict_tables` gerçek enforcement kazanır (şu an audit-only) | staging-yazan script'lerin yanlışlıkla production tablolarına sızmasını önleyen asıl mekanizma |
| G4 | C kriteri mekanik: `sqlite3.connect` → hedef production.db **VE** dosyada write-statement → sadece `write_guard.py`'dan. Read-only connect'ler (mode=ro/query_only) otomatik temiz. **Whitelist listesi yok** | Dosya-bazlı allowlist, "disiplin hafızaya bağımlı" hatasını yeniden kurar |

## 3. Faz 0 — P0 fix (izole, bu tur)

1. `mr-kep/p121_write_gate/db_write_guard.py` → `backend/app/db/write_guard.py` (canonical).
2. mr-kep'teki tüketiciler (book_enrichment_sprint01, B4b — `get_read_connection` kullananlar) backend'den import eder.
3. `ReviewQueryService.execute_action` → `get_write_connection(authorized_context="admin_review_execute_action", restrict_tables=[staging_*, review_actions])` içinde. Doğrudan `sqlite3.connect(self._write_path)` kaldırılır.
4. Otomatik backup+SHA: write öncesi SHA256, write sonrası SHA256, ikisi de audit log'a (`authorized_context` ile). (G2)
5. `backend/tests/test_security_rechecks.py` güncellenir (guard import yolu).

**Kabul kriterleri (Faz 0):**
- `execute_action` artık guard dışı connect içermiyor (grep: `sqlite3.connect` yok).
- `backend/.venv` pytest suite yeşil.
- Guard `DB_PATH` doğru çözümleniyor (production.db mevcut).

## 4. Faz B — ProductionReadAdapter

| 1. Tek read seam: `DbReadService` (catalog) + `ReviewQueryService` read metotları (`get_unified_queue`, `get_item_details`, `get_allowed_actions`) → tek adapter (`backend/app/db/production_read_adapter.py`). Tek `_get_connection` (mode=ro + `PRAGMA query_only=ON`), tek `canonical_tables` listesi, tek pagination bound.|**Uyarı (B1/B2 ayrımı, 2026-08-11):** Bu iki reader **aynı committe değil**, ayrı PR'larda delegate edilir. B1 = `ReviewQueryService` (admin queue read+write delegate + `review_action_writer.py`). B2 = `DbReadService` (frontend catalog read + `db_api.py` router). Neden: B1 kendi başına tutarlı, review kolay; B2 frontend'in canlı katalog endpoint'ini dokunur, izole edilerek review edilir. Path çözümlemesi ortak `shared_paths.resolve_db_path` (her iki adapter de aynı fonksiyonu, copy-paste değil).||
2. **Merkezi fiyat redaction'ı:** adapter çıkışında `production_price`, `price_value`, `price_context`, `pour_size_ml` dahil fiyat kolonları asla emilmez. Açık kolon allowlist'i seam'de tek noktada. `test_db_price_leak` her read method'u kapsayacak şekilde genişletilir (sadece flavor-profile değil).
3. `ReviewQueryService` write metodu ayrılır → `backend/app/db/review_action_writer.py` (guard-backed, Faz 0'daki path'i kullanır). Read/write aynı module'de kalmaz (interface yalan söylemesin).
4. `SqliteReadAdapter` + `db_read.py`: **archive/'a taşınır — silinmez** (KARAR: kullanıcı onayı, 2026-08-11). Gerekçe: P0 price-history bulgusunun (`db_read.py:70-75` — `SHOW_PRICE_DATA` env gate'i, `SELECT *` ile `price_value` sızma potansiyeli) adli kaydı olarak değeri var; silinirse tarih geri getirilemez. Test referansları (`test_security_rechecks.py`) güncellenir.
5. `restrict_tables` enforcement (G3): WriteGate, `restrict_tables` listesinde olmayan tablolara INSERT/UPDATE/DELETE'i runtime'da reddeder.

**Kabul kriterleri (Faz B):**
- `grep -rn "sqlite3.connect" backend/app` → sadece `db/write_guard.py` ve `db/production_read_adapter.py`.
- Fiyat kolonu hiçbir API yanıtında yok (genişletilmiş leak testi).
- Catalog + admin queue testleri yeşil.

## 5. Faz C — guard enforcement (CI lint)

1. Kural (G4): AST/grep tabanlı kontrol — `sqlite3.connect` çağrısı production.db path'ine hedefliyor **VE** dosyada write-statement var → sadece `backend/app/db/write_guard.py` geçerli. CI'da `scripts/gates/check_write_guard.py` (veya benzeri) koşar, fail → pipeline kırmızı.
2. Tarihi write bypass'ları (git geçmişine göre triyaj):
   - **Triyaj ayrımı (kritik):** `_on_copy` / `dry_run_*_on_copy` / sandbox hedefli script'ler (ör. `dry_run_update_low_risk_official_facts_v5/v7/v9/v11_on_copy.py`) **write bypass değildir** — kopya DB üzerinde test/deneme amaçlıdır, production.db hedeflemez. Bunlar C kapsamına girmez (guard'a bağlamaya çalışma; zararsız sandbox'ı bozar).
   - `p95b_phase12_execute.py` (2026-07-18): muhtemelen ölü → archive/ (doğrulama: son 6 ayda commit yok, çalıştırma kanıtı yok).
   - `scripts/apply/apply_low_risk_official_facts_v4/v6/v8/v10.py` (2026-07-01, batch 1-4): ölü → archive/.
   - `apply_low_risk_official_facts_v12.py` (2026-08-05 güncel): **canlı olabilir** → guard'a bağlanır ya da archive/ (uygulama sırasında insan onayı).
   - archive/ path'i C kapsamı dışı (dizin-bazlı exclude — whitelist değil, "bu dizin production kod tabanı değil").
3. C kapsamı = aktif kod tabanı (backend/, mr-kep/ canlı modüller, scripts/ canlı kısmı).

**Kabul kriterleri (Faz C):**
- CI'da kural koşuyor; kasıtlı bypass ekleyince fail ediyor (negatif test).
- Bilinen write bypass sayısı 0 (aktif kod tabanında).

## 6. Kapsam dışı (bu spec'te)

- **A (PromotionWorkflow — scripts/ birleştirme):** 81K LOC refactor, B'nin seam'ine bağımlı; ayrı tur.
- **D (schema/migration):** `schema_postgres.sql` 0 grep hit, kullanılmıyor = zararsız. Acil değil.
- **E (cruft quarantine):** Faz B'deki archive hareketleri E'nin ön tadımı; tam E ayrı tur.

## 7. Test stratejisi

- Faz 0: mevcut backend suite + yeni guard-path testi (execute_action guard içinden geçer).
- Faz B: genişletilmiş price-leak testi (tüm read method'ları), adapter tekliği (tek canonical_tables).
- Faz C: negatif test (kasıtlı bypass → lint fail).
- Frontend (26 test): davranış değişmez, regresyon kontrolü.

## 8. Riskler

| Risk | Azaltma |
|------|---------|
| mr-kep → backend import kırılması (modül taşıma) | Faz 0'da taşıma sonrası mr-kep import'ları doğrulanır; mr-kep sys.path yönü korunur |
| `restrict_tables` enforcement yanlışlıkla meşru staging write'ı engeller | Faz B'de allowlist'ler `staging_*` + `review_actions` + promotion tabloları ile test edilir |
| archive taşıma kırık referanslar bırakır | `grep` ile referans kontrolü; taşıma tek commit'te, ayrı |
| CI lint false positive (read-only dosya yanlışlıkla fail) | Kriter mekanik: read-only marker (mode=ro/query_only) otomatik temiz |

## 9. Onay geçmişi

- [x] C kapsamı: bağlantı-yolu bazlı, whitelist yok (G4) — kullanıcı onayı
- [x] Write bypass stratejisi: canlı → guard, ölü → archive/ — kullanıcı onayı
- [x] Guard konumu: backend canonical (G1) — kullanıcı onayı (Seçenek C)
- [x] GO modeli: otomatik backup+SHA, insan GO yok (G2) — kullanıcı önerisi, agent onayı
- [x] Spec review — **ONAYLANDI** (kullanıcı, 2026-08-11): Faz 0/B/C ayrımı, guard konumu, G2, G3 eklentisi tutarlı
- [x] Dead-code kararı: `SqliteReadAdapter` + `db_read.py` **arşivlenir, silinmez** (adli kayıt değeri) — kullanıcı onayı
- [x] _on_copy ayrımı: sandbox script'ler C kapsamı dışı — kullanıcı onayı
- [x] Git commit izni: Order 15 — kullanıcı açık izni (docs-only dosya)
