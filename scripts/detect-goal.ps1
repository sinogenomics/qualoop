# detect-goal.ps1 — Help an AI agent self-check whether the user's
# message contains a Qualoop project goal (North Star), and in which form.
#
# Usage:
#   .\scripts\detect-goal.ps1 -Message "<the user's full message verbatim>"
#
# Output: key=value lines (see detect-goal.sh for full spec).
# Detection rules mirror AI-START-HERE.md STEP 0.

param(
    [Parameter(Mandatory = $true)]
    [string] $Message
)

$ErrorActionPreference = 'Stop'

# 1) Strip Qualoop URLs
$stripped = $Message
$stripped = [regex]::Replace($stripped, 'https?://(raw\.)?github(usercontent)?\.com/[A-Za-z0-9_./-]*qualoop[A-Za-z0-9_./-]*', '', 'IgnoreCase')
$stripped = [regex]::Replace($stripped, 'https?://github\.com/sinogenomics/qualoop(\.git)?', '', 'IgnoreCase')

# 2) Path-like candidates
$exts = '(\.md|\.txt|\.rst|\.pdf|\.docx|\.json|\.ya?ml)'
$pathTokenRe = "[A-Za-z0-9_./\\:-]+($exts|/[A-Za-z0-9_./\\-]+)"
$matches = [regex]::Matches($stripped, $pathTokenRe)
$candidates = @()
foreach ($m in $matches) {
    $v = $m.Value.Trim()
    if ($v -match '^(https?:|git@)') { continue }
    if (-not ($candidates -contains $v)) { $candidates += $v }
}

function Score-Candidate([string]$p) {
    $base = Split-Path -Leaf $p
    $s = 0
    if ($base -match '(?i)GOAL|OBJECTIVE|REQUIREMENT|PRD|SPEC|NORTH[_-]?STAR') { $s += 10 }
    if ($base -match '目标|需求|说明书|规格') { $s += 10 }
    if ($base -match $exts) { $s += 3 }
    return $s
}

$best = $null
$bestScore = -1
foreach ($p in $candidates) {
    $sc = Score-Candidate $p
    if ($sc -gt $bestScore) { $bestScore = $sc; $best = $p }
}

if ($null -ne $best) {
    if (Test-Path $best -PathType Leaf) {
        Write-Output "MODE=file"
        Write-Output "PATH=$best"
        Write-Output "EXISTS=yes"
        exit 0
    } else {
        $nearby = @()
        try {
            $nearby = Get-ChildItem -ErrorAction SilentlyContinue | Where-Object {
                $_.Name -match '(?i)GOAL|目标|需求|OBJECTIVE|REQUIREMENT|PRD|SPEC|NORTH[_-]?STAR'
            } | Select-Object -First 5 -ExpandProperty Name
        } catch { }
        Write-Output "MODE=file"
        Write-Output "PATH=$best"
        Write-Output "EXISTS=no"
        Write-Output ("NEARBY=" + ($nearby -join ','))
        exit 0
    }
}

# 3) No path candidate → oneliner if there's substantial leftover text
$leftover = [regex]::Replace($stripped, 'https?://\S+', '')
$leftover = ($leftover -replace '\s+', ' ').Trim()
$wordCount = ($leftover -split '\s+' | Where-Object { $_.Length -gt 0 }).Count

if ($wordCount -ge 3) {
    Write-Output "MODE=oneliner"
    Write-Output "ONELINER=$leftover"
    exit 0
}

Write-Output "MODE=missing"
Write-Output "ASK=Ask the user once: provide a goal file path (e.g. docs/GOALS.md) OR a one-line goal sentence."
exit 0
