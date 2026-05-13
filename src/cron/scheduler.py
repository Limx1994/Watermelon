"""Cron scheduler for autonomous task execution with tick mechanism"""

import json
import logging
import random
import tempfile
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..utils.path import get_project_root

logger = logging.getLogger(__name__)

TASKS_FILE = "config/scheduled_tasks.json"


class CronTask:
    """A single scheduled task definition. Supports both interval and cron expressions."""

    def __init__(
        self,
        name: str,
        prompt: str,
        cron_expression: Optional[str] = None,
        interval_minutes: Optional[int] = None,
        enabled: bool = True,
    ):
        self.name = name
        self.prompt = prompt
        self.cron_expression = cron_expression
        self.interval_minutes = interval_minutes
        self.enabled = enabled
        self.last_run: Optional[datetime] = None
        self.next_run: Optional[datetime] = None
        self._cron_iter = None

        if cron_expression:
            self._init_cron(cron_expression)
        elif interval_minutes:
            self.initialize_next_run()

    def _init_cron(self, expr: str) -> None:
        """Initialize cron iterator from croniter."""
        try:
            from croniter import croniter
            self._cron_iter = croniter(expr, datetime.now())
            self.next_run = self._cron_iter.get_next(datetime)
        except ImportError:
            logger.warning("croniter not installed, falling back to interval")
            self._cron_iter = None
            self.interval_minutes = 60
            self.initialize_next_run()
        except Exception as e:
            logger.error(f"Invalid cron expression '{expr}': {e}")
            self.enabled = False

    def initialize_next_run(self) -> None:
        if self.interval_minutes:
            self.next_run = datetime.now() + timedelta(minutes=self.interval_minutes)

    def is_due(self) -> bool:
        if not self.enabled:
            return False
        if self._cron_iter:
            now = datetime.now()
            return now >= self.next_run if self.next_run else True
        if self.next_run is None:
            return False
        return datetime.now() >= self.next_run

    def mark_run(self) -> None:
        self.last_run = datetime.now()
        if self._cron_iter:
            self.next_run = self._cron_iter.get_next(datetime)
        elif self.interval_minutes:
            self.next_run = datetime.now() + timedelta(minutes=self.interval_minutes)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "prompt": self.prompt,
            "cron_expression": self.cron_expression,
            "interval_minutes": self.interval_minutes,
            "enabled": self.enabled,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "next_run": self.next_run.isoformat() if self.next_run else None,
        }


