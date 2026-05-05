"""Glob tool for finding files by pattern"""

import logging
from pathlib import Path
from typing import Any, Dict, List

from .base import BaseTool, ToolResult
from ..utils.path import resolve_path, get_project_root

logger = logging.getLogger(__name__)


class GlobTool(BaseTool):
    """Tool for finding files by pattern"""

    def __init__(self):
        super().__init__(
            name="glob",
            description="Find files by filename pattern within the project directory."
        )

    def execute(self, pattern: str, path: str = ".", **kwargs) -> ToolResult:
        """
        Find files matching a pattern

        Args:
            pattern: Filename pattern (e.g., '*.py', '*.txt')
            path: Directory path to search in (default: project root)
        """
        logger.info(f"Glob search: pattern='{pattern}', path={path}")
        try:
            results = self._glob(pattern, path)
            if not results:
                logger.debug(f"Glob no matches: pattern='{pattern}'")
                return ToolResult(success=True, content="No files found matching pattern.")
            output = "\n".join(results)
            logger.debug(f"Glob found {len(results)} files for pattern='{pattern}'")
            return ToolResult(success=True, content=output)
        except Exception as e:
            logger.error(f"Glob search failed: {e}")
            return ToolResult(success=False, content="", error=str(e))

    def _glob(self, pattern: str, path: str) -> List[str]:
        """Perform glob search"""
        root = resolve_path(path.lstrip("./"))
        matches = list(root.glob(pattern))
        return [str(m.relative_to(get_project_root())) for m in matches[:50]]

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Filename pattern (e.g., '*.py', '*.txt')"
                },
                "path": {
                    "type": "string",
                    "description": "Directory path to search in (default: project root)",
                    "default": "."
                }
            },
            "required": ["pattern"]
        }