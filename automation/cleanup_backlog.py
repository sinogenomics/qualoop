"""One-shot backlog hygiene: dedupe performance issues, close orphan verifications.

Usage:
  py -3.8-64 -m automation.cleanup_backlog          # apply
  py -3.8-64 -m automation.cleanup_backlog --dry-run # preview only
"""
from __future__ import annotations

import argparse
import re
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from .issue_store import IssueStore, STATUSES_TERMINAL, store_lock
from .paths import ensure_layout
from .reports import write_automation_outcomes, write_latest_snapshot

_PERF_URL_RE = re.compile(r"https?://[^\s]+|/api/health")


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _perf_url(issue: dict[str, Any]) -> str | None:
    md = issue.get("metadata") or {}
    url = md.get("url")
    if url:
        return str(url).rstrip("/")
    m = _PERF_URL_RE.search(issue.get("description") or "")
    return m.group(0).rstrip("/") if m else None


def _static_key(issue: dict[str, Any]) -> tuple[str, tuple[str, ...]]:
    paths = tuple(sorted(issue.get("paths") or []))
    return (issue.get("type", ""), paths)


def _mark_duplicate(issue: dict[str, Any], keeper_id: str, reason: str) -> None:
    meta = dict(issue.get("metadata") or {})
    meta["duplicate_of"] = keeper_id
    meta["cleanup_note"] = reason
    issue["status"] = "duplicate"
    issue["assigned_executor"] = None
    issue["metadata"] = meta
    issue["updated_at"] = _utc_now()


def cleanup_backlog(*, dry_run: bool = False) -> dict[str, int]:
    ensure_layout()
    store = IssueStore()
    stats = {
        "performance_deduped": 0,
        "verification_orphans_closed": 0,
        "static_wontfix_deduped": 0,
        "assigned_cleared_on_terminal": 0,
    }

    with store_lock():
        data = store._read_unlocked()
        issues: list[dict[str, Any]] = data.get("issues", [])
        by_id = {i["id"]: i for i in issues}

        # --- 1) Performance: one active issue per URL ---
        perf_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for issue in issues:
            if issue.get("type") != "performance":
                continue
            if issue.get("status") in STATUSES_TERMINAL:
                continue
            url = _perf_url(issue)
            if not url:
                continue
            perf_groups[url].append(issue)

        for url, group in perf_groups.items():
            if len(group) <= 1:
                continue
            group.sort(
                key=lambda i: (
                    0 if i.get("status") in ("assigned", "in_progress") else 1,
                    i.get("updated_at") or i.get("created_at") or "",
                ),
                reverse=True,
            )
            keeper = group[0]
            for dup in group[1:]:
                _mark_duplicate(
                    dup,
                    keeper["id"],
                    f"performance dedupe for {url}",
                )
                stats["performance_deduped"] += 1

        # --- 2) Orphan verification: parent already terminal ---
        for issue in issues:
            if issue.get("type") != "verification":
                continue
            if issue.get("status") in STATUSES_TERMINAL:
                continue
            parent_id = (issue.get("metadata") or {}).get("parent_issue")
            if not parent_id:
                continue
            parent = by_id.get(parent_id)
            if not parent:
                continue
            pstatus = parent.get("status")
            if pstatus not in STATUSES_TERMINAL:
                continue
            meta = dict(issue.get("metadata") or {})
            meta["executor_note"] = f"cleanup: parent {parent_id[:8]} is {pstatus}"
            issue["metadata"] = meta
            issue["status"] = pstatus if pstatus == "wontfix" else "resolved"
            issue["assigned_executor"] = None
            issue["updated_at"] = _utc_now()
            stats["verification_orphans_closed"] += 1

        # --- 3) Wontfix static duplicates (same paths) ---
        wontfix_static: dict[tuple[str, tuple[str, ...]], list[dict[str, Any]]] = (
            defaultdict(list)
        )
        for issue in issues:
            if issue.get("status") != "wontfix":
                continue
            if issue.get("type") != "static":
                continue
            key = _static_key(issue)
            if not key[1]:
                continue
            wontfix_static[key].append(issue)

        for key, group in wontfix_static.items():
            if len(group) <= 1:
                continue
            group.sort(key=lambda i: i.get("created_at") or "")
            keeper = group[0]
            for dup in group[1:]:
                _mark_duplicate(
                    dup,
                    keeper["id"],
                    f"wontfix static dedupe {key[1]}",
                )
                stats["static_wontfix_deduped"] += 1

        # --- 4) Clear stale assignments on terminal issues ---
        for issue in issues:
            if issue.get("status") in STATUSES_TERMINAL:
                if issue.get("assigned_executor"):
                    issue["assigned_executor"] = None
                    issue["updated_at"] = _utc_now()
                    stats["assigned_cleared_on_terminal"] += 1

        if not dry_run:
            data["meta"] = data.get("meta") or {}
            data["meta"]["last_cleanup"] = _utc_now()
            store._write_unlocked(data)

    if not dry_run:
        write_latest_snapshot(store)
        write_automation_outcomes(window_hours=10.0)

    return stats


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Clean Qualoop issue backlog")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute changes but do not write issues.json",
    )
    args = parser.parse_args(argv)
    if args.dry_run:
        print("DRY RUN — no files will be written")
    stats = cleanup_backlog(dry_run=args.dry_run)
    print("Backlog cleanup applied:")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    store = IssueStore()
    from collections import Counter

    counts = Counter(i.get("status") for i in store.list_issues())
    print("Status after cleanup:", dict(counts))
    active = store.list_issues(
        status_filter={"open", "assigned", "in_progress"}
    )
    print(f"Active backlog: {len(active)} issues")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
