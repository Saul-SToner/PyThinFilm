param([string]$ArchivePath)

$ErrorActionPreference = 'Stop'
$project = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$frontend = Join-Path $project 'Frontend\V3\frontend'
$destination = Join-Path $frontend 'generaltmm-runtime'
$venv = Join-Path $project 'Frontend\V3\.venv\Lib\site-packages'
$manifest = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'release-dependencies.json') -Raw | ConvertFrom-Json
$temporary = Join-Path ([IO.Path]::GetTempPath()) ("pythonfilm-embed-" + [guid]::NewGuid().ToString('N'))

if (-not $destination.StartsWith($frontend + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Runtime destination must be inside the frontend build directory.'
}
if (Test-Path -LiteralPath $destination) {
    Remove-Item -LiteralPath $destination -Recurse -Force
}
New-Item -ItemType Directory -Path $temporary | Out-Null
try {
    $archive = if ($ArchivePath) { (Resolve-Path -LiteralPath $ArchivePath).Path } else { Join-Path $temporary 'python-embed.zip' }
    if (-not $ArchivePath) { Invoke-WebRequest -Uri $manifest.embedded_python.url -OutFile $archive }
    $hash = (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash
    if ($hash -ne $manifest.embedded_python.sha256) { throw "Embedded Python archive checksum mismatch: $hash" }
    Expand-Archive -LiteralPath $archive -DestinationPath $destination

    foreach ($package in @('numpy', 'numpy.libs', 'GeneralTmm', 'eigency')) {
        $source = Join-Path $venv $package
        if (-not (Test-Path -LiteralPath $source)) { throw "Missing runtime dependency: $source" }
        Copy-Item -LiteralPath $source -Destination $destination -Recurse
    }
    foreach ($pattern in @('numpy-*.dist-info', 'generaltmm-*.dist-info', 'eigency-*.dist-info')) {
        $matches = @(Get-ChildItem -LiteralPath $venv -Directory -Filter $pattern)
        if ($matches.Count -ne 1) { throw "Expected one distribution metadata directory matching $pattern" }
        Copy-Item -LiteralPath $matches[0].FullName -Destination $destination -Recurse
    }

    $solver = Join-Path $destination 'solver'
    New-Item -ItemType Directory -Path $solver | Out-Null
    foreach ($name in @('__init__.py', 'registry.py', 'generaltmm_adapter.py')) {
        Copy-Item -LiteralPath (Join-Path $project "thinfilm\solvers\$name") -Destination $solver
    }
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'generaltmm_worker.py') -Destination (Join-Path $destination 'worker.py')
    $python = Join-Path $destination 'python.exe'
    & $python -c 'import numpy as np; from GeneralTmm import Material,Tmm; s=Tmm(wl=550e-9,beta=0); s.AddIsotropicLayer(float("inf"),Material.Static(1)); s.AddIsotropicLayer(100e-9,Material.Static(1.5)); s.AddIsotropicLayer(float("inf"),Material.Static(1)); assert float(s.Sweep("beta",np.asarray([0.0]))["R11"]) >= 0'
    if ($LASTEXITCODE -ne 0) { throw "Embedded GeneralTmm runtime failed: exit $LASTEXITCODE" }
    Write-Host "Verified bundled GeneralTmm runtime: $destination"
} finally {
    if (Test-Path -LiteralPath $temporary) { Remove-Item -LiteralPath $temporary -Recurse -Force }
}
