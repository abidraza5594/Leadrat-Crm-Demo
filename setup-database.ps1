# Dedicated Beacon database. Never resets Docker or deletes an existing volume.
$ErrorActionPreference='Stop'
Set-Location $PSScriptRoot
docker info --format '{{.ServerVersion}}'
if($LASTEXITCODE -ne 0){throw 'Docker engine is unavailable. Start Docker Desktop and retry. Existing data is unchanged.'}
New-Item -ItemType Directory -Force -Path '.state' | Out-Null
$secretFile=Join-Path $PSScriptRoot '.state\database.env'
if(-not (Test-Path -LiteralPath $secretFile)){
    $bytes=New-Object byte[] 32
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    $password=[Convert]::ToBase64String($bytes).Replace('+','a').Replace('/','b').Replace('=','')
    Set-Content -LiteralPath $secretFile -Value "BEACON_DB_PASSWORD=$password"
}
docker compose --env-file $secretFile -p beacon-context up -d --wait
if($LASTEXITCODE -ne 0){throw 'Database did not become healthy. Beacon configuration was not changed.'}
$password=(Get-Content -LiteralPath $secretFile -Raw).Trim().Substring('BEACON_DB_PASSWORD='.Length)
$settingsPath=Join-Path $PSScriptRoot '.env'
$settings=Get-Content -LiteralPath $settingsPath -Raw
if($settings -notmatch '(?m)^BEACON_DATABASE_URL='){
    Add-Content -LiteralPath $settingsPath -Value "`nBEACON_DATABASE_URL=postgresql://beacon:${password}@127.0.0.1:55432/beacon"
}
Write-Host 'Beacon PostgreSQL is ready on localhost:55432. Restart Beacon to connect. Existing SQLite records are not automatically migrated.'
