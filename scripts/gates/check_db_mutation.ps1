param()

Write-Host "=== DB Mutation Guard ===" -ForegroundColor Cyan

# Check staged files
$stagedFiles = git diff --name-only --cached

$patterns = @(
    "output/import/.*\.db$",
    "output/import/.*\.sqlite$",
    "output/import/.*\.sqlite3$",
    "output/import/.*\.db-wal$",
    "output/import/.*\.db-shm$",
    "output/import/production_before_.*\.db$"
)

$hasStagedProtected = $false
foreach ($file in $stagedFiles) {
    foreach ($pattern in $patterns) {
        if ($file -match $pattern) {
            Write-Host "BLOCKED: Staged protected artifact found -> $file" -ForegroundColor Red
            $hasStagedProtected = $true
            break
        }
    }
}

if ($hasStagedProtected) {
    Write-Host "NO-GO. DB artifacts are staged for commit. Please unstage them unless explicitly approved." -ForegroundColor Red
    Exit 1
}

# Check modified but not staged
$modifiedFiles = git diff --name-only
foreach ($file in $modifiedFiles) {
    if ($file -match "output/import/production\.db$") {
        Write-Host "WARNING: production.db is modified locally but not staged." -ForegroundColor Yellow
        break
    }
}

Write-Host "GO. No protected DB artifacts staged." -ForegroundColor Green
Exit 0
