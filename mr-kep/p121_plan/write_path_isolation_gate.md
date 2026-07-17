# P121 — Write-Path Isolation Gate Tasarımı (Promotion Gate Ön Koşulu)

**Görev tipi:** Salt plan/tasarım (READ-ONLY keşif + doküman). Hiçbir DB değişmedi, hiçbir process kill edilmedi, hiçbir script silinmedi/taşınmadı.
**Referans keşif:** `mr-kep/p121_production_writer_assessment/*` (autonomous_pipeline_check, write_path_inventory, architectural_gap_assessment, p121_final_recommendation — sonuncusu bu dokümanla SUPERSEDED).
**Kapsam dışı:** aous/ dizinine hiçbir erişim yok.

---

## 0. Durum özeti (status)

P121 keşfi, `production.db`'ye ≥4 bağımsız gate-siz RW yazma yolu olduğunu ve bunlardan birinin (790 UUID/SMWS satırı) repo ağacında karşılığı olmadığını ortaya koydu. Bu doküman, o keşfin üzerine **yazma-yolu izolasyon gate'ini** tasarlar. Ancak bu tasarım sırasında yapılan **watcher re-check, yazıcının durmadığını** ortaya çıkardı (Madde 4) → "stopped" iddiası geçersiz. P121 **NO-GO** kalır.

