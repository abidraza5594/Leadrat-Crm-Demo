# Starts everything: the Beacon backend (port 8010, this window) and the test website (port 8011, background).
# Settings, API key and CRM login come from .env. -OpenAI / -Ollama override PLANNER_PROVIDER; -NoBrowser skips opening the site.
param([switch]$OpenAI,[switch]$Ollama,[switch]$Login,[switch]$NoBrowser)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (-not (Test-Path '.venv\Scripts\python.exe')) {
    python -m venv .venv
}
& '.\.venv\Scripts\python.exe' -m pip install -q -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
if (-not (Test-Path '.env')) { Copy-Item '.env.example' '.env'; Write-Host 'Created .env from .env.example. Fill in OPENAI_API_KEY and BEACON_LOGIN_USER/PASSWORD to skip prompts.' }
$site = $null
if (-not (Get-NetTCPConnection -LocalPort 8011 -State Listen -ErrorAction SilentlyContinue)) {
    $site = Start-Process -FilePath (Resolve-Path '.venv\Scripts\python.exe') -ArgumentList '-m','http.server','8011','--bind','127.0.0.1' -WorkingDirectory (Join-Path $PSScriptRoot 'web') -WindowStyle Hidden -PassThru
}
$arguments = @('operator_start.py')
if ($OpenAI) { $arguments += '--openai' }
# -Login is the older name for the local Ollama planner.
if ($Ollama -or $Login) { $arguments += '--ollama' }
if ($NoBrowser) { $arguments += '--no-browser' }
try { & '.\.venv\Scripts\python.exe' @arguments }
finally { if ($site) { Stop-Process -Id $site.Id -ErrorAction SilentlyContinue } }
