"""Autonomous multi-step workflow execution engine."""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from ..shared.config import get_settings
from ..shared.logging import get_logger
from ..shared.models import (
    WorkflowDefinition,
    WorkflowResult,
    WorkflowStatus,
    WorkflowStep,
)

logger = get_logger(__name__)

_WORKFLOWS_PATH = Path("./data/workflows.json")


class WorkflowAgent:
    """Loads, stores, and executes named multi-step workflows."""

    def __init__(self) -> None:
        self._workflows: Dict[str, WorkflowDefinition] = {}
        self._action_registry: Dict[str, Callable] = {}
        self._load_workflows()
        self._register_builtins()

    def _load_workflows(self) -> None:
        _WORKFLOWS_PATH.parent.mkdir(parents=True, exist_ok=True)
        if _WORKFLOWS_PATH.exists():
            try:
                raw = json.loads(_WORKFLOWS_PATH.read_text())
                for item in raw:
                    wf = WorkflowDefinition(**item)
                    self._workflows[wf.name] = wf
                logger.info("Loaded %d workflows", len(self._workflows))
            except Exception as exc:
                logger.error("Failed to load workflows: %s", exc)

    def _save_workflows(self) -> None:
        data = [wf.model_dump(mode="json") for wf in self._workflows.values()]
        _WORKFLOWS_PATH.write_text(json.dumps(data, indent=2))

    def _register_builtins(self) -> None:
        self._action_registry["sleep"] = self._action_sleep
        self._action_registry["log"] = self._action_log
        self._action_registry["echo"] = self._action_echo
        self._action_registry["http_get"] = self._action_http_get
        self._action_registry["set_var"] = self._action_set_var

    def register_action(self, name: str, handler: Callable) -> None:
        self._action_registry[name] = handler
        logger.debug("Registered workflow action: %s", name)

    def add_workflow(self, wf: WorkflowDefinition) -> None:
        self._workflows[wf.name] = wf
        self._save_workflows()
        logger.info("Added workflow: %s", wf.name)

    def list_workflows(self) -> List[WorkflowDefinition]:
        return list(self._workflows.values())

    def get_workflow(self, name: str) -> Optional[WorkflowDefinition]:
        return self._workflows.get(name)

    async def run(
        self,
        name: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> WorkflowResult:
        wf = self._workflows.get(name)
        if not wf:
            return WorkflowResult(
                workflow_name=name,
                status=WorkflowStatus.FAILED,
                steps_completed=0,
                steps_total=0,
                error=f"Workflow '{name}' not found",
            )

        settings = get_settings()
        context: Dict[str, Any] = dict(params or {})
        results: List[Dict[str, Any]] = []
        start = time.monotonic()

        for i, step in enumerate(wf.steps):
            logger.info("Workflow '%s' step %d/%d: %s", name, i + 1, len(wf.steps), step.name)
            step_result = await self._execute_step(step, context)
            results.append({"step": step.name, **step_result})

            if not step_result.get("success") and step.on_failure == "stop":
                return WorkflowResult(
                    workflow_name=name,
                    status=WorkflowStatus.FAILED,
                    steps_completed=i,
                    steps_total=len(wf.steps),
                    results=results,
                    error=f"Step '{step.name}' failed: {step_result.get('error')}",
                    duration_ms=(time.monotonic() - start) * 1000,
                )

            if step_result.get("output") is not None:
                context[f"step_{i}_output"] = step_result["output"]

        return WorkflowResult(
            workflow_name=name,
            status=WorkflowStatus.COMPLETED,
            steps_completed=len(wf.steps),
            steps_total=len(wf.steps),
            results=results,
            duration_ms=(time.monotonic() - start) * 1000,
        )

    async def _execute_step(
        self, step: WorkflowStep, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        handler = self._action_registry.get(step.action)
        if not handler:
            return {"success": False, "error": f"Unknown action: {step.action}"}

        merged_params = {**step.params, **context}
        try:
            result = await asyncio.wait_for(
                self._call_handler(handler, merged_params),
                timeout=float(step.timeout),
            )
            return result
        except asyncio.TimeoutError:
            return {"success": False, "error": f"Step timed out after {step.timeout}s"}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    async def _call_handler(
        self, handler: Callable, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        if asyncio.iscoroutinefunction(handler):
            return await handler(params)
        return handler(params)

    # Built-in action handlers
    async def _action_sleep(self, params: Dict[str, Any]) -> Dict[str, Any]:
        duration = float(params.get("seconds", 1))
        await asyncio.sleep(duration)
        return {"success": True, "slept": duration}

    async def _action_log(self, params: Dict[str, Any]) -> Dict[str, Any]:
        message = params.get("message", "")
        logger.info("[Workflow] %s", message)
        return {"success": True, "output": message}

    async def _action_echo(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return {"success": True, "output": params.get("value", "")}

    async def _action_http_get(self, params: Dict[str, Any]) -> Dict[str, Any]:
        try:
            import httpx  # type: ignore[import]
            url = params["url"]
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, timeout=10.0)
            return {"success": True, "status": resp.status_code, "output": resp.text[:2000]}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    async def _action_set_var(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return {"success": True, "output": params.get("value")}
