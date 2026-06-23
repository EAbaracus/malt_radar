# Malt Radar Agent Instructions

## Language and Style
- Respond in Turkish.
- Be concise, command-focused, and implementation-oriented.
- Avoid long explanations unless explicitly requested.
- Always include exact PowerShell / Flutter / git commands when recommending actions.

## Token-Lite Rules
- Do not scan the whole repository unless explicitly requested.
- Do not read large files fully.
- For CSV/JSON/log files, use count/head/sample/stat commands.
- For SQLite DB, use targeted SQL counts and readonly checks.
- Start with:
  - git status --short
  - git diff --stat
  - git diff --name-status
- Read only files directly relevant to the task.
- Avoid repeating project history in every response.
- Summarize command outputs; do not paste full logs unless necessary.
- Prefer small scoped stages over broad refactors.

## File Scope Rules
- In one task, prefer reading max 8 source files.
- In one task, prefer modifying max 1-5 files.
- If more files are needed, report first and ask for next stage.
- Do not edit unrelated frontend/backend/data files.

## Malt Radar DB Safety
- Treat output/import/production.db as protected.
- Do not write to production.db unless the user explicitly asks.
- Before any DB write:
  - create backup
  - compute SHA256
  - run dry-run
  - produce report and GO/NO-GO gate
- staging_tasting_notes must pass QA before production apply.
- License-risk data must stay staging/quarantine unless approved.

## Git Safety
- Do not commit unless explicitly requested.
- Do not push unless explicitly requested.
- Do not delete untracked files unless explicitly requested.
- Always show git status before and after changes.

## Report Format
Use this short format:
- Ne yaptım
- Değişen dosyalar
- Çalıştırılan komutlar
- Test sonucu
- GO / WARN_GO / NO-GO
- Sonraki önerilen komut

## Preferred Workflow
1. Recon
2. Preview / dry-run
3. QA report
4. Controlled apply only if approved
5. Commit only if approved
