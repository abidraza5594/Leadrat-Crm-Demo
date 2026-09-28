# Operator-only: sign the hidden demo browser in to the test CRM once (opens a visible Chrome window).
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (-not (Test-Path '.venv\Scripts\python.exe')) { throw 'Run ./start.ps1 once first to install dependencies.' }
& '.\.venv\Scripts\python.exe' operator_login.py
