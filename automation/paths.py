"""Resolve project paths and automation directories."""
from __future__ import annotations

import json
from pathlib import Path

import os

_PKG = Path(__file__).resolve().parent
_DEFAULT_ROOT = _PKG.parent
PROJECT_ROOT = str(_DEFAULT_ROOT)

_CANDIDATE_ROOTS = [
    _DEFAULT_ROOT,
]


def get_abs_path(rel_path: str) -> str:
    """Convert a repository-relative path to an absolute path."""
    if os.path.isabs(rel_path):
        return rel_path
    if rel_path.startswith("./"):
        rel_path = rel_path[2:]
    elif rel_path.startswith("/"):
        rel_path = rel_path[1:]
    return os.path.abspath(os.path.join(PROJECT_ROOT, rel_path))


def get_rel_path(abs_path: str) -> str:
    """Convert an absolute path to a repository-relative path."""
    return os.path.relpath(abs_path, PROJECT_ROOT)


def load_config() -> dict:
    cfg_path = _PKG / "config.json"
    if not cfg_path.exists():
        # Fallback dictionary if config doesn't exist yet
        return {
            "_project_root": _DEFAULT_ROOT,
            "project_root": ".",
            "tester": {
                "probe_localhost": True,
                "static_python_corruption_check": True,
            }
        }
    with cfg_path.open(encoding="utf-8-sig") as f:
        cfg = json.load(f)
    root_override = cfg.get("project_root")
    if root_override:
        cfg["_project_root"] = Path(root_override)
    else:
        cfg["_project_root"] = resolve_project_root()
    return cfg


def resolve_project_root() -> Path:
    if (_DEFAULT_ROOT / "app.py").is_file():
        return _DEFAULT_ROOT
    for candidate in _CANDIDATE_ROOTS:
        if candidate != _DEFAULT_ROOT and (candidate / "app.py").is_file():
            return candidate
    return _DEFAULT_ROOT


def load_qualoop_json(project_root: Path | None = None) -> dict:
    root = project_root or resolve_project_root()
    path = root / "qualoop.json"
    if not path.is_file():
        return {}
    try:
        with path.open(encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def maturity_level(cfg: dict | None = None) -> str:
    """Always return L3 as L1 and L2 are deprecated/removed."""
    return "L3"


_MATURITY_ORDER = {"L3": 3, "L4": 4}


def maturity_at_least(level: str, cfg: dict | None = None) -> bool:
    # Since only L3 exists, anything requiring <= L3 is satisfied
    need = _MATURITY_ORDER.get(level.upper(), 1)
    return 3 >= need


def automation_dir(cfg: dict | None = None) -> Path:
    root = (cfg or load_config())["_project_root"]
    d = root / "automation"
    d.mkdir(parents=True, exist_ok=True)
    return d


def ensure_layout(cfg: dict | None = None) -> dict[str, Path]:
    auto = automation_dir(cfg)
    paths = {
        "root": auto.parent,
        "automation": auto,
        "issues": auto / "issues.json",
        "store_lock": auto / ".store.lock",
        "locks": auto / "locks",
        "logs": auto / "logs",
        "reports": auto / "reports",
        "screenshots": auto / "reports" / "screenshots",
        "fixtures": auto / "fixtures",
    }
    for key in ("locks", "logs", "reports", "screenshots", "fixtures"):
        paths[key].mkdir(parents=True, exist_ok=True)
    return paths
