while ($true) {
    # 15 dakikada bir çalıştır (900 saniye)
    Start-Sleep -Seconds 900
    
    # Değişiklik var mı kontrol et
    $status = git status --porcelain
    
    if ($status) {
        $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        git add .
        git commit -m "Auto-save commit: $timestamp"
        git push origin main
    }
}
