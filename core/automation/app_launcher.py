"""Application launcher using subprocess with process tracking."""

from __future__ import annotations

import os
import subprocess
import sys
from typing import Dict, List, Optional

from ..shared.logging import get_logger

logger = get_logger(__name__)

# Safe application aliases (cross-platform)
APP_ALIASES: Dict[str, Dict[str, str]] = {
    "notepad": {"win32": "notepad.exe", "linux": "gedit", "darwin": "TextEdit"},
    "calculator": {"win32": "calc.exe", "linux": "gnome-calculator", "darwin": "Calculator"},
    "browser": {"win32": "start chrome", "linux": "google-chrome", "darwin": "open -a Google\\ Chrome"},
    "terminal": {"win32": "cmd.exe", "linux": "gnome-terminal", "darwin": "Terminal"},
    "explorer": {"win32": "explorer.exe", "linux": "nautilus", "darwin": "Finder"},
    "vscode": {"win32": "code", "linux": "code", "darwin": "code"},
    "spotify": {"win32": "spotify", "linux": "spotify", "darwin": "Spotify"},
    "slack": {"win32": "slack", "linux": "slack", "darwin": "Slack"},
}


class AppLauncher:
    """Launches applications by name or path."""

    def __init__(self) -> None:
        self._platform = sys.platform
        self._running: Dict[str, subprocess.Popen] = {}

    def launch(
        self,
        app_name: str,
        args: Optional[List[str]] = None,
        working_dir: Optional[str] = None,
    ) -> Dict:
        """Launch an application and track its process."""
        resolved_cmd = self._resolve_command(app_name, args or [])
        if not resolved_cmd:
            return {"success": False, "error": f"Cannot resolve app: {app_name}"}

        try:
            proc = subprocess.Popen(
                resolved_cmd,
                cwd=working_dir,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                shell=isinstance(resolved_cmd, str),
            )
            self._running[app_name] = proc
            logger.info("Launched '%s' pid=%d", app_name, proc.pid)
            return {"success": True, "pid": proc.pid, "app_name": app_name}
        except FileNotFoundError:
            return {"success": False, "error": f"Executable not found: {app_name}"}
        except Exception as exc:
            logger.error("Launch error for '%s': %s", app_name, exc)
            return {"success": False, "error": str(exc)}

    def _resolve_command(
        self, app_name: str, args: List[str]
    ) -> Optional[list | str]:
        # Check alias table
        if app_name.lower() in APP_ALIASES:
            alias_map = APP_ALIASES[app_name.lower()]
            cmd = alias_map.get(self._platform) or alias_map.get("linux", "")
            if self._platform == "win32":
                return cmd + (" " + " ".join(args) if args else "")
            return [cmd] + args

        # Treat as direct executable
        cmd = [app_name] + args
        return cmd

    def terminate(self, app_name: str) -> bool:
        proc = self._running.get(app_name)
        if proc and proc.poll() is None:
            proc.terminate()
            logger.info("Terminated '%s'", app_name)
            return True
        return False

    def list_running(self) -> List[Dict]:
        results = []
        for name, proc in list(self._running.items()):
            poll = proc.poll()
            results.append({
                "name": name,
                "pid": proc.pid,
                "running": poll is None,
            })
            if poll is not None:
                del self._running[name]
        return results

    @property
    def available_aliases(self) -> List[str]:
        return list(APP_ALIASES.keys())
