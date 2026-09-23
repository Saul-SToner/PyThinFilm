#requires -Version 7
param(
    [Parameter(Mandatory = $true)][string]$ResourcesPath,
    [string]$BackendPath
)

$ErrorActionPreference = 'Stop'
$resources = (Resolve-Path -LiteralPath $ResourcesPath).Path
$backend = if ($BackendPath) { (Resolve-Path -LiteralPath $BackendPath).Path } else { Join-Path $resources 'backend' }
$electron = Join-Path (Split-Path $resources -Parent) 'PythonFilm.exe'
if (Get-NetTCPConnection -LocalPort 8122 -State Listen -ErrorAction SilentlyContinue) {
    throw 'Port 8122 is already in use; stop the existing backend before this check.'
}

$env:THINFILM_APP_ROOT = $resources
$env:THINFILM_OUTPUT_DIR = Join-Path $env:APPDATA 'thinfilm-desktop-app\outputs'
$env:THINFILM_MATERIALS_METADATA_CSV = Join-Path $resources 'materials\app_materials_metadata.csv'
$env:THINFILM_NODE_EXECUTABLE = $electron
$env:THINFILM_TMMCORE_BRIDGE = Join-Path $resources 'tmmcore\tmmcore_bridge.mjs'
$env:THINFILM_PYTHINFILM_ROOT = $backend
$env:THINFILM_OPTILAND_ROOT = Join-Path $backend 'optiland'
$env:THINFILM_OPTILAND_PYTHON = Join-Path $backend 'thinfilm-backend.exe'

$process = Start-Process -FilePath (Join-Path $backend 'thinfilm-backend.exe') -WorkingDirectory $backend -WindowStyle Hidden -PassThru
$failures = @()
try {
    $deadline = (Get-Date).AddSeconds(120)
    do {
        try {
            $health = Invoke-RestMethod 'http://127.0.0.1:8122/health' -TimeoutSec 2
            if ($health.status -eq 'ok') { break }
        } catch { Start-Sleep -Milliseconds 500 }
        $process.Refresh()
        if ($process.HasExited) { throw "Backend exited during startup: $($process.ExitCode)" }
    } while ((Get-Date) -lt $deadline)
    if ($health.status -ne 'ok') { throw 'Backend did not become healthy within 120 seconds.' }

    $rcwa = Invoke-WebRequest 'http://127.0.0.1:8122/api/specialist/rcwa' -Method Post -ContentType 'application/json' -SkipHttpErrorCheck -TimeoutSec 90 -Body '{"wavelength_start_um":0.50,"wavelength_stop_um":0.52,"wavelength_points":2,"period_um":0.7,"thickness_um":0.2,"n_grating":2.0,"n_void":1.0,"harmonics":3}'
    if ($rcwa.StatusCode -ne 200 -or ($rcwa.Content | ConvertFrom-Json).R.Count -ne 2) {
        $failures += "EMT/RCWA failed: HTTP $($rcwa.StatusCode), $($rcwa.Content)"
    } else {
        Write-Output 'EMT/RCWA: 200, 2 points'
    }

    $tammCases = @(
        'tamm_interface_priority', 'tamm_phase_bundle', 'tamm_phase_candidates',
        'tamm_phase_focus', 'tamm_reflection_phase_screen',
        'tamm_interface_window_bundle', 'tamm_interface_window_scan'
    )
    foreach ($caseId in $tammCases) {
        try {
            $body = @{ case_id = $caseId; wavelength_start_nm = 500; wavelength_stop_nm = 510; wavelength_points = 2 } | ConvertTo-Json
            $tamm = Invoke-WebRequest 'http://127.0.0.1:8122/api/specialist/generaltmm' -Method Post -ContentType 'application/json' -SkipHttpErrorCheck -TimeoutSec 120 -Body $body
            if ($tamm.StatusCode -ne 200 -or ($tamm.Content | ConvertFrom-Json).R.Count -ne 2) {
                $failures += "Tamm $caseId failed: HTTP $($tamm.StatusCode), $($tamm.Content)"
            } else {
                Write-Output "Tamm $caseId : 200"
            }
        } catch {
            $failures += "Tamm $caseId transport failed: $($_.Exception.Message)"
        }
    }

    try {
        $detail = Invoke-WebRequest 'http://127.0.0.1:8122/api/case-library/tamm_phase_bundle' -SkipHttpErrorCheck -TimeoutSec 20
        if ($detail.StatusCode -ne 200) {
            $failures += "Research detail failed: HTTP $($detail.StatusCode)"
        } else {
            Write-Output 'Research detail after calculations: 200'
        }
    } catch {
        $failures += "Research detail transport failed: $($_.Exception.Message)"
    }
    try {
        $pdrc = Invoke-WebRequest 'http://127.0.0.1:8122/api/specialist/wptherml' -Method Post -ContentType 'application/json' -SkipHttpErrorCheck -TimeoutSec 120 -Body '{"case_id":"pdrc_cooling_bundle","wavelength_start_nm":300,"wavelength_stop_nm":13000,"wavelength_points":11,"temperature_k":300}'
        if ($pdrc.StatusCode -ne 200 -or ($pdrc.Content | ConvertFrom-Json).A.Count -ne 11) {
            $failures += "PDRC/WPTherml failed: HTTP $($pdrc.StatusCode), $($pdrc.Content)"
        } else {
            Write-Output 'PDRC/WPTherml: 200, 11 points'
        }
    } catch {
        $failures += "PDRC/WPTherml transport failed: $($_.Exception.Message)"
    }
    if ($failures.Count) { throw ($failures -join '; ') }
} finally {
    $process.Refresh()
    if (-not $process.HasExited) { Stop-Process -Id $process.Id -Force }
}
