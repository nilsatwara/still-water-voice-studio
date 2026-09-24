$ErrorActionPreference = 'Stop'
$studioRoot = $PSScriptRoot
$studioUrl = 'http://127.0.0.1:8766'
try {
    $existing = Invoke-RestMethod "$studioUrl/api/state" -TimeoutSec 2
    if ($null -ne $existing.jobs) { Start-Process $studioUrl; exit }
} catch {}
$studioPython = Join-Path $studioRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $studioPython)) { throw 'The studio environment is missing. Run setup.ps1 first.' }
& $studioPython -c 'import edge_tts, aiohttp, kokoro, imageio_ffmpeg'
if ($LASTEXITCODE -ne 0) { throw 'Install dependencies first: python -m pip install -r requirements.txt' }
Start-Process -FilePath $studioPython -ArgumentList @('"' + (Join-Path $studioRoot 'server.py') + '"') -WorkingDirectory $studioRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $studioRoot 'server.log') -RedirectStandardError (Join-Path $studioRoot 'server-error.log')
for ($attempt = 0; $attempt -lt 45; $attempt++) {
    Start-Sleep -Seconds 1
    try {
        $ready = Invoke-RestMethod "$studioUrl/api/state" -TimeoutSec 2
        Start-Process $studioUrl
        exit
    } catch {}
}
throw 'The studio could not start. See server-error.log in this folder.'
