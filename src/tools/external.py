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
            # Use executable path directly (never shlex.split it — breaks paths with spaces)
            cmd_parts = [cmd_str]
            for key, value in kwargs.items():
                # Convert underscores to hyphens for CLI args
                arg_name = f"--{key.replace('_', '-')}"
                # Handle boolean flags: True = pass flag only, False = skip
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
                    # 统一以秒为单位，加 10 秒缓冲
                    _sub_timeout = max(10, _timeout_val + 10)
                except (ValueError, TypeError):
                    _sub_timeout = 70
            else:
                _sub_timeout = 70
            result = subprocess.run(
                cmd_parts,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=str(self._project_root),
                timeout=_sub_timeout
            )
            elapsed = time.monotonic() - t0
            _stdout = result.stdout or ""
            _stderr = result.stderr or ""
            logger.debug(f"[tool:{self.name}] exit={result.returncode} | {elapsed:.2f}s | stdout={len(_stdout)}B stderr={len(_stderr)}B")

            if result.stdout:
                try:
                    data = json.loads(result.stdout)
                    success = data.get("success")
                    if success is None:
                        # 兼容旧版输出：无 success 字段时根据 exit code 推断
                        success = result.returncode == 0

                    # 对于 winshell 类工具：检查 stderr 字段，非空则视为错误
                    stderr_content = data.get("stderr", "")
                    if stderr_content and success:
                        # stderr 有内容但 success=true — 修正为失败
                        success = False
                        logger.warning(f"[tool:{self.name}] stderr detected | stderr={stderr_content[:300]}")

                    if not success:
                        logger.warning(f"[tool:{self.name}] success=false | error={data.get('error', '')[:300]} stderr={stderr_content[:300]}")

                    # Extract content - for read_file, content is the primary field
                    # but for image/pdf/notebook, data may be in other fields
                    content = data.get("content") or ""
                    if not content:
                        # For image/pdf/notebook, serialize the relevant data
                        if 'base64' in data:
                            content = json.dumps({"type": data.get("type", "unknown"), "base64": data["base64"], "filePath": data.get("filePath", "")})
                        elif 'cells' in data:
                            content = json.dumps({"type": "notebook", "cells": data["cells"], "filePath": data.get("filePath", "")})
                        elif 'stdout' in data:
                            content = data['stdout'] or ""

                    content = content.replace('\r', '')

                    # 错误信息优先级：error > stderr
                    error_msg = data.get("error") or (stderr_content if stderr_content else None)

                    # Build metadata excluding reserved fields and nested metadata
                    metadata = {}
                    for k, v in data.items():
                        if k not in ("success", "content", "error", "metadata"):
                            metadata[k] = v

                    # 确保 returnCode 在 metadata 中（对 shell 工具有用）
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
                    logger.error(f"[tool:{self.name}] invalid JSON | stdout={result.stdout[:300]}")
                    return ToolResult(
                        success=False,
                        content="",
                        error=f"Invalid JSON output: {result.stdout[:200]}"
                    )

            if result.stderr:
                logger.warning(f"[tool:{self.name}] stderr={result.stderr[:500]}")
                return ToolResult(
                    success=False,
                    content="",
                    error=result.stderr
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