"""Grep tool for searching file contents"""

import logging
import re
from pathlib import Path
from typing import Any, Dict, List

from .base import BaseTool, ToolResult
from ..utils.path import resolve_path, get_project_root

logger = logging.getLogger(__name__)


class GrepTool(BaseTool):
    """Tool for searching text in files"""

    def __init__(self):
        super().__init__(
            name="grep",
            description="Search for text patterns in files within the project directory."
        )

    def execute(self, pattern: str, path: str = ".", recursive: bool = True, **kwargs) -> ToolResult:
        """
        Search for a pattern in files

        Args:
            pattern: The text pattern to search for
            path: Directory path to search in (default: project root)
            recursive: Whether to search recursively
        """
        logger.info(f"Grep search: pattern='{pattern}', path={path}, recursive={recursive}")
        try:
            results = self._grep(pattern, path, recursive)
            if not results:
                logger.debug(f"Grep no matches: pattern='{pattern}'")
                return ToolResult(success=True, content="No matches found.")
            output = "\n".join(results)
            logger.debug(f"Grep found {len(results)} matches for pattern='{pattern}'")
            return ToolResult(success=True, content=output)
        except Exception as e:
            logger.error(f"Grep search failed: {e}")
            return ToolResult(success=False, content="", error=str(e))

    def _grep(self, pattern: str, path: str, recursive: bool) -> List[str]:
        """Perform grep search"""
        root = resolve_path(path.lstrip("./"))
        results = []

        if recursive:
            files = root.rglob("*")
        else:
            files = root.glob("*")

        for file in files:
            if file.is_file() and self._should_search(file):
                try:
                    content = file.read_text(encoding="utf-8", errors="ignore")
                    for i, line in enumerate(content.splitlines(), 1):
                        if re.search(pattern, line, re.IGNORECASE):
                            results.append(f"{file}:{i}: {line.rstrip()}")
                except Exception:
                    continue

        return results[:100]  # Limit results

    def _should_search(self, file: Path) -> bool:
        """Check if file should be searched"""
        skip_dirs = {".git", "__pycache__", "node_modules", ".venv", "venv"}
        skip_extensions = {".pyc", ".exe", ".dll", ".so", ".bin"}

        if any(part in skip_dirs for part in file.parts):
            return False
        if file.suffix in skip_extensions:
            return False
        return True

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "The text pattern to search for"
                },
                "path": {
                    "type": "string",
                    "description": "Directory path to search in (default: project root)"
                },
                "recursive": {
                    "type": "boolean",
                    "description": "Whether to search recursively",
                    "default": True
                }
            },
            "required": ["pattern"]
        }