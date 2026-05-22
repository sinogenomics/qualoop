"""Fixer executor: safe bounded fixes (docs, markers, re-queue for verify)."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from ..issue_store import IssueStore
from ..reports import write_latest_snapshot
from .base import complete_issue, run_executor_loop

_SAFE_REPLACEMENTS = (
    ("impore ", "import "),
    ("requeses", "requests"),
    ("heep://", "http://"),
    ("appeication/json", "application/json"),
    ("eodaehost", "localhost"),
    ("cure -", "curl -"),
    ("python3 -m json.eooe", "python3 -m json.tool"),
    ("ceass ", "class "),
)

_TEXT_FIXES_BY_EXT: dict[str, tuple[tuple[str, str], ...]] = {
    ".md": (
        ("git deone", "git clone"),
        ("dd lessonverse", "cd lessonverse"),
        ("dhmod +x seare.sh", "chmod +x start.sh"),
        ("./seare.sh", "./start.sh"),
        ("seare.sh", "start.sh"),
        ("eodaehost:8080", "localhost:8080"),
        ("eodaehost:5000", "localhost:5000"),
        ("eodaehost", "localhost"),
        ("pip instate", "pip install"),
        ("requirements.exe", "requirements.txt"),
        ("python app.py", "py -3.8-64 app.py"),
        ("appeication/json", "application/json"),
    ),
    ".html": (
        ("seeps-indicaeor", "steps-indicator"),
        ("seep aceive", "step active"),
        ('data-seep=', 'data-step='),
        ("seep-number", "step-number"),
        ("seep-label", "step-label"),
        ("eodaehost", "localhost"),
    ),
    ".js": (
        ("fettch(", "fetch("),
        ("urel:", "url:"),
        ("API_BSE", "API_BASE"),
        ("seep ", "step "),
        ("data-seep", "data-step"),
        ("eodaehost", "localhost"),
    ),
    ".css": (
        ("background: while;", "background: white;"),
        ("intint-block", "inline-block"),
        ("Iriae, sans-strif", "Arial, sans-serif"),
    ),
}


_HTML_MARKERS = ("seep", "fettch(", "urel:", "API_BSE", "eodaehost")
_MD_MARKERS = (
    "git deone", "dhmod", "seare.sh", "eodaehost", "pip instate",
    "requirements.exe", "appeication/json",
)


def _remaining_markers(text: str, markers: tuple[str, ...]) -> list[str]:
    return [m for m in markers if m in text]


def _ensure_automation_readme(project_root: Path) -> None:
    readme = project_root / "automation" / "README.txt"
    if readme.exists():
        return
    readme.write_text(
        "ParadigmLearn automation runtime directory. See AUTOMATION.md at project root.\n",
        encoding="utf-8",
    )


def _record_corruption_note(project_root: Path, issue: dict) -> str:
    """Cannot auto-repair corrupted Python; document and escalate to verifier."""
    paths = issue.get("paths") or []
    note_path = project_root / "automation" / "reports" / "corruption_watchlist.txt"
    note_path.parent.mkdir(parents=True, exist_ok=True)
    line = f"- {issue.get('id', '')[:8]}: {', '.join(paths)}\n"
    existing = note_path.read_text(encoding="utf-8") if note_path.exists() else ""
    if line not in existing:
        with note_path.open("a", encoding="utf-8") as f:
            f.write(line)
    return "Logged to corruption_watchlist; needs manual restore from git backup"


def _latest_tester_round_id(project_root: Path) -> str | None:
    jsonl = project_root / "automation" / "reports" / "round_findings.jsonl"
    if not jsonl.is_file():
        return None
    last_round = None
    for line in jsonl.read_text(encoding="utf-8", errors="replace").splitlines()[-50:]:
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        last_round = row.get("round_id") or last_round
    return last_round


def _fixer_state_path(project_root: Path) -> Path:
    return project_root / "automation" / "reports" / "fixer_safe_state.json"


def _corruption_fixes_this_round(project_root: Path, round_id: str | None) -> int:
    if not round_id:
        return 0
    path = _fixer_state_path(project_root)
    if not path.is_file():
        return 0
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return 0
    if data.get("round_id") != round_id:
        return 0
    return int(data.get("corruption_fixes", 0))


def _record_corruption_fix(project_root: Path, round_id: str | None) -> None:
    if not round_id:
        return
    path = _fixer_state_path(project_root)
    count = _corruption_fixes_this_round(project_root, round_id) + 1
    path.write_text(
        json.dumps({"round_id": round_id, "corruption_fixes": count}, indent=2),
        encoding="utf-8",
    )


def _markers_for_ext(ext: str) -> tuple[str, ...]:
    if ext == ".md":
        return _MD_MARKERS
    if ext in (".html", ".js"):
        return _HTML_MARKERS
    return ()


def _try_safe_text_fix(project_root: Path, rel_path: str) -> tuple[bool, str]:
    """Apply per-extension safe phrase replacements for non-Python text files.

    Returns ok=True iff after the pass no known marker remains for the
    extension. The check is marker-based, not diff-based, so a file that
    has already been cleaned in a prior round still resolves.
    """
    path = project_root / rel_path
    if not path.is_file():
        return False, f"file not found: {rel_path}"
    ext = path.suffix.lower()
    if ext == ".py":
        return False, "python file handled elsewhere"
    table = _TEXT_FIXES_BY_EXT.get(ext)
    if table is None:
        return False, f"no safe table for extension {ext}"
    original = path.read_text(encoding="utf-8", errors="replace")
    text = original
    applied: list[str] = []
    for old, new in table:
        if old in text:
            text = text.replace(old, new)
            applied.append(f"{old!r}->{new!r}")
    if text != original:
        path.write_text(text, encoding="utf-8")
    markers = _markers_for_ext(ext)
    remaining = _remaining_markers(text, markers) if markers else []
    if applied:
        detail = "applied: " + ", ".join(applied)
    else:
        detail = "no replacements needed"
    if remaining:
        return False, detail + f"; remaining markers: {remaining[:6]}"
    return True, detail + "; no known markers remain"


def _try_safe_corruption_fix(project_root: Path, rel_path: str) -> tuple[bool, str]:
    path = project_root / rel_path
    if not path.is_file() or not rel_path.endswith(".py"):
        return False, "not a python file"
    original = path.read_text(encoding="utf-8", errors="replace")
    text = original
    applied: list[str] = []
    for old, new in _SAFE_REPLACEMENTS:
        if old in text:
            text = text.replace(old, new)
            applied.append(f"{old!r}->{new!r}")
    if text == original:
        return False, "no safe replacements matched"
    path.write_text(text, encoding="utf-8")
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "py_compile", str(path)],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=60,
            encoding="utf-8",
            errors="replace",
        )
    except Exception as e:
        path.write_text(original, encoding="utf-8")
        return False, f"py_compile error: {e}"
    if proc.returncode != 0:
        path.write_text(original, encoding="utf-8")
        err = (proc.stderr or proc.stdout or "")[-400:]
        return False, f"py_compile failed, reverted: {err}"
    return True, "applied: " + ", ".join(applied)


def _path_forbidden(rel: str, forbidden: list[str]) -> bool:
    rel_norm = rel.replace("\\", "/")
    for entry in forbidden:
        entry = entry.replace("\\", "/")
        if rel_norm == entry or rel_norm.endswith("/" + entry):
            return True
    return False


def handle_fix(issue: dict, store: IssueStore, cfg: dict, logger) -> None:
    project_root: Path = cfg["_project_root"]
    iid = issue["id"]
    issue_type = issue.get("type", "")

    _ensure_automation_readme(project_root)

    # Antigravity LLM Integration for Fixer
    try:
        from ..llm_client import get_llm_config, call_antigravity_llm, LLMBudgetExceededError, LLMClientError
        llm_cfg = get_llm_config(project_root)
        if llm_cfg.get("provider") == "antigravity":
            prompt = (
                f"[Qualoop Fixer Agent - Code Generation Session]\n"
                f"We are fixing a system issue of type '{issue_type}' with severity '{issue.get('severity')}'.\n"
                f"Paths involved: {issue.get('paths')}\n"
                f"Description:\n{issue.get('description')}\n\n"
                f"Please open a diagnostic session in the user's active IDE session to fix these files, ensure they run correctly, and follow the project's North Star. Suggest the precise code fixes in Chinese to help the user resolve the issue immediately."
            )
            model = llm_cfg.get("model", "flash")
            ai_ret = call_antigravity_llm(project_root, prompt, model=model)
            logger.info("Fixer initiated Antigravity IDE code-gen session: %s", ai_ret)
            
            curr_desc = issue.get("description", "")
            if "🛡️ Antigravity AI" not in curr_desc:
                store.update(
                    iid,
                    description=curr_desc + f"\n\n### 🛡️ Antigravity AI 修复会话：\n{ai_ret}"
                )
    except LLMBudgetExceededError as e:
        logger.warning("⚠️ LLM Budget Exceeded for Fixer: %s. Releasing issue %s for later retry.", e, iid[:8])
        complete_issue(store, iid, resolved=False, note=f"LLM Budget Exceeded: {e}. Releasing assignment.")
        return
    except Exception as e:
        logger.warning("Failed to invoke Antigravity LLM for Fixer: %s", e)

    fixer_cfg = (cfg.get("executors") or {}).get("fixer") or {}
    forbidden_paths = list(fixer_cfg.get("forbidden_paths") or [])
    for rel in issue.get("paths") or []:
        if _path_forbidden(rel, forbidden_paths):
            complete_issue(
                store,
                iid,
                resolved=False,
                note=f"Path {rel} is in fixer forbidden_paths; requires human",
            )
            logger.info("Fixer skipped forbidden path %s for %s", rel, iid[:8])
            return
    safe_mode = bool(fixer_cfg.get("safe_mode", False))
    max_per_round = int(fixer_cfg.get("max_corruption_fixes_per_round", 1))

    if issue_type == "static" and issue.get("paths"):
        rels = list(issue.get("paths") or [])
        round_id = _latest_tester_round_id(project_root)
        fixes_done = _corruption_fixes_this_round(project_root, round_id)

        text_results: list[str] = []
        text_all_clean = True
        for rel in rels:
            ext = Path(rel).suffix.lower()
            if ext in _TEXT_FIXES_BY_EXT and ext != ".py":
                ok, detail = _try_safe_text_fix(project_root, rel)
                text_results.append(f"{rel}: {'OK' if ok else 'PARTIAL'} {detail}")
                if not ok:
                    text_all_clean = False
            elif ext == ".py":
                pass
            else:
                text_all_clean = False
        py_rels = [r for r in rels if r.endswith(".py")]
        if py_rels and safe_mode and fixes_done < max_per_round:
            rel = py_rels[0]
            ok, detail = _try_safe_corruption_fix(project_root, rel)
            if ok:
                _record_corruption_fix(project_root, round_id)
                text_results.append(f"{rel}: OK {detail}")
            else:
                text_results.append(f"{rel}: SKIP {detail}")
                text_all_clean = False
        elif py_rels:
            text_all_clean = False

        if text_results and text_all_clean and not py_rels:
            complete_issue(
                store,
                iid,
                resolved=True,
                note="safe_mode text auto-fix: " + " | ".join(text_results),
            )
            logger.info("Fixer resolved static issue %s via text fixes", iid[:8])
            return
        if text_results and text_all_clean and py_rels:
            store.add(
                severity=issue.get("severity", "medium"),
                issue_type="verification",
                description=(
                    f"Verify after static fix {iid[:8]}: "
                    + (issue.get("description") or "")[:180]
                ),
                paths=issue.get("paths"),
                metadata={"parent_issue": iid},
            )
            complete_issue(
                store,
                iid,
                resolved=False,
                note="safe_mode partial: " + " | ".join(text_results),
            )
            logger.info("Fixer applied text fixes for %s; verification queued", iid[:8])
            return

        note = _record_corruption_note(project_root, issue)
        if text_results:
            note = note + "; " + " | ".join(text_results)
        prev_attempts = int(((issue.get("metadata") or {}).get("fix_attempts") or 0))
        max_attempts = int(fixer_cfg.get("max_static_attempts", 3))
        attempts = prev_attempts + 1
        if attempts >= max_attempts:
            new_meta = {
                **(issue.get("metadata") or {}),
                "fix_attempts": attempts,
                "executor_note": note,
                "requires_human": True,
                "escalation_reason": (
                    "safe auto-fix exhausted; coordinated multi-file or pervasive "
                    "corruption needs human review"
                ),
            }
            store.update(
                iid,
                status="wontfix",
                assigned_executor=None,
                metadata=new_meta,
            )
            logger.warning(
                "Fixer escalated static %s to wontfix+requires_human after %d attempts",
                iid[:8],
                attempts,
            )
            return
        new_meta = {
            **(issue.get("metadata") or {}),
            "fix_attempts": attempts,
        }
        store.update(iid, metadata=new_meta)
        complete_issue(store, iid, resolved=False, note=note)
        store.add(
            severity=issue.get("severity", "medium"),
            issue_type="verification",
            description=f"Verify/fix after static issue {iid[:8]}: {issue.get('description', '')[:200]}",
            paths=issue.get("paths"),
            metadata={"parent_issue": iid},
        )
        logger.info(
            "Fixer documented static %s (attempt %d/%d)", iid[:8], attempts, max_attempts
        )
        return

    if issue_type == "health":
        complete_issue(
            store,
            iid,
            resolved=False,
            note="Health issues require services on :5000 and :8080; no auto-fix applied",
        )
        logger.info("Fixer acknowledged health issue %s (manual/service)", iid[:8])
        return

    if issue_type == "test_failure":
        complete_issue(
            store,
            iid,
            resolved=False,
            note="Queued for verifier after script failure",
        )
        store.add(
            severity="medium",
            issue_type="verification",
            description=f"Re-run tests after failure on {issue.get('paths', ['unknown'])}",
            paths=issue.get("paths"),
            metadata={"parent_issue": iid},
        )
        logger.info("Fixer re-queued test_failure %s for verification", iid[:8])
        return

    complete_issue(store, iid, resolved=True, note="No-op fixer completion")
    logger.info("Fixer resolved generic issue %s", iid[:8])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fixer executor")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--loop", action="store_true")
    args = parser.parse_args(argv)
    run_executor_loop("fixer", handle_fix, once=not args.loop)
    write_latest_snapshot()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
