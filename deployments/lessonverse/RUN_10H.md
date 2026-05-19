# LessonVerse — 10-hour continuous optimization run

This deployment bridges **Qualoop** methodology (`e:/path/to/qualoop\`) with LessonVerse’s existing `automation/` stack.

## What runs

| Role | Module | Interval (this run) |
|------|--------|---------------------|
| **Guardian** | `automation.guardian` | Supervises all agents; stops after **10 hours** |
| **Tester** | `automation.tester --loop` | ~6 min (360s) — health, static scan, legacy scripts, browser E2E |
| **Scheduler** | `automation.scheduler --loop` | ~2 min (120s) — sole assignment writer (ADOPTION_GUIDE) |
| **Fixer** | `automation.executors.fixer --loop` | ~5 min — safe fixes only (watchlist, re-queue, no mass restore) |
| **Improver** | `automation.executors.improver --loop` | ~9 min — improvement scripts, suggestions JSONL |
| **Verifier** | `automation.executors.verifier --loop` | ~5 min — re-run checks, close or reopen issues |

Outputs: `lessonverse/automation/issues.json`, `reports/latest_issues.md`, `logs/*.log`, optional `reports/dev_log_entries.json`.

Metrics copies (each report snapshot): `deployments/lessonverse/metrics/`.

## Start (fresh 10h session)

```powershell
cd e:/path/to/qualoop\deployments\lessonverse
powershell -ExecutionPolicy Bypass -File .\start_10h.ps1
```

The launcher will:

1. Stop any existing `automation.guardian` / tester / scheduler / executor processes
2. Ensure backend `:5000` and frontend `:8080` are up (starts `app.py` + `http.server` if needed)
3. Copy `deployments/lessonverse/config.json` → `lessonverse/automation/config.json`
4. Start Guardian detached with `--duration-hours 10`
5. Write PIDs and planned end time to `run_log.json`

## Verify it is running

```powershell
Get-Content e:/path/to/qualoop\deployments\lessonverse\run_log.json | ConvertFrom-Json | Format-List
Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
  Where-Object { $_.CommandLine -match 'automation\.(guardian|tester|scheduler|executors)' } |
  Select-Object ProcessId, CommandLine
Get-Content E:\20260502_MZH\lessonverse\automation\logs\guardian_*.log -Tail 15
```

## Stop early

```powershell
powershell -ExecutionPolicy Bypass -File e:/path/to/qualoop\deployments\lessonverse\stop_automation.ps1
```

Or kill the Guardian PID from `run_log.json` (child agents exit with it).

## Paths

| Item | Path |
|------|------|
| Deployment | `e:/path/to/qualoop\deployments\lessonverse\` |
| App automation | `E:\20260502_MZH\lessonverse\automation\` |
| Run log | `deployments/lessonverse/run_log.json` |
| Metrics | `deployments/lessonverse/metrics/` |

## Methodology

- `Qualoop/METHODOLOGY.md` — four roles, issue lifecycle
- `Qualoop/ADOPTION_GUIDE.md` — single scheduler, path locks, safe executor bounds
- `Qualoop/case-study/LESSONVERSE.md` — prior findings
