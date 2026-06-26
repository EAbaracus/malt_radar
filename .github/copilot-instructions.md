# GitHub Copilot Rules for Malt Radar

- Küçük, scoped (dar kapsamlı) öneriler ver.
- `production.db`'ye yazan öneri üretme.
- `AppConfig.useDbApi=false` kuralına uy.
- Kaldırılmış `/api/db/search`, `/api/db/stats`, `/api/db/filters` endpointlerini geri getirme.
- DB/data işlerinde her zaman staging-first policy uygula.
- Değişiklikleri tamamlarken test önerilerini unutma.
- Absolute path yerine her zaman relative path kullan (`C:\Users\eltun\Documents\malt radar` vb. kullanma).
