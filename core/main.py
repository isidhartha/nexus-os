"""NexusOS FastAPI server — REST API and WebSocket gateway."""

from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, List, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .nexus import NexusOS, get_nexus
from .shared.config import get_settings
from .shared.logging import get_logger
from .shared.models import (
    AppLaunchRequest,
    AppLaunchResponse,
    BrowserControlRequest,
    BrowserControlResponse,
    CommandRequest,
    CommandResponse,
    HealthResponse,
    MemoryEntry,
    WebSocketMessage,
    WorkflowDefinition,
    WorkflowResult,
    WorkflowRunRequest,
)

logger = get_logger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    nexus = get_nexus()
    await nexus.initialize()
    logger.info("NexusOS server started")
    yield
    await nexus.shutdown()
    logger.info("NexusOS server stopped")


app = FastAPI(
    title="NexusOS API",
    description="NexusOS — voice-controlled desktop automation and AI assistant",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health ─────────────────────────────────────────────────────────────────


@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check() -> HealthResponse:
    nexus = get_nexus()
    return HealthResponse(
        status="ok",
        service="NexusOS",
        version=NexusOS.VERSION,
        uptime_seconds=nexus.uptime_seconds,
        subsystems=nexus.subsystem_status(),
    )


# ── Command API ────────────────────────────────────────────────────────────


@app.post("/api/v1/command", response_model=CommandResponse, tags=["Commands"])
async def execute_command(request: CommandRequest) -> CommandResponse:
    nexus = get_nexus()
    return await nexus.execute_command(request)


# ── Voice API ──────────────────────────────────────────────────────────────


@app.post("/api/v1/voice/start", tags=["Voice"])
async def start_voice() -> Dict[str, str]:
    nexus = get_nexus()
    nexus.start_voice_listener()
    return {"status": "listening", "wake_word": settings.wake_word}


@app.post("/api/v1/voice/stop", tags=["Voice"])
async def stop_voice() -> Dict[str, str]:
    nexus = get_nexus()
    nexus.stop_voice_listener()
    return {"status": "stopped"}


# ── Memory API ─────────────────────────────────────────────────────────────


@app.get("/api/v1/memory", response_model=List[MemoryEntry], tags=["Memory"])
async def get_memory(
    category: Optional[str] = None,
    limit: int = 50,
) -> List[MemoryEntry]:
    nexus = get_nexus()
    return nexus.get_memories(category=category, limit=limit)


@app.post("/api/v1/memory", tags=["Memory"])
async def store_memory(
    key: str,
    value: str,
    category: str = "general",
) -> Dict[str, Any]:
    nexus = get_nexus()
    entry = nexus.memory_agent.remember(key, value, category)
    return {"id": entry.id, "key": entry.key}


@app.get("/api/v1/memory/search", tags=["Memory"])
async def search_memory(query: str, limit: int = 10) -> List[MemoryEntry]:
    nexus = get_nexus()
    return nexus.memory_agent.recall(query, limit=limit)


# ── Workflow API ───────────────────────────────────────────────────────────


@app.get("/api/v1/workflows", response_model=List[WorkflowDefinition], tags=["Workflows"])
async def list_workflows() -> List[WorkflowDefinition]:
    nexus = get_nexus()
    return nexus.list_workflows()


@app.post("/api/v1/workflow/run", response_model=WorkflowResult, tags=["Workflows"])
async def run_workflow(request: WorkflowRunRequest) -> WorkflowResult:
    nexus = get_nexus()
    return await nexus.run_workflow(request)


@app.post("/api/v1/workflow", tags=["Workflows"])
async def create_workflow(definition: WorkflowDefinition) -> Dict[str, str]:
    nexus = get_nexus()
    nexus.add_workflow(definition)
    return {"name": definition.name, "status": "created"}


# ── App Launcher API ───────────────────────────────────────────────────────


@app.post("/api/v1/apps/launch", response_model=AppLaunchResponse, tags=["Apps"])
async def launch_app(request: AppLaunchRequest) -> AppLaunchResponse:
    nexus = get_nexus()
    return nexus.launch_app(request)


@app.get("/api/v1/apps/running", tags=["Apps"])
async def list_running_apps() -> List[Dict[str, Any]]:
    nexus = get_nexus()
    return nexus.app_launcher.list_running()


@app.get("/api/v1/apps/available", tags=["Apps"])
async def list_available_apps() -> Dict[str, List[str]]:
    nexus = get_nexus()
    return {"aliases": nexus.app_launcher.available_aliases}


# ── Browser API ────────────────────────────────────────────────────────────


@app.post(
    "/api/v1/browser/control",
    response_model=BrowserControlResponse,
    tags=["Browser"],
)
async def browser_control(request: BrowserControlRequest) -> BrowserControlResponse:
    nexus = get_nexus()
    return await nexus.control_browser(request)


# ── Smart Home API ─────────────────────────────────────────────────────────


@app.get("/api/v1/iot/devices", tags=["SmartHome"])
async def list_iot_devices() -> List[Dict[str, Any]]:
    nexus = get_nexus()
    return [d.model_dump(mode="json") for d in nexus.smart_home.list_devices()]


@app.post("/api/v1/iot/control", tags=["SmartHome"])
async def control_iot_device(
    device_id: str,
    command: str,
    value: Optional[Any] = None,
) -> Dict[str, Any]:
    nexus = get_nexus()
    success = nexus.smart_home.control_device(device_id, command, value)
    return {"success": success, "device_id": device_id, "command": command}


# ── Security API ───────────────────────────────────────────────────────────


@app.get("/api/v1/security/events", tags=["Security"])
async def get_security_events(unacknowledged_only: bool = False) -> List[Dict]:
    nexus = get_nexus()
    return nexus.security.list_events(unacknowledged_only=unacknowledged_only)


# ── Sandbox API ────────────────────────────────────────────────────────────


@app.post("/api/v1/sandbox/run", tags=["Sandbox"])
async def run_sandboxed(command: str) -> Dict[str, Any]:
    nexus = get_nexus()
    return await nexus.sandbox.run(command)


# ── WebSocket ──────────────────────────────────────────────────────────────


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: List[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.append(ws)
        logger.info("WebSocket client connected (%d total)", len(self._connections))

    def disconnect(self, ws: WebSocket) -> None:
        self._connections.remove(ws)
        logger.info("WebSocket client disconnected (%d total)", len(self._connections))

    async def broadcast(self, message: str) -> None:
        dead = []
        for ws in self._connections:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._connections.remove(ws)


_manager = ConnectionManager()


@app.websocket("/ws/nexus")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await _manager.connect(websocket)
    nexus = get_nexus()

    def broadcast_callback(msg: WebSocketMessage) -> None:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(
                    _manager.broadcast(msg.model_dump_json()),
                    loop=loop,
                )
        except RuntimeError:
            pass

    nexus.subscribe(broadcast_callback)

    try:
        await websocket.send_json(
            {"type": "connected", "data": {"service": "NexusOS", "version": NexusOS.VERSION}}
        )

        while True:
            raw = await websocket.receive_text()
            try:
                payload = json.loads(raw)
                msg_type = payload.get("type", "command")

                if msg_type == "command":
                    text = payload.get("text", "")
                    mode = payload.get("mode", "text")
                    req = CommandRequest(text=text, mode=mode)
                    result = await nexus.execute_command(req)
                    await websocket.send_json(
                        {"type": "command_result", "data": result.model_dump(mode="json")}
                    )

                elif msg_type == "ping":
                    await websocket.send_json({"type": "pong", "data": {}})

                else:
                    await websocket.send_json(
                        {"type": "error", "data": {"message": f"Unknown type: {msg_type}"}}
                    )

            except json.JSONDecodeError:
                await websocket.send_json(
                    {"type": "error", "data": {"message": "Invalid JSON"}}
                )
            except Exception as exc:
                logger.error("WebSocket handler error: %s", exc)
                await websocket.send_json(
                    {"type": "error", "data": {"message": str(exc)}}
                )

    except WebSocketDisconnect:
        pass
    finally:
        nexus.unsubscribe(broadcast_callback)
        _manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "core.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=settings.log_level.lower(),
    )
