"""Heuristic improvement suggestions when a tester round has no new issues or failures."""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .goal_context import (
    fallback_suggestion_rationale,
    fallback_suggestion_text,
    goal_rejection_reason,
    is_goal_aligned,
)
from .issue_store import STATUSES_OPEN, IssueStore
from .round_findings import RoundFindings

_PRIORITIES = ("critical", "high", "medium", "low")


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def new_suggestion_id() -> str:
    return f"sug-{uuid.uuid4().hex[:12]}"


def _suggestion_id() -> str:
    return new_suggestion_id()


def _row(
    *,
    round_id: str,
    text: str,
    rationale: str,
    category: str,
    priority: str = "medium",
    strict: bool | None = None,
) -> dict[str, Any]:
    aligned = is_goal_aligned(text, strict=strict)
    return {
        "id": _suggestion_id(),
        "round_id": round_id,
        "ts": _utc_now(),
        "text": text,
        "rationale": rationale,
        "goal_alignment": aligned,
        "priority": priority if priority in _PRIORITIES else "medium",
        "category": category,
    }


def _log_rejected(
    reports_dir: Path,
    row: dict[str, Any],
    reason: str,
    *,
    strict: bool | None,
) -> None:
    path = reports_dir / "rejected_suggestions.jsonl"
    reports_dir.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": _utc_now(),
        "round_id": row.get("round_id"),
        "suggestion_id": row.get("id"),
        "text": row.get("text") or "",
        "rationale": row.get("rationale"),
        "category": row.get("category"),
        "priority": row.get("priority"),
        "reason": reason,
        "strict": strict,
        "goal_alignment": False,
    }
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def fallback_aligned_suggestion(
    round_id: str,
    *,
    strict: bool | None = None,
) -> dict[str, Any]:
    """PROJECT_BRIEF-aligned template when heuristics all fail validation."""
    text = fallback_suggestion_text()
    return _row(
        round_id=round_id,
        text=text,
        rationale=fallback_suggestion_rationale(),
        category="ux",
        priority="low",
        strict=strict,
    )


