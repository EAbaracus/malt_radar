# Runtime Process Analysis — `production.db` Mutation (P120 Forensic)

_READ-ONLY. Process command lines captured via `Get-CimInstance Win32_Process` + `tasklist`/`netstat`. No process killed._

## Running processes evaluated

| PID | Image | Command line | DB writer? |
|---|---|---|---|
| 25216 / 19196 | python.exe | `hermes_cli.main serve --host 127.0.0.1 --port 0` | No (agent server) |
| 38272 / 7588 / 25088 / 30312 / 41700 / 16012 / 43100 / 48372 / 12992 / 53416 / 50100 / 49856 | python.exe | `tui_gateway.slash_worker --session-key ... --model ...` | No (agent workers) |
| 7676 / 43440 | python.exe | `moa_proxy.py` | No (model proxy) |
| 32664 | python.exe | `GOG Galaxy\plugin_runner.py` | No (game launcher) |
| 5916 | pythonw.exe | `hermes_cli.main gateway run` | No (agent gateway) |
| many | node.exe | Hermes desktop app / frontend tooling | No |
| 5112 / 18140 | (svc) | Docker/EpicGamesLauncher helpers | No |
| 7924 / 41792 / 2996 / 41024 | Hermes.exe | Hermes desktop app | No |

## Servers / listeners
- `8090` → `moa_proxy.py` (PID 43440) — model proxy, not a DB writer.
- `9000` / `9090` → PID 5112 (empty cmdline; Docker/Epic helper).
- `24563` → `EpicGamesLauncher.exe`.
- **No listener on `:8080`** → the FastAPI `backend/run.py` (default port 8080) is **NOT running**.
- **No `flutter`/`dart` process** → Flutter app not running.

## Open-file check
`openfiles.exe /query` returned no handle for `production.db` (requires admin; no
match). No `-journal` / `-wal` / `-shm` file present beside `production.db`
(`journal_mode=delete`), confirming **no active write transaction** at capture.

## Conclusion
**No running process can be tied to the `production.db` writes.** The writer has
already terminated; the database is now stable (mtime `2026-07-15 21:17:54`,
whisky count steady at 4,749 across two consecutive read-only checks).

## Rejected action (safety note)
Reference suggestions to `taskkill /im python.exe /f` were **NOT executed**: this
would terminate the Hermes agent and the user's desktop app (they are Python
processes), is destructive (not read-only), and is unnecessary because the writer
has stopped on its own. Killing processes is outside the P120 forensic scope and
the project's read-only mandate.
