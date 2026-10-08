param([ValidateSet('all','regression','api','ui','defects')][string]$Suite='all')
$ErrorActionPreference='Stop'
$project=Split-Path $PSScriptRoot -Parent
Set-Location $project
$runId=Get-Date -Format 'yyyyMMdd-HHmmss'
$env:EVIDENCE_DIR="$project\evidence\runs\$runId-$Suite"
$env:PYTHONIOENCODING='utf-8'
$env:PLAYWRIGHT_BROWSERS_PATH='D:\Codex\Cache\ms-playwright'
New-Item -ItemType Directory -Force $env:EVIDENCE_DIR | Out-Null
$argsList=@('-m','pytest','-q','--alluredir',"$env:EVIDENCE_DIR\allure-results",'--junitxml',"$env:EVIDENCE_DIR\junit.xml",'--log-file',"$env:EVIDENCE_DIR\pytest.log")
switch ($Suite) {
    'api' { $argsList+='tests/api' }
    'ui' { $argsList+='tests/ui' }
    'regression' { $argsList+=@('-m','not defect') }
    'defects' { $argsList+=@('-m','defect') }
}
& "$project\.venv\Scripts\python.exe" @argsList 2>&1 | Tee-Object "$env:EVIDENCE_DIR\execution.log"
$testExitCode=$LASTEXITCODE
@'
OS=Windows
Java=OpenJDK8.0.504
Python=3.10.11
MySQL=8.4.11
Database=litemall_qa_on_127.0.0.1_13306
Backend=http://127.0.0.1:8080
Frontend=http://127.0.0.1:6255
UI=Chromium_390x844
Source_commit=a1ef964a718b7277925b19ea26afe78ea3a1d325
'@ | Set-Content "$env:EVIDENCE_DIR\allure-results\environment.properties" -Encoding ascii
$env:JAVA_HOME=(Get-ChildItem "$project\.tools" -Directory -Filter '*jdk8*' | Select-Object -First 1).FullName
$env:Path="$env:JAVA_HOME\bin;$env:Path"
$allure=(Get-ChildItem "$project\.tools" -Directory -Filter 'allure-*' | Select-Object -First 1).FullName
& "$allure\bin\allure.bat" generate "$env:EVIDENCE_DIR\allure-results" -o "$env:EVIDENCE_DIR\allure-report" --clean
if ($LASTEXITCODE -ne 0) { throw 'Allure report generation failed' }
& "$project\.venv\Scripts\python.exe" "$PSScriptRoot\summarize.py" "$env:EVIDENCE_DIR"
if ($LASTEXITCODE -ne 0) { throw 'Summary generation failed' }
Write-Host "Evidence: $env:EVIDENCE_DIR"
Write-Host "Test exit code: $testExitCode (unfixed defect assertions intentionally remain failing)"
exit $testExitCode
