"""
Reference: throttle external discovery channels (copy into your project's automation/).

No third-party dependencies. Integrate from Tester before browser_e2e / live API probes:

    from external_touch_guard import try_acquire, record_use, seconds_until_allowed

    allowed, msg = try_acquire(cfg, "browser_e2e", force=manual_run, logger=log)
    if not allowed:
        append_throttled_channel_report(...)
        return
    try:
        run_e2e(...)
        record_use(cfg, "browser_e2e", "pass")
    except Exception as e:
        record_use(cfg, "browser_e2e", "error", detail=str(e))
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

__all__ = [
    "seconds_until_allowed",
    "try_acquire",
    "record_use",
    "format_wait_human",
    "append_throttled_channel_report",
]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _state_path(cfg: dict, automation_dir: Path) -> Path:
    guard = _guard_cfg(cfg)
    rtl = guard.get("state_file") or "state/external_touch_usage.json"
    path = Path(rtl)
    if not path.is_absolute():
        path = automation_dir / path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


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
    base = cfg.get("external_touch_guard") or cfg.get("notebooklm_guard") or {}
    if not isinstance(base, dict):
        base = {}
    default_interval = int(base.get("min_interval_sec", 21_600))
    channels = base.get("channels") if isinstance(base.get("channels"), dict) else {}
    return {
        "enabled": bool(base.get("enabled", True)),
        "min_interval_sec": max(60, default_interval),
        "channels": channels,
        "max_events": int(base.get("max_events", 50)),
        "state_file": base.get("state_file"),
    }


def _interval_for(cfg: dict, purpose: str) -> int:
    g = _guard_cfg(cfg)
    ch = g["channels"].get(purpose)
    if isinstance(ch, dict) and ch.get("min_interval_sec") is not None:
        return max(60, int(ch["min_interval_sec"]))
    return g["min_interval_sec"]


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
    cfg: dict,
    purpose: str,
    automation_dir: Path,
    *,
    force: bool = False,
) -> float:
    if force:
        return 0.0
    g = _guard_cfg(cfg)
    if not g["enabled"]:
        return 0.0
    interval = _interval_for(cfg, purpose)
    state = _load_state(_state_path(cfg, automation_dir))
    last = _last_event_ts(state.get("events", []), purpose)
    if last is None:
        return 0.0
    remaining = interval - (time.time() - last)
    return remaining if remaining > 0 else 0.0


def try_acquire(
    cfg: dict,
    purpose: str,
    automation_dir: Path,
    *,
    force: bool = False,
    logger=None,
) -> tuple[bool, str]:
    wait = seconds_until_allowed(cfg, purpose, automation_dir, force=force)
    if wait <= 0:
        path = _state_path(cfg, automation_dir)
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

    msg = (
        f"External channel throttled ({purpose}): "
        f"wait {int(wait)}s (~{wait / 3600:.1f}h)"
    )
    if logger:
        logger.info(msg)
    return False, msg


def record_use(
    cfg: dict,
    purpose: str,
    automation_dir: Path,
    outcome: str,
    *,
    detail: str = "",
) -> None:
    path = _state_path(cfg, automation_dir)
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
        return f"{int(seconds)}s"
    if seconds < 7200:
        return f"{int(seconds / 60)}m"
    return f"{seconds / 3600:.1f}h"


def append_throttled_channel_report(
    reports_dir: Path,
    *,
    channel: str,
    wait_sec: float,
    round_id: str = "",
) -> None:
    reports_dir.mkdir(parents=True, exist_ok=True)
    path = reports_dir / "throttled_channels.jsonl"
    line = json.dumps(
        {
            "ts": _utc_now_iso(),
            "channel": channel,
            "wait_sec": round(wait_sec, 1),
            "round_id": round_id,
        },
        ensure_ascii=False,
    )
    with path.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
