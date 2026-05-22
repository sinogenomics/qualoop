# -*- coding: utf-8 -*-
"""Scheduler: assigns open issues to executors with path leases."""
from __future__ import annotations

# Ensure project root is in sys.path for robust module imports
import sys
import os
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)


import argparse
from datetime import datetime, timedelta, timezone

from automation.issue_store import IssueStore, STATUSES_OPEN
from automation.locks import LockTimeout, path_lock, store_lock
from automation.logging_util import setup_logger
from automation.paths import ensure_layout, load_config, maturity_at_least
from automation.reports import write_latest_snapshot

# issue type -> executor name
_TYPE_ROUTING = {
    "health": "verifier",
    "api": "verifier",
    "test_failure": "fixer",
    "static": "fixer",
    "improvement": "improver",
    "verification": "verifier",
    "performance": "verifier",
    "browser_e2e": "verifier",
}

_EXECUTOR_CAPS = {
    "fixer": 2,
    "improver": 1,
    "verifier": 10,
}


def _lease_until(minutes: int) -> str:
    return (
        datetime.now(timezone.utc) + timedelta(minutes=minutes)
    ).replace(microsecond=0).isoformat()


def _paths_conflict(paths_a: list[str], paths_b: list[str]) -> bool:
    if not paths_a or not paths_b:
        return False
    set_a = {p.replace("\\", "/") for p in paths_a}
    set_b = {p.replace("\\", "/") for p in paths_b}
    for a in set_a:
        for b in set_b:
            if a == b or a.startswith(b + "/") or b.startswith(a + "/"):
                return True
    return False


_FACT_TYPES = frozenset(
    {"health", "api", "test_failure", "static", "performance", "browser_e2e", "verification"}
)


from automation.scorer import QualoopScorer

def _auto_score_fact_issues(store: IssueStore, logger) -> int:
    """Uses the unified QualoopScorer to score open fact-type issues.

    Per METHODOLOGY §1.5 every opinion should be Scorer-rated. Fact-type detections
    (health, api, static, performance, test_failure, verification, browser_e2e)
    are scored dynamically based on their metrics.
    """
    updated = 0
    scorer = QualoopScorer()
    for issue in store.list_issues(status_filter=STATUSES_OPEN):
        if "value_score" in issue.get("metadata", {}):
            continue
        if issue.get("type") not in _FACT_TYPES:
            continue
        
        scorer.evaluate_and_score(issue, round_id="scheduler-autoscore")
        
        # Save Scorer outcomes
        store.update(
            issue["id"],
            metadata=issue.get("metadata"),
        )
        updated += 1
    if updated:
        logger.info("Auto-scored %d fact-type issues via unified scorer", updated)
    return updated


def run_once(cfg: dict | None = None) -> dict:
    cfg = cfg or load_config()
    ensure_layout(cfg)
    logger = setup_logger("scheduler", cfg)
    store = IssueStore()
    sched_cfg = cfg.get("scheduler", {})
    dry_run = sched_cfg.get("dry_run", False)
    if not maturity_at_least("L2", cfg):
        dry_run = True
        logger.info("maturity < L2: scheduler dry-run only")
    require_vq = sched_cfg.get("require_value_qualified", True)
    lease_min = sched_cfg.get("default_lease_minutes", 30)
    project_root = cfg["_project_root"]

    _auto_score_fact_issues(store, logger)

    open_issues = store.list_issues(status_filter=STATUSES_OPEN)
    assigned_counts = {name: 0 for name in _EXECUTOR_CAPS}
    in_progress_paths: list[list[str]] = []

    # Count existing assignments
    for issue in store.list_issues():
        ex = issue.get("assigned_executor")
        st = issue.get("status")
        if ex in assigned_counts and st in ("assigned", "in_progress"):
            assigned_counts[ex] += 1
            if issue.get("paths"):
                in_progress_paths.append(issue["paths"])

    results = []
    for issue in sorted(
        open_issues,
        key=lambda i: {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(
            i.get("severity", "low"), 9
        ),
    ):
        if issue.get("status") != "open":
            continue
        if issue.get("assigned_executor"):
            continue
        if require_vq and issue.get("metadata", {}).get("value_qualified") is not True:
            continue

        issue_type = issue.get("type", "static")
        executor = _TYPE_ROUTING.get(issue_type, "fixer")
        cap = cfg.get("executors", {}).get(executor, {}).get(
            "max_concurrent", _EXECUTOR_CAPS.get(executor, 1)
        )
        if assigned_counts.get(executor, 0) >= cap:
            continue

        paths = issue.get("paths") or []
        is_verifier = executor == "verifier"
        if not is_verifier and any(_paths_conflict(paths, busy) for busy in in_progress_paths):
            logger.info("Skip %s: path conflict", issue.get("id", "")[:8])
            continue

        # Try path locks
        locked = True
        lock_paths = paths or [f"issue:{issue.get('id', '')[:8]}"]
        if is_verifier:
            lock_paths = [f"issue:{issue.get('id', '')[:8]}"]
        try:
            for rtl in lock_paths:
                with path_lock(project_root, rtl, timeout=2.0):
                    pass
        except LockTimeout:
            locked = False

        if not locked:
            continue

        lease = _lease_until(lease_min)
        if dry_run:
            results.append(
                {"issue_id": issue["id"], "executor": executor, "dry_run": True}
            )
            logger.info(
                "[dry-run] Would assign %s -> %s", issue["id"][:8], executor
            )
            continue

        ok = store.assign(issue["id"], executor, lease_until=lease)
        if ok:
            assigned_counts[executor] = assigned_counts.get(executor, 0) + 1
            in_progress_paths.append(paths)
            results.append(
                {
                    "issue_id": issue["id"],
                    "executor": executor,
                    "lease_until": lease,
                }
            )
            logger.info("Assigned %s -> %s", issue["id"][:8], executor)

    write_latest_snapshot(store)
    return {"assignments": results, "dry_run": dry_run}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ParadigmLearn automation scheduler")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--loop", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    cfg = load_config()
    if args.dry_run:
        cfg.setdefault("scheduler", {})["dry_run"] = True

    interval = cfg.get("intervals_seconds", {}).get("scheduler", 30)

    if args.loop:
        import time
        logger = setup_logger("scheduler", cfg)
        while True:
            try:
                run_once(cfg)
            except Exception:
                logger.exception("Scheduler loop error")
            time.sleep(interval)
    else:
        run_once(cfg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
