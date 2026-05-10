"""Tool registry for managing available tools"""

import logging
import threading
from typing import Any, Dict, List, Optional

from .base import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Registry for managing and accessing tools"""

    _instance: Optional["ToolRegistry"] = None

    def __new__(cls) -> "ToolRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tools: Dict[str, BaseTool] = {}
            cls._instance._lock = threading.Lock()
        return cls._instance

    def register(self, tool: BaseTool) -> None:
        """Register a tool"""
        with self._lock:
            self._tools[tool.name] = tool
        logger.debug(f"Registered tool: {tool.name}")

    def unregister(self, name: str) -> None:
        """Unregister a tool"""
        with self._lock:
            if name in self._tools:
                del self._tools[name]
        logger.debug(f"Unregistered tool: {name}")

    def get(self, name: str) -> Optional[BaseTool]:
        """Get a tool by name"""
        with self._lock:
            return self._tools.get(name)

    def list_tools(self) -> List[str]:
        """List all registered tool names"""
        with self._lock:
            return list(self._tools.keys())

    def get_all_definitions(self) -> List[Dict[str, Any]]:
        """Get definitions for all registered tools"""
        with self._lock:
            return [tool.get_definition() for tool in self._tools.values()]

    def execute_tool(self, name: str, **kwargs) -> ToolResult:
        """Execute a tool by name"""
        tool = self.get(name)
        if not tool:
            logger.warning(f"[registry] tool not found: {name}")
            return ToolResult(
                success=False,
                content="",
                error=f"Tool '{name}' not found"
            )
        try:
            result = tool.execute(**kwargs)
            logger.info(f"[registry] {name} -> success={result.success} content={len(result.content or '')}B")
            return result
        except Exception as e:
            logger.error(f"[registry] {name} exception: {type(e).__name__}: {e}")
            return ToolResult(
                success=False,
                content="",
                error=str(e)
            )

    def clear(self) -> None:
        """Clear all registered tools"""
        with self._lock:
            count = len(self._tools)
            self._tools.clear()
        logger.debug(f"Cleared {count} tools from registry")


# Global registry instance
registry = ToolRegistry()