<#
Cizgi Masasi - 19:30 eski guncelle.ps1 sonrasinda takip verilerini GitHub'a aktarir.
Mevcut guncelle.ps1 degistirilmez; Odds API anahtari GitHub'a gitmez.

Ornek:
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\cizgi-masasi\tracking_1930_aktar.ps1" -OriginalScript "C:\cizgi-masasi\guncelle.ps1" -RepoDir "C:\cizgi-masasi-updater"

Ilk calistirmada TestOnly kullanin; GitHub'a gondermez:
 ... -TestOnly
#>
param(
    [Parameter(Mandatory=$true)][string]$OriginalScript,
    [Parameter(Mandatory=$true)][string]$RepoDir,
    [switch]$TestOnly
)
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

function Run-Git([string[]]$Arguments) {
    & git -C $RepoDir @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Git komutu basarisiz: $($Arguments -join ' ')" }
}

if (-not (Test-Path -LiteralPath $OriginalScript -PathType Leaf)) { throw "guncelle.ps1 yok: $OriginalScript" }
if (-not (Test-Path -LiteralPath (Join-Path $RepoDir '.git'))) { throw "Git deposu yok: $RepoDir" }
$OriginalScript = (Resolve-Path -LiteralPath $OriginalScript).Path
$RepoDir = (Resolve-Path -LiteralPath $RepoDir).Path
$CacheDir = Join-Path (Split-Path -Parent $OriginalScript) 'cache'
$Exporter = Join-Path $RepoDir 'scripts\export_tracking_local.ps1'
$Output = Join-Path $RepoDir 'seed\tracking-local.json'
if (-not (Test-Path -LiteralPath $Exporter -PathType Leaf)) {
    throw "Aktarma araci Git deposunda eksik: $Exporter"
}

if (-not $TestOnly) {
    $branch = (& git -C $RepoDir branch --show-current).Trim()
    if ($LASTEXITCODE -ne 0 -or $branch -ne 'main') { throw 'Git deposunun main dalinda oldugundan emin olun.' }
    $dirty = @(& git -C $RepoDir status --porcelain --untracked-files=no | Where-Object { $_ -notmatch 'seed/tracking-local.json$' })
    if ($dirty.Count -gt 0) { throw 'Depoda baska kaydedilmemis degisiklik var. GitHub gonderimi durduruldu.' }
    Run-Git @('pull','--ff-only','origin','main')
}

Write-Host '[1/4] Eski guncelle.ps1 calisiyor...'
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $OriginalScript
if ($LASTEXITCODE -ne 0) { throw 'guncelle.ps1 hata verdi; tracking aktarimi durduruldu.' }

Write-Host '[2/4] Gercek tracking onbellegi disari aktariliyor...'
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $Exporter -CacheDir $CacheDir -Output $Output -RecentDays 4
if ($LASTEXITCODE -ne 0) { throw 'Tracking JSON aktarimi basarisiz; GitHub degistirilmedi.' }

if ($TestOnly) {
    Write-Host 'TEST BASARILI: tracking-local.json hazir. GitHub gonderimi yapilmadi.'
    exit 0
}

Write-Host '[3/4] GitHub deposu guncelleniyor...'
Run-Git @('add','--','seed/tracking-local.json')
& git -C $RepoDir diff --cached --quiet --exit-code
$diffResult = $LASTEXITCODE
if ($diffResult -eq 0) { Write-Host 'Yeni tracking degisikligi yok; gonderim gerekmiyor.'; exit 0 }
if ($diffResult -ne 1) { throw 'Git degisiklik kontrolu basarisiz.' }
Run-Git @('-c','user.name=Cizgi Masasi Tracking','-c','user.email=cizgi-masasi-tracking@users.noreply.github.com','commit','-m','data: import local NBA tracking cache')
Write-Host '[4/4] Github a aktariliyor...'
Run-Git @('push','origin','main')
Write-Host 'BASARILI: Tracking verisi GitHub a gonderildi. Birlesme workflow unu kontrol edin.'
