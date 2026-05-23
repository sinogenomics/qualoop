"""Append resolved-issue events to dev_log_entries.json for dev-log.html."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .paths import ensure_layout


def _entries_path() -> Path:
    return ensure_layout()["reports"] / "dev_log_entries.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"meta": {"version": 1, "updated_at": _utc_now()}, "entries": []}
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _save(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data.setdefault("meta", {})["updated_at"] = _utc_now()
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    tmp.replace(path)


def append_resolved_issue(issue: dict[str, Any], *, note: str = "") -> None:
    """Record a resolved issue for the dev-log UI."""
    path = _entries_path()
    data = _load(path)
    entry = {
        "at": issue.get("updated_at") or _utc_now(),
        "kind": "resolved",
        "category": issue.get("type", "unknown"),
        "title": (issue.get("description") or "")[:120],
        "detail": note or (issue.get("metadata") or {}).get("executor_note", ""),
        "paths": issue.get("paths") or [],
        "issue_id": issue.get("id"),
        "automation_only": True,
    }
    data.setdefault("entries", []).append(entry)
    _save(path, data)


def append_detected_issue(issue: dict[str, Any]) -> None:
    """Optional: record newly created issues (not wired by default)."""
    path = _entries_path()
    data = _load(path)
    entry = {
        "at": issue.get("created_at") or _utc_now(),
        "kind": "detected",
        "category": issue.get("type", "unknown"),
        "title": (issue.get("description") or "")[:120],
        "detail": "",
        "paths": issue.get("paths") or [],
        "issue_id": issue.get("id"),
        "automation_only": True,
    }
    data.setdefault("entries", []).append(entry)
    _save(path, data)
