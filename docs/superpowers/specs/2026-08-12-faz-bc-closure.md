---
title: Faz B/C Kapanış Raporu — Read-Seam + Write-Gate Enforcement
date: 2026-08-12
status: CLOSED
tags: [b-read-seam, c-guard-enforcement, closure]
related_spec: docs/superpowers/specs/2026-08-11-read-write-seam-guard-design.md
production_sha_before: a9960053da30cc8da0897919c5e25392a7fc1c0f5ffed46a0d4325df7eaab6b4
production_sha_after:  a9960053da30cc8da0897919c5e25392a7fc1c0f5ffed46a0d4325df7eaab6b4
---

# Faz B + C Kapanış Raporu

Hedef: `malt radar CLEAN` deposunda read-only mimari sevkiyat
B (read seam: ProductionReadAdapter) + C (guard zorunluluğu:
`restrict_tables` enforcement + `sqlite3.connect` CI shim).

**Kapstün:** `production.db` SHA `a9960053…` **hiçbir commit değişmedi.**
Bu rapordaki tüm PR'lar read-only (C1 temp DB'de test) — production'a hiçbir yazma yapılmadı.

---

## Faz B — Read Seam (B1 + B2)

| PR | Commit | Kapsam | Kabul |
|---|---|---|---|
| **#40 (B1)** | `acf1f53` | `production_read_adapter.py` (mode=ro, query_only, `resolve_db_path`, `_redact_prices`) + `review_action_writer.py` + `utils/shared_paths.py` | MERGED |
| **#41 (B2)** | `6413c5d` + `35458fd` | `db_read_service.py` delegate → adapter (connection seam), `db_api.py` router | MERGED |

**B1** — ReviewQueryService read metotları adapter'a, write metotları ReviewActionWriter'a.
**B2** — DbReadService (frontend catalog) sadece `_get_connection`'ı adapter'a yönlendirir; 480 satır JOIN/filtre/normalize mantığı taşınmaz.

**G4 kabul kriteri (§ görüldü):** `sqlite3.connect()` → yalnızca
`backend/app/db/write_guard.py` (canonical write) + `production_read_adapter.py` (mode=ro).
`auth/store.py` ayrı auth DB, `archive/` dead. Suite 55 → 74 passed (C1 sonrası).

---

## Faz C — Guard Enforcement (C1 + C2)

| PR | Commit | Kapsam | Kabul |
|---|---|---|---|
| **#42 (C1)** | `44f9078` | `WriteGate._RestrictedConnection` — `restrict_tables` runtime enforcement + Row-aware `_post_validate` | OPEN (MERGEABLE, CLEAN) |
| **#43 (C2)** | `34e8233` + `fd260f6` | `check_write_guard.py` AST lint shim + `repo-gates.yml` CI step | OPEN (MERGEABLE, UNSTABLE*) |

### C1 — restrict_tables enforcement
`WriteGate.__enter__` içinde conn replacement: `restrict_tables` listesindeki
tablolar dışındaki INSERT/UPDATE/DELETE/REPLACE → `RuntimeError`.
- `_RestrictedConnection` = **composition** (sqlite3.Connection subclass DEĞİL —
  Windows'ta C-level init hatası + temp DB lock veriyordu).
- `_extract_target_table` 8-case parametrized (INSERT/OR-IGNORE/UPDATE/DELETE/REPLACE
  + SELECT/PRAGMA/CREATE non-target).
- `_post_validate` Row-factory aware (`sqlite3.Row` ile `("ok",)` tuple eşleşmesi).
- Dead code: eski `_file_only_mode` branch + `_TABLE_RE` kaldırıldı.

### C2 — G4 CI lint shim (gerçek kök neden)
`UNSTABLE` durumu **C2 kodundan değil**: repo'nun CodeQL workflow'u
`codeql.yml.disabled` (kodlanmış), GitHub hâlâ varsayılan `Analyze (python)` job'ını
bekliyor (0s pending). C2 kendisi `gates: pass` (CI shim step eklendi, line 30-31).

Shim `check_write_guard.py` AST-based: `sqlite3.connect` + production.db target →
sadece `write_guard.py` + `production_read_adapter.py` geçer; `archive/` skip.
`repo-gates.yml`'e step eklendi (PR #43 öncesi CI'de G4 hiç çalışmıyordu).

---

## C3 — Tarihi write script triyajı (KOD DOKUNMADI, read-only)

**Bulgu:** root worktree'de canlı production.db yazma script'i **YOK**.
Sadece `backend/app/db/` guard + adapter + review_action_writer.

`apply_low_risk_official_facts_v12.py` + `p95b_phase12_execute.py` →
`.worktrees/t_b17c90fa/` altında (branch `malt-radar-clean/t_b17c90fa-hiram`,
commit `0d46e86`, 2026-07-30). `git worktree list` **aktif** gösteriyor
(orphan değil, prune edilemez) → **ayrı branch'in sorumluluğu**, root B/C kapsamı dışı.

**Karar:** C3 = read-only triyaj, kod dokunulmadı. Archive yönlendirme ayrı iş
(bu worktree aktif). `_on_copy` script'leri onayla C3 dışı.

---

## Doğrulama (taze, 2026-08-12)

| Kontrol | Sonuç |
|---|---|
| `production.db SHA` | `a9960053…` (önce=sonra, hiç yazma) |
| C1 13-parametrize ad-hoc | 13/13 PASS |
| C2 shim exit | 0 (`sqlite3.connect → write_guard + production_read_adapter`) |
| Suite (C1 branch) | 74 passed, 1 skipped |
| `restrict_tables` case | `whiskies INSERT blocked (RuntimeError)` |
| `post_validate` Row-aware | temp DB rows=1, integrity clean |
| PR #42 / #43 | MERGEABLE; #42 CLEAN, #43 UNSTABLE (CodeQL — repo config, kod değil) |

## Açık Kalemler
- [ ] PR #42 (C1) — merge (MERGEABLE, CLEAN)
- [ ] PR #43 (C2) — merge sonrası CodeQL UNSTABLE (repo config ayrı iş)
- [ ] `.worktrees/t_b17c90fa` — aktif ayrı branch; archive/guard kararı root dışı (ops)
- [ ] AL-A..AL-D (Anonymous Read Layer) — AYRı spec, ayrı oturum (B/C devamı değil)