"""Base helpers for executor agents."""
from __future__ import annotations

from pathlib import Path

from ..issue_store import IssueStore
from ..locks import path_lock
from ..logging_util import setup_logger
from ..paths import load_config, maturity_at_least, maturity_level


def fetch_assigned(store: IssueStore, executor_name: str) -> list[dict]:
    issues = store.list_issues()
    return [
        i
        for i in issues
        if i.get("assigned_executor") == executor_name
        and i.get("status") in ("assigned", "in_progress")
    ]


def claim_issue(store: IssueStore, issue_id: str, executor_name: str) -> bool:
    issue = store.get(issue_id)
    if not issue or issue.get("assigned_executor") != executor_name:
        return False
    if issue.get("status") == "assigned":
        store.update(issue_id, status="in_progress")
        return True
    return issue.get("status") == "in_progress"


def complete_issue(
    store: IssueStore,
    issue_id: str,
    *,
    resolved: bool,
    note: str = "",
) -> None:
    status = "resolved" if resolved else "open"
    fields = {"status": status, "assigned_executor": None}
    issue = store.get(issue_id) or {}
    if note:
        meta = dict(issue.get("metadata") or {})
        meta["executor_note"] = note
        fields["metadata"] = meta
    store.update(issue_id, **fields)
    if resolved:
        try:
            from ..dev_log_sync import append_resolved_issue

            merged = {**issue, **fields, "id": issue_id}
            append_resolved_issue(merged, note=note)
        except Exception:
            pass


def run_executor_loop(
    executor_name: str,
    handler,
    *,
    once: bool = False,
) -> None:
    cfg = load_config()
    interval = cfg.get("intervals_seconds", {}).get(executor_name, 60)
    logger = setup_logger(executor_name, cfg)
    store = IssueStore()
    project_root: Path = cfg["_project_root"]

    import time

    while True:
        issues = fetch_assigned(store, executor_name)
        if not issues:
            logger.debug("No assigned issues for %s", executor_name)
        for issue in issues:
            iid = issue["id"]
            if not claim_issue(store, iid, executor_name):
                continue
            paths = issue.get("paths") or [f"issue:{iid[:8]}"]
            try:
                with path_lock(project_root, paths[0], timeout=30.0):
                    handler(issue, store, cfg, logger)
            except Exception as e:
                logger.exception("Executor %s failed on %s: %s", executor_name, iid[:8], e)
                store.update(iid, status="open", assigned_executor=None)
        if once:
            break
        time.sleep(interval)
