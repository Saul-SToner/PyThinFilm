param(
    [string]$Destination = 'C:\Users\L2791\Downloads\PythonFilm-Minimal-20260921'
)

$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$target = [System.IO.Path]::GetFullPath($Destination)
if (Test-Path -LiteralPath $target) { throw "目标文件夹已存在，避免覆盖：$target" }
if ($target.StartsWith($projectRoot + [System.IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
    throw '目标文件夹必须位于原工作区之外。'
}

function Copy-MinimalFiles([string]$Source, [string]$TargetRelative, [string[]]$Extensions) {
    $sourcePath = Join-Path $projectRoot $Source
    if (-not (Test-Path -LiteralPath $sourcePath)) { throw "缺少必须目录：$sourcePath" }
    $allowed = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach ($ext in $Extensions) { [void]$allowed.Add($ext) }
    Get-ChildItem -LiteralPath $sourcePath -File -Recurse | Where-Object {
        $allowed.Contains($_.Extension) -and $_.FullName.Substring($sourcePath.Length) -notmatch '[\\/](__pycache__|node_modules|outputs|tests|report-screenshots)[\\/]'
    } | ForEach-Object {
        $relative = $_.FullName.Substring($sourcePath.Length).TrimStart('\','/')
        $fileTarget = Join-Path (Join-Path $target $TargetRelative) $relative
        $parent = Split-Path -Parent $fileTarget
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
        Copy-Item -LiteralPath $_.FullName -Destination $fileTarget
    }
}

New-Item -ItemType Directory -Path $target | Out-Null
Copy-MinimalFiles 'thinfilm' 'thinfilm' @('.py')
Copy-MinimalFiles 'data\real_nk' 'data\real_nk' @('.csv','.json')
Copy-MinimalFiles 'web3d\public' 'web3d\public' @('.json','.csv')
Copy-MinimalFiles 'Frontend\V3\backend\app' 'Frontend\V3\backend\app' @('.py')
Copy-MinimalFiles 'Frontend\V3\frontend\src' 'Frontend\V3\frontend\src' @('.ts','.tsx','.css','.png','.csv')
Copy-MinimalFiles 'Frontend\V3\frontend\electron' 'Frontend\V3\frontend\electron' @('.ts')
Copy-MinimalFiles 'Frontend\V3\frontend\build' 'Frontend\V3\frontend\build' @('.ico')
Copy-MinimalFiles 'Frontend\V3\frontend\node_modules\tmmcore' 'Frontend\V3\frontend\node_modules\tmmcore' @('.js','.mjs','.cjs','.json','.d.ts','.md')

$fromOptiland = [System.IO.Path]::GetFullPath((Join-Path $projectRoot '..\optiland\optiland'))
if (-not (Test-Path -LiteralPath $fromOptiland)) { throw "缺少 Optiland 源码：$fromOptiland" }
$optilandTarget = Join-Path $target 'optiland\optiland'
Get-ChildItem -LiteralPath $fromOptiland -File -Recurse | Where-Object {
    $_.FullName -notmatch '[\\/](__pycache__|tests|docs|scripts)[\\/]' -and $_.Extension -in @('.py','.csv','.yml','.yaml','.json','.npy','.npz','.png','.ttf','.txt')
} | ForEach-Object {
    $relative = $_.FullName.Substring($fromOptiland.Length).TrimStart('\','/')
    $fileTarget = Join-Path $optilandTarget $relative
    New-Item -ItemType Directory -Path (Split-Path -Parent $fileTarget) -Force | Out-Null
    Copy-Item -LiteralPath $_.FullName -Destination $fileTarget
}

$files = @{
    'Frontend\V3\backend\run.py' = 'Frontend\V3\backend\run.py'
    'Frontend\V3\backend\requirements.txt' = 'Frontend\V3\backend\requirements.txt'
    'Frontend\V3\backend\requirements-specialists.txt' = 'Frontend\V3\backend\requirements-specialists.txt'
    'requirements.txt' = 'requirements.txt'
    'Frontend\V3\frontend\package.json' = 'Frontend\V3\frontend\package.json'
    'Frontend\V3\frontend\package-lock.json' = 'Frontend\V3\frontend\package-lock.json'
    'Frontend\V3\frontend\index.html' = 'Frontend\V3\frontend\index.html'
    'Frontend\V3\frontend\vite.config.ts' = 'Frontend\V3\frontend\vite.config.ts'
    'Frontend\V3\frontend\tsconfig.json' = 'Frontend\V3\frontend\tsconfig.json'
    'Frontend\V3\frontend\tsconfig.electron.json' = 'Frontend\V3\frontend\tsconfig.electron.json'
    'Frontend\V3\frontend\tsconfig.node.json' = 'Frontend\V3\frontend\tsconfig.node.json'
    'Frontend\V3\frontend\postcss.config.js' = 'Frontend\V3\frontend\postcss.config.js'
    'Frontend\V3\frontend\tailwind.config.js' = 'Frontend\V3\frontend\tailwind.config.js'
    'Frontend\V3\frontend\tools\tmmcore_bridge.mjs' = 'Frontend\V3\frontend\tools\tmmcore_bridge.mjs'
    'docs\evidence\rough_absorbing_surface_topic_v1_baseline_spectrum.csv' = 'docs\evidence\rough_absorbing_surface_topic_v1_baseline_spectrum.csv'
    'tools\minimal-package\README.md' = 'README.md'
    'tools\minimal-package\安装依赖.ps1' = '安装依赖.ps1'
    'tools\minimal-package\启动PythonFilm.ps1' = '启动PythonFilm.ps1'
    'tools\minimal-package\requirements-optiland.txt' = 'optiland\requirements-runtime.txt'
}
$experiments = @('optiland_ar_comparison.py','optiland_draft_render.py','optiland_engineering_nsq.py','optiland_poc.py','optiland_real_material_ar_comparison.py','optiland_sampling.py')
foreach ($name in $experiments) { $files["experiments\$name"] = "experiments\$name" }
foreach ($source in $files.Keys) {
    $sourcePath = Join-Path $projectRoot $source
    if (-not (Test-Path -LiteralPath $sourcePath)) { throw "缺少必须文件：$sourcePath" }
    $fileTarget = Join-Path $target $files[$source]
    New-Item -ItemType Directory -Path (Split-Path -Parent $fileTarget) -Force | Out-Null
    Copy-Item -LiteralPath $sourcePath -Destination $fileTarget
}

$zip = "$target.zip"
if (Test-Path -LiteralPath $zip) { throw "目标压缩包已存在，避免覆盖：$zip" }
Compress-Archive -LiteralPath $target -DestinationPath $zip -CompressionLevel Optimal
$count = (Get-ChildItem -LiteralPath $target -File -Recurse | Measure-Object).Count
$size = (Get-Item -LiteralPath $zip).Length
Write-Host "完成：$target，$count 个文件；ZIP $zip（$([math]::Round($size / 1MB, 1)) MB）"
