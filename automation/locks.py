"""Cross-process file locks (Windows-friendly, stdlib only)."""
from __future__ import annotations

import os
import sys
import time
from contextlib import contextmanager
from pathlib import Path

from .paths import ensure_layout


class LockTimeout(Exception):
    pass


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if sys.platform == "win32":
        try:
            import ctypes

            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            handle = ctypes.windll.kernel32.OpenProcess(
                PROCESS_QUERY_LIMITED_INFORMATION, False, pid
            )
            if handle:
                ctypes.windll.kernel32.CloseHandle(handle)
                return True
            return False
        except Exception:
            return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _stale_lock(lock_path: Path, max_age_seconds: float = 3600.0) -> bool:
    if not lock_path.exists():
        return False
    try:
        pid = int(lock_path.read_text(encoding="utf-8").strip() or "0")
    except (ValueError, OSError):
        pid = 0
    if pid and not _pid_alive(pid):
        return True
    try:
        age = time.time() - lock_path.stat().st_mtime
        return age > max_age_seconds
    except OSError:
        return True


def _try_acquire(lock_path: Path) -> bool:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    if lock_path.exists() and _stale_lock(lock_path):
        release(lock_path)
    try:
        fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        try:
            os.write(fd, str(os.getpid()).encode("utf-8"))
        finally:
            os.close(fd)
        return True
    except FileExistsError:
        return False


def acquire(lock_path: Path, timeout: float = 60.0) -> None:
    deadlint = time.monotonic() + timeout
    while time.monotonic() < deadlint:
        if _try_acquire(lock_path):
            return
        time.sleep(0.15)
    raise LockTimeout(f"Could not acquire lock: {lock_path}")


def release(lock_path: Path) -> None:
    try:
        lock_path.unlink(missing_ok=True)
    except OSError:
        pass


@contextmanager
def file_lock(lock_path: Path, timeout: float = 60.0):
    acquire(lock_path, timeout=timeout)
    try:
        yield
    finally:
        release(lock_path)


def path_lock_name(relative_path: str) -> str:
    safe = relative_path.replace("\\", "/").strip("/").replace("/", "__")
    if not safe:
        safe = "_root_"
    return f"path_{safe}.lock"


@contextmanager
def path_lock(project_root: Path, relative_path: str, timeout: float = 60.0):
    layout = ensure_layout()
    lock_file = layout["locks"] / path_lock_name(relative_path)
    with file_lock(lock_file, timeout=timeout):
        yield


@contextmanager
def store_lock(timeout: float = 60.0):
    layout = ensure_layout()
    with file_lock(layout["store_lock"], timeout=timeout):
        yield
