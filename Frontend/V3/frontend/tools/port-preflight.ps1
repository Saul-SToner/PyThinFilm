param([int]$Port = 8122)

$ErrorActionPreference = 'Stop'
$connections = @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
$owners = @($connections | Select-Object -ExpandProperty OwningProcess -Unique)
foreach ($ownerPid in $owners) {
    $owner = Get-CimInstance Win32_Process -Filter "ProcessId=$ownerPid"
    if (-not $owner) { continue }
    $isBackend = $owner.ExecutablePath -match '[\\/]backend[\\/]thinfilm-backend\.exe$'
    $isDevelopment = $owner.Name -eq 'python.exe' -and
        $owner.ExecutablePath -match '[\\/]PyThinFilm[\\/]Frontend[\\/]V3[\\/]\.venv[\\/]Scripts[\\/]python\.exe$' -and
        $owner.CommandLine -match 'uvicorn app\.main:app'
    if (-not ($isBackend -or $isDevelopment)) {
        throw "Port $Port is used by another application (PID $ownerPid, $($owner.Name)). PythonFilm will not close it."
    }
    $parent = Get-CimInstance Win32_Process -Filter "ProcessId=$($owner.ParentProcessId)"
    if ($parent -and $parent.Name -in @('PythonFilm.exe', '薄膜光学仿真.exe')) {
        Stop-Process -Id $parent.ProcessId -Force -ErrorAction SilentlyContinue
    }
    if ($isDevelopment -and $parent -and $parent.Name -eq 'python.exe' -and $parent.CommandLine -match 'uvicorn app\.main:app') {
        Stop-Process -Id $parent.ProcessId -Force -ErrorAction SilentlyContinue
    }
    Stop-Process -Id $ownerPid -Force -ErrorAction SilentlyContinue
}

$deadline = (Get-Date).AddSeconds(8)
while ((Get-Date) -lt $deadline) {
    if (-not (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)) { exit 0 }
    Start-Sleep -Milliseconds 200
}
throw "Port $Port is still occupied after closing the previous PythonFilm backend."