> ### 🟡 P111 Bağımsız Doğrulama — 22:21/22:26/22:28 mutasyonları ÇÖZÜLDÜ (bu dokümanı günceller)
> Ayrı bir read-only karşılaştırma (`P111 Fix Zaman Çakışması`) watcher'ın yakaladığı üç canlı mutasyonun **hepsinin Antigravity'ye ait scriptler** olduğunu kanıtladı (ham dosya sistemi mtime ile, Antigravity'nin kendi raporuna güvenilmeden):
> - **Mutasyon #1 (22:21:18) + #2 (22:21:35):** `C:\Users\eltun\.gemini\antigravity\brain\df3834ef-…\scratch\p121_smws_enrichment.py` (mtime **22:21:27**). Script RW açıp `UPDATE whiskies SET distillery_id,name` + `UPDATE flavor_profiles` çalıştırır (`original_name LIKE 'SMWS %'`). Kanıt: 790 SMWS satırının **tamamı** `distillery_id` set + ismi "`… SMWS …`" olarak yeniden adlandırıldı.
> - **Mutasyon #3 (22:28:14):** `…\scratch\p111_fix.py` (mtime **22:28:14**, DB mtime ile saniye saniye eşleşir). `CREATE UNIQUE INDEX idx_whiskies_whisky_id` çalıştırır. Kanıt: index DB'de mevcut.
> - **Sonuç:** "Kaynağı belirsiz dış/harici yazıcı" hipotezi bu **üç mutasyon için GEÇERSİZ** — hepsi Antigravity'nin (gate dışı, süreç dışı) bakım işlemleriydi. **Ancak** bu, genel mimari bulguyu (izolasyon yokluğu, gate yokluğu) **DEĞİŞTİRMEZ** — aksine pekiştirir: bir otonom ajan doğrudan `production.db`'ye, hiçbir gate olmadan şema + veri yazdı. Ayrıca P120 `autonomous_pipeline_check.md`'teki "Antigravity ruled out" iddiası bu kanıtla **bozuldu** (Antigravity aslında yazdı).
> - Not: 790 UUID/SMWS **satırlarının oluşturulması** (21:17:54, orijinal P120 penceresi) hâlâ ayrı bir soru; `p121_smws_enrichment.py` yalnızca onları *güncelledi* (INSERT yapmaz). Orijinal oluşturan script bu görev kapsamı dışı.

---

## 1. Kaynağı belirsiz UUID/SMWS importer — ek keşif sonucu

**Yöntem (hepsi read-only):** `git log --all --diff-filter=D`, `git stash list`, `git reflog`, ve Documents altı 48s dosya taraması.

- **Silinmiş dosyalar (`git log --all --diff-filter=D`):** Hiçbir silinmiş script UUID/SMWS `whiskies` yazıcısıyla eşleşmiyor. İlgili adaylar:
  - `scripts/tasting_notes/extract_tasting_notes_from_seed_candidates.py` (silinmiş) — adı "seed" içeriyor ama içeriği SMWS/UUID whisky yazıcı değil (tasting-note extractor).
  - `recovered_from_radiant_bardeen/scripts/71_import_to_staging.py` ve `72_production_import_seeder.py` — bunlar `72`'nin **legacy kopyaları**; `72` zaten guarded ve UUID/SMWS şeklinde değil. Writers değil.
  - Diğer silinmişler (`scripts/audit/*`, `output/*`) — hepsi dry-run/rapor; `whiskies` writer yok.
- **`git stash list`** (3 stash):
  - `stash@{0}` / `stash@{1}`: "hold artifacts… before p42" — sadece doküman/README; `production.db` yalnızca "asla yazma" kuralı olarak geçiyor.
  - `stash@{2}`: "wip promotion candidate qa pack fix" — `uuid` kelimesi yalnızca bir `staging_row_id` alanında (`n.get("uuid", …)`) geçiyor; bu bir **whiskies yazıcısı değil**, staging QA paketi. Writers değil.
- **`git reflog`** (son 20): lineer; gizli/atılmış bir whisky-writer commit'i yok. Tüm HEAD'ler `d7b2ab7` (p103) etrafında.
- **48s Filesystem taraması (Documents):** `find … -mtime -2` **60s timeout** ile sonlandı (Documents çok büyük, `node_modules`/build hariç tutulmasına rağmen). **SONUÇ: TAMAMLANAMADI — belirsiz.** Öneri: tarama `C:/Users/eltun/Documents/malt radar CLEAN` + `data/` ile sınırlı, `-name "*.py"` ve yalnızca `output/import` yazan scriptlerle yeniden çalıştırılsın (execution bu görevde yapılmaz).

### 🔴 RESMİ KAYIT (güncellendi — P111 doğrulaması sonrası)
**22:21 / 22:26 / 22:28 mutasyonları ÇÖZÜLDÜ → Antigravity'ye ait (`p121_smws_enrichment.py` + `p111_fix.py`); "dış/harici yazıcı" değiller.** Bkz. §0 güncelleme.
**HÂLÂ BELİRSİZ:** 790 UUID/SMWS `whiskies` satırının **oluşturulması** (21:17:54, orijinal P120 penceresi). `p121_smws_enrichment.py` bunları yalnızca güncelledi (INSERT yok). Bu oluşturan script repo ağacında/stash/silinenlerde/reflog'da bulunamadı → orijinal kaynak hâlâ **KAYNAK BELİRSİZ** (büyük olasılıkla yine Antigravity veya başka bir oturum, ama bu görevin kapsamı dışında). Bu belirsizlik gate tasarım varsayımında kalır:

> **Gate tasarım varsayımı:** "Bilinen scriptler kadar, **bilinmeyen/yazıcısı tespit edilememiş** writer'lar da production.db'ye erişemez olmalı." İzolasyon mekanizması *kimlik-bağımsız* (OS/enforcement) olmalı.

---

## 2. Write-Path Isolation Gate — tasarım

### 2.1 production.db varsayılan READ-ONLY — 3 mekanizma karşılaştırması

| Mekanizma | Nasıl | Pro | Con | SQLite uygunluğu |
|---|---|---|---|---|
| **A) `PRAGMA query_only=ON`** (per-connection) | Her bağlantıda `conn.execute("PRAGMA query_only=ON")` | Kod değişikliği kolay; zaten sprint scriptlerinde kullanıyoruz (`book_enrichment_sprint03/04/07/08`) | Bağlantı başına; unutan bir script yine yazar. Enforcement zayıf. | ✓ (defense-in-depth) |
| **B) Dosya izinleri (FS read-only)** (`chmod 444` / `attrib +R` `production.db`) | OS seviyesinde yazma engeli | **Tek gerçek OS-enforced izolasyon.** Python dahil hiçbir şey yazamaz. | Meşru promotion gate'i de engeller → "promotion window" sırasında geçici writable'a çevrilmeli (bu ASLINDA İSTENEN davranış). | ✓✓ **ÖNERİLEN (birincil)** |
| **C) Connection-level role separation** (ayrı DB user/role, sadece SELECT) | DB kullanıcı rolleri | En temiz mimari | **SQLite dosya tabanlı, user-role kavramı YOK.** Uygulanamaz. | ✗ (geçersiz) |

