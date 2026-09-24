$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$studioPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $studioPython)) {
    python -m venv --system-site-packages .venv
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the Python environment.' }
}
& $studioPython -c 'import torch'
if ($LASTEXITCODE -ne 0) {
    & $studioPython -m pip install 'torch==2.6.0' --index-url https://download.pytorch.org/whl/cpu
    if ($LASTEXITCODE -ne 0) { throw 'CPU Torch installation failed.' }
}
& $studioPython -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
& $studioPython setup_models.py
if ($LASTEXITCODE -ne 0) { throw 'Model download failed.' }
Write-Output 'Setup complete. Double-click start.cmd to open the studio.'
