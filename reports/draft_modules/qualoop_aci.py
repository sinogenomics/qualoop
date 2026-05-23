# -*- coding: utf-8 -*-
"""
Qualoop ACI (Agent-Computer Interface) - Draft Implementation
Provides a safe, structured, OS-independent interface for AI agents.
Filters command execution, manages path slashes, and prevents syntax failures.
"""
import os
import sys
import re
import subprocess
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("QualoopACI")

class ACIError(Exception):
    """Base exception for ACI violations or errors."""
    pass

class QualoopACI(object):
    def __init__(self, workspace_root):
        self.workspace_root = os.path.abspath(workspace_root)
        logger.info("Initializing Qualoop ACI with workspace root: %s", self.workspace_root)

    def normalize_path(self, relative_path):
        """Converts relative paths to absolute and normalizes directory separators for safety."""
        # Prevent path traversal attacks
        abs_path = os.path.abspath(os.path.join(self.workspace_root, relative_path))
        if not abs_path.startswith(self.workspace_root):
            raise ACIError("Path traversal detected! Attempted to access: {}".format(relative_path))
        return abs_path

    def safe_read_file(self, relative_path, start_line=None, end_line=None):
        """Reads specific line ranges of a file to optimize context size (inspired by SWE-agent)."""
        abs_path = self.normalize_path(relative_path)
        if not os.path.exists(abs_path):
            raise ACIError("File not found: {}".format(relative_path))
        
        try:
            with open(abs_path, "r") as f:
                lines = f.readlines()
            
            total_lines = len(lines)
            start = 1 if start_line is None else max(1, int(start_line))
            end = total_lines if end_line is None else min(total_lines, int(end_line))
            
            if start > end:
                return "Empty selection (start_line {} is greater than end_line {})".format(start, end)
            
            selected_lines = lines[start - 1:end]
            formatted_output = []
            for idx, line in enumerate(selected_lines, start=start):
                formatted_output.append("{:4d}: {}".format(idx, line.rstrip("\r\n")))
                
            return "\n".join(formatted_output)
        except Exception as e:
            raise ACIError("Failed to read file {}: {}".format(relative_path, str(e)))

    def safe_write_file(self, relative_path, content, overwrite=False):
        """Structured writing to prevent direct unsafe file overwrite commands."""
        abs_path = self.normalize_path(relative_path)
        if os.path.exists(abs_path) and not overwrite:
            raise ACIError("File already exists and overwrite is set to False: {}".format(relative_path))
            
        try:
            dir_name = os.path.dirname(abs_path)
            if not os.path.exists(dir_name):
                os.makedirs(dir_name)
            with open(abs_path, "w") as f:
                f.write(content)
            logger.info("Successfully wrote %d bytes to %s", len(content), relative_path)
            return "File successfully written."
        except Exception as e:
            raise ACIError("Failed to write to file {}: {}".format(relative_path, str(e)))

    def safe_execute_command(self, cmd_args, timeout=30):
        """
        Executes external command safely by passing structured argument lists instead of raw shells.
        Prevents shell injection (like &&/;) and handles cross-platform differences.
        """
        # Block dangerous commands
        forbidden_keywords = ["rm -rf", "del /s", "format", "mkfs", "curl", "wget"]
        cmd_str = " ".join(cmd_args) if isinstance(cmd_args, list) else cmd_args
        for kw in forbidden_keywords:
            if kw in cmd_str:
                raise ACIError("Security Block: Command contains forbidden operation '{}'".format(kw))

        # Under Windows PowerShell/cmd, ensure list execution doesn't fail due to bad characters
        try:
            # Use shell=False (default behavior) for argument security
            process = subprocess.Popen(
                cmd_args,
                cwd=self.workspace_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False
            )
            stdout, stderr = process.communicate()
            
            # Use UTF-8 or Fallback encoding
            try:
                out_decoded = stdout.decode("utf-8")
                err_decoded = stderr.decode("utf-8")
            except UnicodeDecodeError:
                out_decoded = stdout.decode("gbk", errors="ignore")
                err_decoded = stderr.decode("gbk", errors="ignore")

            return {
                "exit_code": process.returncode,
                "stdout": out_decoded,
                "stderr": err_decoded
            }
        except Exception as e:
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": "Execution failed: {}".format(str(e))
            }

if __name__ == "__main__":
    # Test execution using the actual repository root
    aci = QualoopACI(r"e:\20260502_MZH\Qualoop")
    print("Testing ACI File View:")
    print(aci.safe_read_file("qualoop.json", 1, 5))
    
    print("\nTesting ACI Safe Command:")
    res = aci.safe_execute_command(["git", "status"])
    print("Exit Code:", res["exit_code"])
    print("Stdout:", res["stdout"].strip())
