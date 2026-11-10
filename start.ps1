# Starts everything: the Beacon backend (port 8010, this window) and the test website (port 8011, background).
# Settings and CRM login come from .env.
#   ./start.ps1         answers with DeepSeek (hosted, needs DEEPSEEK_API_KEY)
#   ./start.ps1 local   answers with the open-source Qwen3-4B model and Beacon's trained adapter, on this machine
param([Parameter(Position = 0)][ValidateSet('deepseek', 'local')][string]$Model = 'deepseek', [switch]$NoBrowser)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
# The choice on the command line wins over PLANNER_PROVIDER in .env.
$provider = $Model.ToLower()
$env:PLANNER_PROVIDER = $provider
# Reuse a running Beacon before installing packages or loading the model again.
if (Get-NetTCPConnection -LocalPort 8010 -State Listen -ErrorAction SilentlyContinue) {
    try { $running = Invoke-RestMethod 'http://127.0.0.1:8010/api/health' -TimeoutSec 10 }
    catch { throw 'Port 8010 is occupied but Beacon is not responding. Check the existing server before restarting.' }
    if ($running.status -ne 'ok' -or $running.screen_transport -ne 'authenticated_jpeg_polling') {
        throw 'Port 8010 is being used by another application. No process was stopped.'
    }
    if ($running.provider -ne $provider) {
        throw "Beacon is already running with $($running.provider). Stop it (Ctrl+C in its window), then run this again. No process was stopped."
    }
    if (-not (Get-NetTCPConnection -LocalPort 8011 -State Listen -ErrorAction SilentlyContinue)) {
        Start-Process -FilePath (Resolve-Path '.venv\Scripts\python.exe') -ArgumentList '-m','http.server','8011','--bind','127.0.0.1' -WorkingDirectory (Join-Path $PSScriptRoot 'web') -WindowStyle Hidden | Out-Null
    }
    Write-Host "Beacon is already running. Provider: $($running.provider) | Website: http://localhost:8011"
    if (-not $running.model_available) { Write-Warning 'The server is running, but its model is not ready yet.' }
    if (-not $NoBrowser) { Start-Process 'http://localhost:8011' }
    return
}
if (-not (Test-Path '.venv\Scripts\python.exe')) {
    python -m venv .venv
}
$requirementsHash = (Get-FileHash -LiteralPath 'requirements.txt' -Algorithm SHA256).Hash
$requirementsStamp = '.venv\beacon-requirements.sha256'
if (-not (Test-Path -LiteralPath $requirementsStamp) -or (Get-Content -LiteralPath $requirementsStamp -Raw).Trim() -ne $requirementsHash) {
    & '.\.venv\Scripts\python.exe' -m pip install -q -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
    Set-Content -LiteralPath $requirementsStamp -Value $requirementsHash
}
if (-not (Test-Path '.env')) { Copy-Item '.env.example' '.env'; Write-Host 'Created .env from .env.example. Fill in BEACON_LOGIN_USER/PASSWORD to skip prompts, and DEEPSEEK_API_KEY unless you start with "local".' }
$site = $null
if (-not (Get-NetTCPConnection -LocalPort 8011 -State Listen -ErrorAction SilentlyContinue)) {
    $site = Start-Process -FilePath (Resolve-Path '.venv\Scripts\python.exe') -ArgumentList '-m','http.server','8011','--bind','127.0.0.1' -WorkingDirectory (Join-Path $PSScriptRoot 'web') -WindowStyle Hidden -PassThru
}
$arguments = @('operator_start.py')
if ($NoBrowser) { $arguments += '--no-browser' }
try { & '.\.venv\Scripts\python.exe' @arguments }
finally { if ($site) { Stop-Process -Id $site.Id -ErrorAction SilentlyContinue } }