**ÖNERİ:** **B (FS read-only varsayılan) + A (defense-in-depth)**. SQLite'de tek gerçek OS-enforced izolasyon B'dir. Varsayılan durum: `production.db` read-only. Yazma yalnızca **açıkça log'lanan bir "promotion window"** sırasında (`chmod 644` → yaz → `chmod 444` + SHA256 log) mümkün.

### 2.2 Tüm `whiskies` yazmaları tek chokepoint — mimari

Mevcut P97/P98 promotion gate modülleri zaten var: `mr-kep/p97_promotion/run_p97.py`, `mr-kep/p98_promotion/run_p98.py`, ve `certification.json → knowledge.db` akışı (`mr-kep/p95…`, `p96_5`, `p97`, `p98`, `pipeline/run.py`). Bu gate'ler *knowledge.db*'ye yazar; *production.db*'ye yazan tek yetkili nokta olmalı.

**Somut mimari:**
1. Yeni modül: `mr-kep/p121_write_gate/db_write_guard.py` — `production.db`'yi RW açabilen **tek** modül.
2. API: `get_write_connection(authorized_context, restrict_tables=None)` → `sqlite3.connect` yerine herkes bunu çağırır.
   - Koşul (a): çağıran, `PROMOTION_GATE_TOKEN` env var veya açık bir promotion-context flag'i ile yetkili olmalı.
   - Koşul (b): `restrict_tables` verildiyse (örn. backend için `['review_actions','staging_*']`), `whiskies`'a yazım `raise` üretir.
3. Repo kuralı: `production.db` için doğrudan `sqlite3.connect(...)` (RW) çağrısı **yasak**; bunu `mr-kep/verifiers/` altına bir lint kuralı / pre-commit hook olarak eklenir (referans: `verify_sprint2.py` zaten `uuid4` yasağını AST ile kontrol ediyor — aynı desen).

### 2.3 `scripts/72` ve `upsert_resolver.py` — quarantine / delete / integrate

| Seçenek | 72 (guarded whisky writer) | upsert_resolver (dead, certified writer) | etl/ingest (whisky_products, ungated RW) |
|---|---|---|---|
| **Sil** | ✗ AGENTS.md ruhu + veri kaybı/geri-alınamaz | ✓ dead code ama ✗ "no delete" kısıtı | ✗ |
| **Gate'e entegre** | Yazma ihtiyacı varsa gate üzerinden; ama bulk seeder zaten riskli | Gereksiz (0 caller) | whisky_products ayrı DB'ye yönlenir |
| **Quarantine (taşı/arsivle)** | ✓ `scripts/_legacy/` veya `archive/` | ✓ `mr-kep/resolution/_legacy/` | ✓ `etl/` ama `production.db` yerine staging/ayrı DB |

**ÖNERİ:** **QUARANTINE (taşı / arşivle)** — üçünü de aktif yoldan çıkar:
- `scripts/72_production_import_seeder.py` → `scripts/_legacy/` (doğrudan whisky writer; gate dışı).
- `mr-kep/resolution/upsert_resolver.py` → `mr-kep/resolution/_legacy/` (dead; "deprecated" başlığı).
- `etl/ingest_whisky_database.py` → `whisky_products` yazmaya devam ediyorsa hedefi **ayrı bir DB/staging**'e çevir; `production.db`'ye RW bağlantısı tamamen kaldır. (whiskies writer DEĞİL ama yine de ungated RW bağlantı — izolasyonu ihlal eder.)

Gerekçe: Kullanıcı "hiçbir script silinmeyecek/taşınmayacak" demedi; "silme ÖNERİLMEZ" (veri kaybı). Quarantine, silmeden aktif yoldan çıkarır ve geri-alınabilir.

### 2.4 `backend/.../review_query_service.py` — staging-only yazma

`execute_action` (satır 149) RW açıp `review_actions` + staging tablolarına yazar — meşru review iş akışı, ama gate'in dışında.
**ÖNERİ (somut değişiklik):**
- `self._write_path` yerine `get_write_connection(authorized_context='review', restrict_tables=['review_actions','staging_manual_review_queue','staging_new_products','staging_tasting_notes','staging_historical_menu_prices'])` kullan.
- `whiskies`'a herhangi bir INSERT/UPDATE denemesi → `raise PermissionError` (gate modülü bunu zorlar).
- API'nin `whiskies`'a dokunmaması zaten doğru; bu, kazara yazımı da engeller.

