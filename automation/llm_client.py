# -*- coding: utf-8 -*-
"""Antigravity LLM Client for Qualoop agentic loops."""
from __future__ import annotations

import json
import logging
import os
import re
import shlex
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("automation.llm_client")

DEFAULT_CLI_PATH = r"C:\Users\TQT\.gemini\antigravity\bin\agentapi.bat"


def resolve_windows_bat_command(cli_path: str) -> list[str]:
    """Under Windows, if cli_path is a .bat file, parse it to find the actual executable
    to bypass cmd.exe multiline argument truncation.
    """
    if sys.platform != "win32" or not cli_path.lower().endswith(".bat"):
        return [cli_path]
    try:
        content = Path(cli_path).read_text(encoding="utf-8", errors="replace")
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("@") or line.lower().startswith("rem") or line.lower().startswith("echo"):
                continue
            match = re.match(r'^"([^"]+)"\s*(.*)$', line)
            if not match:
                match = re.match(r'^([^\s]+)\s*(.*)$', line)
            if match:
                exe = match.group(1)
                args_str = match.group(2)
                args_str = args_str.replace("%*", "").strip()
                try:
                    args = shlex.split(args_str)
                except Exception:
                    args = args_str.split()
                return [exe] + args
    except Exception as e:
        logger.warning("Failed to parse batch file %s: %s", cli_path, e)
    return [cli_path]


class LLMClientError(Exception):
    """Base exception for LLM Client issues."""
    pass


class LLMBudgetExceededError(LLMClientError):
    """Exception raised when LLM hourly API call budget is exceeded."""
    pass


def get_llm_config(project_root: Path) -> dict:
    config_file = project_root / "qualoop.json"
    if not config_file.is_file():
        return {}
    try:
        data = json.loads(config_file.read_text(encoding="utf-8"))
        return data.get("llm") or {}
    except Exception as e:
        logger.warning("Failed to load llm config from qualoop.json: %s", e)
        return {}


def _check_and_record_llm_budget(project_root: Path, max_calls: int = 10) -> tuple[bool, str]:
    state_file = project_root / "automation" / "state" / "llm_usage.json"
    state_file.parent.mkdir(parents=True, exist_ok=True)
    
    state = {}
    if state_file.is_file():
        try:
            state = json.loads(state_file.read_text(encoding="utf-8"))
        except Exception:
            pass
            
    now = time.time()
    last_ts = state.get("last_call_ts", 0)
    # Reset count if last call was more than 1 hour ago
    if now - last_ts > 3600:
        calls_count = 0
    else:
        calls_count = state.get("calls_count", 0)
        
    if calls_count >= max_calls:
        return False, f"LLM Call rejected: Exceeded max budget of {max_calls} calls/hour to prevent LLM Storm."
        
    state["calls_count"] = calls_count + 1
    state["last_call_ts"] = now
    state["last_call_time"] = datetime.now().isoformat()
    
    try:
        state_file.write_text(json.dumps(state, indent=2), encoding="utf-8")
    except Exception as e:
        logger.warning("Failed to write llm_usage.json: %s", e)
        
    return True, ""


def call_antigravity_llm(project_root: Path, prompt: str, model: str = "flash") -> str:
    """Invokes the local Antigravity CLI client via agentapi.bat to launch a model query.
    
    Returns a status string detailing the successfully spawned conversation ID.
    Raises LLMClientError/LLMBudgetExceededError if there are errors or limit rejections.
    """
    llm_cfg = get_llm_config(project_root)
    provider = llm_cfg.get("provider", "antigravity")
    if provider != "antigravity":
        raise LLMClientError("LLM provider is not set to antigravity")

    # SWE-agent style safety budget check to prevent LLM Storms
    max_calls = llm_cfg.get("max_calls_per_hour", 10)
    allowed, budget_msg = _check_and_record_llm_budget(project_root, max_calls)
    if not allowed:
        logger.warning(budget_msg)
        raise LLMBudgetExceededError(budget_msg)

    cli_path = llm_cfg.get("cli_path", DEFAULT_CLI_PATH)
    if not os.path.isfile(cli_path):
        # Fallback check inside the user's .gemini directory if path differs
        fallback = Path(os.path.expanduser("~")) / ".gemini" / "antigravity" / "bin" / "agentapi.bat"
        if fallback.is_file():
            cli_path = str(fallback)
        else:
            raise LLMClientError(f"Antigravity CLI wrapper not found at {cli_path}")

    if sys.platform == "win32":
        if cli_path.lower().endswith(".bat"):
            base_cmd = resolve_windows_bat_command(cli_path)
            cmd = base_cmd + [
                "new-conversation",
                f"--model={model}",
                prompt
            ]
        else:
            cmd = [
                cli_path,
                "new-conversation",
                f"--model={model}",
                prompt
            ]
    else:
        cmd = [
            cli_path,
            "new-conversation",
            f"--model={model}",
            prompt
        ]

    try:
        logger.info("Executing Antigravity CLI call...")
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            encoding="utf-8",
            errors="replace"
        )
        if proc.returncode != 0:
            err = proc.stderr or proc.stdout
            logger.error("Antigravity CLI failed with exit code %s: %s", proc.returncode, err)
            raise LLMClientError(f"CLI error: {err.strip()}")

        # Parse JSON output returned by language_server agentapi
        out = proc.stdout.strip()
        try:
            res = json.loads(out)
            new_conv = res.get("response", {}).get("newConversation", {})
            conv_id = new_conv.get("conversationId", "unknown")
            msg = f"Successfully launched Antigravity IDE agentic conversation (ID: {conv_id})"
            logger.info(msg)
            return msg
        except json.JSONDecodeError:
            # Fallback if non-JSON output is captured
            return f"Antigravity response: {out}"

    except subprocess.TimeoutExpired as e:
        logger.warning("Antigravity CLI execution timed out after 30 seconds")
        raise LLMClientError("Antigravity CLI call timed out") from e
    except Exception as e:
        logger.error("Failed to run Antigravity CLI: %s", e)
        if isinstance(e, LLMClientError):
            raise
        raise LLMClientError(f"Execution error: {e}") from e


if __name__ == "__main__":
    # Test script execution
    logging.basicConfig(level=logging.INFO)
    root = Path(__file__).resolve().parent.parent
    print("Testing Antigravity CLI Client...")
    try:
        ret = call_antigravity_llm(
            root,
            prompt="A standard diagnostic check. Reply with 'OK' to acknowledge.",
            model="flash_lite"
        )
        print(ret)
    except Exception as e:
        print(f"Failed with exception: {e}")
