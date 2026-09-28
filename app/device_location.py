"""Local operator-only Windows device location. Never use on a remote public host.

Returns a real OS reading, not invented coordinates; coordinates stay in memory.
Requires Windows Location Services and the operator's prior location permission.
"""
import asyncio
import json
import sys

_cached=None
_lookup=None

def known_location():return _cached

async def cached_windows_location():
    """One real OS reading per process; concurrent callers share the lookup."""
    global _cached,_lookup
    if _cached:return _cached
    if _lookup is None or _lookup.done():_lookup=asyncio.ensure_future(actual_windows_location())
    _cached=await asyncio.shield(_lookup)
    return _cached

async def actual_windows_location():
    if sys.platform!='win32':return None
    command=r'''
Add-Type -AssemblyName System.Device
$watcher = New-Object System.Device.Location.GeoCoordinateWatcher
try {
  $watcher.Start($false)
  $deadline = [DateTime]::UtcNow.AddSeconds(20)
  while ($watcher.Status -ne 'Ready' -and [DateTime]::UtcNow -lt $deadline -and $watcher.Permission -ne 'Denied') { Start-Sleep -Milliseconds 200 }
  $location = $watcher.Position.Location
  if (-not $location.IsUnknown -and $watcher.Status -eq 'Ready') {
    @{latitude=$location.Latitude;longitude=$location.Longitude;accuracy=$location.HorizontalAccuracy} | ConvertTo-Json -Compress
  } else { '{}' }
} finally { $watcher.Stop(); $watcher.Dispose() }
'''
    process=await asyncio.create_subprocess_exec('C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe','-NoProfile','-NonInteractive','-Command',command,
        stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE,creationflags=0x08000000)
    try:
        out,_=await asyncio.wait_for(process.communicate(),25)
        values=json.loads(out.decode('utf-8-sig').strip() or '{}')
        if not all(k in values for k in ['latitude','longitude','accuracy']):return None
        if not(-90<=values['latitude']<=90 and -180<=values['longitude']<=180):return None
        return values
    except (ValueError,asyncio.TimeoutError):
        if process.returncode is None:process.kill();await process.wait()
        return None
