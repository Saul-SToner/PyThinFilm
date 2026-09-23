$ErrorActionPreference = 'Stop'
$packageRoot = $PSScriptRoot
$venvPython = Join-Path $packageRoot 'Frontend\V3\.venv\Scripts\python.exe'
$frontendRoot = Join-Path $packageRoot 'Frontend\V3\frontend'
if (-not (Test-Path -LiteralPath $venvPython) -or -not (Test-Path -LiteralPath (Join-Path $frontendRoot 'node_modules\electron'))) {
    throw 'Dependencies are missing. Run the installation script in this folder first.'
}
$env:THINFILM_OPTILAND_ROOT = Join-Path $packageRoot 'optiland'
$env:THINFILM_OPTILAND_PYTHON = $venvPython
Push-Location $frontendRoot
try {
    npm run dev
} finally {
    Pop-Location
}
