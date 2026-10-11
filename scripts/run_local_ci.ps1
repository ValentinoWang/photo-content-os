[CmdletBinding()]
param(
  [string]$ObsidianRoot = $env:OBSIDIAN_ROOT
)
$ErrorActionPreference = 'Stop'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepositoryRoot = (Resolve-Path (Join-Path $ScriptDir '..')).Path
$Python = Join-Path $RepositoryRoot '.venv\Scripts\python.exe'
if (-not (Test-Path $Python -PathType Leaf)) {
  throw "Fixed development runtime is missing. Run setup_dev_environment.ps1 first: $Python"
}
$TempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("photo-content-os-ci-" + [guid]::NewGuid())
New-Item -ItemType Directory -Path $TempRoot | Out-Null
try {
  Set-Location $RepositoryRoot
  Write-Host '== Runtime contract =='
  & $Python (Join-Path $ScriptDir 'check_runtime_contract.py')
  if ($LASTEXITCODE -ne 0) { throw 'Runtime contract failed.' }

  Write-Host '== Doctor (offline-tolerant) =='
  & $Python (Join-Path $ScriptDir 'doctor.py') --allow-offline
  if ($LASTEXITCODE -ne 0) { throw 'Doctor failed.' }

  Write-Host '== Unit tests =='
  & $Python -m unittest discover -s tests
  if ($LASTEXITCODE -ne 0) { throw 'Unit tests failed.' }

  Write-Host '== Outline contract =='
  $OutlineArgs = @((Join-Path $ScriptDir 'check_outline_contract.py'), '.')
  if (-not $ObsidianRoot -or -not (Test-Path $ObsidianRoot -PathType Container)) { $OutlineArgs += '--skip-obsidian-sync' }
  & $Python @OutlineArgs
  if ($LASTEXITCODE -ne 0) { throw 'Outline contract failed.' }

  & $Python (Join-Path $ScriptDir 'validate_review_capability_registry.py')
  if ($LASTEXITCODE -ne 0) { throw 'Review capability registry failed.' }
  & $Python (Join-Path $ScriptDir 'check_repository_safety.py')
  if ($LASTEXITCODE -ne 0) { throw 'Repository safety check failed.' }

  foreach ($Entry in @('validate_content_os_task.py','validate_jianying_draft.py','transcribe_audio.py','render_preview.py','doctor.py','launch_studio.py','openclaw_media_agent.py')) {
    & $Python (Join-Path $ScriptDir $Entry) --help | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Entry point failed: $Entry" }
  }

  & $Python (Join-Path $ScriptDir 'create_demo_project.py') --workspace-root $TempRoot --project-name local_ci_demo
  if ($LASTEXITCODE -ne 0) { throw 'Synthetic trial failed.' }
  Write-Host 'Local CI passed.'
} finally {
  if (Test-Path $TempRoot) { Remove-Item -Recurse -Force $TempRoot }
}
