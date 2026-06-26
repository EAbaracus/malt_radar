status:
    git branch --show-current
    git status --short

db-check:
    powershell -ExecutionPolicy Bypass -File scripts/gates/check_db_mutation.ps1

repo-check:
    powershell -ExecutionPolicy Bypass -File scripts/gates/check_repo_state.ps1

diff:
    git diff --stat
    git status --short

frontend-gate:
    cd frontend && flutter analyze

backend-gate:
    python -m pytest -q

gate:
    just status
    just db-check
    just frontend-gate
    just backend-gate
    just diff
