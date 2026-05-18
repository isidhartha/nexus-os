"""Safe command execution sandbox with allowlist and timeout enforcement."""

from __future__ import annotations

import asyncio
import shlex
import subprocess
import sys
from typing import Dict, List, Optional

from ..shared.config import get_settings
from ..shared.logging import get_logger

logger = get_logger(__name__)


class CommandSandbox:
    """Executes shell commands restricted to an allowlist."""

    def __init__(
        self,
        allowed_commands: Optional[List[str]] = None,
        timeout: Optional[int] = None,
    ) -> None:
        settings = get_settings()
        self.allowed_commands = set(
            allowed_commands or settings.allowed_commands_list
        )
        self.timeout = timeout or settings.sandbox_timeout
        logger.info(
            "Sandbox initialized (allowed=%s, timeout=%ds)",
            self.allowed_commands,
            self.timeout,
        )

    def is_allowed(self, command: str) -> bool:
        """Return True if the command's base executable is in the allowlist."""
        try:
            parts = shlex.split(command)
            if not parts:
                return False
            base = parts[0].split("/")[-1].split("\\")[-1]
            # Strip .exe on Windows
            base = base.replace(".exe", "")
            return base in self.allowed_commands
        except ValueError:
            return False

    async def run(self, command: str, stdin_input: Optional[str] = None) -> Dict:
        """Run a command and return stdout, stderr, and return code."""
        if not self.is_allowed(command):
            logger.warning("Blocked disallowed command: %s", command)
            return {
                "success": False,
                "error": f"Command not in allowlist: {command.split()[0]}",
                "stdout": "",
                "stderr": "",
                "returncode": -1,
            }

        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.PIPE if stdin_input else None,
            )
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(input=stdin_input.encode() if stdin_input else None),
                timeout=float(self.timeout),
            )
            stdout = stdout_bytes.decode("utf-8", errors="replace")
            stderr = stderr_bytes.decode("utf-8", errors="replace")
            logger.debug("Command '%s' rc=%d", command, proc.returncode)
            return {
                "success": proc.returncode == 0,
                "stdout": stdout,
                "stderr": stderr,
                "returncode": proc.returncode,
                "error": None,
            }
        except asyncio.TimeoutError:
            logger.warning("Command timed out: %s", command)
            return {
                "success": False,
                "error": f"Command timed out after {self.timeout}s",
                "stdout": "",
                "stderr": "",
                "returncode": -1,
            }
        except Exception as exc:
            logger.error("Sandbox execution error: %s", exc)
            return {
                "success": False,
                "error": str(exc),
                "stdout": "",
                "stderr": "",
                "returncode": -1,
            }

    def add_allowed(self, command: str) -> None:
        self.allowed_commands.add(command)
        logger.info("Added to allowlist: %s", command)

    def remove_allowed(self, command: str) -> None:
        self.allowed_commands.discard(command)
        logger.info("Removed from allowlist: %s", command)
