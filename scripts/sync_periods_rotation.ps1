param(
    [string]$SourceFolder = (Join-Path $env:USERPROFILE 'Downloads\cizgi-masasi'),
    [string]$RepoUrl = 'https://github.com/kmelihsari-jpg/cizgi-masasi-updater.git'
)
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$logDir = Join-Path $env:USERPROFILE 'Downloads\cizgi-masasi'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log = Join-Path $logDir 'periods-rotation-sync.log'
function Log([string]$msg) {
    ('[{0}] {1}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $msg) | Tee-Object -FilePath $log -Append
}
function Run-Git([string[]]$GitArgs) {
    & git @GitArgs
    if ($LASTEXITCODE -ne 0) { throw ('Git basarisiz: git ' + ($GitArgs -join ' ')) }
}
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw 'Git PATH icinde bulunamadi' }
$paths = @{}
foreach ($name in @('periods.json','rotation.json')) {
    $p = Join-Path $SourceFolder $name
    if (Test-Path -LiteralPath $p) {
        try {
            $data = Get-Content -LiteralPath $p -Raw -Encoding UTF8 | ConvertFrom-Json
            if ($name -eq 'periods.json') {
                if (-not $data.rows -or -not $data.dates -or $data.rows.Count -lt 100) { throw 'eksik periyot verisi' }
            } elseif (-not $data.t -or -not $data.updated) { throw 'eksik rotasyon verisi' }
            $paths[$name] = $p
            Log ('KAYNAK: {0} ({1})' -f $name, (Get-Item $p).LastWriteTime)
        } catch { Log ('GECERSIZ: {0} ({1})' -f $name, $_); throw }
    } else { Log ('BULUNAMADI: {0}' -f $p) }
}
if ($paths.Count -eq 0) { Log 'Aktaracak yerel dosya bulunamadi'; exit 0 }
$tmp = Join-Path ([IO.Path]::GetTempPath()) ('cm-period-rot-' + [guid]::NewGuid().ToString('N'))
try {
    Run-Git -GitArgs @('clone','--depth','1','--branch','main',$RepoUrl,$tmp)
    $seed = Join-Path $tmp 'seed'
    New-Item -ItemType Directory -Force -Path $seed | Out-Null
    foreach ($name in $paths.Keys) {
        $target = Join-Path $seed $name
        $source = $paths[$name]
        $fresh = Get-Content -LiteralPath $source -Raw -Encoding UTF8 | ConvertFrom-Json
        if (Test-Path -LiteralPath $target) {
            $old = Get-Content -LiteralPath $target -Raw -Encoding UTF8 | ConvertFrom-Json
            if ($name -eq 'periods.json' -and $old.dates.Count -gt 0) {
                $oldDate = [string]$old.dates[-1]
                $newDate = [string]$fresh.dates[-1]
                if ($newDate -lt $oldDate) { Log ('ATLANDI eski periods: {0} < {1}' -f $newDate,$oldDate); continue }
                if ($newDate -eq $oldDate -and $fresh.rows.Count -lt $old.rows.Count) {
                    Log 'ATLANDI eksik periods satirlari'; continue
                }
            }
            if ($name -eq 'rotation.json' -and $old.updated -and ([string]$fresh.updated -lt [string]$old.updated)) {
                Log ('ATLANDI eski rotation: {0} < {1}' -f $fresh.updated,$old.updated); continue
            }
        }
        Copy-Item -LiteralPath $source -Destination $target -Force
        Log ('HAZIR: ' + $name)
    }
    Run-Git -GitArgs @('-C',$tmp,'add','-A','--','seed')
    & git -C $tmp diff --cached --quiet
    $diff = $LASTEXITCODE
    if ($diff -eq 0) { Log 'Yeni veri yok'; exit 0 }
    if ($diff -ne 1) { throw 'Git diff hatasi' }
    Run-Git -GitArgs @('-C',$tmp,'-c','user.name=Cizgi Masasi Local Sync','-c','user.email=local-sync@users.noreply.github.com','commit','-m','data: sync local periods and rotation')
    Run-Git -GitArgs @('-C',$tmp,'push','origin','HEAD:main')
    Log 'BASARILI: periods/rotation GitHub push. Actions otomatik kontrol edip yayinlayacak.'
} finally {
    if (Test-Path -LiteralPath $tmp) { Remove-Item -LiteralPath $tmp -Recurse -Force -ErrorAction SilentlyContinue }
}
