"""PC automation agent using pyautogui with safe operation boundaries."""

from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, Optional, Tuple

from ..shared.logging import get_logger

logger = get_logger(__name__)


class ComputerAgent:
    """Automate mouse, keyboard, and screen operations."""

    def __init__(self) -> None:
        self._available = False
        self._init()

    def _init(self) -> None:
        try:
            import pyautogui  # type: ignore[import]
            pyautogui.FAILSAFE = True
            pyautogui.PAUSE = 0.1
            self._pyautogui = pyautogui
            self._available = True
            logger.info("ComputerAgent initialized via pyautogui")
        except ImportError:
            logger.warning("pyautogui not installed — ComputerAgent in mock mode")

    async def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch a named action with parameters."""
        handlers = {
            "click": self._click,
            "double_click": self._double_click,
            "right_click": self._right_click,
            "type": self._type_text,
            "hotkey": self._hotkey,
            "screenshot": self._screenshot,
            "move": self._move,
            "scroll": self._scroll,
            "get_screen_size": self._get_screen_size,
            "locate": self._locate_on_screen,
        }

        handler = handlers.get(action)
        if not handler:
            return {"success": False, "error": f"Unknown action: {action}"}

        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None, lambda: handler(params)
            )
            return result
        except Exception as exc:
            logger.error("ComputerAgent action '%s' failed: %s", action, exc)
            return {"success": False, "error": str(exc)}

    def _click(self, params: Dict[str, Any]) -> Dict[str, Any]:
        if not self._available:
            return self._mock("click", params)
        x, y = params.get("x", 0), params.get("y", 0)
        self._pyautogui.click(x, y)
        return {"success": True, "action": "click", "position": (x, y)}

    def _double_click(self, params: Dict[str, Any]) -> Dict[str, Any]:
        if not self._available:
            return self._mock("double_click", params)
        x, y = params.get("x", 0), params.get("y", 0)
        self._pyautogui.doubleClick(x, y)
        return {"success": True, "action": "double_click", "position": (x, y)}

    def _right_click(self, params: Dict[str, Any]) -> Dict[str, Any]:
        if not self._available:
            return self._mock("right_click", params)
        x, y = params.get("x", 0), params.get("y", 0)
        self._pyautogui.rightClick(x, y)
        return {"success": True, "action": "right_click", "position": (x, y)}

    def _type_text(self, params: Dict[str, Any]) -> Dict[str, Any]:
        if not self._available:
            return self._mock("type", params)
        text = params.get("text", "")
        interval = params.get("interval", 0.05)
        self._pyautogui.typewrite(text, interval=interval)
        return {"success": True, "action": "type", "text": text}

    def _hotkey(self, params: Dict[str, Any]) -> Dict[str, Any]:
        if not self._available:
            return self._mock("hotkey", params)
        keys = params.get("keys", [])
        self._pyautogui.hotkey(*keys)
        return {"success": True, "action": "hotkey", "keys": keys}

    def _screenshot(self, params: Dict[str, Any]) -> Dict[str, Any]:
        if not self._available:
            return self._mock("screenshot", params)
        import base64
        import io

        region = params.get("region")
        img = self._pyautogui.screenshot(region=region)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode()
        return {"success": True, "action": "screenshot", "image_base64": b64}

    def _move(self, params: Dict[str, Any]) -> Dict[str, Any]:
        if not self._available:
            return self._mock("move", params)
        x, y = params.get("x", 0), params.get("y", 0)
        duration = params.get("duration", 0.2)
        self._pyautogui.moveTo(x, y, duration=duration)
        return {"success": True, "action": "move", "position": (x, y)}

    def _scroll(self, params: Dict[str, Any]) -> Dict[str, Any]:
        if not self._available:
            return self._mock("scroll", params)
        clicks = params.get("clicks", 3)
        x, y = params.get("x"), params.get("y")
        self._pyautogui.scroll(clicks, x=x, y=y)
        return {"success": True, "action": "scroll", "clicks": clicks}

    def _get_screen_size(self, params: Dict[str, Any]) -> Dict[str, Any]:
        if not self._available:
            return {"success": True, "width": 1920, "height": 1080}
        size = self._pyautogui.size()
        return {"success": True, "width": size.width, "height": size.height}

    def _locate_on_screen(self, params: Dict[str, Any]) -> Dict[str, Any]:
        if not self._available:
            return self._mock("locate", params)
        image_path = params.get("image_path", "")
        confidence = params.get("confidence", 0.9)
        try:
            location = self._pyautogui.locateOnScreen(image_path, confidence=confidence)
            if location:
                return {"success": True, "found": True, "location": list(location)}
            return {"success": True, "found": False}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def _mock(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("[MOCK ComputerAgent] %s %s", action, params)
        return {"success": True, "mock": True, "action": action, "params": params}

    @property
    def is_available(self) -> bool:
        return self._available
