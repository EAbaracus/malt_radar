param()

Write-Host "=== DB Mutation Guard ===" -ForegroundColor Cyan

# Check staged files with status
$stagedFiles = git diff --cached --name-status

$patterns = @(
    "output/import/.*\.db$",
    "output/import/.*\.sqlite$",
    "output/import/.*\.sqlite3$",
    "output/import/.*\.db-wal$",
    "output/import/.*\.db-shm$",
    "output/import/production_before_.*\.db$"
)

$hasBlockedArtifact = $false
$hasWarnGo = $false

foreach ($line in $stagedFiles) {
    if ([string]::IsNullOrWhiteSpace($line)) { continue }
    
    $parts = $line -split '\s+'
    $status = $parts[0]
    
    $matched = $false
    $matchedFile = ""
    for ($i = 1; $i -lt $parts.Count; $i++) {
        $file = $parts[$i]
        foreach ($pattern in $patterns) {
            if ($file -match $pattern) {
                $matched = $true
                $matchedFile = $file
                break
            }
        }
        if ($matched) { break }
    }

    if ($matched) {
        if ($status -match "^D") {
            Write-Host "WARN_GO: protected DB artifact is staged for deletion/untracking only -> $matchedFile" -ForegroundColor Yellow
            $hasWarnGo = $true
        } else {
            Write-Host "BLOCKED: Staged protected artifact found ($status) -> $matchedFile" -ForegroundColor Red
            $hasBlockedArtifact = $true
        }
    }
}

if ($hasBlockedArtifact) {
    Write-Host "NO-GO. DB artifacts are staged for commit (A/M/R/C). Please unstage them unless explicitly approved." -ForegroundColor Red
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

if (-not $hasWarnGo) {
    Write-Host "GO. No protected DB artifacts staged." -ForegroundColor Green
}
Exit 0
