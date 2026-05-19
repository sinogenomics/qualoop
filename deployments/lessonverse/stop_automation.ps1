# Stop LessonVerse automation agents (guardian + children)
$patterns = @(
    "automation.guardian",
    "automation.tester",
    "automation.scheduler",
    "automation.executors"
)
Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
    Where-Object {
        $cmd = $_.CommandLine
        if (-not $cmd) { return $false }
        foreach ($p in $patterns) { if ($cmd -like "*$p*") { return $true } }
        return $false
    } |
    ForEach-Object {
        Write-Host "Stopping $($_.ProcessId)"
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }
$runLog = Join-Path $PSScriptRoot "run_log.json"
if (Test-Path $runLog) {
    $log = Get-Content $runLog -Raw | ConvertFrom-Json
    $log.status = "stopped_manual"
    $log.ended_at = (Get-Date).ToUniversalTime().ToString("o")
    $json = $log | ConvertTo-Json -Depth 6
    [System.IO.File]::WriteAllText($runLog, $json, [System.Text.UTF8Encoding]::new($false))
}
Write-Host "Automation stopped."
