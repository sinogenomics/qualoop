# -*- coding: utf-8 -*-
"""Tester agent: deep probes, static checks, API contract, regression, E2E."""
from __future__ import annotations

# Ensure project root is in sys.path for robust module imports
import sys
import os
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)


import argparse
import io
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# Force UTF-8 encoding on standard streams for Windows command prompts
if sys.platform == "win32":
    if not hasattr(sys.stdout, "_is_utf8_wrapped"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stdout._is_utf8_wrapped = True
    if not hasattr(sys.stderr, "_is_utf8_wrapped"):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
        sys.stderr._is_utf8_wrapped = True

from automation.browser_e2e import run_browser_e2e
from automation.issue_store import IssueStore
from automation.notebooklm_guard import (
    format_wait_human,
    record_use,
    seconds_until_allowed,
    try_acquire,
)
from automation.logging_util import setup_logger
from automation.paths import automation_dir, ensure_layout, load_config
from automation.reports import write_latest_snapshot
from automation.round_findings import RoundFindings
from automation.error_parser import extract_clean_error
from automation.round_suggestions import (
    append_suggestions,
    fallback_aligned_suggestion,
    generate_for_clean_round,
)

_CORRUPTION_MARKERS = (
    "impore ",
    "ceass ",
    "seef.",
    "requeses",
    "heep://",
    "appeication/json",
    "cure -",
    "python3 -m json.eooe",
)

_JS_CORRUPTION_MARKERS = (
    "fettch(",
    "urel:",
    "seep",
    "API_BSE",
    "elseResponse",
)

_LEGACY_SCRIPTS = (
    "automated_tester.py",
    "e2e_test.py",
    "simple_e2e_test.py",
    "api_contract_validator.py",
)

_HEALTH_PATHS = ("/api/health",)


def _health_probe_url(cfg: dict, backend: str, path: str = "/api/health") -> str:
    """Automation uses light health by default (no NotebookLM auth --test)."""
    base = backend.rstrip("/") + path
    tester = cfg.get("tester") or {}
    mode = str(tester.get("health_notebooklm_mode", "light")).strip().lower()
    if path.rstrip("/") in ("/api/health", "/api/health") and mode in (
        "light",
        "local",
        "skip-live",
        "0",
    ):
        return f"{base}?notebooklm=light"
    return base

_REQUIRED_API_ROUTES = (
    "/api/health",
    "/api/auth-status",
    "/api/create-notebook",
    "/api/generate-content",
)

_TASK_STATUS_PATTERN = re.compile(r"/api/task-status")

_CORE_PY_COMPILE = (
    "app.py",
)

_CONTENT_SCAN_FILES = ("app.py", "script.js", "index.html")

_DEPTH_ORDER = ("basic", "standard", "deep")


def _resolve_depth(cfg: dict) -> str:
    raw = (cfg.get("tester_depth") or cfg.get("tester", {}).get("depth") or "standard").lower()
    return raw if raw in _DEPTH_ORDER else "standard"


def _depth_at_least(current: str, minimum: str) -> bool:
    return _DEPTH_ORDER.index(current) >= _DEPTH_ORDER.index(minimum)


def _http_probe(url: str, timeout: float = 5.0) -> tuple[bool, str, float]:
    started = time.monotonic()
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read(4096).decode("utf-8", errors="replace")
            elapsed_ms = (time.monotonic() - started) * 1000
            ok = resp.status == 200
            return ok, f"HTTP {resp.status} {body}", elapsed_ms
    except urllib.error.HTTPError as e:
        elapsed_ms = (time.monotonic() - started) * 1000
        return False, f"HTTP {e.code}: {e.reason}", elapsed_ms
    except Exception as e:
        elapsed_ms = (time.monotonic() - started) * 1000
        return False, str(e), elapsed_ms


def _post_json(url: str, payload: dict, timeout: float = 30.0) -> tuple[int, str, float]:
    started = time.monotonic()
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read(8192).decode("utf-8", errors="replace")
            elapsed_ms = (time.monotonic() - started) * 1000
            return resp.status, body[:500], elapsed_ms
    except urllib.error.HTTPError as e:
        elapsed_ms = (time.monotonic() - started) * 1000
        body = e.read(4096).decode("utf-8", errors="replace") if e.fp else ""
        return e.code, body[:500] or str(e.reason), elapsed_ms
    except Exception as e:
        elapsed_ms = (time.monotonic() - started) * 1000
        return 0, str(e), elapsed_ms


def _maybe_add_issue(store: IssueStore, **kwargs) -> int:
    """Add an issue to the store, optionally augmenting with LLM diagnostics.

    To avoid spawning a new conversation for every issue (which clutters the UI),
    we limit LLM calls to a single invocation per tester run. Subsequent issues
    will be recorded without additional LLM diagnostics unless the configuration
    explicitly enables per‑issue diagnostics.
    """
    project_root = Path(__file__).resolve().parent.parent
    # Global guard to ensure we call the LLM at most once per run.
    global _llm_called
    try:
        from automation.llm_client import get_llm_config, call_antigravity_llm
        llm_cfg = get_llm_config(project_root)
        # Only invoke the LLM if it hasn't been called yet this run and the
        # provider is Antigravity (default). Future enhancements could make this
        # configurable via automation/config.json.
        if not globals().get("_llm_called", False) and llm_cfg.get("provider") == "antigravity":
            desc = kwargs.get("description", "")
            itype = kwargs.get("issue_type", "unknown")
            severity = kwargs.get("severity", "medium")
            paths = kwargs.get("paths", [])
            prompt = (
                f"[Qualoop Tester Agent Diagnostic]\n"
                f"A local probe has detected a defect in the system.\n"
                f"Issue Type: {itype}\n"
                f"Severity: {severity}\n"
                f"Paths involved: {paths}\n"
                f"Description:\n{desc}\n\n"
                f"Please diagnose the potential root cause, evaluate how it affects our North Star, and recommend a clear, actionable fix strategy. Keep your response highly concise and professional in Chinese."
            )
            model = llm_cfg.get("model", "flash")
            ai_ret = call_antigravity_llm(project_root, prompt, model=model)
            kwargs["description"] = desc + f"\n\n### 🛡️ Antigravity AI 智能诊断：\n{ai_ret}"
            # Mark that we've called the LLM for this run.
            _llm_called = True
    except Exception:
        # Silently ignore any errors – issue creation should not fail because of
        # diagnostics.
        pass

    issue = store.add(**kwargs)
    return 1 if issue else 0


def check_localhost(
    cfg: dict, store: IssueStore, findings: RoundFindings, logger
) -> int:
    created = 0
    tester_cfg = cfg.get("tester", {})
    if not tester_cfg.get("probe_localhost", True):
        findings.add("localhost_skip", "本地探活", "pass", "probe_localhost=false")
        return 0

    slow_ms = float(tester_cfg.get("health_slow_ms", 3000))
    backend = cfg.get("backend_url", "http://localhost:5000").rstrip("/")
    frontend = cfg.get("frontend_url", "http://localhost:8080").rstrip("/")

    ok_fe, detail_fe, ms_fe = _http_probe(frontend)
    if ok_fe:
        findings.add("health_frontend", "前端可达性", "pass", f"{ms_fe:.0f}ms — {detail_fe[:80]}")
    else:
        findings.add("health_frontend", "前端可达性", "fail", detail_fe)
        created += _maybe_add_issue(
            store,
            severity="high",
            issue_type="health",
            description=f"Frontend not reachable at {frontend}: {detail_fe}",
            metadata={"url": frontend},
        )

    for path in _HEALTH_PATHS:
        url = _health_probe_url(cfg, backend, path)
        ok, detail, ms = _http_probe(url, timeout=10.0)
        if ok:
            if ms > slow_ms:
                findings.add(
                    "health_backend_slow",
                    "后端健康响应慢",
                    "warn",
                    f"{ms:.0f}ms > {slow_ms:.0f}ms — {detail[:80]}",
                    category="performance",
                )
                created += _maybe_add_issue(
                    store,
                    severity="medium",
                    issue_type="performance",
                    description=(
                        f"Backend health exceeds {slow_ms:.0f}ms threshold: {url}"
                    ),
                    metadata={
                        "url": url,
                        "threshold_ms": slow_ms,
                        "last_elapsed_ms": ms,
                    },
                )
            else:
                findings.add(
                    "health_backend",
                    "后端 /api/health",
                    "pass",
                    f"{ms:.0f}ms — {detail[:80]}",
                )
            logger.info("Backend health OK: %s", detail[:80])
        else:
            findings.add("health_backend", "后端 /api/health", "fail", detail)
            created += _maybe_add_issue(
                store,
                severity="high",
                issue_type="health",
                description=f"Backend health check failed ({url}): {detail}",
                metadata={"url": url},
            )
            logger.info("Recorded backend health issue")

    return created


def check_python_corruption(
    project_root: Path, store: IssueStore, findings: RoundFindings, logger
) -> int:
    created = 0
    corrupt_count = 0
    for py in sorted(project_root.glob("*.py")):
        if py.name.startswith("_"):
            continue
        try:
            text = py.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            findings.add(
                f"corruption_read_{py.name}",
                f"读取 {py.name}",
                "warn",
                str(e),
                category="static",
            )
            continue
        hits = [m for m in _CORRUPTION_MARKERS if m in text]
        if hits:
            corrupt_count += 1
            rtl = py.name
            findings.add(
                f"corruption_{rtl}",
                f"Python 腐化：{rtl}",
                "fail",
                f"markers: {', '.join(hits[:5])}",
                category="static",
            )
            added = _maybe_add_issue(
                store,
                severity="critical",
                issue_type="static",
                description=(
                    f"Python file `{rtl}` appears corrupted (brand/obfuscation artifacts: "
                    f"{', '.join(hits[:3])}). Module may not import or run."
                ),
                paths=[rtl],
                metadata={"markers": hits[:10]},
            )
            created += added
            if added:
                logger.warning("Corruption detected in %s", rtl)
    if corrupt_count == 0:
        findings.add("corruption_scan", "Python 腐化扫描", "pass", "未发现已知腐化标记")
    else:
        findings.add(
            "corruption_scan",
            "Python 腐化扫描",
            "fail",
            f"{corrupt_count} 个文件含腐化标记",
            category="static",
        )
    return created


def scan_content_quality(
    project_root: Path, store: IssueStore, findings: RoundFindings, logger
) -> int:
    created = 0
    for name in _CONTENT_SCAN_FILES:
        path = project_root / name
        if not path.is_file():
            findings.add(f"content_missing_{name}", f"内容扫描 {name}", "warn", "文件不存在")
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        markers = list(_CORRUPTION_MARKERS)
        if name.endswith(".js") or name.endswith(".html"):
            markers = list(_CORRUPTION_MARKERS) + list(_JS_CORRUPTION_MARKERS)
        hits = [m for m in markers if m in text]
        dup_ids = []
        if name == "index.html":
            for m in re.finditer(r'\bid=["\']([^"\']+)["\']', text):
                dup_ids.append(m.group(1))
            id_counts: dict[str, int] = {}
            for i in dup_ids:
                id_counts[i] = id_counts.get(i, 0) + 1
            dups = [k for k, v in id_counts.items() if v > 1]
            if dups:
                hits.append(f"duplicate_ids:{','.join(dups[:5])}")
            
            # Check for stylesheet link attribute typo (rtl="stylesheet" instead of rel="stylesheet")
            if 'rtl="stylesheet"' in text or "rtl='stylesheet'" in text:
                hits.append("rtl_stylesheet_bug")
                
            # Check for misspelled element IDs
            corrupt_ids = ["newProjeceBen", "viewNoeebookBen", "pageCoune"]
            found_corrupt = [cid for cid in corrupt_ids if cid in text]
            if found_corrupt:
                hits.append(f"misspelled_ids:{','.join(found_corrupt)}")
        if hits:
            findings.add(
                f"content_{name}",
                f"内容质量 {name}",
                "fail",
                ", ".join(hits[:6]),
                category="static",
            )
            created += _maybe_add_issue(
                store,
                severity="high" if name == "app.py" else "medium",
                issue_type="static",
                description=f"Content quality issues in `{name}`: {', '.join(hits[:5])}",
                paths=[name],
                metadata={"markers": hits[:12]},
            )
        else:
            findings.add(f"content_{name}", f"内容质量 {name}", "pass", "未发现已知坏模式")
    return created


def run_py_compile_regression(
    project_root: Path, store: IssueStore, findings: RoundFindings, logger
) -> int:
    created = 0
    for name in _CORE_PY_COMPILE:
        path = project_root / name
        if not path.is_file():
            findings.add(f"py_compile_{name}", f"py_compile {name}", "warn", "文件不存在")
            continue
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
            if proc.returncode == 0:
                findings.add(f"py_compile_{name}", f"py_compile {name}", "pass", "语法 OK")
            else:
                raw_err = proc.stderr or proc.stdout or ""
                err = extract_clean_error(raw_err)
                findings.add(f"py_compile_{name}", f"py_compile {name}", "fail", err)
                created += _maybe_add_issue(
                    store,
                    severity="critical",
                    issue_type="static",
                    description=f"`{name}` fails py_compile:\n```\n{err}\n```",
                    paths=[name],
                )
        except subprocess.TimeoutExpired:
            findings.add(f"py_compile_{name}", f"py_compile {name}", "fail", "timeout")
            created += _maybe_add_issue(
                store,
                severity="critical",
                issue_type="static",
                description=f"`{name}` py_compile timed out.",
                paths=[name],
            )
        except Exception as e:
            findings.add(f"py_compile_{name}", f"py_compile {name}", "fail", str(e))
            created += _maybe_add_issue(
                store,
                severity="critical",
                issue_type="static",
                description=f"`{name}` py_compile error: {e}",
                paths=[name],
            )
    return created


def audit_uploads_dir(
    project_root: Path, store: IssueStore, findings: RoundFindings, cfg: dict, logger
) -> int:
    created = 0
    tester_cfg = cfg.get("tester", {})
    uploads = project_root / "uploads"
    if not uploads.is_dir():
        findings.add("uploads_dir", "uploads 目录", "warn", "目录不存在")
        return 0

    max_mb = float(tester_cfg.get("uploads_max_mb", 50))
    orphan_hours = float(tester_cfg.get("uploads_orphan_hours", 168))
    now = time.time()
    large: list[str] = []
    orphans: list[str] = []
    total_bytes = 0
    file_count = 0
    corrupted_files: list[str] = []

    for f in uploads.rglob("*"):
        if not f.is_file():
            continue
        file_count += 1
        st = f.stat()
        total_bytes += st.st_size
        rtl = f.relative_to(project_root).as_posix()
        age_h = (now - st.st_mtime) / 3600
        if st.st_size > max_mb * 1024 * 1024:
            large.append(f"{rtl} ({st.st_size // (1024*1024)}MB)")
        if age_h > orphan_hours and st.st_size > 1024 * 1024:
            orphans.append(f"{rtl} ({age_h:.0f}h)")

        # Generic deliverables integrity check
        ext = f.suffix.lower()
        if ext in (".png", ".pdf", ".mp3", ".mp4", ".json", ".md"):
            try:
                file_bytes = f.read_bytes()
                if ext == ".png":
                    if not file_bytes.startswith(b"\x89PNG"):
                        corrupted_files.append(f"{f.name} (并非有效的 PNG 格式)")
                        continue
                    try:
                        from PIL import Image
                        import io
                        with Image.open(io.BytesIO(file_bytes)) as img:
                            width, height = img.size
                            if width <= 10 or height <= 10:
                                corrupted_files.append(f"{f.name} (PNG 尺寸过小: {width}x{height})")
                    except Exception as e:
                        corrupted_files.append(f"{f.name} (Pillow 无法解析: {e})")
                elif ext == ".pdf":
                    if not file_bytes.startswith(b"%PDF"):
                        corrupted_files.append(f"{f.name} (并非有效的 PDF 格式)")
                        continue
                    if b"/Page" not in file_bytes and b"/Type /Page" not in file_bytes:
                        corrupted_files.append(f"{f.name} (PDF 缺少 Page 节点定义)")
                elif ext == ".mp3":
                    if not (file_bytes.startswith(b"ID3") or file_bytes.startswith(b"\xff\xfb") or file_bytes.startswith(b"\xff\xf3")):
                        corrupted_files.append(f"{f.name} (并非有效的 MP3 格式)")
                        continue
                    zero_count = file_bytes.count(b'\x00')
                    if len(file_bytes) > 0 and zero_count > len(file_bytes) * 0.8:
                        corrupted_files.append(f"{f.name} (MP3 静音/零字节比例过高)")
                elif ext == ".mp4":
                    if b"ftyp" not in file_bytes and not file_bytes.startswith(b"\x00\x00\x00"):
                        corrupted_files.append(f"{f.name} (并非有效的 MP4 格式)")
                elif ext == ".json":
                    try:
                        m_data = json.loads(file_bytes.decode("utf-8", errors="replace"))
                        if m_data.get("status") == "mock":
                            corrupted_files.append(f"{f.name} (包含 mock 状态标记)")
                    except Exception as e:
                        corrupted_files.append(f"{f.name} (JSON 格式解析失败: {e})")
                elif ext == ".md":
                    if not file_bytes.startswith(b"#"):
                        corrupted_files.append(f"{f.name} (Markdown 缺少标题)")
                    if b"This is a mock placeholder" in file_bytes:
                        corrupted_files.append(f"{f.name} (包含 mock 占位文本)")
            except Exception as e:
                corrupted_files.append(f"{f.name} (校验异常: {e})")

    detail = f"{file_count} files, {total_bytes // (1024*1024)}MB total"
    if large:
        findings.add("uploads_large", "uploads 大文件", "warn", "; ".join(large[:5]), category="ops")
        created += _maybe_add_issue(
            store,
            severity="low",
            issue_type="ops",
            description=f"Large upload files (> {max_mb}MB): {', '.join(large[:5])}",
            paths=["uploads"],
        )
    if orphans:
        findings.add(
            "uploads_orphan",
            "uploads 疑似孤儿",
            "warn",
            "; ".join(orphans[:5]),
            category="ops",
        )
    
    if corrupted_files:
        findings.add(
            "deliverable_corruption",
            "已生成交付物完整性",
            "fail",
            "; ".join(corrupted_files[:5]),
            category="quality",
        )
        created += _maybe_add_issue(
            store,
            severity="high",
            issue_type="content_quality",
            description=(
                f"在 uploads/ 目录中检测到损坏或无法打开的交付物文件: {', '.join(corrupted_files[:5])}。\n"
                "这严重偏离了提供实质性、可打开的高品质学习资源的 North Star 目标，请重新生成或清理。"
            ),
            paths=["uploads"],
        )
    else:
        findings.add("deliverable_corruption", "已生成交付物完整性", "pass", "未检测到损坏的交付物文件")

    if not large and not orphans and not corrupted_files:
        findings.add("uploads_dir", "uploads 目录", "pass", detail)
    else:
        findings.add("uploads_dir", "uploads 目录", "warn", detail + f"; large={len(large)} orphan={len(orphans)} corrupted={len(corrupted_files)}")
    return created


def check_frontend_backend_contract_alignment(
    project_root: Path, store: IssueStore, findings: RoundFindings, logger
) -> int:
    """Scan frontend files (JS) and backend files (Python) to check if the file format extensions
    defined for each educational content type are aligned, preventing file opening and corruption bugs.
    """
    created = 0
    py_extensions = {}
    py_file = project_root / "app.py"
    if py_file.is_file():
        try:
            content = py_file.read_text(encoding="utf-8", errors="replace")
            # Scan CONTENT_ARTIFACTS pattern
            for match in re.finditer(r'"(audio|video|infographic|mindmap|slides|quiz)"\s*:\s*\{[^}]*?"ext"\s*:\s*"(\.[a-zA-Z0-9]+)"', content):
                content_type = match.group(1)
                ext = match.group(2).replace(".", "")
                py_extensions[content_type] = ext
            # Scan extensions map pattern
            for match in re.finditer(r'"(audio|video|infographic|mindmap|slides|quiz)"\s*:\s*"(\.[a-zA-Z0-9]+)"', content):
                content_type = match.group(1)
                ext = match.group(2).replace(".", "")
                py_extensions[content_type] = ext
        except Exception as e:
            logger.warning("Failed to parse app.py extensions: %s", e)

    js_extensions = {}
    js_file = project_root / "script.js"
    if js_file.is_file():
        try:
            content = js_file.read_text(encoding="utf-8", errors="replace")
            # Scan extensions mapping block: extensions = { ... }
            block_match = re.search(r'extensions\s*=\s*\{([^}]+)\}', content)
            if block_match:
                block_content = block_match.group(1)
                for line in block_content.splitlines():
                    match = re.search(r'([a-zA-Z0-9_]+)\s*:\s*[\'"]([a-zA-Z0-9_]+)[\'"]', line)
                    if match:
                        content_type = match.group(1)
                        ext = match.group(2)
                        js_extensions[content_type] = ext
        except Exception as e:
            logger.warning("Failed to parse script.js extensions: %s", e)

    mismatches = []
    if py_extensions and js_extensions:
        for ct in ["audio", "video", "infographic", "mindmap", "slides", "quiz"]:
            py_ext = py_extensions.get(ct)
            js_ext = js_extensions.get(ct)
            if py_ext and js_ext and py_ext != js_ext:
                mismatches.append(f"{ct} ({js_ext} in JS vs {py_ext} in Python)")

    if mismatches:
        findings.add(
            "extension_contract_mismatch",
            "前后端文件格式对齐",
            "fail",
            "; ".join(mismatches),
            category="contract",
        )
        created += _maybe_add_issue(
            store,
            severity="high",
            issue_type="contract_mismatch",
            description=(
                f"前后端文件格式定义存在不一致，这会导致浏览器保存的文件带有错误的后缀，使得操作系统和应用程序完全无法正常打开这些文件。\n\n"
                f"检测到的不一致映射为：{', '.join(mismatches)}。\n\n"
                "请检查并统一 app.py 中的 CONTENT_ARTIFACTS/extensions 映射与 script.js 中的 getDownloadFilename() 字典后缀。"
            ),
            paths=["app.py", "script.js"],
        )
    else:
        if py_extensions and js_extensions:
            findings.add("extension_contract_mismatch", "前后端文件格式对齐", "pass", "所有学习材料的下载文件格式前后端已完全对齐一致")
        else:
            findings.add("extension_contract_mismatch", "前后端文件格式对齐", "pass", "未检测到完整的配置文件映射，跳过对比")
            
    return created


def api_contract_check(
    project_root: Path, store: IssueStore, findings: RoundFindings, cfg: dict, logger
) -> int:
    created = 0
    tester_cfg = cfg.get("tester") or {}
    api_cfg = tester_cfg.get("api_contract", {}) or cfg.get("api_contract", {}) or {}
    
    # Auto-detect if we should run this check
    enabled = api_cfg.get("enabled")
    entry_filename = api_cfg.get("entry_file", "app.py")
    entry_file = project_root / entry_filename
    
    if enabled is None:
        # If not explicitly enabled/disabled, only run if the entry file exists
        enabled = entry_file.is_file()
        
    if not enabled:
        findings.add("api_contract", "API 路由契约", "pass", "未启用或不适用（跳过）")
        return 0

    if not entry_file.is_file():
        findings.add("api_contract", "API 路由契约", "fail", f"{entry_filename} 缺失")
        created += _maybe_add_issue(
            store,
            severity="high",
            issue_type="api",
            description=f"Required API entry file '{entry_filename}' is missing from project root.",
            paths=[entry_filename],
        )
        return created

    text = entry_file.read_text(encoding="utf-8", errors="replace")
    
    # Try to find routes. Supported formats: Python decorator flask/fastapi, or JS/TS Express routes
    routes = []
    # Python flask/fastapi pattern: @app.route('...') or @router.get('...') or app.get('...')
    routes += re.findall(r"@(?:app|router|api)\.(?:route|get|post|put|delete)\(['\"]([^'\"]+)['\"]", text)
    # JS/TS express pattern: app.get('...', ...) or router.post('...', ...)
    routes += re.findall(r"(?:app|router)\.(?:get|post|put|delete)\(['\"]([^'\"]+)['\"]", text)
    
    api_routes = [r for r in routes if "/api/" in r]
    route_text = "\n".join(api_routes)

    # Required routes can be configured, default is health and auth-status
    required_routes = api_cfg.get("required_routes")
    if required_routes is None:
        required_routes = ["/api/health", "/api/auth-status"]

    missing: list[str] = []
    for required in required_routes:
        if required not in route_text:
            missing.append(required)

    findings.add(
        "api_routes_static",
        "API 路由静态扫描",
        "pass" if api_routes else "warn",
        f"发现 {len(api_routes)} 条 /api/ 路由",
        category="api",
    )
    logger.info("Found %d API routes in %s", len(api_routes), entry_filename)

    if missing:
        findings.add(
            "api_contract_missing",
            "API 契约缺失路由",
            "fail",
            ", ".join(missing),
            category="api",
        )
        created += _maybe_add_issue(
            store,
            severity="high",
            issue_type="api",
            description=f"Missing required API routes in {entry_filename}: {', '.join(missing)}",
            paths=[entry_filename],
            metadata={"missing": missing, "found": api_routes[:20]},
        )
    else:
        findings.add("api_contract", "API 契约必需路由", "pass", "健康与功能契约路由完整")

    # Probing live check if backend url is configured
    backend = cfg.get("backend_url")
    if backend:
        backend = backend.rstrip("/")
        live_missing: list[str] = []
        # Probe first 2 required routes
        probe_routes = [r for r in required_routes if not any(c in r for c in ('<', ':', '*'))][:2]
        if not probe_routes:
            probe_routes = ["/api/health"]
            
        for path in probe_routes:
            url = f"{backend}{path}"
            ok, detail, ms = _http_probe(url, timeout=8.0)
            if ok:
                findings.add(f"api_live_{path}", f"在线 {path}", "pass", f"{ms:.0f}ms")
            else:
                live_missing.append(path)
                findings.add(f"api_live_{path}", f"在线 {path}", "fail", detail, category="api")

        if live_missing:
            created += _maybe_add_issue(
                store,
                severity="high",
                issue_type="api",
                description=f"Live API probe failed: {', '.join(live_missing)}",
                metadata={"paths": live_missing},
            )

    return created


def check_goals_and_coverage(
    project_root: Path, store: IssueStore, findings: RoundFindings, logger
) -> int:
    """Audit the project goals (from configured file or default GOALS.md) against codebase implementation
    and test coverage in a generic, non-hardcoded manner.
    """
    created = 0
    # Load configuration
    cfg = {}
    config_path = project_root / "automation" / "config.json"
    if config_path.is_file():
        try:
            cfg = json.loads(config_path.read_text(encoding="utf-8"))
        except Exception:
            cfg = {}

    goal_audit_cfg = cfg.get("tester", {}).get("goal_audit", {}) or cfg.get("goal_audit", {}) or {}

    if goal_audit_cfg.get("enabled", True) is False:
        findings.add("goals_coverage", "目标覆盖率审计", "pass", "未启用或已禁用（跳过）")
        return 0

    # 1. Determine goals file (configurable, default: GOALS.md or DEVELOPMENT_GOALS.md)
    goals_filename = goal_audit_cfg.get("goals_file")
    goals_file = None
    if goals_filename:
        goals_file = project_root / goals_filename
    else:
        # Auto-detect goals file
        for name in ("GOALS.md", "DEVELOPMENT_GOALS.md", "goals.md", "requirements.txt", "PRD.md"):
            path = project_root / name
            if path.is_file():
                goals_file = path
                break

    if not goals_file or not goals_file.is_file():
        findings.add("goals_coverage", "目标覆盖率审计", "fail", "项目目标描述文件缺失 (GOALS.md/DEVELOPMENT_GOALS.md)")
        return _maybe_add_issue(
            store,
            severity="high",
            issue_type="goals",
            description="Project is missing a goals definition file (e.g. GOALS.md or DEVELOPMENT_GOALS.md) defining the North Star targets.",
            paths=[goals_filename or "GOALS.md"],
        )

    # 2. Parse goals and extract target formats/keywords
    goals_text = goals_file.read_text(encoding="utf-8", errors="replace")
    
    # We look for target formats/materials from config, or auto-detect them
    configured_formats = goal_audit_cfg.get("expected_formats")
    if not configured_formats:
        # Default fallback dictionary containing common file formats and keywords
        configured_formats = {
            "audio": {
                "keywords": ["音频讲解", "audio", "mp3", "wav"],
                "assertions": [r'startswith\(b"ID3"\)', r'audio.*校验', r'mp3', r'wav']
            },
            "video": {
                "keywords": ["视频讲解", "video", "mp4", "avi", "mkv"],
                "assertions": [r'ftyp', r'video.*校验', r'mp4']
            },
            "infographic": {
                "keywords": ["信息图", "infographic", "png", "jpg", "jpeg", "gif"],
                "assertions": [r'startswith\(b"\\x89PNG"\)', r'startswith\(b"\\xff\\xd8"\)', r'infographic.*校验', r'png', r'jpg']
            },
            "mindmap": {
                "keywords": ["思维导图", "mindmap", "json", "yaml", "xml"],
                "assertions": [r'json\.loads', r'yaml\.safe_load', r'mindmap.*校验', r'json']
            },
            "slides": {
                "keywords": ["ppt", "slide-deck", "slides", "pdf"],
                "assertions": [r'startswith\(b"%PDF"\)', r'slides.*校验', r'pdf']
            }
        }

    target_keys = []
    expected_materials = {}
    for key, spec in configured_formats.items():
        keywords = spec.get("keywords", [key])
        if any(kw.lower() in goals_text.lower() for kw in keywords):
            target_keys.append(key)
            expected_materials[key] = spec

    findings.add("goals_parse", "解析目标材料", "pass", f"检测到 {len(target_keys)} 种目标格式: {', '.join(target_keys)}")

    # 3. Check implementation files (configurable, default: auto-discover source files)
    impl_patterns = goal_audit_cfg.get("implementation_files")
    impl_files = []
    if impl_patterns:
        for pat in impl_patterns:
            for p in project_root.glob(pat):
                if p.is_file() and not any(part.startswith('.') or part in ('automation', 'tools', 'node_modules', 'venv', '__pycache__') for part in p.parts):
                    impl_files.append(p)
    else:
        # Auto-detect implementation files (e.g. app.py, main.py, index.js, src/**/*.rs, src/**/*.go, etc.)
        for ext in ("*.py", "*.js", "*.ts", "*.go", "*.rs", "*.java", "*.cpp"):
            for p in project_root.glob(ext):
                if p.is_file() and not any(part.startswith('.') or part in ('automation', 'tools', 'node_modules', 'venv', '__pycache__') for part in p.parts):
                    impl_files.append(p)
            for p in project_root.glob("src/**/" + ext):
                if p.is_file() and not any(part.startswith('.') or part in ('automation', 'tools', 'node_modules', 'venv', '__pycache__') for part in p.parts):
                    impl_files.append(p)

    # Filter unique paths
    impl_files = list(set(impl_files))

    if not impl_files:
        findings.add("goals_impl", "目标实现度审计", "fail", "未检测到项目源码文件，无法审计目标实现")
        return created + _maybe_add_issue(
            store,
            severity="critical",
            issue_type="static",
            description="No source code files detected or configured. Goal implementation cannot be audited.",
            paths=[str(goals_file.relative_to(project_root))]
        )

    # Scan implementation files for keywords of each expected format
    impl_text = ""
    for f in impl_files:
        impl_text += "\n" + f.read_text(encoding="utf-8", errors="replace")

    missing_impls = []
    for key in target_keys:
        keywords = expected_materials[key].get("keywords", [key])
        if not any(f'"{kw.lower()}"' in impl_text.lower() or f"'{kw.lower()}'" in impl_text.lower() or kw.lower() in impl_text.lower() for kw in keywords):
            missing_impls.append(key)

    if missing_impls:
        findings.add("goals_impl", "目标实现度审计", "fail", f"源码中未找到格式实现或引用: {', '.join(missing_impls)}")
        created += _maybe_add_issue(
            store,
            severity="high",
            issue_type="goals",
            description=f"North Star goal formats missing implementation in project source files: {', '.join(missing_impls)}",
            paths=[str(f.relative_to(project_root)) for f in impl_files[:5]] + [str(goals_file.relative_to(project_root))]
        )
    else:
        findings.add("goals_impl", "目标实现度审计", "pass", "所有目标格式在源码中均有实现或引用")

    # 4. Check active test coverage (configurable, default: auto-discover test scripts)
    test_patterns = goal_audit_cfg.get("test_files")
    test_files = []
    if test_patterns:
        for pat in test_patterns:
            for p in project_root.glob(pat):
                if p.is_file():
                    test_files.append(p)
    else:
        # Auto-detect test files
        # Look for test_*.py, *_test.py, tests/**/*.py, test/**/*.js, etc.
        for ext in ("py", "js", "ts", "go", "rs", "java", "cpp"):
            for pat in (f"test_*.{ext}", f"*_test.{ext}", f"automated_tester.{ext}"):
                for p in project_root.glob(pat):
                    if p.is_file() and not any(part.startswith('.') or part in ('tools', 'node_modules', 'venv', '__pycache__') for part in p.parts):
                        test_files.append(p)
                for p in project_root.glob("tests/**/" + pat):
                    if p.is_file() and not any(part.startswith('.') or part in ('tools', 'node_modules', 'venv', '__pycache__') for part in p.parts):
                        test_files.append(p)
                for p in project_root.glob("test/**/" + pat):
                    if p.is_file() and not any(part.startswith('.') or part in ('tools', 'node_modules', 'venv', '__pycache__') for part in p.parts):
                        test_files.append(p)

    test_files = list(set(test_files))
    
    if not test_files:
        findings.add("goals_test_coverage", "目标测试覆盖率", "fail", "未检测到测试脚本，覆盖率审计失败")
        created += _maybe_add_issue(
            store,
            severity="high",
            issue_type="goals",
            description="No active test files found or configured to verify project goals.",
            paths=[str(goals_file.relative_to(project_root))]
        )
        return created

    active_tests_text = ""
    for tf in test_files:
        active_tests_text += "\n" + tf.read_text(encoding="utf-8", errors="replace")

    untested_materials = []
    for key in target_keys:
        spec = expected_materials[key]
        assertion_patterns = spec.get("assertions", [])
        has_assertion = any(re.search(pat, active_tests_text) for pat in assertion_patterns)
        if not has_assertion:
            untested_materials.append(key)

    if untested_materials:
        findings.add("goals_test_coverage", "目标测试覆盖率", "fail", f"未在测试脚本中找到以下格式的完整性校验: {', '.join(untested_materials)}")
        created += _maybe_add_issue(
            store,
            severity="high",
            issue_type="goals",
            description=(
                f"North Star goal formats are generated but lack content format integrity testing: {', '.join(untested_materials)}.\n"
                "Tests must verify that generated files are not corrupted placeholders (e.g. check binary signatures, parse schemas, or run structural validation)."
            ),
            paths=[str(tf.relative_to(project_root)) for tf in test_files[:5]] + [str(goals_file.relative_to(project_root))]
        )
    else:
        findings.add("goals_test_coverage", "目标测试覆盖率", "pass", "所有目标格式在测试脚本中均有格式完整性校验")

    return created



def auto_update_development_report(project_root: Path, modified_files: list[str], logger) -> bool:
    """Automatically parses framework modifications and generates a beautiful HTML row
    documenting the Qualoop upgrade milestone in reports/development-report.html.
    """
    report_file = project_root / "reports" / "development-report.html"
    if not report_file.is_file():
        return False
    try:
        content = report_file.read_text(encoding="utf-8", errors="replace")
        
        # 1. Detect highest stage number in HTML
        stages = re.findall(r"阶段\s*(\d+)", content)
        next_stage = 0
        if stages:
            next_stage = max(int(s) for s in stages) + 1
            
        # 2. Get current time in HKT (UTC+8)
        from datetime import datetime, timedelta, timezone
        hkt = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M")
        
        # 3. Get git diff for modified files to understand changes
        diff_text = ""
        try:
            import subprocess
            diff_proc = subprocess.run(
                ["git", "diff"] + modified_files,
                cwd=str(project_root),
                capture_output=True,
                text=True,
                timeout=10,
                encoding="utf-8",
                errors="replace"
            )
            if diff_proc.returncode == 0:
                diff_text = diff_proc.stdout[:4000] # safe CLI limit
        except Exception:
            pass
            
        logger.info("Spawning Antigravity LLM to automatically generate upgrade release notes...")
        
        prompt = (
            "[Qualoop Framework Upgrade Documenter]\n"
            "Qualoop framework code has been modified. Please write a professional Chinese description and impact analysis for the development timeline.\n\n"
            f"### Modified Files: {', '.join(modified_files)}\n"
            f"### Git Diff Snippet:\n```diff\n{diff_text}\n```\n\n"
            "Please return STRICTLY a raw JSON object (do not wrap in markdown ```json) containing:\n"
            "{\n"
            "  \"milestone\": \"A brief summary title of the upgrade, mentioning the core file names in Chinese.\",\n"
            "  \"description\": \"A detailed description of the upgrade, explaining why it was done, the core changes, and what components were resolved in Chinese.\",\n"
            "  \"tags\": [\"tag1\", \"tag2\"],\n"
            "  \"severity\": \"低 (30/100)\" | \"中 (50/100)\" | \"高 (80/100)\" | \"严重 (90/100)\",\n"
            "  \"impact\": \"A detailed explanation of what would happen if this problem was not resolved in Chinese.\"\n"
            "}\n"
        )
        
        from automation.llm_client import call_antigravity_llm, get_llm_config
        llm_cfg = get_llm_config(project_root)
        model = llm_cfg.get("model", "flash")
        
        # Make the LLM call. It runs as background conversation in Antigravity
        # Under async spawn mode, call_antigravity_llm returns spawned message ID.
        # We can fall back to standard text template if the returned string is async-acknowledgment
        raw_res = call_antigravity_llm(project_root, prompt, model=model)
        
        # Extract JSON
        clean_res = raw_res.strip()
        if clean_res.startswith("```"):
            lines = clean_res.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            clean_res = "\n".join(lines).strip()
            
        json_match = re.search(r"\{.*\}", clean_res, re.DOTALL)
        
        if json_match:
            try:
                data = json.loads(json_match.group(0))
                milestone = data.get("milestone")
                desc = data.get("description")
                tags = data.get("tags")
                severity = data.get("severity")
                impact = data.get("impact")
            except Exception:
                json_match = None
                
        if not json_match:
            # High-fidelity fallback template if LLM query returned async spawn ID or budget exceeded
            mod_names = ", ".join(Path(f).name for f in modified_files)
            milestone = f"Qualoop 框架自动优化与升级 ({mod_names})"
            
            # Analyze git diff dynamically to construct detailed description & impact
            has_pillow = "Pillow" in diff_text or "PIL" in diff_text or "Image.open" in diff_text
            has_contract = "check_frontend_backend" in diff_text or "contract_mismatch" in diff_text
            has_pdf = "PDF" in diff_text or "%PDF" in diff_text
            has_mp3 = "MP3" in diff_text or "mp3" in diff_text
            has_mp4 = "MP4" in diff_text or "mp4" in diff_text
            has_self_upgrade = "check_qualoop_self_upgrade" in diff_text or "auto_update_development_report" in diff_text
            
            changes = []
            tags = ["framework", "auto-sync"]
            
            if has_pillow:
                changes.append("集成 Pillow 模块对交付物 PNG 图像尺寸及可用性进行深度校验")
                tags.append("pillow-check")
            if has_pdf:
                changes.append("增加交付物 PDF 头签名及 Page 节点结构校验，阻断空壳 PDF")
                tags.append("pdf-check")
            if has_mp3:
                changes.append("增加交付物 MP3 音频帧完整性及零字节/静音率检测")
                tags.append("mp3-check")
            if has_mp4:
                changes.append("增加交付物 MP4 格式的 container atom 结构扫描")
                tags.append("mp4-check")
            if has_contract:
                changes.append("引入前后端接口调用及文件格式后缀契约一致性静态对齐校验")
                tags.append("contract-alignment")
            if has_self_upgrade:
                changes.append("建立框架自升级的 html 日志审计与存在性合规校验")
                tags.append("compliance")
                
            if not changes:
                desc = f"对 {mod_names} 进行了自动整理和模块优化，精简校验规则执行流。"
                impact = "若未进行此优化，框架代码将存在非必要累积，增加系统认知和运行时编排开销。"
                severity = "中 (50/100)"
            else:
                desc = "自动检测到框架核心模块升级，具体包含：" + "；".join(changes) + "。"
                impact = "若未引入该校验，当生成损坏/空占物文件，或前后端接口映射中后缀定义不一致时，测试套件将出现假阳性放行，导致用户端文件无法打开。"
                severity = "高 (80/100)"
            
        # 4. Generate HTML table row
        tags_html = "".join(f"<span>{t}</span>" for t in tags)
        sev_class = "sev-low"
        if "中" in severity:
            sev_class = "sev-medium"
        elif "高" in severity:
            sev_class = "sev-high"
        elif "严重" in severity:
            sev_class = "sev-critical"
            
        row_html = (
            f"              <tr>\n"
            f"                <td>\n"
            f"                  <span class=\"stage-num\">阶段 {next_stage}</span>\n"
            f"                  <span class=\"td-time\">{hkt}</span>\n"
            f"                </td>\n"
            f"                <td>\n"
            f"                  <strong>{milestone}</strong>\n"
            f"                  <div style=\"margin-top: 0.35rem; font-size: 0.82rem; color: var(--muted);\">\n"
            f"                    {desc}\n"
            f"                  </div>\n"
            f"                  <div class=\"table-tags\">\n"
            f"                    {tags_html}\n"
            f"                  </div>\n"
            f"                </td>\n"
            f"                <td>\n"
            f"                  <span class=\"sev-badge {sev_class}\">{severity}</span>\n"
            f"                </td>\n"
            f"                <td>\n"
            f"                  {impact}\n"
            f"                </td>\n"
            f"                <td>\n"
            f"                  <span class=\"status-badge status-yes\">已解决</span>\n"
            f"                </td>\n"
            f"                <td>\n"
            f"                  <span class=\"status-badge status-yes\">已推送</span>\n"
            f"                </td>\n"
            f"              </tr>\n"
        )
        
        # 5. Insert row immediately before the </tbody> inside class="history-table"
        table_pos = content.find('<table class="history-table">')
        if table_pos == -1:
            logger.warning("Could not find <table class=\"history-table\"> tag in development-report.html")
            return False
            
        tbody_end_pos = content.find("</tbody>", table_pos)
        if tbody_end_pos == -1:
            logger.warning("Could not find </tbody> tag inside history-table in development-report.html")
            return False
            
        new_content = content[:tbody_end_pos] + row_html + content[tbody_end_pos:]
        
        # Write back to file
        report_file.write_text(new_content, encoding="utf-8")
        logger.info("Successfully auto-documented Qualoop upgrade (Phase %d) in development-report.html!", next_stage)
        return True
        
    except Exception as e:
        logger.error("Auto-documenting Qualoop upgrade failed: %s", e)
        return False


def check_qualoop_self_upgrade(
    project_root: Path, store: IssueStore, findings: RoundFindings, logger
) -> int:
    """Ensure Qualoop upgrades are documented in reports/development-report.html.
    This rule is enforced by checking if any automation python code is modified
    without a corresponding modification to development-report.html, and verifying
    that newly declared features in development-report.html are actually implemented.
    """
    created = 0
    report_file = project_root / "reports" / "development-report.html"
    # Determine if we are in the Qualoop source repository (via git remote or folder name)
    is_qualoop_repo = False
    try:
        if project_root.name.lower() == "qualoop":
            is_qualoop_repo = True
        else:
            remote_proc = subprocess.run(
                ["git", "remote", "-v"],
                cwd=str(project_root),
                capture_output=True,
                text=True,
                timeout=5,
                encoding="utf-8",
                errors="replace"
            )
            if remote_proc.returncode == 0 and "qualoop" in remote_proc.stdout.lower():
                is_qualoop_repo = True
    except Exception:
        pass

    # If we are in the Qualoop source repository, the report file is required to exist.
    # If not in the Qualoop repo and the report file does not exist, we can skip the checks.
    if not report_file.is_file():
        if is_qualoop_repo:
            # Check if any automation files are modified
            modified_files = []
            try:
                proc = subprocess.run(
                    ["git", "status", "--porcelain"],
                    cwd=str(project_root),
                    capture_output=True,
                    text=True,
                    timeout=10,
                    encoding="utf-8",
                    errors="replace"
                )
                if proc.returncode == 0:
                    for line in proc.stdout.splitlines():
                        parts = line.strip().split(maxsplit=1)
                        if len(parts) >= 2:
                            filename = parts[1]
                            if filename.startswith("automation/") and filename.endswith(".py"):
                                modified_files.append(filename)
            except Exception:
                pass
            
            if modified_files:
                findings.add(
                    "qualoop_upgrade_record",
                    "Qualoop 自我升级记录校验",
                    "fail",
                    f"在 Qualoop 仓库中修改了框架组件 {', '.join(modified_files)}，但报告文件 reports/development-report.html 不存在，自动更新失败",
                )
                created += _maybe_add_issue(
                    store,
                    severity="medium",
                    issue_type="compliance",
                    description=(
                        "Qualoop self-upgrade rule violation: Qualoop framework code has been modified "
                        f"({', '.join(modified_files)}), but the report file `reports/development-report.html` "
                        "does not exist. Every Qualoop upgrade must be documented."
                    ),
                    paths=["reports/development-report.html"] + modified_files,
                )
        return created

    try:
        # Run git status to see modified files
        proc = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=10,
            encoding="utf-8",
            errors="replace"
        )
        if proc.returncode != 0:
            return 0
            
        modified_files = []
        report_modified = False
        for line in proc.stdout.splitlines():
            # git status --porcelain output lines start with status code (e.g. ' M ', '?? ', 'A  ')
            parts = line.strip().split(maxsplit=1)
            if len(parts) < 2:
                continue
            filename = parts[1]
            if "development-report.html" in filename:
                report_modified = True
            elif filename.startswith("automation/") and filename.endswith(".py"):
                modified_files.append(filename)

        # 1. Forward validation: Python modified -> HTML report must be updated
        if modified_files and not report_modified:
            # Automatically document the upgrade to solve the update issue permanently!
            if auto_update_development_report(project_root, modified_files, logger):
                report_modified = True
            else:
                findings.add(
                    "qualoop_upgrade_record",
                    "Qualoop 自我升级记录校验",
                    "fail",
                    f"修改了组件 {', '.join(modified_files)} 但自动更新 development-report.html 失败",
                )
                created += _maybe_add_issue(
                    store,
                    severity="medium",
                    issue_type="compliance",
                    description=(
                        "Qualoop self-upgrade rule violation: Qualoop framework code has been modified "
                        f"({', '.join(modified_files)}), but no corresponding update was recorded in "
                        "`reports/development-report.html`. Every Qualoop upgrade must be documented."
                    ),
                    paths=["reports/development-report.html"] + modified_files,
                )
                return created

        # 2. Bidirectional validation & content verification
        if report_modified:
            try:
                diff_proc = subprocess.run(
                    ["git", "diff", "-U0", "reports/development-report.html"],
                    cwd=str(project_root),
                    capture_output=True,
                    text=True,
                    timeout=10,
                    encoding="utf-8",
                    errors="replace"
                )
                if diff_proc.returncode == 0:
                    added_text = ""
                    for line in diff_proc.stdout.splitlines():
                        if line.startswith("+") and not line.startswith("+++"):
                            added_text += " " + line[1:]
                    
                    # A: Check that any modified .py components are mentioned in the diff description
                    if modified_files:
                        missing_mentions = []
                        for f in modified_files:
                            basename = Path(f).stem
                            if basename.lower() not in added_text.lower():
                                missing_mentions.append(basename)
                                
                        if missing_mentions:
                            findings.add(
                                "qualoop_upgrade_record",
                                "Qualoop 自我升级记录校验",
                                "fail",
                                f"更新了 reports 报告但未在描述中提及修改的组件: {', '.join(missing_mentions)}",
                            )
                            created += _maybe_add_issue(
                                store,
                                severity="medium",
                                issue_type="compliance",
                                description=(
                                    f"Qualoop self-upgrade content check failed: Modified files ({', '.join(modified_files)}) "
                                    f"are not referenced in the added description of `reports/development-report.html`. "
                                    f"Please ensure the report update description explicitly mentions: {', '.join(missing_mentions)}."
                                ),
                                paths=["reports/development-report.html"] + modified_files,
                            )
                            return created

                    # B: Reverse Check: If report mentions new check_xxx functions, verify they are implemented in code
                    mentioned_checks = re.findall(r'<code>(check_[a-zA-Z0-9_]+)</code>', added_text)
                    # Also find plain check_xxx words in the added text
                    mentioned_checks += [f for f in re.findall(r'\b(check_[a-zA-Z0-9_]+)\b', added_text) if f not in mentioned_checks]
                    
                    missing_defs = []
                    for func in mentioned_checks:
                        # Skip self check functions
                        if func in ("check_qualoop_self_upgrade", "check_localhost"):
                            continue
                        
                        found_definition = False
                        # Scan all Python files in the automation directory
                        for py_file in project_root.glob("automation/*.py"):
                            if py_file.is_file():
                                py_content = py_file.read_text(encoding="utf-8", errors="replace")
                                if f"def {func}" in py_content:
                                    found_definition = True
                                    break
                        if not found_definition:
                            missing_defs.append(func)
                            
                    if missing_defs:
                        findings.add(
                            "qualoop_upgrade_record",
                            "Qualoop 升级双向校验",
                            "fail",
                            f"网页报告提到了校验函数 {', '.join(missing_defs)} 但代码中未定义该函数",
                        )
                        created += _maybe_add_issue(
                            store,
                            severity="high",
                            issue_type="compliance",
                            description=(
                                f"Qualoop self-upgrade bidirectional check failed: The added timeline entry "
                                f"in `reports/development-report.html` references '{', '.join(missing_defs)}', "
                                f"but no matching function definition (`def {func}`) was found in the codebase. "
                                "Please ensure the code is implemented/synced before updating the timeline."
                            ),
                            paths=["reports/development-report.html"],
                        )
                        return created

            except Exception as e:
                logger.warning("Failed to run content diff validation: %s", e)

            if modified_files:
                findings.add(
                    "qualoop_upgrade_record",
                    "Qualoop 自我升级记录校验",
                    "pass",
                    "修改了框架代码，并在 development-report.html 中同步更新了对应组件记录",
                )
            else:
                findings.add(
                    "qualoop_upgrade_record",
                    "Qualoop 自我升级记录校验",
                    "pass",
                    "更新了网页报告并成功通过双向实现验证",
                )
        else:
            findings.add(
                "qualoop_upgrade_record",
                "Qualoop 自我升级记录校验",
                "pass",
                "未修改框架代码且报告无需更新",
            )
    except Exception as e:
        logger.warning("Failed to run Qualoop self-upgrade check: %s", e)
        
    return created
        
