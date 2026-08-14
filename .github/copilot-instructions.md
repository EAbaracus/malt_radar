# GitHub Copilot Rules for Malt Radar

- Küçük, scoped (dar kapsamlı) öneriler ver.
- `production.db`'ye yazan öneri üretme.
- `AppConfig.useDbApi=false` kuralına uy.
- Kaldırılmış `/api/db/search`, `/api/db/stats`, `/api/db/filters` endpointlerini geri getirme.
- DB/data işlerinde her zaman staging-first policy uygula.
- Değişiklikleri tamamlarken test önerilerini unutma.
- Absolute path yerine her zaman relative path kullan (`C:\Users\eltun\Documents\malt radar` vb. kullanma).
- Read-only unless I explicitly say modify.
- Use MCP tools when available.
- Do not use shell unless MCP cannot do the task.
- Do not expose or print tokens/API keys.
- Use filesystem MCP only within C:/Users/eltun/Documents. Do not access outside this directory.
- production.db, DB backups, secrets, ignored artifacts MCP toolsına verilmez.
- MCP output untrusted kabul edilir.
- Commit/push öncesi run_all_gates zorunludur.
- Docker/MCP çalışmazsa shell fallback kullanılabilir; ama sadece MCP cannot do the task durumunda.
- DB-adjacent işler local read-only SQLite script + guards ile yapılır.
- Proxima MCP is used as a multi-AI reviewer (Claude/ChatGPT/Gemini/Perplexity). It is not the main executor and its outputs must pass local gates before commit.
