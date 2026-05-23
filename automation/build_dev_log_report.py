"""Aggregate automation outcomes for dev-log.html and DEV_PROCESS_LOG.md."""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .issue_store import STATUSES_OPEN, STATUSES_TERMINAL, IssueStore
from .paths import ensure_layout, load_config
from .round_suggestions import load_suggestions

_LOG_TS = re.compile(
    r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \[(\w+)\] ([\w.]+): (.*)$"
)
# Guardian/tester logs use Hong Kong wall-clock (HKT, Asia/Hong_Kong) without TZ suffix
_HKT_TZ = timezone(timedelta(hours=8))
_LOG_TZ = _HKT_TZ
_METRICS_ISSUES = re.compile(r"^issues_(\d{8}T\d{6}Z)\.json$", re.I)
_AUTO_MARKERS = ("<!-- AUTO_OUTCOMES_START -->", "<!-- AUTO_OUTCOMES_END -->")
_MAX_INSPECTION_ROUNDS = 50
_TESTER_DONE = re.compile(
    r"Tester done: (\d+) new issues(?:, (\d+) checks \(pass=(\d+) warn=(\d+) fail=(\d+)\), depth=(\w+))?"
    r"(?:, suggestions=(\d+))?"
)
_TESTER_DONE_LEGACY = re.compile(r"Tester done: (\d+) new issues")
_RECORDED_FAILURE = re.compile(r"Recorded failure for (.+)$")
_CORRUPTION = re.compile(r"Corruption detected in (?P<file>.+)$")
_API_ROUTES = re.compile(r"Found (\d+) API routes")
_BASELINE_NEW_ISSUES = 5
_OPEN_SAMPLE = 3
_SEVERITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3, "unknown": 4}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _parse_ts(raw: str | None) -> datetime | None:
    if not raw:
        return None
    s = raw.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _format_hkt_display(dt: datetime | None) -> str:
    """Human-readable Hong Kong time for UI (e.g. 2026-05-19 15:30 HKT)."""
    if not dt:
        return ""
    return dt.astimezone(_HKT_TZ).strftime("%Y-%m-%d %H:%M HKT")


def _metrics_dir(cfg: dict) -> Path | None:
    dep = cfg.get("deployment") or {}
    raw = dep.get("metrics_dir")
    if raw:
        p = Path(raw)
        return p if p.is_dir() or p.parent.is_dir() else None
    return None


def _in_window(dt: datetime | None, start: datetime, end: datetime) -> bool:
    return dt is not None and start <= dt <= end


