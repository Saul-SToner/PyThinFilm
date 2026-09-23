$ErrorActionPreference = 'Stop'
$packageRoot = $PSScriptRoot
$venvPython = Join-Path $packageRoot 'Frontend\V3\.venv\Scripts\python.exe'
$frontendRoot = Join-Path $packageRoot 'Frontend\V3\frontend'

if (-not (Test-Path -LiteralPath $venvPython)) {
    py -3 -m venv (Join-Path $packageRoot 'Frontend\V3\.venv')
    if ($LASTEXITCODE -ne 0) { throw 'Could not create Python environment. Python 3.11 or newer is required.' }
}
& $venvPython -m pip install -r (Join-Path $packageRoot 'Frontend\V3\backend\requirements.txt')
if ($LASTEXITCODE -ne 0) { throw 'Backend dependency installation failed.' }
& $venvPython -m pip install -r (Join-Path $packageRoot 'Frontend\V3\backend\requirements-specialists.txt')
if ($LASTEXITCODE -ne 0) { throw 'Specialist solver dependency installation failed.' }
& $venvPython -m pip install -r (Join-Path $packageRoot 'optiland\requirements-runtime.txt')
if ($LASTEXITCODE -ne 0) { throw 'Optiland dependency installation failed.' }
Push-Location $frontendRoot
try {
    npm ci
    if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency installation failed.' }
} finally {
    Pop-Location
}
Write-Host 'Dependencies installed. Run the launch script to open PythonFilm.'
