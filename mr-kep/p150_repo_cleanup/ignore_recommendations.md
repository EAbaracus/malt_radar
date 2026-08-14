# P150 — .gitignore Recommendations

Current `.gitignore` already excludes: `*.db`, `*.sqlite`, `*.sqlite3`, `*.bak`, `*.tmp`, `__pycache__/`, `*.pyc`.
NOT covered — should be added:

```gitignore
# P149 / production safety backups (database copies - never commit)
knowledge.db.p149_old
knowledge.db.p139_old
knowledge.db.p141_old
knowledge.db.p142_old
backups/
mr-kep/*/backups/

# Hermes runtime leftovers
.agents/
skills-lock.json
archive/

# Windows device-name artifact
nul
```

## Reasoning
- `knowledge.db.p*.old` are pre-write DB backups (4-12 MB) — NOT matched by `*.db`.
- `backups/` (root) holds `production_pre_isolation_gate_*.db` — a full production.db copy; must stay out of git.
- `.agents/`, `skills-lock.json`, `archive/` are agent/runtime state, not source.
- `nul` is a Windows reserved device-name file from a stray `> nul` redirect.

## Never commit (already enforced)
- `*.db`, `*.bak`, `backups/`, `knowledge.db.p149_old` — confirmed absent from any commit.
