"""Playwright-based browser E2E for the automation tester (runs locally, no Cursor MCP)."""
from __future__ import annotations

import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from .issue_store import IssueStore
from .paths import automation_dir
from .round_findings import RoundFindings

_FIXTURE_NAME = "sample.png"
_MINIMAL_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f"
    b"\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _expand_path(raw: str, project_root: Path) -> Path:
    expanded = os.path.expandvars(os.path.expanduser(raw.strip()))
    path = Path(expanded)
    if not path.is_absolute():
        path = (project_root / path).resolve()
    return path


def _default_desktop_textbook_candidates() -> list[Path]:
    home = Path.home()
    name = "预习0518.jpg"
    return [
        home / "Desktop" / name,
        home / "桌面" / name,
    ]


def ensure_generated_fixture(project_root: Path) -> Path:
    fixture_dir = project_root / "automation" / "fixtures"
    fixture_dir.mkdir(parents=True, exist_ok=True)
    path = fixture_dir / _FIXTURE_NAME
    if path.is_file() and path.stat().st_size >= 500:
        return path
    try:
        from PIL import Image

        img = Image.new("RGB", (128, 128), color=(102, 126, 234))
        img.save(path, format="PNG", optimize=True)
    except Exception:
        path.write_bytes(_MINIMAL_PNG)
    return path


def resolve_upload_fixture(cfg: dict, project_root: Path, logger=None) -> Path:
    """Prefer configured/desktop textbook photo; fall back to generated sample.png."""
    candidates: list[Path] = []
    configured = cfg.get("browser_fixture_path") or cfg.get("browser_upload_image")
    if configured:
        candidates.append(_expand_path(str(configured), project_root))
    candidates.extend(_default_desktop_textbook_candidates())
    repo_copy = project_root / "automation" / "fixtures" / "预习0518.jpg"
    candidates.append(repo_copy)
    candidates.append(ensure_generated_fixture(project_root))

    seen: set[str] = set()
    for path in candidates:
        key = str(path.resolve()) if path.exists() else str(path)
        if key in seen:
            continue
        seen.add(key)
        if path.is_file() and path.stat().st_size > 0:
            if logger:
                logger.info("Browser E2E upload fixture: %s (%d bytes)", path, path.stat().st_size)
            return path.resolve()
    return ensure_generated_fixture(project_root)


def ensure_fixture(project_root: Path) -> Path:
    """Backward-compatible alias."""
    return ensure_generated_fixture(project_root)


def _screenshot_dir(cfg: dict) -> Path:
    d = automation_dir(cfg) / "reports" / "screenshots"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _save_screenshot(page: Any, cfg: dict, label: str) -> str:
    shots = _screenshot_dir(cfg)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = shots / f"browser_e2e_{label}_{stamp}.png"
    page.screenshot(path=str(path), full_page=True)
    rtl = path.relative_to(cfg["_project_root"]).as_posix()
    return rtl


def _record_failure(
    store: IssueStore,
    description: str,
    *,
    screenshot: str | None = None,
    metadata: dict | None = None,
) -> bool:
    meta = dict(metadata or {})
    if screenshot:
        meta["screenshot"] = screenshot
    issue = store.add(
        severity="high",
        issue_type="browser_e2e",
        description=description,
        paths=["index.html", "script.js"],
        metadata=meta,
    )
    return issue is not None


def _f(
    findings: RoundFindings | None,
    check_id: str,
    name: str,
    status: str,
    detail: str = "",
    *,
    new_issue: bool = False,
) -> None:
    if findings is not None:
        findings.add(
            check_id,
            name,
            status,
            detail,
            category="e2e",
            new_issue=new_issue,
        )


def _step_visible(page: Any, step: int) -> bool:
    """Step panels use #step1..#step3 (legacy #seep* kept for older HTML)."""
    for selector in (f"#step{step}", f"#seep{step}"):
        loc = page.locator(selector)
        if loc.count() > 0 and loc.first.is_visible():
            return True
    content = page.locator(f"#step{step}.step-content")
    if content.count() > 0 and content.first.is_visible():
        return True
    return False


