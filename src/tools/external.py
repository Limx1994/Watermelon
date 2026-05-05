"""External tool executor for CLI programs"""

import json
import logging
import subprocess
from pathlib import Path
from typing import Any, Dict

from .base import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class ExternalTool(BaseTool):
    """Tool that executes an external CLI program"""

    def __init__(
        self,
        name: str,
        description: str,
        command: str,
        schema: Dict[str, Any]
    ):
        super().__init__(name, description)
        self.command = command
        self.schema = schema
        self._project_root = self._find_project_root()

    def _find_project_root(self) -> Path:
        """Find the project root directory"""
        current = Path(__file__).resolve().parent
        while current != current.parent:
            if (current / "config.json").exists():
                return current
            current = current.parent
        return Path.cwd()

    def _is_absolute_path(self, path: str) -> bool:
        """Check if path is absolute"""
        if not path:
            return False
        # Windows: C:\, D:\ etc. or UNC \\server\share
        # Unix: / (root)
        return Path(path).is_absolute() or (
            len(path) >= 2 and path[1] == ':'
        ) or path.startswith('\\\\')

    def execute(self, **kwargs) -> ToolResult:
        """Execute the external CLI program"""
        logger.info(f"Executing external tool: {self.name}")
        try:
            # Determine if command is relative or absolute
            cmd_str = self.command
            if not self._is_absolute_path(cmd_str):
                # Relative path: join with project root
                cmd_str = str(self._project_root / cmd_str)

            # Build command with arguments
            cmd_parts = cmd_str.split()
            for key, value in kwargs.items():
                # Convert underscores to hyphens for CLI args
                arg_name = f"--{key.replace('_', '-')}"
                cmd_parts.extend([arg_name, str(value)])

            logger.debug(f"Running: {' '.join(cmd_parts)}")
            result = subprocess.run(
                cmd_parts,
                capture_output=True,
                text=True,
                cwd=str(self._project_root)
            )

            if result.stdout:
                try:
                    data = json.loads(result.stdout)
                    success = data.get("success", False)
                    if not success:
                        logger.warning(f"External tool {self.name} returned success=false")

                    # Extract content - for read_file, content is the primary field
                    # but for image/pdf/notebook, data may be in other fields
                    content = data.get("content", "")
                    if not content:
                        # For image/pdf/notebook, serialize the relevant data
                        if 'base64' in data:
                            content = json.dumps({"type": data.get("type", "unknown"), "base64": data["base64"], "filePath": data.get("filePath", "")})
                        elif 'cells' in data:
                            content = json.dumps({"type": "notebook", "cells": data["cells"], "filePath": data.get("filePath", "")})

                    # Build metadata excluding reserved fields and nested metadata
                    metadata = {}
                    for k, v in data.items():
                        if k not in ("success", "content", "error", "metadata"):
                            metadata[k] = v

                    return ToolResult(
                        success=success,
                        content=content,
                        error=data.get("error"),
                        metadata=metadata
                    )
                except json.JSONDecodeError:
                    logger.error(f"External tool {self.name} returned invalid JSON")
                    return ToolResult(
                        success=False,
                        content="",
                        error=f"Invalid JSON output: {result.stdout[:200]}"
                    )

            if result.stderr:
                logger.warning(f"External tool {self.name} stderr: {result.stderr[:200]}")
                return ToolResult(
                    success=False,
                    content="",
                    error=result.stderr
                )

            logger.warning(f"External tool {self.name} produced no output")
            return ToolResult(
                success=False,
                content="",
                error="No output from external tool"
            )

        except Exception as e:
            logger.error(f"External tool {self.name} failed: {e}")
            return ToolResult(
                success=False,
                content="",
                error=f"Failed to execute external tool: {e}"
            )

    def get_schema(self) -> Dict[str, Any]:
        return self.schema