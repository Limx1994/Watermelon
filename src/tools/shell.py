"""Shell execution tool"""

import logging
import subprocess
from typing import Any, Dict

from .base import BaseTool, ToolResult
from ..config import config

logger = logging.getLogger(__name__)


class ShellTool(BaseTool):
    """Tool for executing shell commands"""

    def __init__(self):
        super().__init__(
            name="shell",
            description="Execute shell commands on Windows (PowerShell). Use this to run system commands like dir, type, echo, etc."
        )
        self.whitelist = [
            "dir", "Get-ChildItem", "type", "cat", "echo", "mkdir",
            "Remove-Item", "Copy-Item", "Get-Content", "Set-Content",
            "cd", "pwd", "ls", "python", "pip", "node", "npm"
        ]

    def execute(self, command: str, **kwargs) -> ToolResult:
        """Execute a shell command"""
        logger.info(f"Executing shell command: {command[:100]}")
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=30
            )
            output = result.stdout if result.stdout else result.stderr
            if result.returncode != 0:
                logger.warning(f"Shell command failed (exit {result.returncode}): {command[:100]}")
                return ToolResult(
                    success=False,
                    content=output,
                    error=f"Command failed with exit code {result.returncode}"
                )
            logger.debug(f"Shell command completed: {command[:100]}")
            return ToolResult(success=True, content=output)
        except subprocess.TimeoutExpired:
            logger.warning(f"Shell command timed out: {command[:100]}")
            return ToolResult(
                success=False,
                content="",
                error="Command timed out after 30 seconds"
            )
        except Exception as e:
            logger.error(f"Shell command error: {e}")
            return ToolResult(
                success=False,
                content="",
                error=str(e)
            )

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute"
                }
            },
            "required": ["command"]
        }