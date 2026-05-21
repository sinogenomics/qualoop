"""Throttle automation paths that call NotebookLM (avoid rate limits /风控)."""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .paths import automation_dir, ensure_layout


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _state_path(cfg: dict) -> Path:
    layout = ensure_layout(cfg)
    state_dir = layout["automation"] / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir / "notebooklm_usage.json"


def _load_state(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"events": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("events"), list):
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return {"events": []}


def _save_state(path: Path, data: dict[str, Any]) -> None:
    data["updated_at"] = _utc_now_iso()
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _guard_cfg(cfg: dict) -> dict[str, Any]:
    base = cfg.get("notebooklm_guard") or {}
    if not isinstance(base, dict):
        base = {}
    enabled = base.get("enabled", cfg.get("notebooklm_guard_enabled", True))
    default_interval = int(
        base.get(
            "min_interval_sec",
            cfg.get("notebooklm_automation_min_interval_sec", 21_600),
        )
    )
    return {
        "enabled": bool(enabled),
        "min_interval_sec": max(60, default_interval),
        "browser_e2e_min_interval_sec": int(
            base.get(
                "browser_e2e_min_interval_sec",
                cfg.get("browser_e2e_min_interval_sec", default_interval),
            )
        ),
        "max_events": int(base.get("max_events", 50)),
    }


def _last_event_ts(events: list[dict], purpose: str | None = None) -> float | None:
    last: float | None = None
    for ev in events:
        if purpose and ev.get("purpose") != purpose:
            continue
        raw = ev.get("ts_unix")
        if raw is None:
            continue
        try:
            ts = float(raw)
        except (TypeError, ValueError):
            continue
        if last is None or ts > last:
            last = ts
    return last


def seconds_until_allowed(
    cfg: dict, purpose: str, *, force: bool = False
) -> float:
    """Return 0 if allowed now, else seconds to wait."""
    if force:
        return 0.0
    g = _guard_cfg(cfg)
    if not g["enabled"]:
        return 0.0
    interval = g["min_interval_sec"]
    if purpose == "browser_e2e":
        interval = g["browser_e2e_min_interval_sec"]
    state = _load_state(_state_path(cfg))
    last = _last_event_ts(state.get("events", []), purpose)
    if last is None:
        return 0.0
    elapsed = time.time() - last
    remaining = interval - elapsed
    return remaining if remaining > 0 else 0.0


def try_acquire(
    cfg: dict,
    purpose: str,
    *,
    force: bool = False,
    logger=None,
) -> tuple[bool, str]:
    """
    Return (allowed, message).
    Records a reservation timestamp when allowed (call record_use after work finishes).
    """
    wait = seconds_until_allowed(cfg, purpose, force=force)
    if wait <= 0:
        path = _state_path(cfg)
        state = _load_state(path)
        events = list(state.get("events", []))
        events.append(
            {
                "purpose": purpose,
                "ts": _utc_now_iso(),
                "ts_unix": time.time(),
                "status": "started",
            }
        )
        g = _guard_cfg(cfg)
        state["events"] = events[-g["max_events"] :]
        _save_state(path, state)
        return True, "ok"

    hours = wait / 3600.0
    msg = (
        f"NotebookLM automation throttled ({purpose}): "
        f"wait {int(wait)}s (~{hours:.1f}h) to avoid风控"
    )
    if logger:
        logger.info(msg)
    return False, msg


def record_use(
    cfg: dict,
    purpose: str,
    outcome: str,
    *,
    detail: str = "",
) -> None:
    path = _state_path(cfg)
    state = _load_state(path)
    events = list(state.get("events", []))
    events.append(
        {
            "purpose": purpose,
            "ts": _utc_now_iso(),
            "ts_unix": time.time(),
            "status": outcome,
            "detail": (detail or "")[:300],
        }
    )
    g = _guard_cfg(cfg)
    state["events"] = events[-g["max_events"] :]
    _save_state(path, state)


def format_wait_human(seconds: float) -> str:
    if seconds < 90:
        return f"{int(seconds)} 秒"
    if seconds < 7200:
        return f"{int(seconds / 60)} 分钟"
    return f"{seconds / 3600:.1f} 小时"
