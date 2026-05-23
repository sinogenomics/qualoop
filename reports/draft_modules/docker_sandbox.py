# -*- coding: utf-8 -*-
"""
Qualoop Docker Sandbox - Draft Implementation (Suggestion 14)
Wraps Docker CLI commands to coordinate secure verification in temporary
Docker containers with mounted local workspaces.
"""
import subprocess
import os
import sys
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("DockerSandbox")

class DockerSandboxError(Exception):
    pass

class DockerSandbox(object):
    def __init__(self, workspace_root, image_name="python:3.8-slim"):
        self.workspace_root = os.path.abspath(workspace_root)
        self.image_name = image_name
        self.container_name = "qualoop-sandbox-runner"

    def is_docker_available(self):
        """Checks if Docker service is accessible and running."""
        try:
            process = subprocess.Popen(
                ["docker", "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False
            )
            process.communicate()
            return process.returncode == 0
        except Exception:
            return False

    def run_command_in_sandbox(self, command_args, mount_path="/workspace"):
        """
        Runs a test command inside a Docker container with local workspace mounted.
        Automatically removes container after execution.
        """
        if not self.is_docker_available():
            raise DockerSandboxError("Docker command line tool is not available on this host.")

        # Windows paths must be mapped properly to docker volumes
        host_path = self.workspace_root
        if sys.platform == "win32":
            # Convert E:\path\to\dir -> /e/path/to/dir for Docker volumes compatibility
            host_path = host_path.replace("\\", "/")
            if ":" in host_path:
                drive, path = host_path.split(":", 1)
                host_path = "/{}{}".format(drive.lower(), path)

        docker_cmd = [
            "docker", "run", "--rm",
            "-v", "{}:{}".format(self.workspace_root, mount_path),
            "-w", mount_path,
            self.image_name
        ]
        
        if isinstance(command_args, list):
            docker_cmd.extend(command_args)
        else:
            docker_cmd.append(command_args)

        logger.info("Executing Docker Command: %s", " ".join(docker_cmd))
        
        try:
            process = subprocess.Popen(
                docker_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False
            )
            stdout, stderr = process.communicate()
            
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
            raise DockerSandboxError("Failed to run sandbox command: {}".format(str(e)))

if __name__ == "__main__":
    sandbox = DockerSandbox(r"e:\20260502_MZH\Qualoop")
    if sandbox.is_docker_available():
        print("Docker is active. Running safe python check inside Docker container...")
        res = sandbox.run_command_in_sandbox(["python", "--version"])
        print("Exit Code:", res["exit_code"])
        print("Output:", res["stdout"].strip() or res["stderr"].strip())
    else:
        print("Docker not detected or not running on host (Expected on default sandbox configurations).")
