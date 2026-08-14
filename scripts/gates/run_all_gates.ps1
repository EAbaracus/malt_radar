param()

$ErrorActionPreference = "Stop"

Write-Host ">>> Running All Gates..." -ForegroundColor Cyan

Write-Host "`n[1/3] Running Repo State Check..."
powershell -ExecutionPolicy Bypass -File "scripts/gates/check_repo_state.ps1"
$stateExit = $LASTEXITCODE

Write-Host "`n[2/3] Running DB Mutation Guard..."
powershell -ExecutionPolicy Bypass -File "scripts/gates/check_db_mutation.ps1"
$dbExit = $LASTEXITCODE

Write-Host "`n[3/4] Running G4 Write-Path Guard (C2)..."
python scripts/gates/check_write_guard.py --path backend/app
$wgExit = $LASTEXITCODE

Write-Host "`n[4/4] Running Git Diff Check..."
try {
    git diff --check
    $diffExit = $LASTEXITCODE
} catch {
    $diffExit = 1
}

if ($stateExit -ne 0 -or $dbExit -ne 0 -or $wgExit -ne 0 -or $diffExit -ne 0) {
    Write-Host "`n>>> GATES FAILED. NO-GO." -ForegroundColor Red
    Exit 1
}

Write-Host "`n>>> ALL GATES PASSED. GO." -ForegroundColor Green
Exit 0
