param([string]$RunDirectory,[int]$Port=8765)
$ErrorActionPreference='Stop'
$project=Split-Path $PSScriptRoot -Parent
if (-not $RunDirectory) { $RunDirectory=(Get-Content "$project\evidence\final-run.txt" -Raw).Trim() }
if (-not [IO.Path]::IsPathRooted($RunDirectory)) { $RunDirectory=Join-Path $project $RunDirectory }
$report=Join-Path $RunDirectory 'allure-report'
if (-not (Test-Path "$report\index.html")) { throw 'Report does not exist. Run run-tests.ps1 first.' }
$tcp=New-Object Net.Sockets.TcpClient
try { $tcp.Connect('127.0.0.1',$Port); $occupied=$true } catch { $occupied=$false } finally { $tcp.Dispose() }
if ($occupied) {
    $existing=Invoke-RestMethod "http://127.0.0.1:$Port/widgets/summary.json" -TimeoutSec 3
    $expected=Get-Content "$report\widgets\summary.json" -Raw | ConvertFrom-Json
    if ($existing.time.start -eq $expected.time.start -and $existing.statistic.total -eq $expected.statistic.total) {
        Write-Host "This report is already available: http://127.0.0.1:$Port"
        return
    }
    throw "Port $Port serves another report. Pass -Port 8766."
}
Write-Host "Allure report: http://127.0.0.1:$Port (Ctrl+C to stop)"
$python=Join-Path $project ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) { $python=(Get-Command python -ErrorAction Stop).Source }
& $python -m http.server $Port --bind 127.0.0.1 --directory $report