def _heuristic_candidates(
    round_id: str,
    findings: RoundFindings,
    store: IssueStore,
    cfg: dict,
    *,
    strict: bool | None = None,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    counts = findings.counts()
    items = findings.items

    open_issues = store.list_issues(status_filter=STATUSES_OPEN | {"assigned", "in_progress"})
    critical_static = [
        i
        for i in open_issues
        if i.get("severity") == "critical" and i.get("type") == "static"
    ]
    if critical_static:
        sample = critical_static[0]
        paths = sample.get("paths") or ["app.py"]
        out.append(
            _row(
                round_id=round_id,
                text=f"优先修复仍开放的 critical 静态问题（{paths[0]}），恢复 py_compile 与上传→生成主路径可用性。",
                rationale="开放 critical/static 会阻塞课本照片经 NotebookLM 生成材料的核心链路。",
                category="quality",
                priority="critical",
                strict=strict,
            )
        )

    auth_warn = any(
        it.get("check_id") in ("create_notebook_skip", "auth_status_shape")
        and it.get("status") == "warn"
        for it in items
    )
    if auth_warn:
        out.append(
            _row(
                round_id=round_id,
                text="在 Web UI 增加 NotebookLM 认证刷新引导（链接 to notebooklm auth），缩短从「未认证」到可生成的时间。",
                rationale="本轮 auth/create-notebook 探针未就绪；对齐「认证可探测、未认证有明确引导」验收项。",
                category="auth",
                priority="high",
                strict=strict,
            )
        )

    slow_health = any(it.get("check_id") == "health_backend_slow" for it in items)
    if slow_health:
        out.append(
            _row(
                round_id=round_id,
                text="优化 /api/health 与首包响应（缓存 auth 探测、并行依赖检查），降低用户上传后等待「可生成」的感知延迟。",
                rationale="健康检查响应偏慢，影响 time-to-first-download 体验。",
                category="performance",
                priority="medium",
                strict=strict,
            )
        )

    if not cfg.get("browser_test_enabled", False):
        out.append(
            _row(
                round_id=round_id,
                text="启用 browser_test_enabled 并补充「上传样张→开始生成→步骤2/错误模态」E2E，覆盖课本照片主路径回归。",
                rationale="当前配置未跑 Playwright E2E，核心 UI 流程存在覆盖缺口。",
                category="e2e",
                priority="high",
                strict=strict,
            )
        )
    else:
        e2e_ran = any(
            "browser" in (it.get("check_id") or "").lower()
            or "e2e" in (it.get("name") or "").lower()
            for it in items
        )
        if not e2e_ran and counts.get("fail", 0) == 0:
            out.append(
                _row(
                    round_id=round_id,
                    text="在本轮深度探测中固定执行 Playwright E2E（含 sample.png 上传），确保多格式生成按钮与 auth 模态不退化。",
                    rationale="browser 已启用但本轮未见 E2E 检查项，主路径回归覆盖不足。",
                    category="e2e",
                    priority="medium",
                    strict=strict,
                )
            )

    open_health = [i for i in open_issues if i.get("type") == "health"]
    if open_health:
        out.append(
            _row(
                round_id=round_id,
                text="将 :5000/:8080 启服步骤写入 dev-log 与一键启动脚本，减少因服务未起导致的假阴性 health issue。",
                rationale=f"仍有 {len(open_health)} 条开放 health issue，影响本地 Web UI 可用性验收。",
                category="reliability",
                priority="medium",
                strict=strict,
            )
        )

    if not out:
        out.append(
            _row(
                round_id=round_id,
                text="为 generate-content 成功路径增加「首份材料可下载」埋点与 dev-log 展示，量化课本→NotebookLM→下载的端到端耗时。",
                rationale="本轮无新问题且无失败检查；通过可观测性促进 time-to-first-download 持续改进。",
                category="ux",
                priority="low",
                strict=strict,
            )
        )
    return out


def generate_for_clean_round(
    round_id: str,
    findings: RoundFindings,
    store: IssueStore,
    cfg: dict,
    *,
    min_count: int = 1,
    strict: bool | None = None,
) -> list[dict[str, Any]]:
    """Build at least min_count suggestions pre-validated for goal alignment."""
    if strict is None:
        strict = bool(cfg.get("goal_alignment_strict", True))
    candidates = _heuristic_candidates(round_id, findings, store, cfg, strict=strict)
    aligned = [c for c in candidates if c.get("goal_alignment")]
    if len(aligned) >= min_count:
        return aligned[: max(min_count, 3)]
    fallback = fallback_aligned_suggestion(round_id, strict=strict)
    if fallback.get("goal_alignment"):
        return [fallback]
    return []


def append_suggestion(
    row: dict[str, Any],
    reports_dir: Path,
    logger: logging.Logger | None = None,
    *,
    strict: bool | None = None,
) -> dict[str, Any] | None:
    """Hard gate: persist only when is_goal_aligned(); log rejections otherwise."""
    kept = append_suggestions([row], reports_dir, logger, strict=strict)
    return kept[0] if kept else None


def append_suggestions(
    suggestions: list[dict[str, Any]],
    reports_dir: Path,
    logger: logging.Logger | None = None,
    *,
    strict: bool | None = None,
) -> list[dict[str, Any]]:
    """Append aligned rows to round_suggestions.jsonl and improvement_suggestions.jsonl."""
    log = logger or logging.getLogger("tester")
    kept: list[dict[str, Any]] = []
    round_path = reports_dir / "round_suggestions.jsonl"
    global_path = reports_dir / "improvement_suggestions.jsonl"
    reports_dir.mkdir(parents=True, exist_ok=True)

    for row in suggestions:
        text = row.get("text") or ""
        reason = goal_rejection_reason(text, strict=strict)
        if reason:
            log.warning(
                "Rejected misaligned suggestion (%s): %s",
                reason,
                text[:120],
            )
            _log_rejected(reports_dir, row, reason, strict=strict)
            continue
        row["goal_alignment"] = True
        kept.append(row)
        line = json.dumps(row, ensure_ascii=False)
        with round_path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
        global_row = {
            "ts": row.get("ts") or _utc_now(),
            "round_id": row.get("round_id"),
            "suggestion_id": row.get("id"),
            "message": text,
            "rationale": row.get("rationale"),
            "category": row.get("category"),
            "priority": row.get("priority"),
            "goal_alignment": True,
        }
        with global_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(global_row, ensure_ascii=False) + "\n")
    return kept


def load_by_round(
    reports_dir: Path,
    *,
    aligned_only: bool = True,
) -> dict[str, list[dict[str, Any]]]:
    path = reports_dir / "round_suggestions.jsonl"
    by_round: dict[str, list[dict[str, Any]]] = {}
    if not path.is_file():
        return by_round
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if aligned_only and not row.get("goal_alignment"):
            continue
        rid = str(row.get("round_id") or "")
        if rid:
            by_round.setdefault(rid, []).append(row)
    return by_round


def load_suggestions(
    reports_dir: Path,
    *,
    aligned_only: bool = True,
) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    """Grouped by round_id and flat list for interval matching."""
    by_round = load_by_round(reports_dir, aligned_only=aligned_only)
    path = reports_dir / "round_suggestions.jsonl"
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
        if aligned_only and not row.get("goal_alignment"):
            continue
        flat.append(row)
    return by_round, flat