def _error_modal_text(page: Any) -> str:
    modal = page.locator("#errorModal")
    if not modal.is_visible():
        return ""
    return (page.locator("#errorMessage").inner_text() or "").strip()


def _error_modal_with_text(page: Any) -> bool:
    return len(_error_modal_text(page)) > 0


_BUSINESS_FAIL_RE = re.compile(
    r"未能导入|无法处理|failed to process|上传失败|导入.{0,6}失败|"
    r"NotebookLM\s*无法|无法导入|处理该课本照片",
    re.IGNORECASE,
)
_AUTH_FAIL_RE = re.compile(
    r"认证|auth_expired|未认证|401|token\s*fetch|请按以下步骤恢复\s*AI\s*服务",
    re.IGNORECASE,
)


def _classify_modal_failure(msg: str) -> Literal["business", "auth", "generic"]:
    if not msg:
        return "generic"
    if _BUSINESS_FAIL_RE.search(msg):
        return "business"
    if _AUTH_FAIL_RE.search(msg):
        return "auth"
    return "generic"


def _process_step_state(page: Any, step_id: str) -> str | None:
    status = page.locator(f"#{step_id} .status")
    if status.count() == 0:
        return None
    classes = (status.first.get_attribute("class") or "").split()
    for st in ("error", "completed", "processing", "pending"):
        if st in classes:
            return st
    return None


def _pipeline_failure_reason(page: Any) -> str | None:
    msg = _error_modal_text(page)
    if msg:
        kind = _classify_modal_failure(msg)
        return f"[{kind}] {msg[:400]}"
    for step_id in ("process-import", "process-upload", "process-notebook", "process-generate"):
        st = _process_step_state(page, step_id)
        if st == "error":
            label = page.locator(f"#{step_id} span").first.inner_text() if page.locator(f"#{step_id} span").count() else step_id
            return f"处理步骤「{label}」失败 ({step_id})"
    return None


def _record_e2e_failure(
    *,
    page: Any,
    cfg: dict,
    store: IssueStore,
    findings: RoundFindings | None,
    logger,
    description: str,
    check_name: str,
    phase: str,
    step_reached: str,
    url: str,
    label: str = "browser_e2e",
) -> bool:
    shot = None
    try:
        shot = _save_screenshot(page, cfg, label)
    except Exception:
        pass
    new = _record_failure(
        store,
        description,
        screenshot=shot,
        metadata={"url": url, "phase": phase, "step_reached": step_reached},
    )
    _f(
        findings,
        "e2e_pipeline",
        check_name,
        "fail",
        description[:160],
        new_issue=new,
    )
    if new:
        logger.warning("Browser E2E recorded failure: %s", description[:120])
    return bool(new)


def _header_locator(page: Any, element_id: str) -> Any:
    """Target auth UI in the page header (modal duplicates the same ids)."""
    return page.locator(f"header.header #{element_id}").first


def _auth_ok(page: Any) -> bool:
    indicator = _header_locator(page, "auth-indicator")
    if indicator.count() == 0:
        return False
    classes = indicator.get_attribute("class") or ""
    if "success" in classes.split():
        return True
    text_el = _header_locator(page, "auth-text")
    if text_el.count():
        text = (text_el.inner_text() or "").strip()
        return "已就绪" in text
    return False


def _progress_started(page: Any) -> bool:
    fill = page.locator("#progressFill")
    if fill.count():
        style = fill.get_attribute("style") or ""
        if "width:" in style and "0%" not in style.split("width:")[-1][:6]:
            return True
    text = (page.locator("#progressText").inner_text() or "").strip()
    return text not in ("", "0%", "0 %")


