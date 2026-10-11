param(
    [Parameter(Mandatory = $true, Position = 0)][string]$ProjectDir,
    [ValidateSet("metadata", "preview", "deep")][string]$Tier = "preview",
    [switch]$Audio,
    [ValidateSet("pending", "sidecar", "openai_api", "dashscope", "funasr")][string]$TranscriptProvider = "dashscope",
    [switch]$SkipLlm,
    [switch]$Overwrite
)
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = (Resolve-Path (Join-Path $ScriptDir "../..")).Path
$Runtime = Join-Path $RepoRoot "99_System_OpenClaw/.venv-content-os/Scripts/python.exe"
if (-not (Test-Path $Runtime)) {
    $Runtime = if ($env:PYTHON_BIN) { $env:PYTHON_BIN } else { "python" }
}
$argsList = @((Join-Path $ScriptDir "run_analyze_project.py"), $ProjectDir, "--tier", $Tier, "--transcript-provider", $TranscriptProvider)
if ($Audio) { $argsList += "--audio" }
if ($SkipLlm) { $argsList += "--skip-llm" }
if ($Overwrite) { $argsList += "--overwrite" }
& $Runtime @argsList
exit $LASTEXITCODE