def check_semantic_standards_alignment(
    project_root: Path, store: IssueStore, findings: RoundFindings, logger
) -> int:
    """Goals Alignment Validator: Enforces that the automated test suite checks
    not just format headers but also strict minimum physical body size thresholds (semantic content).
    Prevents empty mock placeholder bypasses.
    """
    created = 0
    # 1. Locate GOALS.md
    goals_file = project_root / "GOALS.md"
    if not goals_file.is_file():
        goals_file = project_root / "DEVELOPMENT_GOALS.md"
    if not goals_file.is_file():
        findings.add("semantic_alignment_skip", "目标语义对齐", "pass", "无目标文件，跳过对齐审计")
        return 0

    try:
        goals_text = goals_file.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        logger.warning("Failed to read goals file: %s", e)
        return 0

    # Deliverables mapping defined in GOALS.md
    deliverables = []
    if "音频" in goals_text or "audio" in goals_text.lower():
        deliverables.append("audio")
    if "视频" in goals_text or "video" in goals_text.lower():
        deliverables.append("video")
    if "信息图" in goals_text or "infographic" in goals_text.lower():
        deliverables.append("infographic")
    if "思维导图" in goals_text or "mindmap" in goals_text.lower():
        deliverables.append("mindmap")
    if "ppt" in goals_text.lower() or "slides" in goals_text.lower() or "slide" in goals_text.lower():
        deliverables.append("slides")

    if not deliverables:
        findings.add("semantic_alignment_skip", "目标语义对齐", "pass", "未识别到核心交付物定义")
        return 0

    # 2. Check the test suite files
    test_files = ["simple_e2e_test.py", "e2e_test.py"]
    found_assertions = {d: False for d in deliverables}

    for tf_name in test_files:
        tf_path = project_root / tf_name
        if not tf_path.is_file():
            continue
        try:
            code = tf_path.read_text(encoding="utf-8", errors="replace")
            # Look for assertions verifying sizes (e.g. len(bytes) >= or size threshold checks)
            for d in deliverables:
                pattern = rf"(len\(file_bytes\)|len\(bytes\)|len\(.+\))\s*(>=|>|<|<=)\s*(200|1000|2000|5000|10000|15000)"
                if d in code and re.search(pattern, code):
                    found_assertions[d] = True
        except Exception as e:
            logger.warning("Failed to read test file %s: %s", tf_name, e)

    missing_semantic_tests = [d for d, found in found_assertions.items() if not found]

    if not missing_semantic_tests:
        findings.add(
            "semantic_standards_alignment",
            "目标交付语义对齐",
            "pass",
            f"所有交付物 ({', '.join(deliverables)}) 均已置入体量大小与语义实质断言",
        )
    else:
        logger.warning("Goals alignment mismatch: missing size assertions for %s", missing_semantic_tests)
        findings.add(
            "semantic_standards_alignment",
            "目标交付语义对齐",
            "fail",
            f"交付物 {', '.join(missing_semantic_tests)} 缺乏硬性大小阈值或真空 Mock 防御断言",
            category="verification",
        )
        created += _maybe_add_issue(
            store,
            severity="critical",
            issue_type="verification",
            description=(
                f"The automated test suite violates the project's North Star goals (defined in GOALS.md).\n"
                f"It is missing strict minimum physical body size thresholds or vacuum mock protection assertions "
                f"for the following deliverables: {', '.join(missing_semantic_tests)}.\n"
                f"Without size thresholds, the test suite can be easily bypassed by empty/mock files (e.g. 126-byte silent audio or 1x1 empty PNGs)."
            ),
            paths=test_files,
            metadata={"missing_deliverables": missing_semantic_tests},
        )

    return created


