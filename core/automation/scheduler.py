"""Task scheduling for NexusOS using APScheduler."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from ..shared.logging import get_logger

logger = get_logger(__name__)


class TaskScheduler:
    """Schedule recurring or one-shot tasks."""

    def __init__(self) -> None:
        self._scheduler = None
        self._jobs: Dict[str, Any] = {}
        self._init()

    def _init(self) -> None:
        try:
            from apscheduler.schedulers.asyncio import AsyncIOScheduler  # type: ignore[import]
            self._scheduler = AsyncIOScheduler()
            logger.info("APScheduler initialized")
        except ImportError:
            logger.warning("apscheduler not installed — scheduler in mock mode")

    def start(self) -> None:
        if self._scheduler and not self._scheduler.running:
            self._scheduler.start()
            logger.info("Scheduler started")

    def stop(self) -> None:
        if self._scheduler and self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            logger.info("Scheduler stopped")

    def add_interval_job(
        self,
        job_id: str,
        func: Callable,
        seconds: int,
        args: Optional[List] = None,
    ) -> bool:
        if not self._scheduler:
            return False
        try:
            job = self._scheduler.add_job(
                func,
                "interval",
                seconds=seconds,
                id=job_id,
                args=args or [],
                replace_existing=True,
            )
            self._jobs[job_id] = job
            logger.info("Added interval job '%s' every %ds", job_id, seconds)
            return True
        except Exception as exc:
            logger.error("Failed to add job '%s': %s", job_id, exc)
            return False

    def add_cron_job(
        self,
        job_id: str,
        func: Callable,
        cron_expr: str,
        args: Optional[List] = None,
    ) -> bool:
        if not self._scheduler:
            return False
        try:
            parts = cron_expr.split()
            if len(parts) != 5:
                raise ValueError("Invalid cron expression")
            minute, hour, day, month, day_of_week = parts
            job = self._scheduler.add_job(
                func,
                "cron",
                minute=minute,
                hour=hour,
                day=day,
                month=month,
                day_of_week=day_of_week,
                id=job_id,
                args=args or [],
                replace_existing=True,
            )
            self._jobs[job_id] = job
            logger.info("Added cron job '%s': %s", job_id, cron_expr)
            return True
        except Exception as exc:
            logger.error("Failed to add cron job '%s': %s", job_id, exc)
            return False

    def add_once_job(
        self,
        job_id: str,
        func: Callable,
        run_at: datetime,
        args: Optional[List] = None,
    ) -> bool:
        if not self._scheduler:
            return False
        try:
            job = self._scheduler.add_job(
                func,
                "date",
                run_date=run_at,
                id=job_id,
                args=args or [],
                replace_existing=True,
            )
            self._jobs[job_id] = job
            logger.info("Scheduled one-shot job '%s' at %s", job_id, run_at)
            return True
        except Exception as exc:
            logger.error("Failed to schedule job '%s': %s", job_id, exc)
            return False

    def remove_job(self, job_id: str) -> bool:
        if not self._scheduler:
            return False
        try:
            self._scheduler.remove_job(job_id)
            self._jobs.pop(job_id, None)
            return True
        except Exception:
            return False

    def list_jobs(self) -> List[Dict]:
        if not self._scheduler:
            return []
        jobs = []
        for job in self._scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run": str(job.next_run_time) if job.next_run_time else None,
                "trigger": str(job.trigger),
            })
        return jobs
