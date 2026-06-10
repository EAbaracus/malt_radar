param (
    [switch]$Push = $false
)

while ($true) {
    # 15 dakikada bir çalıştır (900 saniye)
    Start-Sleep -Seconds 900
    
    # Değişiklik var mı kontrol et
    $status = git status --porcelain
    
    if ($status) {
        $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        # Do not use git add . here. Generated output/, DB files and backups must never be auto-added.
        git add -u
        
        Write-Host "Auto-push script detected changes. Tracked files added to index."
        git status --short
        
        if ($Push) {
            git commit -m "Auto-save commit: $timestamp"
            git push origin main
            Write-Host "Changes pushed automatically."
        } else {
            Write-Host "Push skipped because -Push flag was not provided."
        }
    }
}
