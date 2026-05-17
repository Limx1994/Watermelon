"""External tool executor for CLI programs"""

import json
import logging
import subprocess
import time
from pathlib import Path
from typing import Any, Dict

from .base import BaseTool, ToolResult
from ..utils.path import get_project_root

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
        self._project_root = get_project_root()

    def _is_absolute_path(self, path: str) -> bool:
        """Check if path is absolute (Windows: C:\\, UNC; Unix: /)"""
        if not path:
            return False
        try:
            return Path(path).is_absolute()
        except (ValueError, OSError):
            return False

    def execute(self, **kwargs) -> ToolResult:
        """Execute the external CLI program"""
        logger.debug(f"[tool:{self.name}] start | args={list(kwargs.keys())}")
        try:
            # Determine if command is relative or absolute
            cmd_str = self.command
            if not self._is_absolute_path(cmd_str):
                # Relative path: join with project root
                cmd_str = str(self._project_root / cmd_str)

            logger.debug(f"[tool:{self.name}] exe={cmd_str}")

            # Build command with arguments
            cmd_parts = [cmd_str]
            for key, value in kwargs.items():
                arg_name = f"--{key.replace('_', '-')}"
                if isinstance(value, bool):
                    if value:
                        cmd_parts.append(arg_name)
                else:
                    cmd_parts.extend([arg_name, str(value)])

            logger.debug(f"[tool:{self.name}] cmd_parts={cmd_parts}")
            t0 = time.monotonic()
            _user_timeout = kwargs.get("timeout")
            if _user_timeout is not None:
                try:
                    _timeout_val = int(_user_timeout)
                    _sub_timeout = max(10, _timeout_val + 10)
                except (ValueError, TypeError):
                    _sub_timeout = 70
            else:
                _sub_timeout = 70

            proc = None
            try:
                creation_flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
                proc = subprocess.Popen(
                    cmd_parts,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    cwd=str(self._project_root),
                    creationflags=creation_flags,
                )
                stdout, stderr = proc.communicate(timeout=_sub_timeout)
            except subprocess.TimeoutExpired:
                if proc:
                    proc.kill()
                    proc.wait()
                logger.warning(f"[tool:{self.name}] timed out after {_sub_timeout}s")
                return ToolResult(
                    success=False, content="",
                    error=f"Tool execution timed out ({_sub_timeout}s)"
                )
            except KeyboardInterrupt:
                if proc:
                    proc.kill()
                    proc.wait()
                raise

            elapsed = time.monotonic() - t0
            _stdout = stdout or ""
            _stderr = stderr or ""
            result_code = proc.returncode
            logger.debug(f"[tool:{self.name}] exit={result_code} | {elapsed:.2f}s | stdout={len(_stdout)}B stderr={len(_stderr)}B")

            if _stdout:
                try:
                    data = json.loads(_stdout)
                    success = data.get("success")
                    if success is None:
                        success = result_code == 0

                    stderr_content = data.get("stderr", "")
                    if stderr_content and success:
                        success = False
                        logger.warning(f"[tool:{self.name}] stderr detected | stderr={stderr_content[:300]}")

                    if not success:
                        logger.warning(f"[tool:{self.name}] success=false | error={data.get('error', '')[:300]} stderr={stderr_content[:300]}")

                    content = data.get("content") or ""
                    if not content:
                        if 'base64' in data:
                            content = json.dumps({"type": data.get("type", "unknown"), "base64": data["base64"], "filePath": data.get("filePath", "")})
                        elif 'cells' in data:
                            content = json.dumps({"type": "notebook", "cells": data["cells"], "filePath": data.get("filePath", "")})
                        elif 'stdout' in data:
                            content = data['stdout'] or ""

                    content = content.replace('\r', '')
                    error_msg = data.get("error") or (stderr_content if stderr_content else None)

                    metadata = {}
                    for k, v in data.items():
                        if k not in ("success", "content", "error", "metadata"):
                            metadata[k] = v
                    if "returnCode" in data and "returnCode" not in metadata:
                        metadata["returnCode"] = data["returnCode"]

                    logger.debug(f"[tool:{self.name}] ok | content={len(content)}B"
                                f"{' error=' + error_msg[:100] if error_msg else ''}")
                    return ToolResult(
                        success=success,
                        content=content,
                        error=error_msg,
                        metadata=metadata
                    )
                except json.JSONDecodeError:
                    logger.error(f"[tool:{self.name}] invalid JSON | stdout={_stdout[:300]}")
                    return ToolResult(
                        success=False,
                        content="",
                        error=f"Invalid JSON output: {_stdout[:200]}"
                    )

            if _stderr:
                logger.warning(f"[tool:{self.name}] stderr={_stderr[:500]}")
                return ToolResult(
                    success=False,
                    content="",
                    error=_stderr
                )

            logger.warning(f"[tool:{self.name}] no output")
            return ToolResult(
                success=False,
                content="",
                error="No output from external tool"
            )

        except Exception as e:
            logger.error(f"[tool:{self.name}] exception: {type(e).__name__}: {e}")
            return ToolResult(
                success=False,
                content="",
                error=f"Failed to execute external tool: {e}"
            )

    def get_schema(self) -> Dict[str, Any]:
        return self.schema