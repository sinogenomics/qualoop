# LessonVerse 10h optimization — Qualoop deployment launcher
$ErrorActionPreference = "Stop"
$DeployDir = $PSScriptRoot
$ProjectRoot = "E:\20260502_MZH\lessonverse"
$DeployConfig = Join-Path $DeployDir "config.json"
$AutoConfig = Join-Path $ProjectRoot "automation\config.json"
$RunLog = Join-Path $DeployDir "run_log.json"
$MetricsDir = Join-Path $DeployDir "metrics"
$GuardianLogOut = Join-Path $DeployDir "guardian_session.out.log"
$GuardianLogErr = Join-Path $DeployDir "guardian_session.err.log"

$Python = "D:\python38\python.exe"
if (-not (Test-Path $Python)) { $Python = "py" }

function Test-TcpPort([int]$Port) {
    try {
        $c = New-Object System.Net.Sockets.TcpClient
        $c.Connect("127.0.0.1", $Port)
        $c.Close()
        return $true
    } catch { return $false }
}

function Stop-AutomationProcesses {
    $patterns = @(
        "automation.guardian",
        "automation.tester",
        "automation.scheduler",
        "automation.executors.fixer",
        "automation.executors.improver",
        "automation.executors.verifier"
    )
    Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
        Where-Object {
            $cmd = $_.CommandLine
            if (-not $cmd) { return $false }
            foreach ($p in $patterns) { if ($cmd -like "*$p*") { return $true } }
            return $false
        } |
        ForEach-Object {
            Write-Host "Stopping PID $($_.ProcessId): $($_.CommandLine.Substring(0, [Math]::Min(80, $_.CommandLine.Length)))..."
            Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
        }
    Start-Sleep -Seconds 2
}

function Ensure-AppServices {
    if (-not (Test-TcpPort 5000)) {
        Write-Host "Starting backend on :5000..."
        $env:NOTEBOOKLM_MOCK_MODE = "0"
        Start-Process -FilePath $Python -ArgumentList "-u", "app.py" -WorkingDirectory $ProjectRoot -WindowStyle Hidden
        Start-Sleep -Seconds 4
    } else {
        Write-Host "Backend :5000 already listening"
    }
    if (-not (Test-TcpPort 8080)) {
        Write-Host "Starting frontend on :8080..."
        Start-Process -FilePath $Python -ArgumentList "-m", "http.server", "8080" -WorkingDirectory $ProjectRoot -WindowStyle Hidden
        Start-Sleep -Seconds 2
    } else {
        Write-Host "Frontend :8080 already listening"
    }
}

New-Item -ItemType Directory -Force -Path $MetricsDir | Out-Null

Write-Host "=== LessonVerse 10h run ==="
Stop-AutomationProcesses
Ensure-AppServices

Copy-Item -Path $DeployConfig -Destination $AutoConfig -Force
Write-Host "Applied deployment config -> $AutoConfig"

$durationHours = 10
try {
    $cfg = Get-Content $DeployConfig -Raw | ConvertFrom-Json
    if ($cfg.guardian.run_duration_hours) { $durationHours = [double]$cfg.guardian.run_duration_hours }
    elseif ($cfg.run_duration_hours) { $durationHours = [double]$cfg.run_duration_hours }
} catch { }

$started = Get-Date
$plannedEnd = $started.AddHours($durationHours)
$sessionId = "lv10h-" + $started.ToString("yyyyMMdd-HHmmss")

$guardianArgs = @("-m", "automation.guardian", "start", "--duration-hours", $durationHours)
$proc = Start-Process -FilePath $Python -ArgumentList $guardianArgs `
    -WorkingDirectory $ProjectRoot `
    -WindowStyle Hidden `
    -PassThru `
    -RedirectStandardOutput $GuardianLogOut `
    -RedirectStandardError $GuardianLogErr

Start-Sleep -Seconds 6

$agentProcs = @{}
Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -match "automation\.(tester|scheduler|executors|guardian)" } |
    ForEach-Object {
        $name = "unknown"
        if ($_.CommandLine -match "automation\.(\w+)") { $name = $Matches[1] }
        if ($_.CommandLine -match "executors\.(\w+)") { $name = $Matches[1] }
        $agentProcs[$name] = $_.ProcessId
    }

$launcherMeta = @{
    session_id       = $sessionId
    status           = "running"
    started_at       = $started.ToUniversalTime().ToString("o")
    planned_end_at   = $plannedEnd.ToUniversalTime().ToString("o")
    duration_hours   = $durationHours
    guardian_pid     = $proc.Id
    agent_pids       = $agentProcs
    project_root     = $ProjectRoot
    deploy_config    = $DeployConfig
    guardian_log_out = $GuardianLogOut
    guardian_log_err = $GuardianLogErr
} | ConvertTo-Json -Depth 6
[System.IO.File]::WriteAllText($RunLog, $launcherMeta, [System.Text.UTF8Encoding]::new($false))

Write-Host ""
Write-Host "Session:    $sessionId"
Write-Host "Guardian:   PID $($proc.Id)"
Write-Host "Started:    $($started.ToString('yyyy-MM-dd HH:mm:ss')) local"
Write-Host "Ends ~:     $($plannedEnd.ToString('yyyy-MM-dd HH:mm:ss')) local (+${durationHours}h)"
Write-Host "Run log:    $RunLog"
Write-Host "Verify:     Get-Content '$RunLog' | ConvertFrom-Json | Format-List"
