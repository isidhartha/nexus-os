"""NexusOS main AI OS controller — orchestrates all subsystems."""

from __future__ import annotations

import asyncio
import time
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set

from .agents import BrowserAgent, ComputerAgent, FileAgent, MemoryAgent, WorkflowAgent
from .automation import AppLauncher, CommandSandbox, TaskScheduler
from .integrations import PluginManager, SecurityManager, SmartHomeManager
from .shared.config import get_settings
from .shared.logging import get_logger
from .shared.models import (
    AppLaunchRequest,
    AppLaunchResponse,
    BrowserControlRequest,
    BrowserControlResponse,
    CommandMode,
    CommandRequest,
    CommandResponse,
    CommandStatus,
    MemoryEntry,
    WebSocketMessage,
    WorkflowDefinition,
    WorkflowResult,
    WorkflowRunRequest,
)
from .voice import TextToSpeech, VoiceIdentityManager, WakeWordDetector, WhisperSTT

logger = get_logger(__name__)


class NexusOS:
    """Central AI OS controller coordinating all NexusOS subsystems."""

    VERSION = "1.0.0"

    def __init__(self) -> None:
        self._settings = get_settings()
        self._start_time = time.monotonic()
        self._ws_subscribers: Set[Callable] = set()

        # Subsystem initialization
        self.tts = TextToSpeech()
        self.stt = WhisperSTT()
        self.identity = VoiceIdentityManager()
        self.wake_word = WakeWordDetector(callback=self._on_wake_word)

        self.memory_agent = MemoryAgent()
        self.computer_agent = ComputerAgent()
        self.browser_agent = BrowserAgent()
        self.file_agent = FileAgent()
        self.workflow_agent = WorkflowAgent()

        self.app_launcher = AppLauncher()
        self.sandbox = CommandSandbox()
        self.scheduler = TaskScheduler()

        self.smart_home = SmartHomeManager()
        self.security = SecurityManager()
        self.plugins = PluginManager()

        self._voice_listening = False
        self._initialized = False

        logger.info("NexusOS v%s controller created", self.VERSION)

    async def initialize(self) -> None:
        """Async initialization — start long-lived subsystems."""
        if self._initialized:
            return

        self.plugins.set_nexus(self)
        self.plugins.discover_and_load()
        self.scheduler.start()
        self.smart_home.connect()

        self._initialized = True
        logger.info("NexusOS fully initialized")
        self._broadcast(WebSocketMessage(type="system", data={"event": "initialized"}))

    async def shutdown(self) -> None:
        """Graceful shutdown of all subsystems."""
        logger.info("NexusOS shutting down...")
        self.wake_word.stop()
        await self.browser_agent.stop()
        self.smart_home.disconnect()
        self.scheduler.stop()
        logger.info("NexusOS shutdown complete")

    # ── Core Command Execution ─────────────────────────────────────────────

    async def execute_command(self, request: CommandRequest) -> CommandResponse:
        """Parse and route a natural language or structured command."""
        cmd_id = str(uuid.uuid4())
        start = time.monotonic()
        logger.info("Executing command [%s] mode=%s: %s", cmd_id, request.mode, request.text[:80])

        self._broadcast(WebSocketMessage(
            type="command_start",
            data={"id": cmd_id, "text": request.text, "mode": request.mode},
        ))

        context = self.memory_agent.build_context_prompt(request.text)

        try:
            result = await self._route_command(request.text, context, request.mode)
            elapsed = (time.monotonic() - start) * 1000

            self.memory_agent.remember(
                key=f"cmd_{cmd_id[:8]}",
                value=f"Q: {request.text}\nA: {result}",
                category="command_history",
                speaker_id=request.speaker_id,
            )

            response = CommandResponse(
                id=cmd_id,
                status=CommandStatus.SUCCESS,
                result=result,
                execution_time_ms=elapsed,
            )

            self._broadcast(WebSocketMessage(
                type="command_complete",
                data={"id": cmd_id, "result": result, "elapsed_ms": elapsed},
            ))

            if request.mode == CommandMode.VOICE:
                self.tts.speak(result)

            return response

        except Exception as exc:
            logger.error("Command execution failed: %s", exc)
            elapsed = (time.monotonic() - start) * 1000
            return CommandResponse(
                id=cmd_id,
                status=CommandStatus.FAILED,
                error=str(exc),
                execution_time_ms=elapsed,
            )

    async def _route_command(
        self, text: str, context: str, mode: CommandMode
    ) -> str:
        """Route a command to the appropriate handler based on content."""
        text_lower = text.lower()

        # App launching
        for alias in self.app_launcher.available_aliases:
            if f"open {alias}" in text_lower or f"launch {alias}" in text_lower:
                result = self.app_launcher.launch(alias)
                return f"Launching {alias}..." if result["success"] else result["error"]

        # File operations
        if any(k in text_lower for k in ["list files", "show files", "ls ", "list directory"]):
            result = await self.file_agent.execute("list", {"path": "."})
            if result["success"]:
                entries = result.get("entries", [])
                names = [e["name"] for e in entries[:10]]
                return "Files: " + ", ".join(names)

        # Browser
        if "open url" in text_lower or "browse to" in text_lower or "navigate to" in text_lower:
            words = text.split()
            url = next((w for w in words if w.startswith("http")), None)
            if url:
                await self.browser_agent.start()
                result = await self.browser_agent.execute("navigate", {"url": url})
                return f"Navigated to {url}" if result["success"] else result.get("error", "")

        # Memory
        if text_lower.startswith("remember "):
            parts = text[9:].split(" is ", 1)
            if len(parts) == 2:
                self.memory_agent.remember(parts[0].strip(), parts[1].strip())
                return f"Remembered: {parts[0].strip()} = {parts[1].strip()}"

        if text_lower.startswith("recall ") or text_lower.startswith("what is "):
            query = text.split(" ", 1)[1] if " " in text else text
            entries = self.memory_agent.recall(query, limit=3)
            if entries:
                return "I recall: " + "; ".join(f"{e.key}: {e.value}" for e in entries)
            return "I don't have any memory about that."

        # Shell commands
        if text_lower.startswith("run ") or text_lower.startswith("execute "):
            cmd = text.split(" ", 1)[1]
            result = await self.sandbox.run(cmd)
            if result["success"]:
                return result["stdout"] or "Command executed successfully."
            return f"Error: {result.get('error', result.get('stderr', 'Unknown error'))}"

        # AI fallback
        return await self._ai_respond(text, context)

    async def _ai_respond(self, text: str, context: str) -> str:
        """Use AI API to respond to unrecognized commands."""
        if self._settings.openai_api_key:
            return await self._openai_respond(text, context)
        if self._settings.anthropic_api_key:
            return await self._anthropic_respond(text, context)
        return f"[NexusOS] I received: '{text}'. Configure OPENAI_API_KEY or ANTHROPIC_API_KEY for AI responses."

    async def _openai_respond(self, text: str, context: str) -> str:
        try:
            from openai import AsyncOpenAI  # type: ignore[import]
            client = AsyncOpenAI(api_key=self._settings.openai_api_key)
            system_prompt = (
                "You are NexusOS, an AI operating system assistant. "
                "Be concise, helpful, and action-oriented.\n"
            ) + (f"\n{context}" if context else "")
            resp = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text},
                ],
                max_tokens=512,
            )
            return resp.choices[0].message.content or ""
        except Exception as exc:
            logger.error("OpenAI error: %s", exc)
            return f"AI error: {exc}"

    async def _anthropic_respond(self, text: str, context: str) -> str:
        try:
            import anthropic  # type: ignore[import]
            client = anthropic.AsyncAnthropic(api_key=self._settings.anthropic_api_key)
            system_prompt = "You are NexusOS, an AI operating system. " + (context or "")
            resp = await client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=512,
                system=system_prompt,
                messages=[{"role": "user", "content": text}],
            )
            return resp.content[0].text
        except Exception as exc:
            logger.error("Anthropic error: %s", exc)
            return f"AI error: {exc}"

    # ── Voice Control ──────────────────────────────────────────────────────

    def start_voice_listener(self) -> None:
        if self._voice_listening:
            return
        self.wake_word.start()
        self._voice_listening = True
        logger.info("Voice listener started")
        self._broadcast(WebSocketMessage(type="voice", data={"event": "listening_started"}))

    def stop_voice_listener(self) -> None:
        self.wake_word.stop()
        self._voice_listening = False
        logger.info("Voice listener stopped")
        self._broadcast(WebSocketMessage(type="voice", data={"event": "listening_stopped"}))

    def _on_wake_word(self) -> None:
        logger.info("Wake word triggered — activating voice input")
        self._broadcast(WebSocketMessage(type="voice", data={"event": "wake_word_detected"}))
        self.tts.speak("Yes, how can I help?")

    # ── Workflow Management ────────────────────────────────────────────────

    async def run_workflow(self, request: WorkflowRunRequest) -> WorkflowResult:
        return await self.workflow_agent.run(request.name, request.params)

    def list_workflows(self) -> List[WorkflowDefinition]:
        return self.workflow_agent.list_workflows()

    def add_workflow(self, definition: WorkflowDefinition) -> None:
        self.workflow_agent.add_workflow(definition)

    # ── App Control ────────────────────────────────────────────────────────

    def launch_app(self, request: AppLaunchRequest) -> AppLaunchResponse:
        result = self.app_launcher.launch(
            request.app_name, request.args, request.working_dir
        )
        return AppLaunchResponse(
            success=result["success"],
            pid=result.get("pid"),
            app_name=request.app_name,
            error=result.get("error"),
        )

    # ── Browser Control ────────────────────────────────────────────────────

    async def control_browser(self, request: BrowserControlRequest) -> BrowserControlResponse:
        if not self.browser_agent.is_available:
            await self.browser_agent.start()

        params = {"url": request.url, "selector": request.selector, "text": request.text}
        params.update(request.params)
        params = {k: v for k, v in params.items() if v is not None}

        result = await self.browser_agent.execute(request.action, params)
        return BrowserControlResponse(
            success=result.get("success", False),
            result=result.get("result"),
            screenshot=result.get("image_base64"),
            error=result.get("error"),
        )

    # ── Memory ─────────────────────────────────────────────────────────────

    def get_memories(self, category: Optional[str] = None, limit: int = 50) -> List[MemoryEntry]:
        return self.memory_agent.list_recent(limit=limit)

    # ── WebSocket Broadcasting ─────────────────────────────────────────────

    def subscribe(self, callback: Callable) -> None:
        self._ws_subscribers.add(callback)

    def unsubscribe(self, callback: Callable) -> None:
        self._ws_subscribers.discard(callback)

    def _broadcast(self, message: WebSocketMessage) -> None:
        dead = set()
        for sub in self._ws_subscribers:
            try:
                sub(message)
            except Exception:
                dead.add(sub)
        self._ws_subscribers -= dead

    # ── Health / Status ────────────────────────────────────────────────────

    @property
    def uptime_seconds(self) -> float:
        return time.monotonic() - self._start_time

    def subsystem_status(self) -> Dict[str, bool]:
        return {
            "tts": self.tts.is_available,
            "stt": self.stt.is_available,
            "computer_agent": self.computer_agent.is_available,
            "browser_agent": self.browser_agent.is_available,
            "smart_home": self.smart_home.is_available,
            "mqtt_connected": self.smart_home.is_connected,
            "voice_listening": self._voice_listening,
        }


# Singleton accessor
_nexus_instance: Optional[NexusOS] = None


def get_nexus() -> NexusOS:
    global _nexus_instance
    if _nexus_instance is None:
        _nexus_instance = NexusOS()
    return _nexus_instance