def _load_issues(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    return list(data.get("issues") or [])


def _classify_resolution(issue: dict[str, Any]) -> str:
    """automation | manual_collab | unknown"""
    if issue.get("status") != "resolved":
        return "open"
    meta = issue.get("metadata") or {}
    note = (meta.get("executor_note") or "").lower()
    ex = issue.get("assigned_executor") or ""
    if ex == "improver" or "ran " in note and "successfully" in note:
        return "automation"
    if meta.get("automation_only") is True:
        return "automation"
    if meta.get("manual_fix") or meta.get("cursor_agent"):
        return "manual_collab"
    # fixer/verifier often document without closing root cause
    if ex in ("fixer", "verifier") or "no auto-fix" in note or "watchlist" in note:
        return "manual_collab"
    return "automation"


def _aggregate_issues(
    issues: list[dict[str, Any]], start: datetime, end: datetime
) -> dict[str, Any]:
    discovered: list[dict[str, Any]] = []
    resolved_auto: list[dict[str, Any]] = []
    resolved_manual: list[dict[str, Any]] = []
    still_open: list[dict[str, Any]] = []
    by_type: Counter[str] = Counter()
    by_severity: Counter[str] = Counter()

    for issue in issues:
        created = _parse_ts(issue.get("created_at"))
        updated = _parse_ts(issue.get("updated_at"))
        status = issue.get("status", "open")
        itype = issue.get("type", "unknown")
        sev = issue.get("severity", "unknown")

        if _in_window(created, start, end):
            discovered.append(issue)
            by_type[itype] += 1
            by_severity[sev] += 1

        if status in STATUSES_OPEN | {"assigned", "in_progress"}:
            still_open.append(issue)
        elif status == "resolved" and _in_window(updated, start, end):
            bucket = _classify_resolution(issue)
            if bucket == "automation":
                resolved_auto.append(issue)
            else:
                resolved_manual.append(issue)

    return {
        "discovered_count": len(discovered),
        "discovered_by_type": dict(by_type),
        "discovered_by_severity": dict(by_severity),
        "resolved_automation_count": len(resolved_auto),
        "resolved_manual_count": len(resolved_manual),
        "still_open_count": len(still_open),
        "still_open_by_type": dict(Counter(i.get("type", "?") for i in still_open)),
    }


def _parse_log_file(path: Path, start: datetime, end: datetime) -> dict[str, Any]:
    out: dict[str, Any] = {
        "lines": 0,
        "events": [],
    }
    if not path.is_file():
        return out

    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = _LOG_TS.match(line)
        if not m:
            continue
        out["lines"] += 1
        ts_local = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S").replace(tzinfo=_LOG_TZ)
        ts_local = ts_local.astimezone(timezone.utc)
        if not _in_window(ts_local, start, end):
            continue
        out["events"].append(
            {"at": ts_local.isoformat(), "level": m.group(2), "logger": m.group(3), "msg": m.group(4)}
        )
    return out


def _load_round_findings(reports_dir: Path) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    """Load round_findings.jsonl grouped by round_id and as flat list."""
    path = reports_dir / "round_findings.jsonl"
    by_round: dict[str, list[dict[str, Any]]] = defaultdict(list)
    flat: list[dict[str, Any]] = []
    if not path.is_file():
        return by_round, flat
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        flat.append(row)
        rid = row.get("round_id")
        if rid:
            by_round[str(rid)].append(row)
    return by_round, flat


def _rows_for_interval(
    *,
    by_round: dict[str, list[dict[str, Any]]],
    flat: list[dict[str, Any]],
    round_id: str,
    started: datetime,
    ended: datetime,
    ts_key: str = "at",
) -> list[dict[str, Any]]:
    if round_id in by_round:
        return by_round[round_id]
    slack = timedelta(minutes=3)
    end_at = ended or started
    matched: list[dict[str, Any]] = []
    for row in flat:
        at = _parse_ts(row.get(ts_key))
        if at and started - slack <= at <= end_at + slack:
            matched.append(row)
    return matched


def _findings_for_interval(
    *,
    by_round: dict[str, list[dict[str, Any]]],
    flat: list[dict[str, Any]],
    round_id: str,
    started: datetime,
    ended: datetime,
) -> list[dict[str, Any]]:
    return _rows_for_interval(
        by_round=by_round,
        flat=flat,
        round_id=round_id,
        started=started,
        ended=ended,
        ts_key="at",
    )


def _suggestions_for_interval(
    *,
    by_round: dict[str, list[dict[str, Any]]],
    flat: list[dict[str, Any]],
    round_id: str,
    started: datetime,
    ended: datetime,
) -> list[dict[str, Any]]:
    return _rows_for_interval(
        by_round=by_round,
        flat=flat,
        round_id=round_id,
        started=started,
        ended=ended,
        ts_key="ts",
    )


def _summarize_check_items(items: list[dict[str, Any]]) -> dict[str, Any]:
    counts = {"pass": 0, "fail": 0, "warn": 0, "total": len(items)}
    for it in items:
        st = it.get("status", "")
        if st in counts:
            counts[st] += 1
    briefs = [
        {
            "id": "",
            "title": f"[{it.get('status', '?')}] {it.get('name', it.get('check_id', ''))}"
            + (f" — {it.get('detail', '')[:80]}" if it.get("detail") else ""),
            "type": it.get("category", "check"),
            "severity": it.get("status", "info"),
            "fix_status": "fixed" if it.get("status") == "pass" else "pending",
        }
        for it in items
    ]
    stored_new = sum(1 for it in items if it.get("new_issue"))
    return {"counts": counts, "items": briefs, "stored_new": stored_new}


def _depth_label(depth: str | None, check_count: int) -> str:
    d = (depth or "").lower()
    if d in ("basic", "standard", "deep"):
        return d
    if check_count >= 18:
        return "deep"
    if check_count >= 8:
        return "standard"
    return "basic"


def _summarize_tester(events: list[dict[str, Any]]) -> dict[str, Any]:
    runs = 0
    new_issues_total = 0
    e2e = {"runs": 0, "pass": 0, "fail": 0, "modal_ok": 0}
    health_ok = 0
    corruption = 0

    for e in events:
        msg = e.get("msg", "")
        if msg.startswith("Tester run started"):
            runs += 1
        elif msg.startswith("Tester done:"):
            m = _TESTER_DONE.search(msg) or _TESTER_DONE_LEGACY.search(msg)
            if m:
                new_issues_total += int(m.group(1))
        elif "Backend health OK" in msg or "Frontend health OK" in msg:
            health_ok += 1
        elif msg.startswith("Corruption detected"):
            corruption += 1
        elif msg.startswith("Browser E2E starting"):
            e2e["runs"] += 1
        elif msg.startswith("Browser E2E error") or "Browser E2E failed" in msg:
            e2e["fail"] += 1
        elif "Browser E2E: error modal shown" in msg:
            e2e["modal_ok"] += 1
            e2e["pass"] += 1
        elif msg.startswith("Browser E2E OK") or "Browser E2E passed" in msg:
            e2e["pass"] += 1

    return {
        "runs": runs,
        "new_issues_reported": new_issues_total,
        "health_ok_signals": health_ok,
        "corruption_warnings": corruption,
        "browser_e2e": e2e,
    }


def _summarize_scheduler(events: list[dict[str, Any]]) -> dict[str, Any]:
    assignments: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for e in events:
        msg = e.get("msg", "")
        m = re.match(r"Assigned ([0-9a-f-]+) -> (\w+)", msg)
        if not m:
            continue
        key = (m.group(1)[:8], m.group(2))
        if key in seen:
            continue
        seen.add(key)
        assignments.append({"issue": m.group(1)[:8], "executor": m.group(2), "at": e.get("at")})
    by_exec = dict(Counter(a["executor"] for a in assignments))
    return {"unique_assignments": len(assignments), "by_executor": by_exec, "samples": assignments[:8]}


def _summarize_improver(events: list[dict[str, Any]], suggestions_path: Path, start: datetime, end: datetime) -> dict[str, Any]:
    count = sum(1 for e in events if "Improver:" in e.get("msg", ""))
    recent: list[dict[str, Any]] = []
    if suggestions_path.is_file():
        for line in suggestions_path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not row.get("goal_alignment"):
                continue
            ts = _parse_ts(row.get("ts"))
            if _in_window(ts, start, end):
                recent.append(row)
    return {
        "log_actions": count,
        "suggestions_count": len(recent),
        "aligned_count": len(recent),
        "recent": recent[-5:],
    }


def _suggestion_briefs(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        if not row.get("goal_alignment"):
            continue
        out.append(
            {
                "id": (row.get("id") or row.get("suggestion_id") or "")[:12],
                "title": (row.get("text") or row.get("message") or "")[:200],
                "type": row.get("category", "suggestion"),
                "severity": row.get("priority", "info"),
                "fix_status": "suggestion",
                "rationale": (row.get("rationale") or "")[:500],
                "category": row.get("category", ""),
                "goal_alignment": True,
            }
        )
        if len(out) >= 12:
            break
    return out


def _round_has_finding(rnd: dict[str, Any]) -> bool:
    if rnd.get("discovered") or rnd.get("detected_this_round"):
        return True
    cc = rnd.get("check_counts") or {}
    if cc.get("fail", 0) > 0:
        return True
    items = rnd.get("check_items") or []
    return any(it.get("severity") == "fail" or it.get("fix_status") == "pending" and "fail" in (it.get("title") or "") for it in items)


def _metrics_timeline(metrics_dir: Path | None, start: datetime, end: datetime) -> list[dict[str, Any]]:
    if not metrics_dir or not metrics_dir.is_dir():
        return []

    points: list[dict[str, Any]] = []
    for path in sorted(metrics_dir.glob("issues_*.json")):
        m = _METRICS_ISSUES.match(path.name)
        if not m:
            continue
        stamp = m.group(1)
        try:
            snap_at = datetime.strptime(stamp, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if not _in_window(snap_at, start, end):
            continue
        issues = _load_issues(path)
        open_n = sum(1 for i in issues if i.get("status") in STATUSES_OPEN | {"assigned", "in_progress"})
        resolved_n = sum(1 for i in issues if i.get("status") == "resolved")
        points.append(
            {
                "at": snap_at.isoformat(),
                "file": path.name,
                "open_count": open_n,
                "resolved_count": resolved_n,
                "total": len(issues),
            }
        )
    return points


def _issue_title(issue: dict[str, Any], max_len: int = 96) -> str:
    desc = (issue.get("description") or "").strip().replace("\n", " ")
    if len(desc) <= max_len:
        return desc
    return desc[: max_len - 1] + "…"


def _fix_status_key(issue: dict[str, Any]) -> str:
    """fixed | pending | logged_only — maps to 已修复 / 待处理 / 仅记录."""
    status = issue.get("status", "open")
    if status == "resolved":
        return "fixed"
    meta = issue.get("metadata") or {}
    note = (meta.get("executor_note") or "").lower()
    if meta.get("automation_only") is True and status in STATUSES_OPEN:
        return "logged_only"
    if issue.get("assigned_executor") == "fixer" and (
        "no auto-fix" in note or "watchlist" in note or "document" in note
    ):
        return "logged_only"
    if status in {"wontfix", "duplicate"}:
        return "logged_only"
    return "pending"


def _issue_brief(issue: dict[str, Any], *, fix_status: str | None = None) -> dict[str, Any]:
    return {
        "id": (issue.get("id") or "")[:8],
        "title": _issue_title(issue),
        "type": issue.get("type", "unknown"),
        "severity": issue.get("severity", "unknown"),
        "fix_status": fix_status or _fix_status_key(issue),
    }


def _index_by_fingerprint(issues: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for issue in issues:
        key = issue.get("fingerprint") or issue.get("id")
        if key:
            out[str(key)] = issue
    return out


def _diff_snapshots(
    prev: list[dict[str, Any]], curr: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
    prev_idx = _index_by_fingerprint(prev)
    curr_idx = _index_by_fingerprint(curr)
    discovered: list[dict[str, Any]] = []
    resolved: list[dict[str, Any]] = []
    for key, issue in curr_idx.items():
        if key not in prev_idx:
            discovered.append(issue)
        else:
            prev_st = prev_idx[key].get("status")
            curr_st = issue.get("status")
            if prev_st not in STATUSES_TERMINAL and curr_st in STATUSES_TERMINAL:
                resolved.append(issue)
    still_open = sum(
        1
        for i in curr
        if i.get("status") in STATUSES_OPEN | {"assigned", "in_progress"}
    )
    return discovered, resolved, still_open


def _load_metrics_snapshots(
    metrics_dir: Path | None, start: datetime, end: datetime
) -> list[tuple[datetime, Path, list[dict[str, Any]]]]:
    if not metrics_dir or not metrics_dir.is_dir():
        return []
    snaps: list[tuple[datetime, Path, list[dict[str, Any]]]] = []
    for path in sorted(metrics_dir.glob("issues_*.json")):
        m = _METRICS_ISSUES.match(path.name)
        if not m:
            continue
        try:
            snap_at = datetime.strptime(m.group(1), "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if not _in_window(snap_at, start, end):
            continue
        snaps.append((snap_at, path, _load_issues(path)))
    return snaps


def _snapshots_for_interval(
    snaps: list[tuple[datetime, Path, list[dict[str, Any]]]],
    started: datetime,
    ended: datetime | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str | None]:
    if not snaps:
        return [], [], None
    end_at = ended or started
    before = [s for s in snaps if s[0] <= started]
    at_end = [s for s in snaps if s[0] <= end_at]
    prev = before[-1] if before else snaps[0]
    curr = at_end[-1] if at_end else snaps[-1]
    if prev[0] >= curr[0]:
        later = [s for s in snaps if s[0] > curr[0]]
        if later:
            curr = later[0]
    if prev[0] >= curr[0] and len(snaps) > 1:
        idx = snaps.index(curr)
        if idx > 0:
            prev = snaps[idx - 1]
    return prev[2], curr[2], curr[1].name


def _log_detected_titles(messages: list[str]) -> list[str]:
    """Findings logged this run (may already exist in issue store via fingerprint)."""
    titles: list[str] = []
    for msg in messages:
        m = _CORRUPTION.match(msg)
        if m:
            titles.append(f"腐化检测：{m.group('file')}")
            continue
        m = _RECORDED_FAILURE.match(msg)
        if m:
            titles.append(f"测试失败：{m.group(1)}")
            continue
        if msg.startswith("Recorded frontend health"):
            titles.append("前端健康检查失败")
        elif msg.startswith("Recorded backend health"):
            titles.append("后端健康检查失败")
    return titles


def _round_checked_items(messages: list[str]) -> list[str]:
    checked: list[str] = []
    for msg in messages:
        if "Backend health OK" in msg:
            checked.append("后端健康检查通过")
        elif msg.startswith("Recorded backend health"):
            checked.append("后端健康异常（已记录）")
        elif "Frontend health OK" in msg:
            checked.append("前端健康检查通过")
        elif msg.startswith("Recorded frontend health"):
            checked.append("前端健康异常（已记录）")
        m = _API_ROUTES.search(msg)
        if m:
            checked.append(f"API 路由探测：{m.group(1)} 条")
        if msg.startswith("Browser E2E starting"):
            checked.append("浏览器 E2E")
        elif msg.startswith("Browser E2E OK") or "Browser E2E: error modal shown" in msg:
            checked.append("浏览器 E2E（通过/预期弹窗）")
        elif msg.startswith("Browser E2E error") or "Browser E2E failed" in msg:
            checked.append("浏览器 E2E（失败）")
        elif _CORRUPTION.match(msg):
            checked.append("Python 腐化扫描")
        elif _RECORDED_FAILURE.match(msg):
            checked.append("遗留测试脚本")
    # De-dupe while preserving order
    seen: set[str] = set()
    out: list[str] = []
    for item in checked:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _open_issues_sample(issues: list[dict[str, Any]], *, limit: int = _OPEN_SAMPLE) -> list[dict[str, Any]]:
    open_issues = [
        i
        for i in issues
        if i.get("status") in STATUSES_OPEN | {"assigned", "in_progress"}
    ]
    open_issues.sort(
        key=lambda i: (
            _SEVERITY_RANK.get(str(i.get("severity", "unknown")).lower(), 4),
            i.get("created_at") or "",
        )
    )
    return [_issue_brief(i) for i in open_issues[:limit]]


def _briefs_from_titles(titles: list[str]) -> list[dict[str, Any]]:
    return [
        {"id": "", "title": t, "type": "log", "severity": "info", "fix_status": "pending"}
        for t in titles[:12]
    ]


def _round_e2e_from_messages(messages: list[str]) -> dict[str, int]:
    e2e = {"pass": 0, "fail": 0}
    for msg in messages:
        if msg.startswith("Browser E2E starting"):
            continue
        if msg.startswith("Browser E2E error") or "Browser E2E failed" in msg:
            e2e["fail"] += 1
        elif "Browser E2E: error modal shown" in msg or msg.startswith("Browser E2E OK"):
            e2e["pass"] += 1
    return e2e


def _round_summary(
    *,
    round_kind: str,
    newly_discovered: list[dict[str, Any]],
    detected_this_round: list[dict[str, Any]],
    resolved: list[dict[str, Any]],
    still_open: int,
    e2e: dict[str, int],
    reported_new: int,
    checked: list[str],
    check_counts: dict[str, int] | None = None,
    stored_new_from_checks: int = 0,
) -> str:
    n_new = len(newly_discovered)
    n_detected = len(detected_this_round)
    n_res = len(resolved)
    cc = check_counts or {}
    n_checks = cc.get("total", 0)
    e2e_bit = ""
    if e2e.get("pass") or e2e.get("fail"):
        e2e_bit = f"；E2E 通过 {e2e.get('pass', 0)}/失败 {e2e.get('fail', 0)}"

    if round_kind == "baseline":
        n = reported_new or n_new or n_detected
        base = f"基线：累计录入 {n} 项已知问题"
        if still_open:
            base += f"；仍开放 {still_open}"
        return base + e2e_bit

    parts: list[str] = []
    if n_new:
        parts.append(f"新入库 {n_new} 项")
    elif reported_new > 0:
        parts.append(f"新入库 {reported_new} 项")
    else:
        parts.append("新入库 0")

    if n_checks:
        parts.append(
            f"本轮检测 {n_checks} 项（通过 {cc.get('pass', 0)} / 警告 {cc.get('warn', 0)} / 失败 {cc.get('fail', 0)}）"
        )
    elif n_detected:
        parts.append(f"本轮检测 {n_detected} 项（日志项）")

    if n_new == 0 and reported_new == 0 and still_open and n_checks and cc.get("fail", 0) == 0:
        parts.append(f"已知债务 {still_open} 项，本轮无新增")

    if n_res:
        parts.append(f"本轮关闭 {n_res} 项")
    if stored_new_from_checks and not n_new and not reported_new:
        parts.append(f"检查项新入库 {stored_new_from_checks}")
    if not n_checks and checked:
        parts.append("已检查：" + "、".join(checked[:4]))
    return "；".join(parts) + e2e_bit


def _parse_tester_rounds(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One round per Tester run started → done."""
    rounds: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    def _flush() -> None:
        nonlocal current
        if not current:
            return
        current["ended_at"] = current.get("ended_at") or current["started_at"]
        rounds.append(current)
        current = None

    for e in events:
        msg = e.get("msg", "")
        at = _parse_ts(e.get("at"))
        if msg.startswith("Tester run started"):
            _flush()
            current = {
                "started_at": (at or _utc_now()).isoformat(),
                "ended_at": None,
                "messages": [],
                "new_issues_reported": 0,
                "source": "tester",
            }
            continue
        if not current:
            continue
        current["messages"].append(msg)
        if msg.startswith("Browser E2E"):
            pass
        m = _TESTER_DONE.search(msg) or _TESTER_DONE_LEGACY.search(msg)
        if m:
            current["new_issues_reported"] = int(m.group(1))
            if m.group(2) is not None:
                current["check_total"] = int(m.group(2) or 0)
                current["check_pass"] = int(m.group(3) or 0)
                current["check_warn"] = int(m.group(4) or 0)
                current["check_fail"] = int(m.group(5) or 0)
                current["depth"] = m.group(6) or ""
            if m.lastindex and m.lastindex >= 7 and m.group(7) is not None:
                current["suggestions_reported"] = int(m.group(7) or 0)
            current["ended_at"] = (at or _utc_now()).isoformat()
            _flush()

    _flush()
    return rounds


def _issues_created_in_window(
    issues: list[dict[str, Any]], started: datetime, ended: datetime
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for issue in issues:
        created = _parse_ts(issue.get("created_at"))
        if created and started <= created <= ended:
            out.append(issue)
    return out


def _build_inspection_rounds(
    *,
    tester_events: list[dict[str, Any]],
    metrics_dir: Path | None,
    all_issues: list[dict[str, Any]],
    start: datetime,
    end: datetime,
    round_findings: tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]] | None = None,
    round_suggestions: tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    raw_rounds = _parse_tester_rounds(tester_events)
    snaps = _load_metrics_snapshots(metrics_dir, start, end)
    built: list[dict[str, Any]] = []
    findings_by_round, findings_flat = round_findings or ({}, [])
    suggestions_by_round, suggestions_flat = round_suggestions or ({}, [])

    for raw in raw_rounds:
        started = _parse_ts(raw["started_at"]) or start
        ended = _parse_ts(raw.get("ended_at")) or started
        messages = raw.get("messages") or []
        prev_issues, curr_issues, metrics_file = _snapshots_for_interval(snaps, started, ended)
        snapshot_new, resolved_issues, still_open = _diff_snapshots(prev_issues, curr_issues)
        window_new = _issues_created_in_window(all_issues, started, ended)
        # Merge snapshot diff + created_at window (dedupe by fingerprint)
        seen_fp: set[str] = set()
        newly_discovered_issues: list[dict[str, Any]] = []
        for issue in snapshot_new + window_new:
            fp = str(issue.get("fingerprint") or issue.get("id") or "")
            if fp and fp in seen_fp:
                continue
            if fp:
                seen_fp.add(fp)
            newly_discovered_issues.append(issue)

        log_titles = _log_detected_titles(messages)
        checked = _round_checked_items(messages)
        e2e = _round_e2e_from_messages(messages)
        reported_new = int(raw.get("new_issues_reported") or 0)

        stamp = started.strftime("%Y%m%dT%H%M%SZ")
        round_id = f"tester-{stamp}"
        rf_rows = _findings_for_interval(
            by_round=findings_by_round,
            flat=findings_flat,
            round_id=round_id,
            started=started,
            ended=ended,
        )
        check_summary = _summarize_check_items(rf_rows) if rf_rows else None
        if not check_summary and raw.get("check_total"):
            check_summary = {
                "counts": {
                    "total": int(raw.get("check_total") or 0),
                    "pass": int(raw.get("check_pass") or 0),
                    "warn": int(raw.get("check_warn") or 0),
                    "fail": int(raw.get("check_fail") or 0),
                },
                "items": [],
                "stored_new": 0,
            }
        check_counts = (check_summary or {}).get("counts") or {}
        check_items = (check_summary or {}).get("items") or []
        depth = raw.get("depth") or (rf_rows[0].get("depth") if rf_rows else None)
        depth = _depth_label(str(depth) if depth else None, check_counts.get("total", 0))

        newly_briefs = [_issue_brief(i, fix_status="pending") for i in newly_discovered_issues[:20]]
        detected_briefs = _briefs_from_titles(log_titles)
        if not newly_briefs and reported_new > 0 and not detected_briefs:
            newly_briefs = [
                {
                    "id": "",
                    "title": f"Tester 新录入 {reported_new} 项（见 latest_issues.md）",
                    "type": "tester",
                    "severity": "info",
                    "fix_status": "pending",
                }
            ]

        open_sample = _open_issues_sample(curr_issues or all_issues)
        if reported_new >= _BASELINE_NEW_ISSUES or (newly_briefs and reported_new >= 3):
            round_kind = "baseline"
        elif newly_briefs or detected_briefs or reported_new > 0:
            round_kind = "new_findings"
        else:
            round_kind = "retest"
        open_still = (
            open_sample
            if still_open and round_kind in ("retest", "baseline")
            else []
        )

        resolved_briefs = [_issue_brief(i, fix_status="fixed") for i in resolved_issues[:20]]
        sug_rows = _suggestions_for_interval(
            by_round=suggestions_by_round,
            flat=suggestions_flat,
            round_id=round_id,
            started=started,
            ended=ended,
        )
        sug_briefs = _suggestion_briefs(sug_rows)
        summary = _round_summary(
            round_kind=round_kind,
            newly_discovered=newly_briefs,
            detected_this_round=detected_briefs or check_items,
            resolved=resolved_issues,
            still_open=still_open,
            e2e=e2e,
            reported_new=reported_new,
            checked=checked,
            check_counts=check_counts,
            stored_new_from_checks=int((check_summary or {}).get("stored_new") or 0),
        )
        if sug_briefs and not newly_briefs and check_counts.get("fail", 0) == 0:
            summary += f"；改进意见 {len(sug_briefs)} 条（目标对齐）"

        built.append(
            {
                "round_id": round_id,
                "started_at": raw["started_at"],
                "started_at_display": _format_hkt_display(started),
                "ended_at": raw.get("ended_at"),
                "ended_at_display": _format_hkt_display(ended),
                "source": "tester",
                "round_kind": round_kind,
                "metrics_snapshot": metrics_file,
                "checked": checked,
                "check_counts": check_counts,
                "check_items": check_items,
                "check_depth": depth,
                "discovered": newly_briefs,
                "detected_this_round": detected_briefs or check_items,
                "open_still_sample": open_still,
                "resolved_since_last": resolved_briefs,
                "still_open": still_open,
                "e2e_pass": e2e.get("pass", 0),
                "e2e_fail": e2e.get("fail", 0),
                "new_issues_reported": reported_new,
                "improvement_suggestions": sug_briefs,
                "summary": summary,
            }
        )

    # Metrics-only rounds when consecutive snapshots differ but no tester boundary matched
    if snaps and len(snaps) >= 2:
        existing_times = {_parse_ts(r["started_at"]) for r in built}
        for i in range(1, len(snaps)):
            prev_at, prev_path, prev_issues = snaps[i - 1]
            curr_at, curr_path, curr_issues = snaps[i]
            if any(t and abs((t - curr_at).total_seconds()) < 90 for t in existing_times if t):
                continue
            discovered_issues, resolved_issues, still_open = _diff_snapshots(prev_issues, curr_issues)
            if not discovered_issues and not resolved_issues:
                continue
            newly_briefs = [_issue_brief(i, fix_status="pending") for i in discovered_issues[:20]]
            e2e = {"pass": 0, "fail": 0}
            round_kind = "new_findings" if newly_briefs else "retest"
            open_still = _open_issues_sample(curr_issues) if still_open and round_kind == "retest" else []
            summary = _round_summary(
                round_kind=round_kind,
                newly_discovered=newly_briefs,
                detected_this_round=[],
                resolved=resolved_issues,
                still_open=still_open,
                e2e=e2e,
                reported_new=len(discovered_issues),
                checked=["Guardian 指标快照 diff"],
            )
            stamp = curr_at.strftime("%Y%m%dT%H%M%SZ")
            built.append(
                {
                    "round_id": f"metrics-{stamp}",
                    "started_at": curr_at.isoformat(),
                    "started_at_display": _format_hkt_display(curr_at),
                    "ended_at": curr_at.isoformat(),
                    "ended_at_display": _format_hkt_display(curr_at),
                    "source": "metrics",
                    "round_kind": round_kind,
                    "metrics_snapshot": curr_path.name,
                    "checked": ["Guardian 指标快照 diff"],
                    "discovered": newly_briefs,
                    "detected_this_round": [],
                    "open_still_sample": open_still,
                    "resolved_since_last": [_issue_brief(i, fix_status="fixed") for i in resolved_issues[:20]],
                    "still_open": still_open,
                    "e2e_pass": 0,
                    "e2e_fail": 0,
                    "new_issues_reported": len(discovered_issues),
                    "improvement_suggestions": [],
                    "summary": summary,
                }
            )

    for rnd in built:
        if _round_has_finding(rnd) or rnd.get("improvement_suggestions"):
            continue
        rid = rnd.get("round_id") or ""
        started = _parse_ts(rnd.get("started_at")) or start
        ended = _parse_ts(rnd.get("ended_at")) or started
        extra = _suggestions_for_interval(
            by_round=suggestions_by_round,
            flat=suggestions_flat,
            round_id=str(rid),
            started=started,
            ended=ended,
        )
        if extra:
            rnd["improvement_suggestions"] = _suggestion_briefs(extra)
            rnd["summary"] = (rnd.get("summary") or "") + f"；改进意见 {len(extra)} 条（目标对齐）"

    built.sort(key=lambda r: r.get("started_at") or "", reverse=True)
    total = len(built)
    truncated = total > _MAX_INSPECTION_ROUNDS
    rounds = built[:_MAX_INSPECTION_ROUNDS]

    return {
        "rounds": rounds,
        "total_rounds": total,
        "truncated": truncated,
        "definition": (
            "一轮检查 = Tester 日志中一次 run started→done；"
            "新入库=issues.json 指纹去重后新增；本轮检测=round_findings.jsonl 全部检查项（含通过/警告/失败）；"
            "无新 issue 且无 fail 时须产出≥1 条目标对齐改进意见（round_suggestions.jsonl）；"
            "check_depth=basic|standard|deep；"
            "指标轮次 = 相邻 issues_*.json 快照 diff（Guardian ~5min）；"
            "轮次时间为香港时间 (HKT, UTC+8)"
        ),
    }


def _build_timeline(
    *,
    issue_stats: dict[str, Any],
    tester: dict[str, Any],
    scheduler: dict[str, Any],
    metrics_timeline: list[dict[str, Any]],
    dev_entries: list[dict[str, Any]],
    start: datetime,
    end: datetime,
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []

    for pt in metrics_timeline[-6:]:
        items.append(
            {
                "at": pt["at"],
                "kind": "metrics",
                "title": f"指标快照：{pt['open_count']} 条开放 / 共 {pt['total']} 条",
                "detail": pt["file"],
            }
        )

    for entry in dev_entries:
        at = _parse_ts(entry.get("at"))
        if not _in_window(at, start, end):
            continue
        items.append(
            {
                "at": entry.get("at"),
                "kind": entry.get("kind", "event"),
                "title": entry.get("title", ""),
                "detail": entry.get("detail", ""),
                "category": entry.get("category"),
            }
        )

    e2e = tester.get("browser_e2e") or {}
    if e2e.get("runs"):
        items.append(
            {
                "at": end.isoformat(),
                "kind": "browser_e2e",
                "title": f"浏览器 E2E：{e2e.get('runs', 0)} 次运行（通过 {e2e.get('pass', 0)} / 失败 {e2e.get('fail', 0)}）",
                "detail": "含 error modal 预期场景计为通过",
            }
        )

    if scheduler.get("unique_assignments"):
        items.append(
            {
                "at": end.isoformat(),
                "kind": "scheduler",
                "title": f"Scheduler 分派 {scheduler['unique_assignments']} 次（去重）",
                "detail": json.dumps(scheduler.get("by_executor") or {}, ensure_ascii=False),
            }
        )

    items.sort(key=lambda x: x.get("at") or "", reverse=True)
    return items[:24]


def _load_dev_entries(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    return list(data.get("entries") or [])


def build_report(*, window_hours: float = 10.0, cfg: dict | None = None) -> dict[str, Any]:
    cfg = cfg or load_config()
    layout = ensure_layout(cfg)
    end = _utc_now()
    start = end - timedelta(hours=window_hours)

    issues = IssueStore(layout["issues"]).list_issues()
    issue_stats = _aggregate_issues(issues, start, end)

    logs_dir = layout["logs"]
    log_paths = sorted(logs_dir.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    tester_events: list[dict[str, Any]] = []
    scheduler_events: list[dict[str, Any]] = []
    improver_events: list[dict[str, Any]] = []
    for lp in log_paths[:6]:
        name = lp.stem.lower()
        parsed = _parse_log_file(lp, start, end)
        ev = parsed.get("events") or []
        if "tester" in name:
            tester_events.extend(ev)
        elif "scheduler" in name:
            scheduler_events.extend(ev)
        elif "improver" in name:
            improver_events.extend(ev)

    tester_summary = _summarize_tester(tester_events)
    scheduler_summary = _summarize_scheduler(scheduler_events)
    improver_summary = _summarize_improver(
        improver_events,
        layout["reports"] / "improvement_suggestions.jsonl",
        start,
        end,
    )

    metrics_dir = _metrics_dir(cfg)
    metrics_timeline = _metrics_timeline(metrics_dir, start, end)
    round_findings = _load_round_findings(layout["reports"])  # (by_round, flat)
    round_suggestions = load_suggestions(layout["reports"])
    inspection_rounds = _build_inspection_rounds(
        tester_events=tester_events,
        metrics_dir=metrics_dir,
        all_issues=issues,
        start=start,
        end=end,
        round_findings=round_findings,
        round_suggestions=round_suggestions,
    )
    dev_entries = _load_dev_entries(layout["reports"] / "dev_log_entries.json")

    timeline = _build_timeline(
        issue_stats=issue_stats,
        tester=tester_summary,
        scheduler=scheduler_summary,
        metrics_timeline=metrics_timeline,
        dev_entries=dev_entries,
        start=start,
        end=end,
    )

    metrics_path_str = str(metrics_dir) if metrics_dir else ""

    return {
        "meta": {
            "version": 2,
            "built_at": end.isoformat(),
            "window_hours": window_hours,
            "window_start": start.isoformat(),
            "window_end": end.isoformat(),
            "project_root": str(cfg["_project_root"]),
            "metrics_dir": metrics_path_str,
        },
        "summary": {
            "discovered": issue_stats["discovered_count"],
            "resolved_automation": issue_stats["resolved_automation_count"],
            "resolved_manual": issue_stats["resolved_manual_count"],
            "still_open": issue_stats["still_open_count"],
            "tester_runs": tester_summary["runs"],
            "browser_e2e_runs": tester_summary["browser_e2e"]["runs"],
            "browser_e2e_pass": tester_summary["browser_e2e"]["pass"],
            "browser_e2e_fail": tester_summary["browser_e2e"]["fail"],
            "scheduler_assignments": scheduler_summary["unique_assignments"],
            "improver_suggestions": improver_summary["suggestions_count"],
            "metrics_snapshots": len(metrics_timeline),
            "inspection_rounds": len(inspection_rounds.get("rounds") or []),
        },
        "inspection_rounds": inspection_rounds,
        "issues": issue_stats,
        "tester": tester_summary,
        "scheduler": scheduler_summary,
        "improver": improver_summary,
        "metrics_timeline": metrics_timeline,
        "timeline": timeline,
        "links": {
            "latest_issues_md": "automation/reports/latest_issues.md",
            "automation_outcomes_json": "automation/reports/automation_outcomes.json",
            "metrics_dir": metrics_path_str,
        },
        "labels": {
            "resolved_automation": "自动化直接关闭",
            "resolved_manual": "检测后人工/协作处理",
            "still_open": "仍开放",
            "discovered": "窗口内新入库",
            "round_checks": "本轮检测（含通过/警告/失败）",
            "stored_new": "新入库（指纹去重）",
        },
    }


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    tmp.replace(path)


def _markdown_section(report: dict[str, Any]) -> str:
    s = report["summary"]
    meta = report["meta"]
    issues = report["issues"]
    tester = report["tester"]
    e2e = tester.get("browser_e2e") or {}
    lines = [
        "## 自动化运行成果（机器生成）",
        "",
        f"_生成时间：{meta['built_at']} · 统计窗口：最近 {meta['window_hours']} 小时_",
        "",
        "### 摘要",
        "",
        "| 指标 | 数量 | 说明 |",
        "|------|------|------|",
        f"| 新入库问题 | {s['discovered']} | 按 `created_at` 落在窗口内（指纹去重） |",
        f"| 自动化直接关闭 | {s['resolved_automation']} | `issues.json` 中 `resolved` 且归因自动化 |",
        f"| 人工/协作处理 | {s['resolved_manual']} | resolved 但 fixer 文档化或未改代码 |",
        f"| 仍开放 | {s['still_open']} | open / assigned / in_progress |",
        f"| Tester 轮次 | {s['tester_runs']} | 日志中 run started |",
        f"| 浏览器 E2E | {s['browser_e2e_runs']} | 通过 {s['browser_e2e_pass']} / 失败 {s['browser_e2e_fail']} |",
        f"| Scheduler 分派（去重） | {s['scheduler_assignments']} | |",
        f"| Improver 建议 | {s['improver_suggestions']} | `improvement_suggestions.jsonl` |",
        f"| 指标快照 | {s['metrics_snapshots']} | metrics 目录 |",
        "",
    ]

    if issues.get("discovered_by_type"):
        lines.extend(["### 新发现按类型", "", "```json", json.dumps(issues["discovered_by_type"], ensure_ascii=False, indent=2), "```", ""])

    if report.get("metrics_timeline"):
        lines.extend(["### 指标时间线（节选）", ""])
        for pt in report["metrics_timeline"][-8:]:
            lines.append(f"- `{pt['at']}` — 开放 {pt['open_count']} / 共 {pt['total']}（{pt['file']}）")
        lines.append("")

    if report.get("timeline"):
        lines.extend(["### 时间线（节选）", ""])
        for item in report["timeline"][:12]:
            at = (item.get("at") or "")[:19].replace("T", " ")
            lines.append(f"- **{at}** [{item.get('kind', '')}] {item.get('title', '')}")
        lines.append("")

    ir = report.get("inspection_rounds") or {}
    rounds = ir.get("rounds") or []
    if rounds:
        lines.extend(["### 检查轮次（节选，最新优先）", ""])
        for rnd in rounds[:8]:
            at = rnd.get("started_at_display") or _format_hkt_display(_parse_ts(rnd.get("started_at")))
            disc = len(rnd.get("discovered") or [])
            cc = rnd.get("check_counts") or {}
            chk = cc.get("total", len(rnd.get("check_items") or []))
            closed = len(rnd.get("resolved_since_last") or [])
            depth = rnd.get("check_depth", "")
            depth_bit = f" [{depth}]" if depth else ""
            lines.append(
                f"- **{at}**{depth_bit} — {rnd.get('summary', '')} "
                f"（新入库 {disc} / 本轮检测 {chk} / 关 {closed} / 开放 {rnd.get('still_open', 0)}）"
            )
        if ir.get("truncated"):
            lines.append(f"- _另有 {ir.get('total_rounds', 0) - len(rounds)} 轮未列出，见 dev-log.html_")
        lines.append("")

    lines.extend(
        [
            f"完整 JSON：`automation/reports/automation_outcomes.json` · 开放问题列表：`automation/reports/latest_issues.md`",
            "",
        ]
    )
    if meta.get("metrics_dir"):
        lines.append(f"历史指标目录：`{meta['metrics_dir']}`")
        lines.append("")

    return "\n".join(lines)


def _patch_dev_process_log(md_path: Path, section: str) -> None:
    if not md_path.is_file():
        return
    text = md_path.read_text(encoding="utf-8")
    start_m, end_m = _AUTO_MARKERS
    if start_m in text and end_m in text:
        before, rest = text.split(start_m, 1)
        _, after = rest.split(end_m, 1)
        new_text = f"{before}{start_m}\n\n{section.rstrip()}\n\n{end_m}{after}"
    else:
        anchor = "## 如何更新本记录"
        if anchor in text:
            new_text = text.replace(
                anchor,
                f"{start_m}\n\n{section.rstrip()}\n\n{end_m}\n\n---\n\n{anchor}",
            )
        else:
            new_text = text.rstrip() + f"\n\n{start_m}\n\n{section.rstrip()}\n\n{end_m}\n"
    md_path.write_text(new_text, encoding="utf-8")


def write_reports(
    report: dict[str, Any],
    *,
    update_markdown: bool = True,
    layout: dict[str, Path] | None = None,
) -> Path:
    layout = layout or ensure_layout()
    out_json = layout["reports"] / "automation_outcomes.json"
    _write_json(out_json, report)

    md_snippet = layout["reports"] / "automation_outcomes.md"
    md_snippet.write_text(_markdown_section(report), encoding="utf-8")

    if update_markdown:
        md_doc = layout["root"] / "docs" / "DEV_PROCESS_LOG.md"
        _patch_dev_process_log(md_doc, _markdown_section(report))

    return out_json


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build automation outcomes report for dev log")
    parser.add_argument("--hours", type=float, default=10.0, help="Lookback window in hours")
    parser.add_argument("--no-markdown", action="store_true", help="Skip patching DEV_PROCESS_LOG.md")
    args = parser.parse_args(argv)

    report = build_report(window_hours=args.hours)
    path = write_reports(report, update_markdown=not args.no_markdown)
    print(f"Wrote {path}")
    print(json.dumps(report["summary"], indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
