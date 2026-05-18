"""Browser control agent using Playwright with async support."""

from __future__ import annotations

import base64
from typing import Any, Dict, Optional

from ..shared.config import get_settings
from ..shared.logging import get_logger

logger = get_logger(__name__)


class BrowserAgent:
    """Control a browser via Playwright for web automation."""

    def __init__(self) -> None:
        settings = get_settings()
        self.headless = settings.browser_headless
        self._playwright = None
        self._browser = None
        self._page = None
        self._available = False
        self._context = None

    async def start(self) -> bool:
        try:
            from playwright.async_api import async_playwright  # type: ignore[import]

            self._pw_context = async_playwright()
            self._playwright = await self._pw_context.__aenter__()
            self._browser = await self._playwright.chromium.launch(
                headless=self.headless
            )
            self._context = await self._browser.new_context(
                viewport={"width": 1280, "height": 720}
            )
            self._page = await self._context.new_page()
            self._available = True
            logger.info("BrowserAgent started (headless=%s)", self.headless)
            return True
        except ImportError:
            logger.warning("playwright not installed — BrowserAgent in mock mode")
            return False
        except Exception as exc:
            logger.error("BrowserAgent start error: %s", exc)
            return False

    async def stop(self) -> None:
        try:
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._pw_context.__aexit__(None, None, None)
            self._available = False
            logger.info("BrowserAgent stopped")
        except Exception as exc:
            logger.error("BrowserAgent stop error: %s", exc)

    async def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if not self._available:
            return self._mock(action, params)

        handlers = {
            "navigate": self._navigate,
            "click": self._click,
            "fill": self._fill,
            "get_text": self._get_text,
            "screenshot": self._screenshot,
            "evaluate": self._evaluate,
            "wait_for": self._wait_for,
            "go_back": self._go_back,
            "go_forward": self._go_forward,
            "get_url": self._get_url,
            "get_title": self._get_title,
            "scroll": self._scroll,
        }

        handler = handlers.get(action)
        if not handler:
            return {"success": False, "error": f"Unknown browser action: {action}"}

        try:
            return await handler(params)
        except Exception as exc:
            logger.error("BrowserAgent '%s' failed: %s", action, exc)
            return {"success": False, "error": str(exc)}

    async def _navigate(self, params: Dict[str, Any]) -> Dict[str, Any]:
        url = params.get("url", "")
        timeout = params.get("timeout", 30000)
        await self._page.goto(url, timeout=timeout)
        return {"success": True, "url": self._page.url, "title": await self._page.title()}

    async def _click(self, params: Dict[str, Any]) -> Dict[str, Any]:
        selector = params.get("selector", "")
        await self._page.click(selector)
        return {"success": True, "selector": selector}

    async def _fill(self, params: Dict[str, Any]) -> Dict[str, Any]:
        selector = params.get("selector", "")
        text = params.get("text", "")
        await self._page.fill(selector, text)
        return {"success": True, "selector": selector}

    async def _get_text(self, params: Dict[str, Any]) -> Dict[str, Any]:
        selector = params.get("selector", "body")
        text = await self._page.text_content(selector)
        return {"success": True, "text": text}

    async def _screenshot(self, params: Dict[str, Any]) -> Dict[str, Any]:
        full_page = params.get("full_page", False)
        img_bytes = await self._page.screenshot(full_page=full_page)
        b64 = base64.b64encode(img_bytes).decode()
        return {"success": True, "image_base64": b64}

    async def _evaluate(self, params: Dict[str, Any]) -> Dict[str, Any]:
        script = params.get("script", "")
        result = await self._page.evaluate(script)
        return {"success": True, "result": result}

    async def _wait_for(self, params: Dict[str, Any]) -> Dict[str, Any]:
        selector = params.get("selector", "")
        timeout = params.get("timeout", 5000)
        await self._page.wait_for_selector(selector, timeout=timeout)
        return {"success": True, "selector": selector}

    async def _go_back(self, params: Dict[str, Any]) -> Dict[str, Any]:
        await self._page.go_back()
        return {"success": True, "url": self._page.url}

    async def _go_forward(self, params: Dict[str, Any]) -> Dict[str, Any]:
        await self._page.go_forward()
        return {"success": True, "url": self._page.url}

    async def _get_url(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return {"success": True, "url": self._page.url}

    async def _get_title(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return {"success": True, "title": await self._page.title()}

    async def _scroll(self, params: Dict[str, Any]) -> Dict[str, Any]:
        x = params.get("x", 0)
        y = params.get("y", 500)
        await self._page.evaluate(f"window.scrollBy({x}, {y})")
        return {"success": True}

    def _mock(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("[MOCK BrowserAgent] %s %s", action, params)
        return {"success": True, "mock": True, "action": action}

    @property
    def is_available(self) -> bool:
        return self._available