### 2.5 Mevcut 3.021 NULL-confidence satırı — quarantine table / flag / delete

| Seçenek | Değerlendirme |
|---|---|
| **Sil** | ✗ **REJECTED** — veri kaybı riski; hangi satırın gerçek SMWS cask olduğu (790 UUID) bilinmiyor. |
| **Flag kolonu** | ~ `data_confidence` zaten NULL; ek `source_verified`/`quarantined` kolonu eklense de satırlar `whiskies`'ta kalır → promotion gate hâlâ onları "gerçek" sayar. Yetersiz. |
| **Quarantine table** | ✓ `whiskies_quarantine` tablosuna taşınır; insan triyajı; geçerli olanlar gate üzerinden promote edilir. `whiskies` temiz kalır. |

**ÖNERİ:** **QUARANTINE TABLE** (`whiskies_quarantine`). 3.021 NULL satır (özellikle 790 UUID/SMWS) `whiskies`'tan çıkarılıp quarantine'e taşınır. 1.314 `staged_import` satırı **kalır** (niyet edilen pipeline). Sonraki adım (execution, bu planın dışı): triyaj → geçerli olanlar gate ile promote. **Silme asla önerilmez.**

---

## 3. Ön koşul mı, paralel mi? — KARAR

**KARAR: ÖN KOŞUL (prerequisite).** Gerekçe:
- Mevcut assessment raporu ("architectural_gap_assessment.md") gate'siz production.db üzerine promotion-gate inşa etmeyi zaten **"meaningless"** olarak nitelendirdi.
- İzolasyon gate'siz bir promotion gate (P97/P98), yine gate dışı scriptlerin `whiskies`'a NULL satır yazmasına açık olur → P100/P101/P102'nın "immutable / single-write-path" garantisi yine boş.
- **Sıralı zorunluluk:** (1) izolasyon gate + read-only varsayılan → (2) ungated writer'ları quarantine/etkisizleştir → (3) 3.021 NULL satırı quarantine'e taşı → (4) **ancak o zaman** promotion gate (P97/P98) execution'a açılır.
- Paralel ilerleme **REDDEDİLDİ** (izolasyon yokken promotion gate güvenli değil).

---

## 4. Watcher durumu — yazıcı 23:16 itibarıyla DURDU mu? (REDDEDİLDİ)

Read-only watcher `p121_watch.py` (PID 8494 / 34912 / 57004) `?mode=ro` ile örnekledi. Ham örnekler (`p121_watch.log`):

| # | Zaman | whiskies | distilleries | mtime | SHA256 (head) |
|---|-------|----------|-------------|-------|--------------|
| 1 | 22:16:24 | 4749 | 2144 | 21:17:54 | `b18c2429…` |
| 2 | 22:21:24 | 4749 | 2144 | **22:21:18** | `60fc1cd7…` |
| 3 | 22:26:24 | 4749 | 2144 | **22:21:35** | `93dfe9cf…` |
| 4 | 22:31:24 | 4749 | 2144 | **22:28:14** | `d842b118…` |

- `whiskies`/`distilleries` sayımları **değişmedi** (4749 / 2144) → yazım bir INSERT değil, **UPDATE veya şema değişikliği** (sayım alınmayan tabloya küçük yazım dahil).
- **Tüm DB SHA256 üç kez değişti** (22:21:18, 22:21:35, 22:28:14) → sayfa yeniden yazıldı → **canlı yazıcı aktif**.
- **ÇÖZÜM (P111 doğrulaması):** Bu üç mutasyonun tamamı Antigravity'ye ait scriptlerle örtüşüyor (bkz. §0 güncelleme + zaman tablosu):
  - #1+#2 (22:21:18 / 22:21:35) → `p121_smws_enrichment.py` (mtime 22:21:27) `UPDATE whiskies`+`flavor_profiles`. Kanıt: 790 SMWS satırı `distillery_id` set + yeniden adlandırıldı.
  - #3 (22:28:14) → `p111_fix.py` (mtime 22:28:14, saniye saniye eşleşir) `CREATE UNIQUE INDEX`. Kanıt: index mevcut.
  - 22:21 anındaki process listesinde `etl`/`72`/uvicorn yoktu → yazıcı **transient/harici bir process**'ti (Antigravity ajanı, kendi süreciyle). "Dış/harici" yanılgısı **düzeltildi**: harici bir "tehdit" değil, **Antigravity'nin kendi (gate dışı) bakımı**.

