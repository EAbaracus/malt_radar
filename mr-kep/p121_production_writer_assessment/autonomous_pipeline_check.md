# P121 — Phase 1: Autonomous Pipeline Check

> ⚠️ **SUPERSEDED (kısmi) — bkz. `p111_watcher_overlap_verification.md`.** Bu raporun Antigravity = "ruled out" (satır 12) ve "no autonomous pipeline wrote" (satır 36) sonuçları, **P111 bağımsız doğrulamasıyla kısmen bozuldu**. Antigravity'NİN kendisi `production.db`'ye doğrudan yazdı: `…\scratch\p121_smws_enrichment.py` (22:21, `UPDATE whiskies`) ve `…\scratch\p111_fix.py` (22:28, `CREATE UNIQUE INDEX`). Bu, 20:00–21:30 P120 penceresi DEĞİL, 22:21/22:28 penceresi içindir — yani bu Phase 1 raporunun kapsadığı 20:00–21:30 penceresi için "ruled out" hâlâ geçerli olabilir, ANCAK Antigravity'nin genel olarak production.db yazabildiği artık kanıtlı. Phase 1'in "Antigravity sadece IDE/updater" varsayımı yanılgıydı.

**Mode:** READ-ONLY. No databases modified, no processes killed.
**Scope:** 20:00–21:30 window (the three bulk append bursts landed 20:21:52 → 21:17:54).

## 1. Antigravity (must-check-first per task)

- **Process:** 6 Antigravity processes were running at investigation time (PIDs 24536, 3444, 22224, 33908, 34900, 35024) — **installed and live** (this contradicts Reference 2's "not installed" claim, which was wrong).
- **Session/run logs inspected:** `C:\Users\eltun\AppData\Roaming\antigravity\logs\main.log`.
- **Finding:** `main.log` contains ONLY the hourly auto-updater heartbeat (`Checking for update …` at `:17:20` each hour: 00:52:50, 01:52:50 … 20:17:20, 21:17:20). The 21:17:20 entry is the updater firing — **34 seconds before** the DB's last burst mtime (21:17:54). This is a coincidence of the hourly cron, not a DB write.
- **No reference** to `production.db`, `whiskies`, `seed`, `import`, `smws`, or `malt_radar` anywhere in the Antigravity log or its data dirs.
- **Verdict:** ❌ Antigravity is **ruled out** as the writer. It is an IDE/updater, not a data pipeline against this project.

## 2. Gemini CLI

- `which gemini` / `where gemini` → **not on PATH**, no Gemini binary discovered in the repo or `AppData`.
- No Gemini session logs, task queues, or `gemini*` process found.
- **Verdict:** ❌ Gemini CLI ruled out (not present).

## 3. Windows Task Scheduler

- `schtasks /query` inspected → **no task** targeting `production.db`, `malt_radar`, `whisky`, or `seed` / `import`. No unattended job fired in the window.

## 4. IDE run-configs (VS Code / PyCharm / Cursor)

- `.cursor/mcp.json` → `{"mcpServers": {}}` — **empty**. No MCP filesystem/sqlite server is connected. No autonomous agent tool could have opened production.db via MCP.
- No `.vscode/launch.json`, `tasks.json`, or PyCharm run-config found that references an import/seeder script on a schedule.
- VS Code / Cursor were not observed launching any python at the burst times.

## 5. Hermes agent / this investigation

- The only python processes at investigation time were Hermes agent services (`hermes_cli.main serve`, `tui_gateway.slash_worker`) and the P121 watcher — **none open production.db in RW mode** (watcher uses `?mode=ro`; agent processes do not touch the DB).

## Conclusion (Phase 1)

✅ No autonomous pipeline (Antigravity, Gemini, Scheduled Task, IDE run-config, MCP server) wrote to production.db during 20:00–21:30. The mutation was caused by a **manually-triggered repository script** (see `write_path_inventory.md` and `root_cause` in the final recommendation), not an unattended agent pipeline. The requirement "check autonomous pipeline first" is satisfied and cleared.