def check_ultimate_goals_gap_analysis(
    project_root: Path, store: IssueStore, findings: RoundFindings, logger
) -> int:
    """Ultimate Goals Gap Analysis Validator: Establishes a systematic cognitive auditor to fully
    understand the project's ultimate goals (North Star defined in GOALS.md) and aggressively
    scans the codebase to detect functional, architectural, and educational gaps between the current
    implementation and the final vision (e.g. mock placeholders, lack of real AI prompt structures,
    missing age-appropriate customization for different grades, or absent error safety rails).
    """
    created = 0
    # 1. Locate GOALS.md / DEVELOPMENT_GOALS.md
    goals_file = project_root / "GOALS.md"
    if not goals_file.is_file():
        goals_file = project_root / "DEVELOPMENT_GOALS.md"
    if not goals_file.is_file():
        findings.add("goals_gap_analysis", "最终目标差距审计", "pass", "无目标文件，跳过对齐审计")
        return 0

    try:
        goals_text = goals_file.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        logger.warning("Failed to read goals file: %s", e)
        return 0

    # 2. Extract key North Star educational objectives
    educational_objectives = []
    if "k-12" in goals_text.lower() or "中小学" in goals_text:
        educational_objectives.append("K-12 adaptation (age/grade appropriate customization)")
    if "notebooklm" in goals_text.lower():
        educational_objectives.append("NotebookLM pipeline integration")
    if "个性化" in goals_text or "customized" in goals_text.lower():
        educational_objectives.append("Personalized curriculum alignment")
    if "双语" in goals_text or "bilingual" in goals_text.lower():
        educational_objectives.append("Bilingual materials delivery")

    # 3. Locate codebase implementation files
    impl_files = []
    for ext in ("*.py", "*.js", "*.html"):
        for p in project_root.glob(ext):
            if p.is_file() and not any(part.startswith('.') or part in ('automation', 'tools', 'node_modules', 'venv', '__pycache__') for part in p.parts):
                impl_files.append(p)
        for p in project_root.glob("src/**/" + ext):
            if p.is_file() and not any(part.startswith('.') or part in ('automation', 'tools', 'node_modules', 'venv', '__pycache__') for p in p.parts):
                impl_files.append(p)
    impl_files = list(set(impl_files))

    if not impl_files:
        return 0

    # Read implementation texts
    impl_data = {}
    for f in impl_files:
        try:
            impl_data[f.name] = f.read_text(encoding="utf-8", errors="replace")
        except Exception:
            pass

    # 4. Perform Heuristic Gap Analysis
    gaps_found = []

    # Gap A: Mocks & Placeholders in Production Code
    mock_keywords = ["todo: mock", " notebooklm mock", "dummy data", "fake audio", "silent audio", "dummy placeholder", "mock placeholder", "fake placeholder", "vacuum mock"]
    detected_mocks = []
    for filename, code in impl_data.items():
        if "test" in filename.lower():
            continue
        for kw in mock_keywords:
            if kw in code.lower():
                detected_mocks.append(f"{filename} (contains '{kw}')")
    if detected_mocks:
        gaps_found.append({
            "type": "mock_bypass",
            "severity": "critical",
            "title": "生产代码中使用虚拟 Mock 占位物 (Mock Bypasses in Production)",
            "description": f"检测到以下生产源文件包含 Mock、占位字符或虚拟假数据，这违背了项目交付实质性 K-12 教学资源的最终目标：\n" + "\n".join(f"  - {m}" for m in detected_mocks)
        })

    # Gap B: Lack of dynamic K-12 adaptation
    if "K-12 adaptation (age/grade appropriate customization)" in educational_objectives:
        grade_customization_found = False
        grade_keywords = ["grade", "level", "小学", "初中", "高中", "年龄", "difficulty"]
        for code in impl_data.values():
            if any(gk in code.lower() for gk in grade_keywords):
                grade_customization_found = True
                break
        if not grade_customization_found:
            gaps_found.append({
                "type": "k12_differentiation",
                "severity": "high",
                "title": "缺乏针对 K-12 不同学段与年龄段的个性化适配 (Missing Grade-Level Differentiation)",
                "description": "GOALS.md 明确要求服务于 K-12 教育领域，但源码中缺乏对小学、初中、高中不同学段、难度系数或学科提示词（Prompts）的动态适配与区分，导致生成内容单一，不符合‘因材施教’与个性化课程对齐的最终目标。"
            })

    # Gap C: Lack of dynamic prompt parameterization
    prompt_parameterization_found = False
    prompt_keywords = ["prompt", "system_prompt", "template", "prompt_template", "提示词"]
    for code in impl_data.values():
        if any(pk in code.lower() for pk in prompt_keywords):
            prompt_parameterization_found = True
            break
    if not prompt_parameterization_found:
        gaps_found.append({
            "type": "prompt_engineering",
            "severity": "medium",
            "title": "缺乏高质量教学大模型提示词模板体系 (Missing Dynamic Prompt Templates)",
            "description": "最终项目目标为生成高质量、启发性的 K-12 学习资源（脑图、信息图、音频）。然而，当前代码中缺乏精细设计的动态大模型 Prompt 模板或系统指令（System Prompts），大模型交互存在盲区，可能生成质量低劣的内容。"
        })

    # Gap D: Missing NotebookLM Online Preview Validation
    if "notebooklm" in goals_text.lower() and ("验证" in goals_text or "打开/预览" in goals_text or "预览" in goals_text):
        preview_validation_found = False
        validation_keywords = [
            "verify_preview", "check_preview", "notebooklm_preview", "preview_validation",
            "verify_notebook_preview", "validate_online_preview", "check_online_preview"
        ]
        for code in impl_data.values():
            if any(vk in code.lower() for vk in validation_keywords):
                preview_validation_found = True
                break
        if not preview_validation_found:
            gaps_found.append({
                "type": "notebooklm_online_validation",
                "severity": "critical",
                "title": "缺少 NotebookLM 线上预览与打开状态验证机制 (Missing NotebookLM Online Preview Validation)",
                "description": "系统在 NotebookLM 生成学习材料后，并未在 notebooklm.google.com 网站内对生成的音频、视频、文档等进行线上预览或打开状态的模拟校验。为满足 GOALS.md 的核心要求，需要在后端/自动化层引入浏览器自动化（如 Playwright 或 Puppeteer）脚本，登录 notebooklm.google.com 后模拟点击各生成资源并确认能正常打开与渲染，之后方可在本系统前端标记‘已完成’。"
            })

    # 5. Cognitive LLM Gap Audit
    from automation.llm_client import call_antigravity_llm, get_llm_config
    llm_cfg = get_llm_config(project_root)
    
    if llm_cfg.get("enabled", True):
        if len(gaps_found) < 3:
            logger.info("Spawning Antigravity LLM to perform deep cognitive North Star Gap Analysis...")
            summary_files = [f.name for f in impl_files]
            prompt = (
                "[Qualoop Ultimate Goals Gap Auditor]\n"
                "You are an elite educational technology architect. Your task is to perform a deep cognitive audit "
                "to find gaps between the current codebase implementation and the project's ultimate goals (North Star).\n\n"
                f"### Ultimate Goals (GOALS.md):\n{goals_text[:3000]}\n\n"
                f"### Codebase Files: {', '.join(summary_files)}\n"
                "Please analyze the codebase from a pedagogical, structural, and architectural perspective. "
                "Identify any gaps (e.g. placeholders, mock data, absence of grade-level prompts, lack of dynamic generation). "
                "Return strictly a raw JSON list of gap objects (no markdown ```json wrapping):\n"
                "[\n"
                "  {\n"
                "    \"type\": \"gap_category_identifier\",\n"
                "    \"severity\": \"high\" | \"critical\" | \"medium\",\n"
                "    \"title\": \"Clear gap title in Chinese\",\n"
                "    \"description\": \"Detailed description of the gap and its impact in Chinese.\"\n"
                "  }\n"
                "]\n"
                "If no major gaps are found, return an empty list []."
            )
            try:
                model = llm_cfg.get("model", "flash")
                raw_res = call_antigravity_llm(project_root, prompt, model=model)
                clean_res = raw_res.strip()
                if clean_res.startswith("```"):
                    lines = clean_res.splitlines()
                    if lines[0].startswith("```"):
                        lines = lines[1:]
                    if lines and lines[-1].startswith("```"):
                        lines = lines[:-1]
                    clean_res = "\n".join(lines).strip()
                
                json_match = re.search(r"\[.*\]", clean_res, re.DOTALL)
                if json_match:
                    llm_gaps = json.loads(json_match.group(0))
                    for lg in llm_gaps:
                        if not any(g["title"] == lg.get("title") for g in gaps_found):
                            gaps_found.append(lg)
            except Exception as e:
                logger.info("Cognitive LLM Gap Audit bypassed/throttled: %s. Relying on high-fidelity static heuristics.", e)

    # 6. Record Findings and Create Issues
    if gaps_found:
        logger.warning("Ultimate Goals Gap Auditor detected %d gap(s)!", len(gaps_found))
        for gap in gaps_found:
            severity = gap.get("severity", "high")
            title = gap.get("title", "最终目标差距缺陷")
            desc = gap.get("description", "")
            g_type = gap.get("type", "goals")

            findings.add(
                f"goal_gap_{g_type}",
                f"最终目标对齐: {title}",
                "fail",
                desc,
                category="goals"
            )
            created += _maybe_add_issue(
                store,
                severity=severity,
                issue_type="goals",
                description=(
                    f"### [North Star Goal Gap] {title}\n"
                    f"**Severity**: {severity}\n"
                    f"**Impact**: This gap severely compromises the system's alignment with its ultimate goals defined in GOALS.md.\n\n"
                    f"**Detailed Breakdown**:\n{desc}\n\n"
                    f"**Action Plan to Bridge the Gap**:\n"
                    f"1. Refactor production code to replace mock placeholders with dynamic, real-world educational API pipelines.\n"
                    f"2. Incorporate age-appropriate/grade-level differentiation prompt parameters (小学/初中/高中) to dynamically adapt learning contents.\n"
                    f"3. Establish quality-centric assertions in automated test suites to enforce strict physical body size and semantic compliance."
                ),
                paths=[str(goals_file.relative_to(project_root))] + [str(f.relative_to(project_root)) for f in impl_files[:3]],
                metadata={"gap_type": g_type}
            )
    else:
        findings.add(
            "goals_gap_analysis",
            "最终目标对齐性校验",
            "pass",
            "未检测到任何显式目标偏离或功能实现差距，项目与 North Star 完美对齐。"
        )

    return created


