$ErrorActionPreference = 'Stop'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonBin = if ($env:PYTHON_BIN) { $env:PYTHON_BIN } else { 'python' }
& $PythonBin (Join-Path $ScriptDir 'setup_edit_tools.py') @args
exit $LASTEXITCODE