def run_browser_e2e(
    cfg: dict,
    store: IssueStore,
    logger,
    *,
    findings: RoundFindings | None = None,
) -> dict[str, Any]:
    """Run one browser flow. Returns {created, step_reached, findings_count}."""
    created = 0
    step_reached = "not_started"

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        if _record_failure(
            store,
            "Browser E2E skipped: `playwright` is not installed. "
            "Run: `py -3 -m pip install playwright` then `py -3 -m playwright install chromium`.",
            metadata={"reason": "playwright_missing"},
        ):
            created += 1
            _f(findings, "e2e_playwright", "Playwright 依赖", "fail", "未安装", new_issue=True)
            logger.warning("Recorded missing Playwright dependency")
        else:
            _f(findings, "e2e_playwright", "Playwright 依赖", "fail", "未安装（已知）")
        return {"created": created, "step_reached": "playwright_missing"}

    url = cfg.get("browser_test_url", "http://localhost:8080/index.html")
    headless = cfg.get("browser_headless", True)
    timeout_sec = float(cfg.get("browser_timeout_sec", 120))
    settle_sec = float(cfg.get("browser_settle_sec", 15.0))
    project_root: Path = cfg["_project_root"]
    fixture = resolve_upload_fixture(cfg, project_root, logger=logger)

    logger.info("Browser E2E starting: %s (headless=%s)", url, headless)
    _f(findings, "e2e_start", "浏览器 E2E 启动", "pass", url)

    with sync_playwright() as p:
        browser = None
        page = None
        try:
            browser = p.chromium.launch(headless=headless)
            page = browser.new_page()
            page.set_default_timeout(int(timeout_sec * 1000))

            page.goto(url, wait_until="domcontentloaded")
            step_reached = "page_loaded"
            _f(findings, "e2e_goto", "打开页面", "pass", url)

            page.wait_for_selector("#projectName", state="visible", timeout=15000)
            step_reached = "form_visible"
            _f(findings, "e2e_form", "表单可见", "pass", "#projectName")

            try:
                page.wait_for_function(
                    """() => {
                        const el = document.querySelector('header.header #auth-indicator');
                        if (!el) return false;
                        const c = el.className || '';
                        return c.includes('success') || c.includes('error')
                            || c.includes('warning') || el.textContent.trim() !== '';
                    }""",
                    timeout=15000,
                )
                _f(findings, "e2e_auth_settle", "认证指示器", "pass", "已渲染")
            except Exception:
                logger.info("Auth indicator did not settle; continuing")
                _f(findings, "e2e_auth_settle", "认证指示器", "warn", "10s 内未稳定")

            auth_ready = _auth_ok(page)
            _f(
                findings,
                "e2e_auth_ready",
                "认证状态",
                "pass" if auth_ready else "warn",
                "已就绪" if auth_ready else "未就绪",
            )

            page.fill("#projectName", "Automation E2E Test")
            page.set_input_files("#fileInput", str(fixture))
            page.evaluate(
                """() => {
                    const input = document.getElementById('fileInput');
                    if (input) input.dispatchEvent(new Event('change', { bubbles: true }));
                }"""
            )
            page.wait_for_function(
                """() => {
                    const btn = document.getElementById('generateBtn');
                    return btn && !btn.disabled;
                }""",
                timeout=30000,
            )
            step_reached = "file_uploaded"
            _f(findings, "e2e_upload", "上传课本样张", "pass", f"{fixture.name} ({fixture.stat().st_size} B)")

            page.wait_for_function(
                """() => {
                    const btn = document.getElementById('generateBtn');
                    return btn && !btn.disabled;
                }""",
                timeout=10000,
            )
            _f(findings, "e2e_generate_enabled", "生成按钮可用", "pass", "")

            page.click("#generateBtn")
            step_reached = "generate_clicked"
            _f(findings, "e2e_generate_click", "点击生成", "pass", "")

            import_wait_sec = float(cfg.get("browser_import_wait_sec", 200.0))
            pipeline_deadline = time.monotonic() + max(settle_sec, import_wait_sec)
            saw_step2 = False
            regressed_to_step1 = False

            while time.monotonic() < pipeline_deadline:
                if _step_visible(page, 2):
                    saw_step2 = True
                    step_reached = "step2"
                if saw_step2 and _step_visible(page, 1) and not _step_visible(page, 2):
                    regressed_to_step1 = True
                    step_reached = "regressed_step1"
                    break

                if _step_visible(page, 3):
                    step_reached = "step3_success"
                    _f(findings, "e2e_step2", "步骤 2", "pass", "进入处理中")
                    _f(findings, "e2e_step3", "步骤 3 结果页", "pass", "已到达")
                    logger.info("Browser E2E passed: reached step 3 (results)")
                    break

                fail_reason = _pipeline_failure_reason(page)
                if fail_reason:
                    step_reached = "pipeline_failure"
                    if _record_e2e_failure(
                        page=page,
                        cfg=cfg,
                        store=store,
                        findings=findings,
                        logger=logger,
                        description=(
                            "Browser E2E: textbook upload / NotebookLM pipeline failed — "
                            + fail_reason
                        ),
                        check_name="课本→NotebookLM 主路径",
                        phase="pipeline",
                        step_reached=step_reached,
                        url=url,
                        label="pipeline_fail",
                    ):
                        created += 1
                    return {"created": created, "step_reached": step_reached}

                time.sleep(1.0)

            if regressed_to_step1 and not _error_modal_with_text(page):
                if _record_e2e_failure(
                    page=page,
                    cfg=cfg,
                    store=store,
                    findings=findings,
                    logger=logger,
                    description=(
                        "Browser E2E: UI regressed to step 1 after starting generation "
                        "(expected to stay on step 2 or show a clear error)."
                    ),
                    check_name="步骤 2 稳定",
                    phase="regressed_step1",
                    step_reached=step_reached,
                    url=url,
                    label="regressed_step1",
                ):
                    created += 1
                return {"created": created, "step_reached": step_reached}

            if step_reached != "step3_success":
                if not saw_step2:
                    detail = (
                        f"未进入步骤 2（等待 {int(import_wait_sec)}s）；"
                        "请确认前后端与 NotebookLM 认证。"
                    )
                elif _process_step_state(page, "process-import") == "completed" and (
                    _process_step_state(page, "process-generate") == "processing"
                ):
                    detail = (
                        f"导入已完成但 {int(import_wait_sec)}s 内未到步骤 3；"
                        "可能生成过慢或卡在生成材料。"
                    )
                else:
                    detail = (
                        f"{int(import_wait_sec)}s 内未完成主路径"
                        "（未到步骤 3，且无明确错误弹窗）。"
                    )
                if _record_e2e_failure(
                    page=page,
                    cfg=cfg,
                    store=store,
                    findings=findings,
                    logger=logger,
                    description="Browser E2E: pipeline timeout — " + detail,
                    check_name="课本→NotebookLM 主路径",
                    phase="pipeline_timeout",
                    step_reached="pipeline_timeout",
                    url=url,
                    label="pipeline_timeout",
                ):
                    created += 1
                return {"created": created, "step_reached": "pipeline_timeout"}

            _f(findings, "e2e_step2", "步骤 2", "pass", "处理中")
            _f(findings, "e2e_step3", "步骤 3 / 结果", "pass", step_reached)

        except Exception as e:
            shot_path = None
            if page is not None:
                try:
                    shot_path = _save_screenshot(page, cfg, "exception")
                except Exception:
                    pass
            new = _record_failure(
                store,
                f"Browser E2E failed with exception: {e}",
                screenshot=shot_path,
                metadata={"url": url, "error": str(e), "step_reached": step_reached},
            )
            if new:
                created += 1
            _f(findings, "e2e_exception", "浏览器 E2E", "fail", str(e)[:200], new_issue=new)
            logger.error("Browser E2E error: %s", e, exc_info=True)
        finally:
            if browser is not None:
                browser.close()

    complete_status = "pass" if step_reached == "step3_success" else "fail"
    _f(findings, "e2e_complete", "E2E 完成", complete_status, f"step={step_reached}")
    return {"created": created, "step_reached": step_reached}
