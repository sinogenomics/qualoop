"""Per-round check findings (pass/fail/warn) — independent of issue-store dedupe."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class RoundFindings:
    """Collects all checks for one tester run; written to round_findings.jsonl."""

    def __init__(self, round_id: str, *, depth: str = "standard") -> None:
        self.round_id = round_id
        self.depth = depth
        self.started_at = _utc_now()
        self._items: list[dict[str, Any]] = []

    def add(
        self,
        check_id: str,
        name: str,
        status: str,
        detail: str = "",
        *,
        category: str = "general",
        new_issue: bool = False,
        extra: dict[str, Any] | None = None,
    ) -> None:
        if status not in ("pass", "fail", "warn"):
            raise ValueError(f"invalid status: {status}")
        row: dict[str, Any] = {
            "round_id": self.round_id,
            "at": _utc_now(),
            "depth": self.depth,
            "check_id": check_id,
            "name": name,
            "category": category,
            "status": status,
            "detail": (detail or "")[:2000],
            "new_issue": bool(new_issue),
        }
        if extra:
            row.update(extra)
        self._items.append(row)

    @property
    def items(self) -> list[dict[str, Any]]:
        return list(self._items)

    def counts(self) -> dict[str, int]:
        c = {"pass": 0, "fail": 0, "warn": 0, "total": len(self._items)}
        for it in self._items:
            c[it["status"]] = c.get(it["status"], 0) + 1
        return c

    def append_jsonl(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            for row in self._items:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        return path

    def summary_line(self, new_issues: int) -> str:
        c = self.counts()
        return (
            f"Tester done: {new_issues} new issues, "
            f"{c['total']} checks (pass={c['pass']} warn={c['warn']} fail={c['fail']}), "
            f"depth={self.depth}"
        )
