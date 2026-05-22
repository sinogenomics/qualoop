"""Error parser module to clean and extract tracebacks from stdout/stderr, inspired by Aider.

Helps compress the error reports for LLM context, avoiding flooding the prompt with irrelevant logs.
"""
from __future__ import annotations
import re

def extract_clean_error(text: str) -> str:
    """
    Extracts the most relevant error traceback or compiler error from stdout/stderr output.
    This avoids flooding the LLM context with irrelevant stdout lines while preserving
    the exact stack trace.
    """
    if not text:
        return ""

    # 1. Look for Python tracebacks (standard traceback structure)
    tb_pattern = re.compile(
        r"(Traceback \(most recent call last\):.*?\n(?:[A-Za-z0-9_]+Error|Exception):[^\n]*)",
        re.DOTALL
    )
    match = tb_pattern.search(text)
    if match:
        return match.group(1).strip()
    
    # 2. Look for Python SyntaxError compile messages
    syntax_pattern = re.compile(
        r"(File \".*?\", line \d+.*?\n(?:SyntaxError|IndentationError|TabError):[^\n]*)",
        re.DOTALL
    )
    match = syntax_pattern.search(text)
    if match:
        return match.group(1).strip()
        
    # 3. Look for standard test failure patterns (e.g. pytest FAILURES block)
    pytest_fail_pattern = re.compile(
        r"(===+ FAILURES ===+.*?(?:===+|\Z))",
        re.DOTALL
    )
    match = pytest_fail_pattern.search(text)
    if match:
        # Keep up to 1500 chars of the failures block
        return match.group(1).strip()[:1500]

    # 4. Fallback: Extract lines containing FAIL, ERROR, or Exception
    lines = text.splitlines()
    error_lines = []
    for line in lines:
        if any(marker in line.upper() for marker in ("FAIL", "ERROR", "EXCEPTION", "SYNTAX")):
            error_lines.append(line)
    if error_lines:
        return "Relevant Error Lines:\n" + "\n".join(error_lines[-10:])
        
    # 5. Final fallback: return the end of the text
    return text[-1000:].strip()
