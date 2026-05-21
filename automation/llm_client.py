"""Antigravity LLM Client for Qualoop agentic loops."""
from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger("automation.llm_client")

DEFAULT_CLI_PATH = r"C:\Users\TQT\.gemini\antigravity\bin\agentapi.bat"


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


def call_antigravity_llm(project_root: Path, prompt: str, model: str = "flash") -> str:
    """Invokes the local Antigravity CLI client via agentapi.bat to launch a model query.
    
    Returns a status string detailing the successfully spawned conversation ID.
    """
    llm_cfg = get_llm_config(project_root)
    provider = llm_cfg.get("provider", "antigravity")
    if provider != "antigravity":
        return "LLM provider is not set to antigravity"

    cli_path = llm_cfg.get("cli_path", DEFAULT_CLI_PATH)
    if not os.path.isfile(cli_path):
        # Fallback check inside the user's .gemini directory if path differs
        fallback = Path(os.path.expanduser("~")) / ".gemini" / "antigravity" / "bin" / "agentapi.bat"
        if fallback.is_file():
            cli_path = str(fallback)
        else:
            return f"Antigravity CLI wrapper not found at {cli_path}"

    cmd = [
        "cmd.exe", "/c", cli_path,
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
            return f"CLI error: {err.strip()}"

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

    except subprocess.TimeoutExpired:
        logger.warning("Antigravity CLI execution timed out after 30 seconds")
        return "Antigravity CLI call timed out"
    except Exception as e:
        logger.error("Failed to run Antigravity CLI: %s", e)
        return f"Execution error: {e}"


if __name__ == "__main__":
    # Test script execution
    logging.basicConfig(level=logging.INFO)
    root = Path(__file__).resolve().parent.parent
    print("Testing Antigravity CLI Client...")
    ret = call_antigravity_llm(
        root,
        prompt="A standard diagnostic check. Reply with 'OK' to acknowledge.",
        model="flash_lite"
    )
    print(ret)