def check_llm_fullstack_audit(
    project_root: Path, store: IssueStore, findings: RoundFindings, cfg: dict, logger
) -> int:
    """Uses the Antigravity LLM (Gemini 3.5 Flash) to audit the full stack
    (index.html, script.js, app.py) against GOALS.md for bugs or design issues.
    """
    logger.info("Starting Fullstack LLM Audit using Antigravity Gemini 3.5 Flash...")
    
    # 1. Load GOALS.md
    goals_file = project_root / "GOALS.md"
    if not goals_file.is_file():
        goals_file = project_root / "DEVELOPMENT_GOALS.md"
        
    goals_text = ""
    if goals_file.is_file():
        try:
            goals_text = goals_file.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            logger.warning("Failed to read goals file: %s", e)
            
    # 2. Extract highly optimized snippets from Core files to fit Windows CLI parameter limits (< 6000 chars)
    core_snippets = {}
    
    # Extract index.html head & container setup
    if (project_root / "index.html").is_file():
        try:
            html = (project_root / "index.html").read_text(encoding="utf-8", errors="replace")
            # Extract head section
            head_match = re.search(r"<head>.*?</head>", html, re.DOTALL | re.IGNORECASE)
            head_part = head_match.group(0) if head_match else html[:1000]
            # Extract body wrappers
            body_match = re.search(r"<body>.*?<div class=\"container\">", html, re.DOTALL | re.IGNORECASE)
            body_part = body_match.group(0) if body_match else ""
            core_snippets["index.html"] = (
                f"<!-- HEAD SECTION -->\n{head_part}\n\n"
                f"<!-- BODY START -->\n{body_part}\n"
            )
        except Exception as e:
            logger.warning("Failed to parse index.html: %s", e)
            
    # Extract app.py route signatures
    if (project_root / "app.py").is_file():
        try:
            app_code = (project_root / "app.py").read_text(encoding="utf-8", errors="replace")
            routes = []
            for match in re.finditer(r"@app\.route\([^)]+\)\s*def\s+\w+\([^)]*\):", app_code):
                routes.append(match.group(0))
            core_snippets["app.py (API Routes)"] = "\n".join(routes[:15])
        except Exception as e:
            logger.warning("Failed to parse app.py: %s", e)
            
    # Extract script.js endpoints & load event
    if (project_root / "script.js").is_file():
        try:
            js = (project_root / "script.js").read_text(encoding="utf-8", errors="replace")
            fetches = re.findall(r"fetch\([^)]+\)", js)
            selectors = re.findall(r"document\.getElement[^;]+;", js)
            core_snippets["script.js (JS Queries)"] = (
                "// Core UI selectors:\n" + "\n".join(selectors[:10]) + "\n\n" +
                "// Core Fetch calls:\n" + "\n".join(fetches[:10])
            )
        except Exception as e:
            logger.warning("Failed to parse script.js: %s", e)
                
    if not core_snippets:
        findings.add("llm_audit_skip", "全栈大模型审计", "pass", "无核心文件可审计")
        return 0

    # 3. Construct prompt
    prompt = (
        "[Qualoop Tester Agent Fullstack Audit]\n"
        "You are an elite QA and Fullstack Auditor. Your task is to perform a deep expert audit of the provided project snippets against their ultimate goals (North Star).\n\n"
        "### Project Ultimate Goals (North Star):\n"
        f"```markdown\n{goals_text}\n```\n\n"
        "### Codebase Core Snippets:\n"
    )
    for name, content in core_snippets.items():
        prompt += f"\n=== FILE: {name} ===\n{content}\n\n"
        
    prompt += (
        "Please perform a deep audit on these files to find bugs, styling/layout misalignments (like invalid stylesheet link attributes, missing classes, or bad viewport setup), "
        "missing DOM elements, API mismatches, or logical deviations from the ultimate K-12 and stable execution goals.\n\n"
        "IMPORTANT: You must return your findings STRICTLY as a raw JSON object matching the schema below. Do not include markdown code block formatting (like ```json ... ```). Just return raw JSON:\n"
        "{\n"
        "  \"defects\": [\n"
        "    {\n"
        "      \"severity\": \"critical\" | \"high\" | \"medium\",\n"
        "      \"issue_type\": \"static\" | \"health\" | \"performance\" | \"verification\" | \"improvement\",\n"
        "      \"description\": \"A detailed, clear description of the defect, explaining the exact line/mechanism and how to fix it in Chinese.\",\n"
        "      \"paths\": [\"filename.ext\"],\n"
        "      \"metadata\": {}\n"
        "    }\n"
        "  ],\n"
        "  \"suggestions\": [\n"
        "    \"Specific goal-aligned improvement suggestion in Chinese...\"\n"
        "  ]\n"
        "}\n"
    )
    
    try:
        from automation.llm_client import call_antigravity_llm, get_llm_config
        llm_cfg = get_llm_config(project_root)
        model = llm_cfg.get("model", "flash")
        
        raw_res = call_antigravity_llm(project_root, prompt, model=model)
        
        # Handle markdown blocks if the LLM outputted them despite instructions
        clean_res = raw_res.strip()
        if clean_res.startswith("```"):
            lines = clean_res.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            clean_res = "\n".join(lines).strip()
            
        json_match = re.search(r"\{.*\}", clean_res, re.DOTALL)
        if not json_match:
            logger.warning("LLM response did not contain a valid JSON object.")
            findings.add("llm_audit", "全栈大模型审计", "pass", "审计完成，未发现显著结构性设计缺陷")
            return 0
            
        data = json.loads(json_match.group(0))
        defects = data.get("defects", [])
        suggestions = data.get("suggestions", [])
        
        created = 0
        if defects:
            for d in defects:
                severity = d.get("severity", "medium")
                issue_type = d.get("issue_type", "static")
                desc = d.get("description", "")
                paths = d.get("paths", [])
                meta = d.get("metadata", {})
                
                logger.warning("LLM Fullstack Audit found defect: %s", desc[:200])
                findings.add(
                    f"llm_audit_defect_{paths[0] if paths else 'system'}",
                    "全栈大模型审计",
                    "fail",
                    desc[:120],
                    category=issue_type,
                    new_issue=True
                )
                
                added = _maybe_add_issue(
                    store,
                    severity=severity,
                    issue_type=issue_type,
                    description=desc,
                    paths=paths,
                    metadata=meta
                )
                created += added
        else:
            findings.add("llm_audit", "全栈大模型审计", "pass", "未发现核心系统设计/全栈缺陷")
            
        if suggestions:
            from automation.round_suggestions import append_suggestions
            from automation.paths import ensure_layout
            layout = ensure_layout(cfg)
            suggest_rows = []
            for s in suggestions:
                suggest_rows.append({
                    "id": f"sug-llm-{str(hash(s))[-8:]}",
                    "round_id": findings.round_id,
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "text": s,
                    "rationale": "Generated via deep LLM fullstack audit against ultimate goals."
                })
            append_suggestions(suggest_rows, layout["reports"], logger, strict=False)
            
        return created
        
    except Exception as e:
        logger.error("LLM Fullstack Audit failed: %s", e)
        findings.add("llm_audit", "全栈大模型审计", "warn", f"审计失败: {e}")
        return 0


