"""Improver executor: improvement scripts and suggestions."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from ..goal_context import goal_rejection_reason
from ..issue_store import IssueStore
from ..reports import write_latest_snapshot
from ..round_suggestions import append_suggestion, new_suggestion_id
from .base import complete_issue, run_executor_loop


def _run_improvement_script(project_root: Path, logger) -> str:
    candidates = [
        "intelligent_optimizer.py",
        "improvement_tracker.py",
        "continuous_improver.py",
    ]
    for name in candidates:
        path = project_root / name
        if not path.is_file():
            continue
        try:
            proc = subprocess.run(
                [sys.executable, str(path)],
                cwd=str(project_root),
                capture_output=True,
                text=True,
                timeout=180,
                encoding="utf-8",
                errors="replace",
            )
            if proc.returncode == 0:
                return f"Ran {name} successfully"
            return f"{name} exited {proc.returncode}: {(proc.stderr or proc.stdout)[-500:]}"
        except Exception as e:
            return f"{name} error: {e}"
    return "No improvement script available"


def _append_suggestion(
    project_root: Path,
    issue: dict,
    message: str,
    *,
    cfg: dict | None = None,
    logger=None,
) -> bool:
    cfg = cfg or {}
    strict = bool(cfg.get("goal_alignment_strict", True))
    reason = goal_rejection_reason(message, strict=strict)
    if reason:
        if logger:
            logger.warning(
                "Improver rejected misaligned suggestion (%s): %s",
                reason,
                message[:120],
            )
        return False
    reports = project_root / "automation" / "reports"
    round_id = f"improver-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    row = {
        "id": new_suggestion_id(),
        "round_id": round_id,
        "ts": datetime.now(timezone.utc).isoformat(),
        "text": message,
        "rationale": f"Improver follow-up for issue {issue.get('id', '')[:8]}",
        "goal_alignment": True,
        "priority": "medium",
        "category": "improvement",
        "issue_id": issue.get("id"),
    }
    return append_suggestion(row, reports, logger, strict=strict) is not None


def handle_improve(issue: dict, store: IssueStore, cfg: dict, logger) -> None:
    project_root: Path = cfg["_project_root"]
    iid = issue["id"]

    # Antigravity LLM Integration for Improver
    try:
        from ..llm_client import get_llm_config, call_antigravity_llm
        llm_cfg = get_llm_config(project_root)
        if llm_cfg.get("provider") == "antigravity":
            prompt = (
                f"[Qualoop Improver Agent - System Optimization Session]\n"
                f"We are executing an improvement ticket: '{issue.get('description')}'.\n"
                f"Paths involved: {issue.get('paths')}\n\n"
                f"Please open a session in the user's active IDE session to recommend and apply 3 high-impact K-12 learning material optimizations or system optimizations (e.g. accelerating first download times, improving infographic rendering, adding responsive CSS transitions). Respond in Chinese with clear code proposals."
            )
            model = llm_cfg.get("model", "flash")
            ai_ret = call_antigravity_llm(project_root, prompt, model=model)
            logger.info("Improver initiated Antigravity IDE optimization session: %s", ai_ret)
            
            _append_suggestion(
                project_root,
                issue,
                f"Antigravity Optimizer recommended optimizations: {ai_ret}",
                cfg=cfg,
                logger=logger
            )
            
            complete_issue(store, iid, resolved=True, note=f"Antigravity Optimization Session: {ai_ret}")
            write_latest_snapshot(store)
            return
    except Exception as e:
        logger.warning("Failed to invoke Antigravity LLM for Improver: %s", e)

    result = _run_improvement_script(project_root, logger)
    _append_suggestion(project_root, issue, result, cfg=cfg, logger=logger)
    logger.info("Improver: %s", result[:120])

    complete_issue(store, iid, resolved=True, note=result)
    write_latest_snapshot(store)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Improver executor")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--loop", action="store_true")
    args = parser.parse_args(argv)
    run_executor_loop("improver", handle_improve, once=not args.loop)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
