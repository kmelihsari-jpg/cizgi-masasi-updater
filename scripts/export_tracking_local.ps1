<#
Safely extract tracking metrics from EXISTING guncelle.ps1 cache YYYY-MM-DD.json.
Run on your OWN Windows machine after the 19:30 original updater finishes.
No API token is needed by this exporter, no network call is made.
Example:
 powershell -NoProfile -ExecutionPolicy Bypass -File .\export_tracking_local.ps1 -CacheDir "C:\NBA\cache" -Output "C:\Github\cizgi-masasi-updater\seed\tracking-local.json"
#>
param(
  [Parameter(Mandatory=$true)][string]$CacheDir,
  [Parameter(Mandatory=$true)][string]$Output,
  [int]$RecentDays=4
)
$ErrorActionPreference='Stop'
$cutoff = (Get-Date).Date.AddDays(-$RecentDays)
$files = @(Get-ChildItem -LiteralPath $CacheDir -Filter '????-??-??.json' -File | Sort-Object Name)
$records = New-Object System.Collections.Generic.List[object]
$dates = New-Object System.Collections.Generic.List[string]
foreach ($file in $files) {
  $d=$file.BaseName
  try { $parsedDate = [datetime]::ParseExact($d,'yyyy-MM-dd',[Globalization.CultureInfo]::InvariantCulture) }
  catch { continue }
  if ($parsedDate -lt $cutoff) { continue }
  $rows = ConvertFrom-Json -InputObject ([IO.File]::ReadAllText($file.FullName,[Text.Encoding]::UTF8))
  $thisDay=0
  foreach($r in $rows) {
    if ($null -eq $r -or $r.Count -lt 7) { continue }
    $id = [string]$r[0]
    if ($id -notmatch '^\d+$') { continue }
    $o=[ordered]@{date=$d; pid=$id; pot=$r[1]; rc=$r[2]; rcon=$r[3]; runc=$r[4]; rdef=$r[5]}
    $valid=$false
    foreach($metric in @('pot','rc','rcon','runc','rdef')) {
      $v=$o[$metric]
      if ($null -eq $v) {continue}
      if ($v -isnot [int] -and $v -isnot [long] -and $v -isnot [double] -and $v -isnot [decimal]) {throw "Invalid $metric in $($file.Name) for player $id"}
      if ($v -lt 0 -or $v -gt 150) {throw "Out-of-range $metric in $($file.Name)"}
      $valid=$true
    }
    if ($valid) {$records.Add($o); $thisDay++}
  }
  if ($thisDay -gt 0) {$dates.Add($d)}
}
if ($records.Count -lt 1) {throw 'No valid local NBA tracking records: original files remain unchanged.'}
$payload=[ordered]@{
 source='local-nba-tracking-cache-v1'
 exported_at=(Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
 dates=@($dates)
 records=@($records)
}
$json=ConvertTo-Json -InputObject $payload -Depth 6 -Compress
$destDir=Split-Path -Parent $Output
if (-not (Test-Path -LiteralPath $destDir)) {New-Item -ItemType Directory -Path $destDir -Force | Out-Null}
$tmp=$Output+'.tmp'
[IO.File]::WriteAllText($tmp,$json+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))
Move-Item -LiteralPath $tmp -Destination $Output -Force
Write-Host "SUCCESS: $($records.Count) player/date tracking records; $($dates.Count) dates; output $Output"
