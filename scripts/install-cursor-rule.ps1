# Install Qualoop Cursor rule into a business project (one-time).
# Usage:
#   .\install-cursor-rule.ps1 -TargetProject "D:\your-app" -MethodologyRoot "e:\path\to\qualoop"

param(
    [Parameter(Mandatory = $true)]
    [string] $TargetProject,
    [Parameter(Mandatory = $true)]
    [string] $MethodologyRoot
)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $here

$target = Resolve-Path $TargetProject
$methodology = Resolve-Path $MethodologyRoot

$cursorDir = Join-Path $target ".cursor"
$rulesDir = Join-Path $cursorDir "rules"
New-Item -ItemType Directory -Force -Path $rulesDir | Out-Null

$ruleSrc = Join-Path $repoRoot "templates\qualoop.cursor.rule.mdc"
$ruleDst = Join-Path $rulesDir "qualoop.mdc"
Copy-Item -Force $ruleSrc $ruleDst

$jsonPath = Join-Path $cursorDir "qualoop.json"
$methodologyJson = ($methodology.Path -replace '\\', '/')
@{
    methodologyRoot = $methodologyJson
    minValueScore = 60
    minQualifiedPerRound = 1
    maturity = "L1"
} | ConvertTo-Json | Set-Content -Encoding UTF8 $jsonPath

Write-Host "OK: installed"
Write-Host "  rule: $ruleDst"
Write-Host "  config: $jsonPath"
Write-Host ""
Write-Host "Next: open $target in Cursor, add methodology folder to workspace, then say: Qualoop 初始化"
Write-Host "Cross-PC: prefer git submodule at tools/qualoop + commit .cursor/; see references/PROFESSIONAL_SETUP.md"
