param()
Write-Host "Installing Git hooks..." -ForegroundColor Cyan
git config core.hooksPath .githooks
Write-Host "Git hooks installed successfully." -ForegroundColor Green
