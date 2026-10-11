[CmdletBinding()]
param(
  [string]$PythonBin = $env:PYTHON_BIN
)
$ErrorActionPreference = 'Stop'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepositoryRoot = (Resolve-Path (Join-Path $ScriptDir '..\..')).Path
$RuntimeDir = Join-Path $RepositoryRoot '99_System_OpenClaw\.venv-content-os'
$RuntimePython = Join-Path $RuntimeDir 'Scripts\python.exe'
$Requirements = Join-Path $RepositoryRoot 'requirements-dev.txt'
if (-not $PythonBin) { $PythonBin = 'py' }

function Invoke-BootstrapPython([string[]]$Arguments) {
  if ($PythonBin -eq 'py') { & py -3.11 @Arguments } else { & $PythonBin @Arguments }
  if ($LASTEXITCODE -ne 0) { throw "Python command failed: $PythonBin $Arguments" }
}

if (-not (Test-Path $Requirements -PathType Leaf)) { throw "Development requirements are missing: $Requirements" }
if (Test-Path $RuntimeDir) {
  if (-not (Test-Path $RuntimePython -PathType Leaf)) {
    throw "Existing fixed runtime is malformed; refusing to overwrite it: $RuntimeDir"
  }
} else {
  Write-Host '== Create fixed development runtime =='
  Invoke-BootstrapPython @('-c', 'import sys; assert sys.version_info >= (3, 11), sys.version')
  Invoke-BootstrapPython @('-m', 'venv', $RuntimeDir)
}

& $RuntimePython -c "import sys; assert sys.version_info >= (3, 11), sys.version"
if ($LASTEXITCODE -ne 0) { throw 'Python 3.11 or newer is required.' }
Write-Host '== Install pinned development dependencies =='
& $RuntimePython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw 'pip upgrade failed.' }
& $RuntimePython -m pip install --upgrade --requirement $Requirements
if ($LASTEXITCODE -ne 0) { throw 'dependency installation failed.' }

Write-Host '== Verify fixed development runtime =='
& $RuntimePython (Join-Path $ScriptDir 'check_runtime_contract.py')
if ($LASTEXITCODE -ne 0) { throw 'Runtime contract failed.' }
& $RuntimePython (Join-Path $ScriptDir '43_content_os_doctor.py') --allow-offline
if ($LASTEXITCODE -ne 0) { throw 'Content OS doctor failed.' }
Write-Host "Development environment is ready: $RuntimeDir"
