from __future__ import annotations

import logging
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler

from backend.config import settings
from backend.database.db import get_app_settings
from backend.workflows.orchestrator import ComicFactoryOrchestrator

logger = logging.getLogger(__name__)


class SchedulerManager:
    """Built-in Python APScheduler fallback & companion to n8n."""

    def __init__(self) -> None:
        self.scheduler: Optional[BackgroundScheduler] = None
        self.orchestrator = ComicFactoryOrchestrator()

    def start(self) -> None:
        if not settings.scheduler_enabled:
            logger.info("Scheduler disabled via SCHEDULER_ENABLED=false")
            return
        if self.scheduler and self.scheduler.running:
            return

        self.scheduler = BackgroundScheduler(timezone=settings.scheduler_timezone)
        # Check due publishing queue every 5 minutes
        self.scheduler.add_job(
            self._publish_tick,
            "interval",
            minutes=5,
            id="publish_due_posts",
            replace_existing=True,
        )
        # Daily autonomous continuation & episode production at 06:00 local time
        self.scheduler.add_job(
            self._daily_production_tick,
            "cron",
            hour=6,
            minute=0,
            id="daily_episode_production",
            replace_existing=True,
        )
        self.scheduler.start()
        logger.info("BackgroundScheduler started (timezone=%s)", settings.scheduler_timezone)

    def shutdown(self) -> None:
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown(wait=False)

    def _publish_tick(self) -> None:
        cfg = get_app_settings()
        if cfg.get("scheduler_paused") or not cfg.get("auto_publish", True):
            return
        try:
            self.orchestrator.run_due_publishing_workflow(trigger_source="apscheduler")
        except Exception as exc:
            logger.error("Scheduled publish tick failed: %s", exc)

    def _daily_production_tick(self) -> None:
        cfg = get_app_settings()
        if cfg.get("scheduler_paused"):
            return
        try:
            self.orchestrator.run_continuation_workflow(trigger_source="apscheduler")
        except Exception as exc:
            logger.error("Scheduled daily production tick failed: %s", exc)

    def is_running(self) -> bool:
        return bool(self.scheduler and self.scheduler.running)


scheduler_manager = SchedulerManager()
