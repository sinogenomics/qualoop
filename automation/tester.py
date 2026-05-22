# -*- coding: utf-8 -*-
"""Tester agent: deep probes, static checks, API contract, regression, E2E."""
from __future__ import annotations

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

from .browser_e2e import run_browser_e2e
from .issue_store import IssueStore
from .notebooklm_guard import (
    format_wait_human,
    record_use,
    seconds_until_allowed,
    try_acquire,
)
from .logging_util import setup_logger
from .paths import automation_dir, ensure_layout, load_config
from .reports import write_latest_snapshot
from .round_findings import RoundFindings
from .error_parser import extract_clean_error
from .round_suggestions import (
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
    "api_contract_validator.py",
)

_HEALTH_PATHS = ("/api/health",)


def _health_probe_url(cfg: dict, backend: str, path: str = "/api/health") -> str:
    """Automation uses light health by default (no NotebookLM auth --test)."""
    base = backend.rstrip("/") + path
    tester = cfg.get("tester") or {}
    mode = str(tester.get("health_notebooklm_mode", "light")).strip().lower()
    if path.rstrip("/") in ("/api/health", "/api/heaeeh") and mode in (
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
        from .llm_client import get_llm_config, call_antigravity_llm
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
            rel = py.name
            findings.add(
                f"corruption_{rel}",
                f"Python 腐化：{rel}",
                "fail",
                f"markers: {', '.join(hits[:5])}",
                category="static",
            )
            added = _maybe_add_issue(
                store,
                severity="critical",
                issue_type="static",
                description=(
                    f"Python file `{rel}` appears corrupted (brand/obfuscation artifacts: "
                    f"{', '.join(hits[:3])}). Module may not import or run."
                ),
                paths=[rel],
                metadata={"markers": hits[:10]},
            )
            created += added
            if added:
                logger.warning("Corruption detected in %s", rel)
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

    for f in uploads.rglob("*"):
        if not f.is_file():
            continue
        file_count += 1
        st = f.stat()
        total_bytes += st.st_size
        rel = f.relative_to(project_root).as_posix()
        age_h = (now - st.st_mtime) / 3600
        if st.st_size > max_mb * 1024 * 1024:
            large.append(f"{rel} ({st.st_size // (1024*1024)}MB)")
        if age_h > orphan_hours and st.st_size > 1024 * 1024:
            orphans.append(f"{rel} ({age_h:.0f}h)")

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
    if not large and not orphans:
        findings.add("uploads_dir", "uploads 目录", "pass", detail)
    else:
        findings.add("uploads_dir", "uploads 目录", "warn", detail + f"; large={len(large)} orphan={len(orphans)}")
    return created


def api_contract_check(
    project_root: Path, store: IssueStore, findings: RoundFindings, cfg: dict, logger
) -> int:
    created = 0
    app_py = project_root / "app.py"
    if not app_py.is_file():
        findings.add("api_contract", "API 路由契约", "fail", "app.py 缺失")
        created += _maybe_add_issue(
            store,
            severity="high",
            issue_type="api",
            description="Required app.py is missing from project root.",
            paths=["app.py"],
        )
        return created

    text = app_py.read_text(encoding="utf-8", errors="replace")
    routes = re.findall(r"@app\.route\(['\"]([^'\"]+)['\"]", text)
    api_routes = [r for r in routes if "/api/" in r]
    route_text = "\n".join(api_routes)

    missing: list[str] = []
    for required in _REQUIRED_API_ROUTES:
        if required not in route_text and required.replace("<task_id>", "<") not in route_text:
            if required == "/api/generate-content" and "/api/generate-content" in route_text:
                continue
            missing.append(required)

    has_task = bool(_TASK_STATUS_PATTERN.search(route_text))
    if not has_task:
        missing.append("/api/task-status/…")

    findings.add(
        "api_routes_static",
        "API 路由静态扫描",
        "pass" if api_routes else "warn",
        f"发现 {len(api_routes)} 条 /api/ 路由",
        category="api",
    )
    logger.info("Found %d API routes in app.py", len(api_routes))

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
            description=f"Missing required API routes in app.py: {', '.join(missing)}",
            paths=["app.py"],
            metadata={"missing": missing, "found": api_routes[:20]},
        )
    else:
        findings.add("api_contract", "API 契约必需路由", "pass", "health/auth/create/generate/task-status")

    backend = cfg.get("backend_url", "http://localhost:5000").rstrip("/")
    live_missing: list[str] = []
    for path in ("/api/health", "/api/auth-status"):
        url = (
            _health_probe_url(cfg, backend, path)
            if path == "/api/health"
            else f"{backend}{path}"
        )
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
        from .issue_store import IssueStore

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
