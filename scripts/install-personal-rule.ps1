# Install Qualoop personal AI rule into user-level config (one-time).
#
# Usage (PowerShell):
#   iwr -useb https://raw.githubusercontent.com/sinogenomics/qualoop/main/scripts/install-personal-rule.ps1 | iex
#   # then call:
#   Install-QualoopPersonalRule -Tool claude
#
# Or one-liner (downloads + runs):
#   $url='https://raw.githubusercontent.com/sinogenomics/qualoop/main/scripts/install-personal-rule.ps1'; `
#   $s=(iwr $url -UseBasicParsing).Content; iex "$s; Install-QualoopPersonalRule -Tool claude"
#
# Idempotent: re-running upgrades the rule block in place.

function Install-QualoopPersonalRule {
    param(
        [Parameter(Mandatory = $true)]
        [ValidateSet('claude','codex','gemini','cursor','all')]
        [string] $Tool,

        [string] $RawUrl = 'https://raw.githubusercontent.com/sinogenomics/qualoop/main/templates/personal/qualoop.personal-rule.md'
    )

    $ErrorActionPreference = 'Stop'
    Write-Host "Fetching personal rule from:"
    Write-Host "  $RawUrl"
    $raw = (Invoke-WebRequest -Uri $RawUrl -UseBasicParsing).Content

    # Extract section between two '====' separator lines.
    $lines = $raw -split "(`r`n|`n)"
    $inside = $false
    $block = New-Object System.Text.StringBuilder
    foreach ($ln in $lines) {
        if ($ln -eq '====') {
            $inside = -not $inside
            continue
        }
        if ($inside) { [void]$block.AppendLine($ln) }
    }
    if ($block.Length -eq 0) {
        throw "Failed to extract personal rule block (no ==== ... ==== section)."
    }
    $blockText = $block.ToString().TrimEnd("`r","`n")

    $beginTag = '<!-- BEGIN Qualoop personal rule -->'
    $endTag   = '<!-- END Qualoop personal rule -->'

    function Write-Block([string]$file, [string]$kind) {
        $dir = Split-Path -Parent $file
        if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
        if (-not (Test-Path $file)) { Set-Content -Path $file -Value '' -Encoding UTF8 -NoNewline }

        $content = Get-Content -Raw -Path $file -ErrorAction SilentlyContinue
        if ($null -eq $content) { $content = '' }

        if ($content.Contains($beginTag)) {
            $pattern = [regex]::Escape($beginTag) + '[\s\S]*?' + [regex]::Escape($endTag)
            $content = [regex]::Replace($content, $pattern, '').TrimEnd("`r","`n") + "`r`n"
        }

        if ($kind -eq 'mdc') {
            if (-not ($content -match '^---\s*\r?\n')) {
                $fm = "---`r`ndescription: Qualoop personal rule (global)`r`nalwaysApply: true`r`n---`r`n`r`n"
                $content = $fm + $content
            }
        }

        $appended = "`r`n$beginTag`r`n$blockText`r`n$endTag`r`n"
        $final = $content + $appended
        $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
        [System.IO.File]::WriteAllText($file, $final, $utf8NoBom)
        Write-Host "  installed -> $file"
    }

    $home_ = [Environment]::GetFolderPath('UserProfile')
    $paths = @{
        'claude' = @{ file = (Join-Path $home_ '.claude\CLAUDE.md');           kind = 'plain' }
        'codex'  = @{ file = (Join-Path $home_ '.codex\AGENTS.md');            kind = 'plain' }
        'gemini' = @{ file = (Join-Path $home_ '.gemini\GEMINI.md');           kind = 'plain' }
        'cursor' = @{ file = (Join-Path $home_ '.cursor\rules\qualoop.mdc');   kind = 'mdc' }
    }

    if ($Tool -eq 'all') {
        foreach ($k in 'claude','codex','gemini','cursor') {
            Write-Block $paths[$k].file $paths[$k].kind
        }
    } else {
        Write-Block $paths[$Tool].file $paths[$Tool].kind
    }

    Write-Host ""
    Write-Host "OK: Qualoop personal rule installed."
    Write-Host "Next, in ANY new project, just say:"
    Write-Host "  Qualoop 接入, 开发目标见 docs/GOALS.md"
}

if ($MyInvocation.InvocationName -ne '.') {
    # If executed (not dot-sourced) and arg passed, run directly.
    if ($args.Count -ge 1) {
        Install-QualoopPersonalRule -Tool $args[0]
    }
}