class CronScheduler:
    """Background daemon thread that checks scheduled tasks, ticks, and feeds work to the agent."""

    def __init__(self, agent, tasks_config: List[Dict[str, Any]], tick_interval_minutes: int = 10):
        self._agent = agent
        self._tasks: List[CronTask] = []
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._tasks_file = get_project_root() / TASKS_FILE
        self._lock = threading.Lock()

        # Tick mechanism
        self._tick_interval = tick_interval_minutes
        self._last_tick = datetime.now()
        # Add jitter to tick to avoid synchronized wake-ups
        self._tick_jitter = random.uniform(0, min(tick_interval_minutes * 0.1, 2))

        # Network state monitoring
        self._network_ok = True
        self._last_network_check = datetime.now()
        self._network_check_interval = 30  # 每30秒检测一次网络状态

        for task_def in tasks_config:
            task = CronTask(
                name=task_def.get("name", "unnamed"),
                prompt=task_def.get("prompt", ""),
                cron_expression=task_def.get("cron_expression"),
                interval_minutes=task_def.get("interval_minutes"),
                enabled=task_def.get("enabled", True),
            )
            self._tasks.append(task)

        self._load_state()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._loop, daemon=True, name="cron-scheduler"
        )
        self._thread.start()
        logger.info(f"Cron scheduler started: {len(self._tasks)} tasks, tick every {self._tick_interval}m")

    def stop(self) -> None:
        logger.info("Scheduler stopped")
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=3)
        self._save_state()

    def check_network(self) -> bool:
        """检测网络连接状态"""
        try:
            import urllib.request
            # 使用更可靠的检测端点，减少超时时间
            urllib.request.urlopen("https://httpbin.org/get", timeout=3)
            logger.debug("Network check: ok")
            return True
        except Exception:
            logger.debug("Network check: failed")
            return False

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            now = datetime.now()

            # Network state monitoring - 使用统一的检测间隔，避免断网时频繁轮询
            if (now - self._last_network_check).total_seconds() >= self._network_check_interval:
                self._last_network_check = now
                was_ok = self._network_ok
                self._network_ok = self.check_network()
                if not was_ok and self._network_ok:
                    logger.info("Network recovered, triggering immediate tick")
                    if not self._agent._is_sleeping:
                        try:
                            self._agent.submit_work("<tick>", source="network_recover")
                        except Exception as e:
                            logger.error(f"Network recover tick failed: {e}")
                    self._last_tick = now
                    self._tick_jitter = random.uniform(0, min(self._tick_interval * 0.1, 2))
                elif was_ok and not self._network_ok:
                    logger.warning("Network disconnected")

            # Check cron tasks
            with self._lock:
                tasks_snapshot = list(self._tasks)
            for task in tasks_snapshot:
                if task.is_due():
                    logger.info(f"Cron task firing: {task.name}")
                    try:
                        self._agent.submit_work(task.prompt, source=f"cron:{task.name}")
                    except Exception as e:
                        logger.error(f"Cron task submit_work failed: {task.name}: {e}")
                    with self._lock:
                        task.mark_run()
                    self._save_state()

            # Tick mechanism: wake up agent periodically
            tick_elapsed = (now - self._last_tick).total_seconds() / 60
            if tick_elapsed >= self._tick_interval + self._tick_jitter:
                if not self._agent._is_sleeping:
                    logger.info("Tick firing")
                    try:
                        self._agent.submit_work("<tick>", source="tick")
                    except Exception as e:
                        logger.error(f"Tick submit_work failed: {e}")
                else:
                    logger.debug("Tick skipped: agent sleeping")
                self._last_tick = now
                self._tick_jitter = random.uniform(0, min(self._tick_interval * 0.1, 2))

            self._stop_event.wait(timeout=1)

    def _save_state(self) -> None:
        try:
            with self._lock:
                data = [t.to_dict() for t in self._tasks]
            content = json.dumps(data, indent=2, ensure_ascii=False)
            # Atomic write: temp file + rename
            tmp_fd, tmp_path = tempfile.mkstemp(
                dir=str(self._tasks_file.parent), suffix=".tmp"
            )
            try:
                with open(tmp_fd, "w", encoding="utf-8") as f:
                    f.write(content)
                Path(tmp_path).replace(self._tasks_file)
                logger.debug("Cron state saved successfully")
            except Exception:
                Path(tmp_path).unlink(missing_ok=True)
                raise
        except Exception as e:
            logger.error(f"Failed to save cron state: {e}")

    def _load_state(self) -> None:
        if not self._tasks_file.exists():
            logger.debug("No cron state file found, starting fresh")
            return
        try:
            data = json.loads(self._tasks_file.read_text(encoding="utf-8"))
            persisted = {t["name"]: t for t in data}
            restored = []
            for task in self._tasks:
                if task.name in persisted:
                    p = persisted[task.name]
                    if p.get("last_run"):
                        task.last_run = datetime.fromisoformat(p["last_run"])
                    if p.get("next_run") and not task._cron_iter:
                        task.next_run = datetime.fromisoformat(p["next_run"])
                    restored.append(task.name)
            if restored:
                logger.info(f"Cron state loaded: restored {len(restored)} tasks: {restored}")
        except Exception as e:
            logger.warning(f"Failed to load cron state: {e}")
