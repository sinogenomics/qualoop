"""Project north-star context and goal-alignment gate for automation suggestions."""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from .paths import load_config

# Hard prerequisites: suggestions must not undermine the core product flow.
_MISALIGNED_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(
            r"\b(remove|delete|disable|drop|skip|bypass|abandon)\b.{0,40}\b(notebooklm|notebook\s*lm)\b",
            re.I,
        ),
        "undermines_notebooklm",
    ),
    (
        re.compile(
            r"\b(notebooklm|notebook\s*lm)\b.{0,40}\b(remove|delete|disable|drop|skip|bypass)\b",
            re.I,
        ),
        "undermines_notebooklm",
    ),
    (
        re.compile(
            r"\b(remove|delete|disable|drop)\b.{0,30}\b(upload|photo|image)\b",
            re.I,
        ),
        "disables_upload",
    ),
    (
        re.compile(
            r"\b(disable|remove|skip)\b.{0,30}\b(generate|generation|content)\b",
            re.I,
        ),
        "disables_generate",
    ),
    (
        re.compile(
            r"\b(disable|remove|skip)\b.{0,30}\b(download)\b",
            re.I,
        ),
        "disables_download",
    ),
    (
        re.compile(
            r"\b(no\s+longer|stop|cease)\b.{0,30}\b(e2e|browser|playwright)\b",
            re.I,
        ),
        "drops_e2e",
    ),
    (
        re.compile(
            r"\b(remove|delete|disable)\b.{0,30}\b(e2e|playwright|browser)\b",
            re.I,
        ),
        "drops_e2e",
    ),
    (
        re.compile(
            r"\b(replace|substitute)\b.{0,30}\b(notebooklm|notebook\s*lm)\b.{0,30}\b(mock|fake|stub)\b",
            re.I,
        ),
        "mock_replaces_notebooklm",
    ),
    (
        re.compile(
            r"\b(only|just)\s+mock\b.{0,20}\b(generat|material|production|deploy)",
            re.I,
        ),
        "mock_only_production",
    ),
    (
        re.compile(
            r"\b(mock|fake|stub)\s+only\b.{0,30}\b(production|release|deploy|ship)",
            re.I,
        ),
        "mock_only_production",
    ),
    (
        re.compile(
            r"\b(use|switch to|ship)\b.{0,20}\b(mock|fake|stub)\b.{0,30}\b(production|release|deploy)",
            re.I,
        ),
        "mock_only_production",
    ),
    (
        re.compile(
            r"\bremove\b.{0,20}\b(api/(create-notebook|generate-content|auth-status))",
            re.I,
        ),
        "removes_core_api",
    ),
    (
        re.compile(
            r"\b(refactor|restructure|reorganize|rename)\b.{0,60}\b(unrelated|cosmetic|style only|folder layout)\b",
            re.I,
        ),
        "unrelated_refactor",
    ),
    (
        re.compile(
            r"\b(migrate|rewrite)\b.{0,40}\b(framework|stack)\b.{0,20}\b(without|no)\b.{0,20}\b(upload|generate|notebooklm)",
            re.I,
        ),
        "unrelated_refactor",
    ),
)

_POSITIVE_SIGNALS: tuple[str, ...] = (
    "notebooklm",
    "notebook lm",
    "upload",
    "photo",
    "image",
    "auth",
    "generate",
    "e2e",
    "playwright",
    "health",
    "download",
    "材料",
    "课本",
    "上传",
    "认证",
    "生成",
    "下载",
    "可靠性",
    "ux",
    "体验",
    "覆盖",
    "性能",
    "契约",
    "腐化",
    "修复",
    "improve",
    "reduce",
    "缩短",
    "提升",
    "k-12",
    "k12",
    "textbook",
    "slides",
    "ppt",
    "mindmap",
    "infographic",
    "audio",
    "video",
    "学习",
    "教学",
)

_GOAL_KEYWORD_CATEGORIES: tuple[str, ...] = (
    "material",
    "materials",
    "textbook",
    "k-12",
    "k12",
    "课本",
    "材料",
    "notebooklm",
    "upload",
    "generate",
    "download",
    "auth",
    "e2e",
)

_ACCEPTANCE_CRITERIA: tuple[str, ...] = (
    "用户可上传课本照片并触发 NotebookLM 多格式材料生成（音频/视频/信息图/思维导图/PPT）",
    "本地 CLI + 可用 Web UI；后端 health/auth/create-notebook/generate-content/task-status 契约稳定",
    "认证状态可探测；未认证时 UI 有明确引导而非静默失败",
    "自动化每轮必须产出：发现问题（issue/check fail）或目标对齐的改进建议",
)

_FALLBACK_SUGGESTION_TEXT = (
    "为课本照片上传→NotebookLM 多格式材料生成链路增加「首份材料可下载」埋点与 dev-log 耗时展示，"
    "量化 time-to-first-download 并持续优化 K-12 学习体验。"
)

_FALLBACK_SUGGESTION_RATIONALE = (
    "本轮无新问题；依据 PROJECT_BRIEF 验收要点，通过可观测性促进上传→生成→下载主路径。"
)


@lru_cache(maxsize=1)
def _project_root() -> Path:
    return load_config()["_project_root"]


@lru_cache(maxsize=1)
def load_project_brief() -> str:
    path = _project_root() / "PROJECT_BRIEF.md"
    if path.is_file():
        return path.read_text(encoding="utf-8", errors="replace").strip()
    return (
        "K-12 textbook photo → NotebookLM → multi-format learning materials "
        "(audio, video, infographic, mindmap, slides). Local CLI, usable web UI."
    )


def acceptance_criteria() -> list[str]:
    return list(_ACCEPTANCE_CRITERIA)


def goal_summary_for_prompt() -> str:
    brief = load_project_brief()
    criteria = "\n".join(f"- {c}" for c in _ACCEPTANCE_CRITERIA)
    return (
        "## ParadigmLearn（新范式学习）终极目标\n"
        f"{brief[:1200]}\n\n"
        "## 验收要点（建议须促进以下能力，不得削弱）\n"
        f"{criteria}\n"
    )


def goal_rejection_reason(suggestion_text: str, *, strict: bool | None = None) -> str | None:
    """Return a machine-readable rejection reason, or None if aligned."""
    if not suggestion_text or not suggestion_text.strip():
        return "empty_text"
    text = suggestion_text.strip()
    for pat, code in _MISALIGNED_PATTERNS:
        if pat.search(text):
            return code
    if strict is None:
        cfg = load_config()
        strict = bool(cfg.get("goal_alignment_strict", True))
    if strict:
        lowered = text.lower()
        if not any(sig in lowered for sig in _POSITIVE_SIGNALS):
            return "missing_goal_signal"
        if not any(kw in lowered for kw in _GOAL_KEYWORD_CATEGORIES):
            return "missing_goal_keyword_category"
    return None


def is_goal_aligned(suggestion_text: str, *, strict: bool | None = None) -> bool:
    """Rule-based gate: reject suggestions that harm core photo→NotebookLM→materials flow."""
    return goal_rejection_reason(suggestion_text, strict=strict) is None


def fallback_suggestion_text() -> str:
    return _FALLBACK_SUGGESTION_TEXT


def fallback_suggestion_rationale() -> str:
    return _FALLBACK_SUGGESTION_RATIONALE
