$ErrorActionPreference = 'Stop'
$project = Split-Path $PSScriptRoot -Parent
$env:JAVA_HOME = (Get-ChildItem "$project\.tools" -Directory -Filter '*jdk8*' | Select-Object -First 1).FullName
$env:Path = "$env:JAVA_HOME\bin;$env:Path"
Get-Content "$project\.env" | ForEach-Object {
    if ($_ -match '^([A-Z_]+)=(.*)$') { [Environment]::SetEnvironmentVariable($Matches[1], $Matches[2], 'Process') }
}
& "$project\.venv\Scripts\python.exe" "$PSScriptRoot\provision.py"
if ($LASTEXITCODE -ne 0) { throw 'Database provisioning failed' }
$jar = "$project\vendor\litemall-master\litemall-all\target\litemall-all-0.1.0-exec.jar"
if (-not (Test-Path $jar)) { throw 'Build backend before starting' }
$tcp = New-Object Net.Sockets.TcpClient
try { $tcp.Connect('127.0.0.1', 8080); $backendUp = $true } catch { $backendUp = $false } finally { $tcp.Dispose() }
if (-not $backendUp) {
    $config = "$project/config/".Replace('\','/')
    $p = Start-Process "$env:JAVA_HOME\bin\java.exe" -ArgumentList @('-Dfile.encoding=UTF-8','-jar', $jar,
        '--spring.profiles.active=db,core,admin,wx,qa',"--spring.config.additional-location=file:$config") -WorkingDirectory $project -WindowStyle Hidden -PassThru -RedirectStandardOutput "$project\evidence\environment\backend.stdout.log" -RedirectStandardError "$project\evidence\environment\backend.stderr.log"
    $p.Id | Set-Content "$project\.runtime\backend.pid"
}
$env:NODE_OPTIONS = '--openssl-legacy-provider'
$env:npm_config_cache = 'D:\Codex\Cache\npm'
$tcp = New-Object Net.Sockets.TcpClient
try { $tcp.Connect('127.0.0.1', 6255); $uiUp = $true } catch { $uiUp = $false } finally { $tcp.Dispose() }
if (-not $uiUp) {
    $vue = "$project\vendor\litemall-master\litemall-vue"
    $p = Start-Process (Get-Command node.exe).Source -ArgumentList @("$vue/node_modules/@vue/cli-service/bin/vue-cli-service.js", 'serve', '--host', '127.0.0.1') -WorkingDirectory $vue -WindowStyle Hidden -PassThru -RedirectStandardOutput "$project\evidence\environment\frontend.stdout.log" -RedirectStandardError "$project\evidence\environment\frontend.stderr.log"
    $p.Id | Set-Content "$project\.runtime\frontend.pid"
}
for ($i = 0; $i -lt 60; $i++) {
    try {
        $result = Invoke-RestMethod 'http://127.0.0.1:8080/wx/goods/count' -TimeoutSec 2
        if ($result.errno -eq 0) { Write-Host 'Backend ready: http://127.0.0.1:8080'; break }
    } catch { }
    Start-Sleep -Seconds 1
}
if ($i -eq 60) { throw 'Backend not healthy. Inspect evidence/environment/backend logs.' }
Write-Host 'Frontend compiling: http://127.0.0.1:6255'
