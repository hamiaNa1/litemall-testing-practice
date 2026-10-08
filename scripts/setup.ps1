$ErrorActionPreference='Stop'
$project=Split-Path $PSScriptRoot -Parent
$download='D:\Codex\Downloads\mall-testing'
New-Item -ItemType Directory -Force $download,"$project\.tools","$project\vendor","$project\evidence\environment" | Out-Null
function Get-Archive([string]$url,[string]$file,[string]$destination) {
    if (-not (Test-Path $file)) {
        & curl.exe -fL --retry 2 --connect-timeout 15 --max-time 300 $url -o $file
        if ($LASTEXITCODE -ne 0) { throw "Download failed: $url" }
    }
    Expand-Archive -LiteralPath $file -DestinationPath $destination -Force
}
$commit='a1ef964a718b7277925b19ea26afe78ea3a1d325'
$src="$project\vendor\litemall-master"
if (-not (Test-Path "$src\pom.xml")) {
    Get-Archive "https://codeload.github.com/linlinjava/litemall/zip/$commit" "$download\litemall-$commit.zip" "$project\vendor"
    Rename-Item -LiteralPath "$project\vendor\litemall-$commit" -NewName 'litemall-master'
}
if (-not (Test-Path "$project\.tools\zulu8.96.0.205-ca-jdk8.0.504-win_x64")) {
    Get-Archive 'https://cdn.azul.com/zulu/bin/zulu8.96.0.205-ca-jdk8.0.504-win_x64.zip' "$download\jdk8.zip" "$project\.tools"
}
if (-not (Test-Path "$project\.tools\apache-maven-3.9.9")) {
    Get-Archive 'https://repo.maven.apache.org/maven2/org/apache/maven/apache-maven/3.9.9/apache-maven-3.9.9-bin.zip' "$download\maven.zip" "$project\.tools"
}
if (-not (Test-Path "$project\.tools\allure-2.34.1")) {
    Get-Archive 'https://repo.maven.apache.org/maven2/io/qameta/allure/allure-commandline/2.34.1/allure-commandline-2.34.1.zip' "$download\allure.zip" "$project\.tools"
}
if (-not (Test-Path "$project\.venv\Scripts\python.exe")) { & python -m venv "$project\.venv" }
& "$project\.venv\Scripts\python.exe" -m pip install --cache-dir 'D:\Codex\Cache\pip' -r "$project\requirements.txt"
if ($LASTEXITCODE -ne 0) { throw 'Python dependencies failed' }
$env:PLAYWRIGHT_BROWSERS_PATH='D:\Codex\Cache\ms-playwright'
& "$project\.venv\Scripts\python.exe" -m playwright install chromium
if ($LASTEXITCODE -ne 0) { throw 'Chromium installation failed' }
& "$project\.venv\Scripts\python.exe" "$PSScriptRoot\provision.py"
if ($LASTEXITCODE -ne 0) { throw 'MySQL setup failed (MYSQL_BIN must point to existing MySQL binaries)' }
$env:JAVA_HOME="$project\.tools\zulu8.96.0.205-ca-jdk8.0.504-win_x64"
$env:Path="$env:JAVA_HOME\bin;$env:Path"
Push-Location $src
try {
    & "$project\.tools\apache-maven-3.9.9\bin\mvn.cmd" '-Dmaven.repo.local=D:\Codex\Cache\mall-testing\maven' -B -ntp -pl litemall-all -am package *> "$project\evidence\environment\maven-rebuild.log"
    if ($LASTEXITCODE -ne 0) { throw 'Maven build failed; inspect evidence/environment/maven-rebuild.log' }
} finally { Pop-Location }
$env:npm_config_cache='D:\Codex\Cache\npm'
Push-Location "$src\litemall-vue"
try {
    # The only upstream change is its missing deployment runtime dependency.
    & "$project\.venv\Scripts\python.exe" "$PSScriptRoot\prepare_frontend.py"
    npm ci --registry=https://registry.npmjs.org --no-audit --no-fund *> "$project\evidence\environment\npm-vue-rebuild.log"
    if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency install failed' }
} finally { Pop-Location }
if (-not (Test-Path "$project\.tools\newman\node_modules\newman\bin\newman.js")) {
    npm install --prefix "$project\.tools\newman" newman@6.2.2 --no-audit --no-fund *> "$project\evidence\environment\newman-rebuild.log"
    if ($LASTEXITCODE -ne 0) { throw 'Newman install failed' }
}
Write-Host 'Setup complete. Run .\scripts\start.ps1'
