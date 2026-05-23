"""Guardian daemon: supervises tester, scheduler, and executors."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .logging_util import setup_logger
from .paths import ensure_layout, load_config
from .reports import write_latest_snapshot

_AGENTS = (
    ("tester", "automation.tester", "--loop"),
    ("scheduler", "automation.scheduler", "--loop"),
    ("fixer", "automation.executors.fixer", "--loop"),
    ("improver", "automation.executors.improver", "--loop"),
    ("verifier", "automation.executors.verifier", "--loop"),
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _run_log_path(cfg: dict) -> Path | None:
    dep = cfg.get("deployment") or {}
    raw = dep.get("run_log_path")
    if raw:
        return Path(raw)
    return None


def _metrics_dir(cfg: dict) -> Path | None:
    dep = cfg.get("deployment") or {}
    raw = dep.get("metrics_dir")
    if raw:
        return Path(raw)
    return None


def _resolve_duration_hours(cfg: dict, cli_hours: float | None) -> float | None:
    if cli_hours is not None and cli_hours > 0:
        return cli_hours
    g = cfg.get("guardian") or {}
    hours = g.get("run_duration_hours")
    if hours is None:
        hours = cfg.get("run_duration_hours")
    if hours is None or float(hours) <= 0:
        return None
    return float(hours)


def _read_run_log(path: Path) -> dict:
    if path.is_file():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _write_run_log(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _agent_pids(supervisor: "AgentSupervisor") -> dict[str, int]:
    out: dict[str, int] = {}
    for name, proc in supervisor._procs.items():
        if proc.poll() is None:
            out[name] = proc.pid
    return out


def _copy_metrics(cfg: dict, logger) -> None:
    metrics_dir = _metrics_dir(cfg)
    if not metrics_dir:
        return
    metrics_dir.mkdir(parents=True, exist_ok=True)
    auto = cfg["_project_root"] / "automation"
    stamp = _utc_now().strftime("%Y%m%dT%H%M%SZ")
    for rtl in (
        "issues.json",
        "reports/latest_issues.md",
        "reports/dev_log_entries.json",
        "reports/automation_outcomes.json",
        "reports/automation_outcomes.md",
        "reports/corruption_watchlist.txt",
    ):
        src = auto / rtl
        if not src.is_file():
            continue
        dest = metrics_dir / f"{src.stem}_{stamp}{src.suffix}"
        try:
            shutil.copy2(src, dest)
        except OSError as e:
            logger.warning("Metrics copy failed for %s: %s", rtl, e)
    latest = metrics_dir / "latest_issues.md"
    src_report = auto / "reports" / "latest_issues.md"
    if src_report.is_file():
        try:
            shutil.copy2(src_report, latest)
        except OSError:
            pass


class AgentSupervisor:
    def __init__(self, cfg: dict, *, duration_hours: float | None = None):
        self.cfg = cfg
        self.logger = setup_logger("guardian", cfg)
        self.project_root: Path = cfg["_project_root"]
        g = cfg.get("guardian", {})
        self.initial_backoff = g.get("initial_backoff_seconds", 5)
        self.max_backoff = g.get("max_backoff_seconds", 300)
        self.stagger = g.get("health_stagger_seconds", 2)
        self._procs: dict[str, subprocess.Popen] = {}
        self._backoff: dict[str, float] = {}
        self.duration_hours = _resolve_duration_hours(cfg, duration_hours)
        self.deadline: datetime | None = None
        if self.duration_hours:
            self.deadline = _utc_now() + timedelta(hours=self.duration_hours)
        self._run_log_path = _run_log_path(cfg)
        self._session_id = str(uuid.uuid4())[:8]
        self._milestone_10h_logged = False

    def _enabled(self, name: str) -> bool:
        if name in ("fixer", "improver", "verifier"):
            return self.cfg.get("executors", {}).get(name, {}).get("enabled", True)
        return True

    def _start(self, name: str, module: str, extra_args: str) -> None:
        cmd = [sys.executable, "-m", module] + extra_args.split()
        self.logger.info("Starting %s: %s", name, " ".join(cmd))
        self._procs[name] = subprocess.Popen(
            cmd,
            cwd=str(self.project_root),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self._backoff[name] = self.initial_backoff

    def _restart_if_needed(self, name: str, module: str, extra_args: str) -> None:
        proc = self._procs.get(name)
        if proc is not None and proc.poll() is None:
            return
        if proc is not None:
            code = proc.returncode
            self.logger.warning("Agent %s exited (%s), restarting after backoff", name, code)
            wait = min(self._backoff.get(name, self.initial_backoff), self.max_backoff)
            time.sleep(wait)
            self._backoff[name] = min(wait * 2, self.max_backoff)
        self._start(name, module, extra_args)

    def _update_run_log(self, **fields) -> None:
        if not self._run_log_path:
            return
        data = _read_run_log(self._run_log_path)
        data.setdefault("session_id", self._session_id)
        data.update(fields)
        data["agent_pids"] = _agent_pids(self)
        if self.deadline:
            data["planned_end_at"] = self.deadline.replace(microsecond=0).isoformat()
            data["duration_hours"] = self.duration_hours
        _write_run_log(self._run_log_path, data)

    def _shutdown_agents(self) -> None:
        for name, proc in self._procs.items():
            if proc.poll() is None:
                proc.terminate()
                self.logger.info("Terminated %s", name)

    def run(self) -> None:
        ensure_layout(self.cfg)

        # Check and write PID file
        pid_file = self.project_root / "automation" / "logs" / "guardian.pid"
        if pid_file.is_file():
            try:
                import errno
                old_pid = int(pid_file.read_text(encoding="utf-8").strip())
                running = False
                try:
                    os.kill(old_pid, 0)
                    running = True
                except OSError as err:
                    if err.errno == errno.EPERM:
                        running = True
                if running:
                    self.logger.warning("Guardian is already running with PID %d", old_pid)
                    return
            except Exception:
                pass
        pid_file.write_text(str(os.getpid()), encoding="utf-8")

        started = _utc_now()
        self.logger.info("Guardian started at %s", self.project_root)
        if self.deadline:
            self.logger.info(
                "Scheduled stop at %s (%.1f h)",
                self.deadline.isoformat(),
                self.duration_hours,
            )
        self._update_run_log(
            status="running",
            started_at=started.replace(microsecond=0).isoformat(),
            guardian_pid=os.getpid(),
            project_root=str(self.project_root),
        )

        try:
            for idx, (name, module, args) in enumerate(_AGENTS):
                if not self._enabled(name):
                    continue
                if idx:
                    time.sleep(self.stagger)
                self._start(name, module, args)

            report_interval = self.cfg.get("intervals_seconds", {}).get("report_snapshot", 300)
            last_report = 0.0
            start_mono = time.monotonic()

            while True:
                for name, module, args in _AGENTS:
                    if not self._enabled(name):
                        continue
                    self._restart_if_needed(name, module, args)

                now = time.monotonic()
                if now - last_report >= report_interval:
                    try:
                        p = write_latest_snapshot()
                        self.logger.info("Wrote report snapshot: %s", p)
                        _copy_metrics(self.cfg, self.logger)
                    except Exception:
                        self.logger.exception("Snapshot failed")
                    self._update_run_log(status="running", last_snapshot_at=_utc_now().isoformat())
                    last_report = now

                if self.duration_hours and not self._milestone_10h_logged:
                    elapsed_h = (time.monotonic() - start_mono) / 3600.0
                    if elapsed_h >= self.duration_hours:
                        self._milestone_10h_logged = True
                        self.logger.info(
                            "Duration milestone: %.2f h elapsed (configured %.1f h)",
                            elapsed_h,
                            self.duration_hours,
                        )
                        self._update_run_log(
                            status="milestone_elapsed",
                            milestone_at=_utc_now().isoformat(),
                            elapsed_hours=round(elapsed_h, 3),
                        )

                if self.deadline and _utc_now() >= self.deadline:
                    self.logger.info("Duration limit reached; graceful shutdown")
                    self._update_run_log(
                        status="completed",
                        ended_at=_utc_now().replace(microsecond=0).isoformat(),
                    )
                    self._shutdown_agents()
                    return

                self._update_run_log(status="running")
                time.sleep(5)
        except KeyboardInterrupt:
            self.logger.info("Guardian stopping...")
            self._update_run_log(
                status="stopped_keyboard",
                ended_at=_utc_now().replace(microsecond=0).isoformat(),
            )
            self._shutdown_agents()
        finally:
            try:
                if pid_file.is_file():
                    pid_file.unlink()
            except Exception:
                pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ParadigmLearn automation guardian")
    sub = parser.add_subparsers(dest="command")

    start_p = sub.add_parser("start", help="Start supervised daemon")
    start_p.add_argument("--foreground", action="store_true", default=True)
    start_p.add_argument(
        "--duration-hours",
        type=float,
        default=None,
        help="Stop gracefully after N hours (overrides config guardian.run_duration_hours)",
    )

    sub.add_parser("status", help="Show whether issues file exists")

    args = parser.parse_args(argv)
    cfg = load_config()

    if args.command == "start":
        AgentSupervisor(cfg, duration_hours=args.duration_hours).run()
        return 0

    if args.command == "status":
        layout = ensure_layout(cfg)
        issues = layout["issues"]
        print(f"issues: {issues} ({'exists' if issues.exists() else 'missing'})")
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
