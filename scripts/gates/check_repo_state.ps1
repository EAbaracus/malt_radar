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

Write-Host "`n=== Brand token anti-regresyon gates ===" -ForegroundColor Cyan

# 1) Legacy gold residue - must be nowhere
$gold = Get-ChildItem -Recurse frontend/lib -Filter *.dart | Select-String -Pattern "0xFFD4AF37" -List | Select-Object -ExpandProperty Path
if ($gold) {
    Write-Host "GOLD RESIDUE (FORBIDDEN):" -ForegroundColor Red
    $gold | ForEach-Object { Write-Host "  $_" }
    $risk = "HIGH"
} else {
    Write-Host "gold #D4AF37: clean" -ForegroundColor Green
}

# 2) Brass - only lives in app_theme_colors.dart (UI isolation)
$brass = Get-ChildItem -Recurse frontend/lib -Filter *.dart | Select-String -Pattern "0xFFC9A227" -List | Select-Object -ExpandProperty Path
if ($brass) {
    $bad = $brass | Where-Object { $_ -notmatch "app_theme_colors\.dart" }
    if ($bad) {
        Write-Host "BRASS IN UI (FORBIDDEN - only app_theme_colors.dart):" -ForegroundColor Red
        $bad | ForEach-Object { Write-Host "  $_" }
        $risk = "HIGH"
    } else {
        Write-Host "brass: only app_theme_colors.dart (OK)" -ForegroundColor Green
    }
} else {
    Write-Host "brass: no reference (OK)" -ForegroundColor Yellow
}

# 3) Catalog CSV assets - never in client bundle (anti-scrape)
$csv = Select-String -Path frontend/pubspec.yaml -Pattern "^- assets/data" | Select-Object -ExpandProperty Line
if ($csv) {
    Write-Host "CSV ASSET LEAK (FORBIDDEN):" -ForegroundColor Red
    $csv | ForEach-Object { Write-Host "  $_" }
    $risk = "HIGH"
} else {
    Write-Host "csv assets: clean (no catalog in public bundle)" -ForegroundColor Green
}

Write-Host ""
Write-Host "Recommended risk level: $risk" -ForegroundColor Magenta
Exit 0
