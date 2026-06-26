param()

Write-Host "=== Repo State Report ===" -ForegroundColor Cyan

$branch = git branch --show-current
Write-Host "Current branch: $branch"

Write-Host "`nGit status --short:"
git status --short

Write-Host "`nproduction.db tracking status:"
$tracked = git ls-files output/import/production.db
if ($tracked) {
    Write-Host "output/import/production.db is TRACKED." -ForegroundColor Yellow
} else {
    Write-Host "output/import/production.db is NOT TRACKED." -ForegroundColor Green
}

Write-Host "`nproduction.db history:"
$history = git log --all --oneline -- output/import/production.db
if ($history) {
    Write-Host "production.db exists in history." -ForegroundColor Yellow
    $history | Select-Object -First 3 | ForEach-Object { Write-Host "  $_" }
    if ($history.Count -gt 3) { Write-Host "  ..." }
} else {
    Write-Host "production.db NOT found in history." -ForegroundColor Green
}

$risk = "LOW"
if ($tracked -or $history) {
    $risk = "MEDIUM"
}

Write-Host "`nRecommended risk level: $risk" -ForegroundColor Magenta
Exit 0
