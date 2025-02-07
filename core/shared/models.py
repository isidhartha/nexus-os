"""Shared Pydantic models and data types for NexusOS."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class CommandMode(str, Enum):
    VOICE = "voice"
    TEXT = "text"
    AUTONOMOUS = "autonomous"


class CommandStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkflowStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class CommandRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=4096)
    mode: CommandMode = CommandMode.TEXT
    session_id: Optional[str] = None
    speaker_id: Optional[str] = None


class CommandResponse(BaseModel):
    id: str
    status: CommandStatus
    result: Optional[str] = None
    error: Optional[str] = None
    execution_time_ms: Optional[float] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class MemoryEntry(BaseModel):
    id: str
    key: str
    value: str
    category: str = "general"
    speaker_id: Optional[str] = None
    embedding: Optional[List[float]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    access_count: int = 0


class WorkflowStep(BaseModel):
    name: str
    action: str
    params: Dict[str, Any] = Field(default_factory=dict)
    timeout: int = 30
    on_failure: str = "stop"


class WorkflowDefinition(BaseModel):
    name: str
    description: str
    steps: List[WorkflowStep]
    trigger: Optional[str] = None
    enabled: bool = True


class WorkflowRunRequest(BaseModel):
    name: str
    params: Dict[str, Any] = Field(default_factory=dict)


class WorkflowResult(BaseModel):
    workflow_name: str
    status: WorkflowStatus
    steps_completed: int
    steps_total: int
    results: List[Dict[str, Any]] = Field(default_factory=list)
    error: Optional[str] = None
    duration_ms: Optional[float] = None


class AppLaunchRequest(BaseModel):
    app_name: str
    args: List[str] = Field(default_factory=list)
    working_dir: Optional[str] = None


class AppLaunchResponse(BaseModel):
    success: bool
    pid: Optional[int] = None
    app_name: str
    error: Optional[str] = None


class BrowserControlRequest(BaseModel):
    action: str
    url: Optional[str] = None
    selector: Optional[str] = None
    text: Optional[str] = None
    params: Dict[str, Any] = Field(default_factory=dict)


class BrowserControlResponse(BaseModel):
    success: bool
    result: Optional[Any] = None
    screenshot: Optional[str] = None
    error: Optional[str] = None


class VoiceProfile(BaseModel):
    id: str
    name: str
    features: List[float]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_seen: Optional[datetime] = None
    confidence_threshold: float = 0.75


class IoTDevice(BaseModel):
    id: str
    name: str
    type: str
    state: Dict[str, Any] = Field(default_factory=dict)
    online: bool = False
    last_seen: Optional[datetime] = None


class WebSocketMessage(BaseModel):
    type: str
    data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    uptime_seconds: float
    subsystems: Dict[str, bool] = Field(default_factory=dict)
