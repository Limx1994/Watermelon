"""Tool registry for managing available tools"""

import logging
import threading
from typing import Dict, List, Optional

from .base import BaseTool

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

    def get(self, name: str) -> Optional[BaseTool]:
        """Get a tool by name"""
        with self._lock:
            return self._tools.get(name)

    def list_tools(self) -> List[str]:
        """List all registered tool names"""
        with self._lock:
            return list(self._tools.keys())

    def clear(self) -> None:
        """Clear all registered tools"""
        with self._lock:
            count = len(self._tools)
            self._tools.clear()
        logger.debug(f"Cleared {count} tools from registry")


# Global registry instance
registry = ToolRegistry()