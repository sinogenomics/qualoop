"""Verifier executor: re-runs targeted checks and closes issues that no longer reproduce."""
from __future__ import annotations

import argparse
import io
import sys
import time
from pathlib import Path

# Force UTF-8 encoding on standard streams for Windows command prompts
if sys.platform == "win32":
    if not hasattr(sys.stdout, "_is_utf8_wrapped"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stdout._is_utf8_wrapped = True
    if not hasattr(sys.stderr, "_is_utf8_wrapped"):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
        sys.stderr._is_utf8_wrapped = True

from ..issue_store import IssueStore
from ..reports import write_latest_snapshot
from ..tester import _health_probe_url, _http_probe, run_legacy_script
from .base import complete_issue, run_executor_loop


def _probe_health(cfg: dict, backend_url: str, timeout: float = 10.0) -> tuple[bool, str, float]:
    url = _health_probe_url(cfg, backend_url.rstrip("/"))
    return _http_probe(url, timeout=timeout)


def _verify_performance(issue: dict, cfg: dict) -> tuple[bool, str]:
    """Re-probe target URL; close if at least one sample is under threshold."""
    md = issue.get("metadata") or {}
    backend = cfg.get("backend_url", "http://localhost:5000").rstrip("/")
    url = md.get("url") or f"{backend}/api/health"
    if "/api/health" in url.split("?")[0] and "notebooklm=" not in url:
        url = _health_probe_url(cfg, backend)
    threshold = float(md.get("threshold_ms")
                      or cfg.get("tester", {}).get("health_slow_ms", 3000))
    samples = int(cfg.get("verifier", {}).get("perf_samples", 3))
    timings: list[float] = []
    for _ in range(samples):
        ok, _detail, ms = _http_probe(url, timeout=10.0)
        if ok:
            timings.append(ms)
        time.sleep(0.3)
    if not timings:
        return False, f"perf re-probe {url}: all samples failed"
    best = min(timings)
    avg = sum(timings) / len(timings)
    note = (
        f"perf re-probe {url}: samples={len(timings)} best={best:.0f}ms "
        f"avg={avg:.0f}ms threshold={threshold:.0f}ms"
    )
    return best <= threshold, note


def _verify_health(issue: dict, cfg: dict) -> tuple[bool, str]:
    backend = cfg.get("backend_url", "http://localhost:5000")
    md = issue.get("metadata") or {}
    url = md.get("url") or f"{backend.rstrip('/')}/api/health"
    if "/api/health" in url.split("?")[0] and "notebooklm=" not in url:
        url = _health_probe_url(cfg, backend.rstrip("/"))
    ok, detail, ms = _http_probe(url, timeout=10.0)
    return ok, f"health {url}: {'OK' if ok else 'FAIL'} {ms:.0f}ms — {detail[:120]}"


def _verify_python(project_root: Path, paths: list[str]) -> tuple[bool, str]:
    notes = []
    for p in paths:
        if not p.endswith(".py"):
            continue
        ok, out = run_legacy_script(project_root, p, timeout=90)
        notes.append(f"{p}: {'OK' if ok else 'FAIL'}")
        if not ok:
            return False, "\n".join(notes) + "\n" + out[-600:]
    return True, "\n".join(notes) or "python verification passed"


def _verify_generic(project_root: Path, issue: dict, cfg: dict) -> tuple[bool, str]:
    paths = issue.get("paths") or []
    if any(p.endswith(".py") for p in paths):
        ok, note = _verify_python(project_root, paths)
        if not ok:
            return False, note
    if issue.get("type") == "verification":
        ok, hnote = _verify_health(issue, cfg)
        return ok, hnote
    return True, "no re-probe channel; nothing to invalidate"


def handle_verify(issue: dict, store: IssueStore, cfg: dict, logger) -> None:
    project_root: Path = cfg["_project_root"]
    iid = issue["id"]
    itype = issue.get("type", "")

    if itype == "verification":
        parent_id = (issue.get("metadata") or {}).get("parent_issue")
        if parent_id:
            parent = store.get(parent_id)
            if parent and parent.get("status") in ("resolved", "wontfix", "duplicate"):
                pstatus = parent.get("status")
                if pstatus == "resolved":
                    complete_issue(
                        store,
                        iid,
                        resolved=True,
                        note=f"parent {parent_id[:8]} already resolved",
                    )
                else:
                    store.update(
                        iid,
                        status=pstatus,
                        assigned_executor=None,
                        metadata={
                            **(issue.get("metadata") or {}),
                            "executor_note": (
                                f"parent {parent_id[:8]} terminal as {pstatus}"
                            ),
                        },
                    )
                logger.info(
                    "Verifier closed orphan verification %s (parent %s)",
                    iid[:8],
                    pstatus,
                )
                write_latest_snapshot(store)
                return

    try:
        if itype == "performance":
            ok, detail = _verify_performance(issue, cfg)
        elif itype == "health":
            ok, detail = _verify_health(issue, cfg)
        elif itype == "browser_e2e":
            from ..browser_e2e import run_browser_e2e
            res = run_browser_e2e(cfg, store, logger)
            ok = res.get("step_reached") == "step3_success"
            detail = f"browser_e2e re-probe reached step: {res.get('step_reached')}"
        else:
            ok, detail = _verify_generic(project_root, issue, cfg)
    except Exception as e:  # noqa: BLE001
        ok, detail = False, f"verifier error: {e}"

    if ok:
        complete_issue(store, iid, resolved=True, note=detail)
        logger.info("Verifier resolved %s (%s): %s", iid[:8], itype, detail[:160])
        parent = (issue.get("metadata") or {}).get("parent_issue")
        if parent:
            parent_issue = store.get(parent)
            if parent_issue and parent_issue.get("status") in ("open", "assigned", "in_progress"):
                complete_issue(
                    store,
                    parent,
                    resolved=True,
                    note=f"verified via {iid[:8]}: {detail[:200]}",
                )
                logger.info("Verifier also resolved parent %s", parent[:8])
    else:
        complete_issue(store, iid, resolved=False, note=detail)
        logger.info("Verifier kept %s open (%s): %s", iid[:8], itype, detail[:160])
    write_latest_snapshot(store)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verifier executor")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--loop", action="store_true")
    args = parser.parse_args(argv)
    run_executor_loop("verifier", handle_verify, once=not args.loop)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
