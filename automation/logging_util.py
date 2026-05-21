"""Logging setup for automation agents."""
from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path

from .paths import ensure_layout, load_config


def setup_logger(name: str, cfg: dict | None = None) -> logging.Logger:
    layout = ensure_layout(cfg)
    log_dir: Path = layout["logs"]
    log_file = log_dir / f"{name}_{datetime.now():%Y%m%d}.log"

    logger = logging.getLogger(f"automation.{name}")
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setFormatter(fmt)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)

    logger.addHandler(fh)
    logger.addHandler(sh)
    return logger
