"""Sleep tool for autonomous idle waiting"""

import logging
import threading
from typing import Any, Dict

from .base import BaseTool, ToolResult

logger = logging.getLogger(__name__)

MAX_SLEEP_SECONDS = 3600


class SleepTool(BaseTool):
    """Lets the LLM pause autonomous operation when idle."""

    def __init__(self, sleep_event: threading.Event, agent=None):
        super().__init__(
            name="sleep",
            description="Pause autonomous operation when idle. "
                        "Wait for new cron tasks or user input. "
                        "Call this when you have nothing to do."
        )
        self._sleep_event = sleep_event
        self._agent = agent

    def execute(self, duration_seconds: int = 300, reason: str = "") -> ToolResult:
        duration = min(max(int(duration_seconds) if duration_seconds else 300, 1), MAX_SLEEP_SECONDS)
        logger.info(f"[tool:sleep] start | duration={duration}s reason={reason}")

        # Mark agent as sleeping so tick won't be sent
        if self._agent:
            self._agent._is_sleeping = True

        try:
            interrupted = self._sleep_event.wait(timeout=duration)
            if interrupted:
                self._sleep_event.clear()
                logger.info(f"[tool:sleep] interrupted after {duration}s max")
                return ToolResult(
                    success=True,
                    content="Sleep interrupted — new work is available."
                )
            else:
                logger.info(f"[tool:sleep] completed {duration}s")
                return ToolResult(
                    success=True,
                    content=f"Slept for {duration}s. No new work arrived."
                )
        finally:
            if self._agent:
                self._agent._is_sleeping = False

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "duration_seconds": {
                    "type": "integer",
                    "description": f"Maximum seconds to sleep (1-{MAX_SLEEP_SECONDS}, default 300)",
                    "default": 300,
                    "minimum": 1,
                    "maximum": MAX_SLEEP_SECONDS
                },
                "reason": {
                    "type": "string",
                    "description": "Brief reason for sleeping (for logging)"
                }
            },
            "required": []
        }
