# Install Qualoop tool-agnostic AI contract into a business project (one-time).
#
# Works for any AI tool: Codex CLI, Cursor, Claude Code, Gemini CLI, Aider, Amp, etc.
# Does:
#   1) Add qualoop as a git submodule at tools/qualoop (if -Submodule)
#   2) Copy templates/AGENTS.md to <project>/AGENTS.md
#      The North Star block is filled from ONE of:
#        -NorthStar "string"   : a single-line goal
#        -NorthStarFile <path> : embed the whole file as the North Star
#        -NorthStarFile <path> -LinkOnly : just link to it, do not embed
#      If none is given, the placeholder remains.
#   3) Copy templates/CLAUDE.md, templates/GEMINI.md (one-line includes)
#   4) Write <project>/qualoop.json (shared by all tools)
#   5) Optionally install Cursor legacy rule with -WithCursor
#
# Examples:
#   .\scripts\install-agents.ps1 -TargetProject . -NorthStar "make X reliable in Y"
#   .\scripts\install-agents.ps1 -TargetProject . -NorthStarFile docs\GOALS.md
#   .\scripts\install-agents.ps1 -TargetProject . -NorthStarFile docs\GOALS.md -LinkOnly

param(
    [Parameter(Mandatory = $true)]
    [string] $TargetProject,

    [string] $NorthStar = "",

    [string] $NorthStarFile = "",

    [switch] $LinkOnly,

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

if ($NorthStar -ne "" -and $NorthStarFile -ne "") {
    throw "Pass only ONE of -NorthStar or -NorthStarFile, not both."
}

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

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$agentsSrc = Join-Path $repoRoot "templates\AGENTS.md"
$agentsDst = Join-Path $target "AGENTS.md"
$agentsBody = [System.IO.File]::ReadAllText($agentsSrc, $utf8NoBom)

function Build-Header-FromString([string]$text) {
    return "# North Star (from installer)`r`n`r`n> Source: provided as a string at install time.`r`n`r`n- $text`r`n`r`n---`r`n`r`n"
}

function Build-Header-FromFile-Embed([string]$relPath, [string]$content) {
    $h  = "# North Star (from installer)`r`n`r`n"
    $h += "> Source: embedded copy of ``$relPath`` taken at install time.`r`n"
    $h += "> If the source file changes, re-run the installer (or edit this section in sync).`r`n`r`n"
    $h += "<!-- BEGIN: embedded from $relPath -->`r`n"
    $h += $content
    if (-not $content.EndsWith("`n")) { $h += "`r`n" }
    $h += "<!-- END: embedded from $relPath -->`r`n`r`n"
    $h += "---`r`n`r`n"
    return $h
}

function Build-Header-FromFile-Link([string]$relPath) {
    $h  = "# North Star (from installer)`r`n`r`n"
    $h += "> Source: see [``$relPath``](./$relPath) (single source of truth, not embedded).`r`n"
    $h += "> AI agents MUST read that file before producing any opinion this round.`r`n`r`n"
    $h += "@$relPath`r`n`r`n"
    $h += "---`r`n`r`n"
    return $h
}

$header = ""
if ($NorthStar -ne "") {
    $header = Build-Header-FromString $NorthStar
}
elseif ($NorthStarFile -ne "") {
    if (-not (Test-Path $NorthStarFile)) {
        throw "NorthStarFile does not exist: $NorthStarFile"
    }
    $nsAbs = (Resolve-Path $NorthStarFile).Path
    $nsRel = ""
    if ($nsAbs.StartsWith($target, [System.StringComparison]::OrdinalIgnoreCase)) {
        $nsRel = $nsAbs.Substring($target.Length).TrimStart('\','/') -replace '\\','/'
    } else {
        $destPath = Join-Path $target "NORTH_STAR.md"
        Copy-Item -Force $nsAbs $destPath
        $nsRel = "NORTH_STAR.md"
        Write-Host "North Star source is outside the project; copied to: NORTH_STAR.md"
    }

    if ($LinkOnly) {
        $header = Build-Header-FromFile-Link $nsRel
    } else {
        $nsContent = [System.IO.File]::ReadAllText($nsAbs, $utf8NoBom)
        $header = Build-Header-FromFile-Embed $nsRel $nsContent
    }
}

if ($header -ne "") {
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
