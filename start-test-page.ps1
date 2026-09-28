Set-Location (Join-Path $PSScriptRoot 'web')
& '..\.venv\Scripts\python.exe' -m http.server 8011 --bind 127.0.0.1