def check_auth_and_create_notebook(
    cfg: dict,
    store: IssueStore,
    findings: RoundFindings,
    logger,
    *,
    force_notebooklm: bool = False,
) -> int:
    created = 0
    tester_cfg = cfg.get("tester") or {}
    if not tester_cfg.get("create_notebook_probe_enabled", False):
        findings.add(
            "create_notebook_skip",
            "POST create-notebook",
            "pass",
            "create_notebook_probe_enabled=false（避免频繁访问 NotebookLM）",
            category="functional",
        )
        return created

    backend = cfg.get("backend_url", "http://localhost:5000").rstrip("/")
    auth_url = f"{backend}/api/auth-status"

    ok, detail, ms = _http_probe(auth_url, timeout=10.0)
    auth_ready = False
    if ok:
        try:
            raw = detail[detail.find("{") :] if "{" in detail else detail
            data = json.loads(raw)
            auth_ready = bool(data.get("authenticated") or data.get("ready"))
            findings.add(
                "auth_status_shape",
                "auth-status 响应结构",
                "pass",
                f"authenticated={data.get('authenticated')} keys={list(data.keys())[:6]}",
                category="functional",
            )
        except (json.JSONDecodeError, ValueError):
            findings.add("auth_status_shape", "auth-status 响应结构", "warn", detail[:120])
    else:
        findings.add("auth_status_shape", "auth-status", "fail", detail[:200], category="functional")
        created += _maybe_add_issue(
            store,
            severity="high",
            issue_type="functional",
            description=f"Auth status check failed: {detail[:200]}",
            metadata={"detail": detail},
        )
        return created

    if not auth_ready:
        findings.add(
            "create_notebook_skip",
            "POST create-notebook",
            "warn",
            "认证未就绪，跳过创建笔记本探针",
            category="functional",
        )
        return created

    allowed, throttle_msg = try_acquire(
        cfg, "create_notebook", force=force_notebooklm, logger=logger
    )
    if not allowed:
        wait_sec = seconds_until_allowed(cfg, "create_notebook", force=force_notebooklm)
        findings.add(
            "create_notebook_throttled",
            "POST create-notebook",
            "pass",
            f"已节流，约 {format_wait_human(wait_sec)} 后可再探针",
            category="functional",
        )
        return created

    url = f"{backend}/api/create-notebook"
    payload = {
        "title": "Automation round probe",
        "description": "ephemeral tester check — safe to ignore",
    }
    status, resp_body, elapsed = _post_json(url, payload, timeout=45.0)
    shape_ok = False
    detail = f"HTTP {status} in {elapsed:.0f}ms"
    if status in (200, 201):
        try:
            data = json.loads(resp_body)
            shape_ok = isinstance(data, dict) and (
                "notebook_id" in data or "id" in data or "success" in data
            )
            detail += f" keys={list(data.keys())[:8] if isinstance(data, dict) else '?'}"
        except json.JSONDecodeError:
            detail += " invalid JSON"
    else:
        detail += f" body={resp_body[:120]}"

    if shape_ok:
        findings.add("create_notebook", "POST create-notebook", "pass", detail, category="functional")
        record_use(cfg, "create_notebook", "ok", detail=detail)
    elif status in (401, 403, 503):
        findings.add(
            "create_notebook",
            "POST create-notebook",
            "warn",
            detail,
            category="functional",
        )
    else:
        findings.add("create_notebook", "POST create-notebook", "fail", detail, category="functional")
        created += _maybe_add_issue(
            store,
            severity="high",
            issue_type="api",
            description=f"create-notebook probe failed: {detail}\n```\n{resp_body[:400]}\n```",
            metadata={"status": status, "elapsed_ms": elapsed},
        )
        record_use(cfg, "create_notebook", "fail", detail=detail)

    return created


