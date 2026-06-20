$ErrorActionPreference = "Stop"

$RepoRoot = "C:\Users\eltun\Documents\malt radar"
$FrontendRoot = Join-Path $RepoRoot "frontend"

$DriveRemote = "maltgdrive:MaltRadar Beta"

$ApkSource = Join-Path $FrontendRoot "build\app\outputs\flutter-apk\app-release.apk"

$Date = Get-Date -Format "yyyy-MM-dd_HH-mm"
$DistDir = Join-Path $RepoRoot "dist\manual-apk-beta"

$VersionedName = "MaltRadar-beta-release-$Date.apk"
$LatestName = "MaltRadar-beta-latest.apk"
$HashName = "MaltRadar-beta-latest.apk.sha256.txt"

$VersionedApk = Join-Path $DistDir $VersionedName
$LatestApk = Join-Path $DistDir $LatestName
$HashFile = Join-Path $DistDir $HashName

if (!(Test-Path $ApkSource)) {
    throw "APK bulunamadı: $ApkSource"
}

if (!(Test-Path $DistDir)) {
    New-Item -ItemType Directory -Path $DistDir | Out-Null
}

Copy-Item $ApkSource $VersionedApk -Force
Copy-Item $ApkSource $LatestApk -Force

Get-FileHash $LatestApk -Algorithm SHA256 | Out-File $HashFile -Encoding UTF8

Write-Host "APK hazırlandı:"
Write-Host $VersionedApk
Write-Host $LatestApk
Write-Host $HashFile

Write-Host "Yeni APK Google Drive'a yükleniyor..."

rclone copy $VersionedApk "$DriveRemote/" --progress
rclone copy $LatestApk "$DriveRemote/" --progress
rclone copy $HashFile "$DriveRemote/" --progress

Write-Host "Yeni APK yüklendi. Eski versioned APK dosyaları temizleniyor..."

$RemoteReleaseFiles = rclone lsf "$DriveRemote/" --files-only --include "MaltRadar-beta-release-*.apk"

foreach ($File in $RemoteReleaseFiles) {
    $CleanFile = $File.Trim()

    if ($CleanFile -and $CleanFile -ne $VersionedName) {
        Write-Host "Siliniyor: $CleanFile"
        rclone deletefile "$DriveRemote/$CleanFile"
    }

$RemoteReleaseHashFiles = rclone lsf "$DriveRemote/" --files-only --include "MaltRadar-beta-release-*.apk.sha256.txt"

foreach ($File in $RemoteReleaseHashFiles) {
    $CleanFile = $File.Trim()

    if ($CleanFile) {
        Write-Host "Eski versioned hash siliniyor: $CleanFile"
        rclone deletefile "$DriveRemote/$CleanFile"
    }
}
}

Write-Host "Google Drive upload ve eski sürüm temizliği tamamlandı."
Write-Host "Kalan ana dosyalar:"
rclone lsf "$DriveRemote/" --files-only