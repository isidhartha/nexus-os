"""File management agent with sandboxed operations."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..shared.config import get_settings
from ..shared.logging import get_logger

logger = get_logger(__name__)

# Paths the agent will never touch
_BLOCKED_PATHS = {"/etc", "/sys", "/proc", "/dev", "C:\\Windows", "C:\\Program Files"}


def _is_safe_path(path: Path) -> bool:
    resolved = str(path.resolve())
    return not any(resolved.startswith(b) for b in _BLOCKED_PATHS)


class FileAgent:
    """Performs sandboxed file system operations."""

    def __init__(self, base_dir: Optional[str] = None) -> None:
        self.base_dir = Path(base_dir) if base_dir else Path.home()
        logger.info("FileAgent base_dir=%s", self.base_dir)

    async def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        handlers = {
            "list": self._list_dir,
            "read": self._read_file,
            "write": self._write_file,
            "delete": self._delete,
            "copy": self._copy,
            "move": self._move,
            "mkdir": self._mkdir,
            "exists": self._exists,
            "info": self._file_info,
            "search": self._search,
        }

        handler = handlers.get(action)
        if not handler:
            return {"success": False, "error": f"Unknown file action: {action}"}

        try:
            return await handler(params)
        except PermissionError as exc:
            return {"success": False, "error": f"Permission denied: {exc}"}
        except Exception as exc:
            logger.error("FileAgent '%s' failed: %s", action, exc)
            return {"success": False, "error": str(exc)}

    def _resolve(self, path: str) -> Path:
        p = Path(path)
        if not p.is_absolute():
            p = self.base_dir / p
        if not _is_safe_path(p):
            raise PermissionError(f"Path not allowed: {p}")
        return p

    async def _list_dir(self, params: Dict[str, Any]) -> Dict[str, Any]:
        path = self._resolve(params.get("path", "."))
        if not path.is_dir():
            return {"success": False, "error": f"Not a directory: {path}"}

        entries = []
        for item in sorted(path.iterdir()):
            entries.append({
                "name": item.name,
                "type": "dir" if item.is_dir() else "file",
                "size": item.stat().st_size if item.is_file() else None,
            })
        return {"success": True, "path": str(path), "entries": entries}

    async def _read_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        path = self._resolve(params["path"])
        max_size = params.get("max_size", 1024 * 1024)  # 1MB default

        if not path.is_file():
            return {"success": False, "error": f"File not found: {path}"}
        if path.stat().st_size > max_size:
            return {"success": False, "error": "File too large to read"}

        content = path.read_text(encoding="utf-8", errors="replace")
        return {"success": True, "path": str(path), "content": content}

    async def _write_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        path = self._resolve(params["path"])
        content = params.get("content", "")
        mode = params.get("mode", "w")

        path.parent.mkdir(parents=True, exist_ok=True)
        if mode == "a":
            path.open("a").write(content)
        else:
            path.write_text(content, encoding="utf-8")

        return {"success": True, "path": str(path), "bytes_written": len(content)}

    async def _delete(self, params: Dict[str, Any]) -> Dict[str, Any]:
        path = self._resolve(params["path"])
        recursive = params.get("recursive", False)

        if not path.exists():
            return {"success": False, "error": f"Path not found: {path}"}

        if path.is_dir():
            if recursive:
                shutil.rmtree(path)
            else:
                path.rmdir()
        else:
            path.unlink()

        return {"success": True, "path": str(path)}

    async def _copy(self, params: Dict[str, Any]) -> Dict[str, Any]:
        src = self._resolve(params["src"])
        dst = self._resolve(params["dst"])

        if src.is_dir():
            shutil.copytree(src, dst)
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

        return {"success": True, "src": str(src), "dst": str(dst)}

    async def _move(self, params: Dict[str, Any]) -> Dict[str, Any]:
        src = self._resolve(params["src"])
        dst = self._resolve(params["dst"])
        shutil.move(str(src), str(dst))
        return {"success": True, "src": str(src), "dst": str(dst)}

    async def _mkdir(self, params: Dict[str, Any]) -> Dict[str, Any]:
        path = self._resolve(params["path"])
        path.mkdir(parents=True, exist_ok=True)
        return {"success": True, "path": str(path)}

    async def _exists(self, params: Dict[str, Any]) -> Dict[str, Any]:
        path = self._resolve(params["path"])
        return {"success": True, "exists": path.exists(), "path": str(path)}

    async def _file_info(self, params: Dict[str, Any]) -> Dict[str, Any]:
        path = self._resolve(params["path"])
        if not path.exists():
            return {"success": False, "error": f"Path not found: {path}"}
        stat = path.stat()
        return {
            "success": True,
            "path": str(path),
            "type": "dir" if path.is_dir() else "file",
            "size": stat.st_size,
            "modified": stat.st_mtime,
            "created": stat.st_ctime,
        }

    async def _search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        root = self._resolve(params.get("path", "."))
        pattern = params.get("pattern", "*")
        max_results = params.get("max_results", 50)

        results: List[str] = []
        for match in root.rglob(pattern):
            results.append(str(match))
            if len(results) >= max_results:
                break

        return {"success": True, "results": results, "count": len(results)}
