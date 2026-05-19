# Install Qualoop tool-agnostic AI contract into a business project (one-time).
#
# Works for any AI tool: Codex CLI, Cursor, Claude Code, Gemini CLI, Aider, Amp, etc.
# Does:
#   1) Add qualoop as a git submodule at tools/qualoop (if -Submodule)
#   2) Copy templates/AGENTS.md to <project>/AGENTS.md
#      (optionally prepends a "North Star (from installer)" block if -NorthStar is given)
#   3) Copy templates/CLAUDE.md, templates/GEMINI.md (one-line includes)
#   4) Write <project>/qualoop.json (shared by all tools)
#   5) Optionally install Cursor legacy rule with -WithCursor
#
# Usage:
#   .\scripts\install-agents.ps1 -TargetProject "D:\your-app" `
#       [-NorthStar "your one-line goal"] `
#       [-Submodule] `
#       [-WithCursor]

param(
    [Parameter(Mandatory = $true)]
    [string] $TargetProject,

    [string] $NorthStar = "",

    [string] $MethodologyRepo = "https://github.com/sinogenomics/qualoop.git",

    [string] $MethodologyRelPath = "tools/qualoop",

    [switch] $Submodule,

    [switch] $WithCursor
)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $here

if (-not (Test-Path $TargetProject)) {
    throw "TargetProject does not exist: $TargetProject"
}
$target = (Resolve-Path $TargetProject).Path

if ($Submodule) {
    if (-not (Test-Path (Join-Path $target ".git"))) {
        throw "Target is not a git repository: $target. Run 'git init' first or omit -Submodule."
    }
    $subPath = Join-Path $target $MethodologyRelPath
    if (Test-Path $subPath) {
        Write-Host "submodule path already exists, skipping: $subPath"
    } else {
        Push-Location $target
        try {
            git submodule add $MethodologyRepo $MethodologyRelPath
            git submodule update --init --recursive
        } finally {
            Pop-Location
        }
    }
}

$agentsSrc = Join-Path $repoRoot "templates\AGENTS.md"
$agentsDst = Join-Path $target "AGENTS.md"
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$agentsBody = [System.IO.File]::ReadAllText($agentsSrc, $utf8NoBom)
if ($NorthStar -ne "") {
    $header = "# North Star (from installer)`r`n`r`n> The following North Star was provided when this AGENTS.md was installed. It is the project's source of truth; replace it only when the project goal genuinely changes.`r`n`r`n- $NorthStar`r`n`r`n---`r`n`r`n"
    $agentsBody = $header + $agentsBody
}
[System.IO.File]::WriteAllText($agentsDst, $agentsBody, $utf8NoBom)

Copy-Item -Force (Join-Path $repoRoot "templates\CLAUDE.md") (Join-Path $target "CLAUDE.md")
Copy-Item -Force (Join-Path $repoRoot "templates\GEMINI.md") (Join-Path $target "GEMINI.md")

$jsonPath = Join-Path $target "qualoop.json"
if (-not (Test-Path $jsonPath)) {
    @{
        methodologyRoot      = $MethodologyRelPath
        minValueScore        = 60
        minQualifiedPerRound = 1
        maturity             = "L1"
    } | ConvertTo-Json | Set-Content -Encoding UTF8 -Path $jsonPath
}

if ($WithCursor) {
    $methodologyAbs = Join-Path $target $MethodologyRelPath
    & (Join-Path $here "install-cursor-rule.ps1") -TargetProject $target -MethodologyRoot $methodologyAbs
}

Write-Host ""
Write-Host "OK: Qualoop AI contract installed into:"
Write-Host "  $target"
Write-Host "Files written:"
Write-Host "  - AGENTS.md       (authoritative contract for all AI tools)"
Write-Host "  - CLAUDE.md       (one-line include -> AGENTS.md)"
Write-Host "  - GEMINI.md       (one-line include -> AGENTS.md)"
Write-Host "  - qualoop.json    (shared config)"
if ($WithCursor) {
    Write-Host "  - .cursor/rules/qualoop.mdc (Cursor legacy rule)"
}
Write-Host ""
Write-Host "Next: open the project in your AI tool of choice, then say:"
Write-Host "  Qualoop init   (or in Chinese: Qualoop 初始化)"
Write-Host "  (provide a North Star if AGENTS.md still shows the placeholder)"
