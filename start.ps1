param([switch]$Login,[switch]$OpenAI)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (-not (Test-Path '.venv\Scripts\python.exe')) {
    python -m venv .venv
}
& '.\.venv\Scripts\python.exe' -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
if (-not (Test-Path '.env')) { Copy-Item '.env.example' '.env' }
if ($OpenAI) {
    & '.\.venv\Scripts\python.exe' operator_start.py --openai
} elseif ($Login) {
    & '.\.venv\Scripts\python.exe' operator_start.py
} else {
    & '.\.venv\Scripts\python.exe' -m uvicorn app.main:app --host 127.0.0.1 --port 8010 --no-access-log
}
