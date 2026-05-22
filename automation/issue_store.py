# -*- coding: utf-8 -*-
"""JSON issue store with dedupe and single-writer locking."""
from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .locks import store_lock
from .paths import ensure_layout

STATUSES_OPEN = frozenset({"open", "assigned", "in_progress"})
STATUSES_TERMINAL = frozenset({"resolved", "wontfix", "duplicate"})


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _fingerprint(issue_type: str, description: str, paths: list[str] | None = None) -> str:
    norm_desc = re.sub(r'0x[0-9a-fA-F]+|[0-9a-fA-F]{8}\b', '', description.strip())
    blob = f"{issue_type}\n{norm_desc}"
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


class IssueStore:
    def __init__(self, issues_path: Path | None = None):
        layout = ensure_layout()
        self.path = issues_path or layout["issues"]
        if not self.path.exists():
            self._write_unlocked({"issues": [], "meta": {"version": 1}})

    def _read_unlocked(self) -> dict[str, Any]:
        with self.path.open(encoding="utf-8") as f:
            return json.load(f)

    def _write_unlocked(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        tmp.replace(self.path)

    def list_issues(self, status_filter: set[str] | None = None) -> list[dict[str, Any]]:
        with store_lock():
            data = self._read_unlocked()
            issues = data.get("issues", [])
            if status_filter:
                return [i for i in issues if i.get("status") in status_filter]
            return list(issues)

    def get(self, issue_id: str) -> dict[str, Any] | None:
        for issue in self.list_issues():
            if issue.get("id") == issue_id:
                return issue
        return None

    def add(
        self,
        *,
        severity: str,
        issue_type: str,
        description: str,
        paths: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Add issue if not duplicate. Returns issue or None if deduped."""
        fp = _fingerprint(issue_type, description, paths)
        now = _utc_now()
        with store_lock():
            data = self._read_unlocked()
            for existing in data.get("issues", []):
                if existing.get("fingerprint") == fp and existing.get("status") not in STATUSES_TERMINAL:
                    if paths:
                        existing_paths = existing.setdefault("paths", [])
                        for p in paths:
                            if p not in existing_paths:
                                existing_paths.append(p)
                        existing["paths"] = sorted(existing_paths)
                        existing["updated_at"] = now
                        self._write_unlocked(data)
                    return None
            issue = {
                "id": str(uuid.uuid4()),
                "severity": severity,
                "type": issue_type,
                "description": description,
                "status": "open",
                "assigned_executor": None,
                "paths": paths or [],
                "fingerprint": fp,
                "metadata": metadata or {},
                "created_at": now,
                "updated_at": now,
            }
            data.setdefault("issues", []).append(issue)
            self._write_unlocked(data)
            return issue

    def update(self, issue_id: str, **fields: Any) -> dict[str, Any] | None:
        with store_lock():
            data = self._read_unlocked()
            for issue in data.get("issues", []):
                if issue.get("id") != issue_id:
                    continue
                for key, value in fields.items():
                    if key in ("id", "fingerprint", "created_at"):
                        continue
                    issue[key] = value
                issue["updated_at"] = _utc_now()
                self._write_unlocked(data)
                return dict(issue)
        return None

    def assign(self, issue_id: str, executor: str, lease_until: str | None = None) -> bool:
        with store_lock():
            data = self._read_unlocked()
            for issue in data.get("issues", []):
                if issue.get("id") != issue_id:
                    continue
                if issue.get("status") in STATUSES_TERMINAL:
                    return False
                if issue.get("assigned_executor") and issue.get("status") == "in_progress":
                    return False
                issue["assigned_executor"] = executor
                issue["status"] = "assigned"
                issue["lease_until"] = lease_until
                issue["updated_at"] = _utc_now()
                self._write_unlocked(data)
                return True
        return False

    @staticmethod
    def calculate_fingerprint(issue_type: str, description: str, paths: list[str] | None = None) -> str:
        return _fingerprint(issue_type, description, paths)

    def add_candidate(
        self,
        severity: str,
        issue_type: str,
        description: str,
        paths: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        fp = _fingerprint(issue_type, description, paths)
        now = _utc_now()
        with store_lock():
            data = self._read_unlocked()
            for existing in data.get("issues", []):
                if existing.get("fingerprint") == fp and existing.get("status") not in STATUSES_TERMINAL:
                    if paths:
                        existing_paths = existing.setdefault("paths", [])
                        for p in paths:
                            if p not in existing_paths:
                                existing_paths.append(p)
                        existing["paths"] = sorted(existing_paths)
                    if metadata:
                        existing.setdefault("metadata", {}).update(metadata)
                    existing["updated_at"] = now
                    self._write_unlocked(data)
                    return existing
            issue = {
                "id": str(uuid.uuid4()),
                "severity": severity,
                "type": issue_type,
                "description": description,
                "status": "open",
                "assigned_executor": None,
                "paths": paths or [],
                "fingerprint": fp,
                "metadata": metadata or {},
                "created_at": now,
                "updated_at": now,
            }
            data.setdefault("issues", []).append(issue)
            self._write_unlocked(data)
            return issue

    def resolve_missing(self, active_fingerprints: set[str]) -> int:
        now = _utc_now()
        resolved_count = 0
        with store_lock():
            data = self._read_unlocked()
            for issue in data.get("issues", []):
                if (
                    issue.get("status") in STATUSES_OPEN
                    and issue.get("type") != "architecture"
                    and issue.get("fingerprint") not in active_fingerprints
                ):
                    issue["status"] = "resolved"
                    issue["updated_at"] = now
                    issue.setdefault("metadata", {})["resolved_by"] = "tester_auto"
                    resolved_count += 1
            if resolved_count > 0:
                self._write_unlocked(data)
        return resolved_count

    def save(self) -> None:
        pass

    def get_issues(self) -> list[dict[str, Any]]:
        return self.list_issues()

