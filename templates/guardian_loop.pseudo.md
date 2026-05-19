# Guardian 主循环（伪代码）

语言无关；对应 LessonVerse `guardian.py` 行为。

```
CONFIG ← load_config()
AGENTS ← [
  ("tester",   "automation.tester",           "--loop"),
  ("scorer",   "automation.scorer",           "--loop"),
  ("scheduler","automation.scheduler",        "--loop"),
  ("fixer",    "automation.executors.fixer",  "--loop"),
  ("improver", "automation.executors.improver","--loop"),
  ("verifier", "automation.executors.verifier","--loop"),
]

function enabled(name):
  if name == "scorer":
    return CONFIG.scorer.enabled
  if name in executors:
    return CONFIG.executors[name].enabled
  return true

function start_agent(name, module, extra_args):
  cmd ← [python, -m, module] + split(extra_args)
  proc ← spawn(cmd, cwd=PROJECT_ROOT, detach_stdio=true)
  procs[name] ← proc
  backoff[name] ← CONFIG.guardian.initial_backoff_seconds
  log("Started", name, cmd)

function restart_if_needed(name, module, extra_args):
  proc ← procs[name]
  if proc exists AND proc.poll() is null:
    return  // still running

  if proc existed AND proc exited:
    log("Agent exited", name, proc.returncode)
    wait ← min(backoff[name], CONFIG.guardian.max_backoff_seconds)
    sleep(wait)
    backoff[name] ← min(wait * 2, CONFIG.guardian.max_backoff_seconds)

  start_agent(name, module, extra_args)

// --- startup ---
ensure_layout(CONFIG)
for (idx, (name, module, args)) in enumerate(AGENTS):
  if not enabled(name): continue
  if idx > 0:
    sleep(CONFIG.guardian.health_stagger_seconds)
  start_agent(name, module, args)

last_report ← monotonic_now()
report_interval ← CONFIG.intervals_seconds.report_snapshot

// --- supervise loop ---
loop forever:
  for (name, module, args) in AGENTS:
    if not enabled(name): continue
    restart_if_needed(name, module, args)

  if monotonic_now() - last_report >= report_interval:
    try:
      path ← write_latest_snapshot()
      log("Wrote report", path)
    catch Exception as e:
      log_error("Snapshot failed", e)
    last_report ← monotonic_now()

  sleep(5)  // supervisor tick

// --- shutdown (SIGINT) ---
on KeyboardInterrupt:
  for (name, proc) in procs:
    if proc.running:
      proc.terminate()
      log("Terminated", name)
```

## 与 Scheduler / Executor 的边界

- Guardian **不** 读 Issue Store 做分配
- Guardian **不** 执行业务修复
- 子进程各自持有 **store_lock** / **path_lock**（Executor、Tester、Scheduler）

## 配置键

| Key | 典型值 | 含义 |
|-----|--------|------|
| `guardian.initial_backoff_seconds` | 5 | 首次重启等待 |
| `guardian.max_backoff_seconds` | 300 | 退避上限 |
| `guardian.health_stagger_seconds` | 2 | 启动错峰 |
| `intervals_seconds.report_snapshot` | 300 | 报告周期 |