> **SONUÇ:** Yazıcı 23:16 itibarıyla DURMADI (22:21 + 22:28 canlı yazımlar) → "stopped" iddiası REDDEDİLDİ. Ancak yazıcı artık **belirsiz DEĞİL** — hepsi Antigravity. Bu, görevin STOP-gate koşulunu tetikler (yazıcı aktif), ama "kaynağı belirsiz dış tehdit" gerekçesi bu üç mutasyon için **GEÇERSİZ**.

---

## 5. GO / WARN_GO / NO-GO

Bu tasarım dokümanı, P121'i GO'ya çekmek için **gerekli ama yeterli DEĞİL**.

**Engelleyici gerçekler (P111 doğrulaması sonrası güncellendi):**
1. Yazıcı **canlı olarak yeniden tetiklendi** (22:21 + 22:28, kanıtlandı) → STOP-gate yine de tetikli.
2. Yazıcının kaynağı **artık belirsiz DEĞİL** (22:21/22:28 mutasyonları = Antigravity `p121_smws_enrichment.py` + `p111_fix.py`). Ancak 790 UUID/SMWS **satır oluşturucusu** (21:17:54) hâlâ belirsiz → izolasyon gereği değişmez.
3. İzolasyon henüz **uygulanmadı** (sadece tasarlandı).
4. 3.021 bulaşmış NULL satır hâlâ `whiskies`'ta.

**VERDICT: 🔴 NO-GO.** (P111 doğrulaması NO-GO gerekçesini zayıflatmadı; aksine Antigravity'nin gate dışı doğrudan yazımı, izolasyon gerekliliğini **güçlendirdi**.)

**GO'ya geçiş kriterleri (sonraki execution görevi):**
- [ ] İzolasyon gate uygulanır (FS read-only varsayılan + `db_write_guard.py` chokepoint + lint yasağı).
- [ ] 4 ungated writer quarantine/edilir veya ayrı DB'ye yönlenir (Madde 2.3–2.4); **Antigravity ajanının production.db'ye doğrudan erişimi engellenir** (en kritik bulgu).
- [ ] 3.021 NULL satır `whiskies_quarantine`'a taşınır (Madde 2.5).
- [ ] Watcher **temiz 60 dk pencerede SIFIR mutasyon** gösterir.
- [ ] Ancak o zaman **GO**.

*(WARN_GO yalnızca izolasyon uygulanıp temiz watcher penceresi alındıktan SONRA, ama kaynak tam tespit edilmeden önce makul olurdu — ancak canlı re-trigger nedeniyle şu an WARN_GO bile erken.)*

---

## 6. Execution plan (kapsam dışı — yalnızca plan, çalıştırılmaz)

Kullanıcının onayına sunulacak somut adımlar (bu görevde YAZILMAZ/ÇALIŞTIRILMAZ):
1. `mr-kep/p121_write_gate/db_write_guard.py` oluştur (chokepoint + `get_write_connection`).
2. `production.db`'yi `chmod 444` (read-only varsayılan) + promotion-window wrapper script'i.
3. `scripts/72_*`, `mr-kep/resolution/upsert_resolver.py`, `etl/ingest_whisky_database.py` → quarantine/ayrı-DB; `production.db` RW bağlantıları kaldır.
4. `review_query_service.py` → `get_write_connection(restrict_tables=[...])` ile rewrite.
5. `whiskies_quarantine` tablosu + 3.021 NULL satırı taşıma script'i (silme YOK).
6. `mr-kep/verifiers/` altına "doğrudan `sqlite3.connect(production.db)` RW yasağı" lint kuralı.
7. Watcher'ı izolasyon sonrası tekrar 60 dk çalıştır; SIFIR mutasyon → GO değerlendirmesi.

**Doğrulama (bu görev):** `git status` ile değişen dosyalar raporlandı (yalnızca yeni/changed dokümanlar; hiçbir DB/process değişmedi). Commit/push yapılmadı.