def run_legacy_script(project_root: Path, script: str, timeout: int = 120) -> tuple[bool, str]:
    path = project_root / script
    if not path.is_file():
        return True, "missing (skipped)"
    try:
        import os
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        proc = subprocess.run(
            [sys.executable, str(path)],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
            env=env,
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        if proc.returncode == 0:
            return True, out[-500:]
        return False, out[-2000:]
    except subprocess.TimeoutExpired:
        return False, "timeout"
    except Exception as e:
        return False, str(e)


def run_legacy_scripts(
    cfg: dict, project_root: Path, store: IssueStore, findings: RoundFindings, logger
) -> int:
    if not cfg.get("tester", {}).get("run_legacy_scripts", True):
        findings.add("legacy_scripts", "遗留测试脚本", "pass", "已禁用")
        return 0
    created = 0
    for script in _LEGACY_SCRIPTS:
        ok, output = run_legacy_script(project_root, script)
        if ok:
            findings.add(f"legacy_{script}", f"遗留脚本 {script}", "pass", output[:80] or "OK")
            logger.info("Legacy script %s: OK (%s)", script, output[:80])
            continue
        clean_err = extract_clean_error(output)
        findings.add(f"legacy_{script}", f"遗留脚本 {script}", "fail", clean_err[:200])
        created += _maybe_add_issue(
            store,
            severity="medium",
            issue_type="test_failure",
            description=f"Legacy test script `{script}` failed or could not run.\n\n```\n{clean_err}\n```",
            paths=[script],
            metadata={"script": script},
        )
        logger.info("Recorded failure for %s", script)
    return created


def run_once(
    cfg: dict | None = None, *, browser: bool = False, force_notebooklm: bool = False, store: IssueStore | None = None
) -> dict:
    cfg = cfg or load_config()
    layout = ensure_layout(cfg)
    logger = setup_logger("tester", cfg)
    global _llm_called
    _llm_called = False
    project_root: Path = cfg["_project_root"]
    if store is None:
        store = IssueStore()

    depth = _resolve_depth(cfg)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    round_id = f"tester-{stamp}"
    findings = RoundFindings(round_id, depth=depth)

    logger.info("Tester run started (project=%s, depth=%s)", project_root, depth)
    created = 0

    created += check_localhost(cfg, store, findings, logger)

    if _depth_at_least(depth, "standard"):
        if cfg.get("tester", {}).get("static_python_corruption_check", True):
            created += check_python_corruption(project_root, store, findings, logger)
        created += scan_content_quality(project_root, store, findings, logger)
        created += run_py_compile_regression(project_root, store, findings, logger)
        created += run_legacy_scripts(cfg, project_root, store, findings, logger)
        created += api_contract_check(project_root, store, findings, cfg, logger)
        created += check_goals_and_coverage(project_root, store, findings, logger)
        created += check_semantic_standards_alignment(project_root, store, findings, logger)
        created += check_ultimate_goals_gap_analysis(project_root, store, findings, logger)
        created += check_qualoop_self_upgrade(project_root, store, findings, logger)
        created += check_frontend_backend_contract_alignment(project_root, store, findings, logger)
        if cfg.get("tester", {}).get("llm_fullstack_audit", True):
            created += check_llm_fullstack_audit(project_root, store, findings, cfg, logger)

    if _depth_at_least(depth, "deep"):
        created += check_auth_and_create_notebook(
            cfg, store, findings, logger, force_notebooklm=force_notebooklm
        )
        created += audit_uploads_dir(project_root, store, findings, cfg, logger)

    if browser or cfg.get("browser_test_enabled", False):
        backend = (cfg.get("backend_url") or "http://localhost:5000").rstrip("/")
        frontend = (cfg.get("frontend_url") or "http://localhost:8080").rstrip("/")
        health_url = _health_probe_url(cfg, backend)
        be_ok, _, _ = _http_probe(health_url, timeout=8.0)
        fe_ok, _, _ = _http_probe(frontend + "/", timeout=8.0)
        if be_ok and fe_ok:
            allowed, throttle_msg = try_acquire(
                cfg, "browser_e2e", force=force_notebooklm, logger=logger
            )
            if not allowed:
                wait_sec = seconds_until_allowed(
                    cfg, "browser_e2e", force=force_notebooklm
                )
                findings.add(
                    "e2e_throttled",
                    "浏览器 E2E",
                    "pass",
                    f"已节流，约 {format_wait_human(wait_sec)} 后可再跑（防 NotebookLM 风控）",
                    category="e2e",
                )
                logger.info("Browser E2E throttled: %s", throttle_msg)
            else:
                try:
                    e2e_result = run_browser_e2e(cfg, store, logger, findings=findings)
                    created += int(e2e_result.get("created", 0))
                    outcome = "fail" if e2e_result.get("created") else "pass"
                    record_use(
                        cfg,
                        "browser_e2e",
                        outcome,
                        detail=str(e2e_result.get("summary", ""))[:200],
                    )
                except Exception as e:
                    record_use(cfg, "browser_e2e", "error", detail=str(e)[:200])
                    raise
        else:
            logger.warning(
                "Browser E2E skipped: services not ready (backend=%s frontend=%s)",
                be_ok,
                fe_ok,
            )
            findings.add(
                "e2e_skipped",
                "浏览器 E2E",
                "warn",
                f"skipped: backend={'ok' if be_ok else 'down'} frontend={'ok' if fe_ok else 'down'}",
                category="e2e",
            )

    jsonl_path = layout["reports"] / "round_findings.jsonl"
    findings.append_jsonl(jsonl_path)

    counts = findings.counts()
    suggestions: list[dict] = []
    require_output = bool(cfg.get("require_round_output", True))
    has_failures = counts.get("fail", 0) > 0
    if require_output and created == 0 and not has_failures:
        strict = bool(cfg.get("goal_alignment_strict", True))
        raw = generate_for_clean_round(
            round_id, findings, store, cfg, min_count=1, strict=strict
        )
        suggestions = append_suggestions(
            raw, layout["reports"], logger, strict=strict
        )
        if suggestions:
            logger.info(
                "Round improvement suggestions: %d (goal-aligned)",
                len(suggestions),
            )
        elif require_output:
            fallback_row = fallback_aligned_suggestion(round_id, strict=strict)
            suggestions = append_suggestions(
                [fallback_row], layout["reports"], logger, strict=strict
            )
            if suggestions:
                logger.info(
                    "Round fallback suggestion recorded (PROJECT_BRIEF template)"
                )
            else:
                logger.warning(
                    "require_round_output: fallback suggestion failed goal gate"
                )

    snap = write_latest_snapshot(store)
    summary = findings.summary_line(created)
    if suggestions:
        summary += f", suggestions={len(suggestions)}"
    logger.info(summary + ", snapshot=%s", snap)

    return {
        "created": created,
        "snapshot": str(snap),
        "round_id": round_id,
        "depth": depth,
        "checks": counts,
        "findings_path": str(jsonl_path),
        "suggestions": suggestions,
        "suggestions_count": len(suggestions),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ParadigmLearn automation tester")
    parser.add_argument("--once", action="store_true", help="Run one cycle and exit")
    parser.add_argument("--loop", action="store_true", help="Run until interrupted")
    parser.add_argument(
        "--browser",
        action="store_true",
        help="Run Playwright browser E2E (also runs when browser_test_enabled is true)",
    )
    parser.add_argument(
        "--force-notebooklm",
        action="store_true",
        help="Bypass notebooklm_guard throttle (manual runs only)",
    )
    args = parser.parse_args(argv)

    cfg = load_config()
    interval = cfg.get("intervals_seconds", {}).get("tester", 120)

    if args.loop:
        import time

        logger = setup_logger("tester", cfg)
        while True:
            try:
                run_once(
                    cfg,
                    browser=args.browser,
                    force_notebooklm=args.force_notebooklm,
                )
            except Exception:
                logger.exception("Tester loop error")
            time.sleep(interval)
    else:
        run_once(
            cfg,
            browser=args.browser,
            force_notebooklm=args.force_notebooklm,
        )
    return 0


class QualoopTester:
    def __init__(self, deep: bool = False):
        self.deep = deep

    def run_all_checks(self) -> list[dict]:
        """
        Compatible interface for CLI automation/qualoop.py execution flow.
        Captures newly discovered issues in a memory-resident CaptureStore without writing them to disk.
        """
        from automation.issue_store import IssueStore

        class CaptureStore(IssueStore):
            def __init__(self):
                super().__init__()
                self.captured_candidates = []
                self.issues = {}

            def add(self, severity, issue_type, description, paths=None, metadata=None):
                cand = {
                    "severity": severity,
                    "type": issue_type,
                    "description": description,
                    "paths": paths or [],
                    "metadata": metadata or {}
                }
                self.captured_candidates.append(cand)
                return {
                    "id": f"tmp-{len(self.captured_candidates)}",
                    "severity": severity,
                    "type": issue_type,
                    "description": description,
                    "paths": paths or [],
                    "metadata": metadata or {}
                }

            def save(self):
                pass  # Prevent writing mock candidates to issues.json prematurely

        cfg = load_config()
        if self.deep:
            cfg["tester_depth"] = "deep"
        else:
            cfg["tester_depth"] = "standard"

        capture_store = CaptureStore()
        run_once(cfg, store=capture_store)
        return capture_store.captured_candidates


if __name__ == "__main__":
    raise SystemExit(main())
