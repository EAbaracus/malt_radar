# Malt Radar AI Operating Instructions

## Project Overview
Malt Radar is a project consisting of a Flutter frontend and a backend utilizing an SQLite database. These instructions govern how AI tools interact with the repository to ensure safety, token efficiency, and repo integrity.

## AI Operating Mode
- **Antigravity**: Ana writer'dır (Main writer agent).
- **Proxima**: Sadece reviewer/researcher/helper'dır.
- **Copilot**: Sadece inline küçük edit/test/boilerplate yardımcısıdır.
- **Perplexity**: Sadece güncel research/source check içindir.
- **Claude**: Sadece review/security/edge-case için kullanılır.
- **Qwen/Ollama**: Sadece lokal özet/taslak/log analizi içindir.

## Hard Rules
1. `production.db`'ye asla yazma.
2. `output/import/production.db` dosyasını değiştirme.
3. `AppConfig.useDbApi=false` kalmalı.
4. Şu endpointleri geri getirme:
   - `/api/db/search`
   - `/api/db/stats`
   - `/api/db/filters`
5. Repo içine gereksiz prompt dump, MCP config veya deneysel dosya ekleme.
6. Değişiklikler küçük ve kontrollü olsun.
7. Asla absolute path (`C:\Users\eltun\Documents\malt radar` gibi) kullanma, her zaman relative path kullan.

## Protected Files
- `output/import/production.db`
- `AppConfig` configuration values related to `useDbApi`

## DB/Data Policy
- `production.db` explicit approval olmadan mutate edilemez.
- DB/data işleri **staging-first** yapılır.

## API Contract Policy
- Kaldırılan `/api/db/search`, `/api/db/stats`, `/api/db/filters` endpoint'leri geri getirilmeyecek.

## Test Gates
- `just status`, `just db-check`, `just frontend-gate`, `just backend-gate`, `just repo-check` komutlarıyla değişiklikler test edilir.

## Final Report Format
Her aşamada veya görevde rapor şunları içermelidir:
- Ne yaptın?
- Değişen dosyalar
- Çalıştırılan komutlar
- Test sonuçları
- Riskler
- Sonraki önerilen aşama
- GO/NO-GO
