$ErrorActionPreference='Stop'
$project=Split-Path $PSScriptRoot -Parent
foreach ($name in @('frontend','backend','report')) {
    $file="$project\.runtime\$name.pid"
    if (Test-Path $file) {
        $taskProcessId=[int](Get-Content $file)
        $taskProcess=Get-CimInstance Win32_Process -Filter "ProcessId=$taskProcessId"
        if ($taskProcess -and $taskProcess.CommandLine.IndexOf($project,[StringComparison]::OrdinalIgnoreCase) -ge 0) {
            Stop-Process -Id $taskProcessId
            Write-Host "$name stopped"
        }
    }
}
# Graceful shutdown applies only to our verified private MySQL data directory.
& "$project\.venv\Scripts\python.exe" "$PSScriptRoot\stop_mysql.py"
