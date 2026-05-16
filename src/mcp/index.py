"""MCP tool index - O(1) tool to client lookup"""

import logging
import threading
from typing import Any, Dict, List, Optional, Tuple

from .base import BaseMCPClient

logger = logging.getLogger(__name__)


class ToolIndex:
    """Fast in-memory index for tool name to client lookup"""

    def __init__(self):
        # Maps tool_name -> (server_name, client, tool_def)
        self._index: Dict[str, Tuple[str, BaseMCPClient, Dict[str, Any]]] = {}
        self._servers: Dict[str, List[str]] = {}  # server_name -> list of tool names
        self._lock = threading.Lock()

    def register(self, server_name: str, client: BaseMCPClient, tools: List[Dict[str, Any]]) -> None:
        """Register tools from a server.

        Supports two tool formats:
        - Raw format: {"name": "...", "description": "...", ...}
        - OpenAI format: {"type": "function", "function": {"name": "...", ...}}
        """
        tool_names = []
        with self._lock:
            for tool in tools:
                # Handle both raw format and OpenAI function-calling format
                tool_name = tool.get("name") or tool.get("function", {}).get("name")
                if not tool_name:
                    logger.warning(f"Tool missing name in {server_name}, skipping")
                    continue
                if tool_name in self._index:
                    prev_server = self._index[tool_name][0]
                    logger.warning(
                        f"ToolIndex: tool '{tool_name}' from '{server_name}' "
                        f"overwrites registration from '{prev_server}'"
                    )
                self._index[tool_name] = (server_name, client, tool)
                tool_names.append(tool_name)
            self._servers[server_name] = tool_names
        logger.debug(f"Registered {len(tool_names)} tools for {server_name}")

    def find(self, tool_name: str) -> Optional[Tuple[str, BaseMCPClient]]:
        """Find client for a tool by name. Returns (server_name, client) or None."""
        with self._lock:
            entry = self._index.get(tool_name)
        if entry:
            return (entry[0], entry[1])  # server_name, client
        logger.debug(f"ToolIndex: tool '{tool_name}' not found in index ({len(self._index)} tools)")
        return None

    def get_all_definitions(self) -> List[Dict[str, Any]]:
        """Get all registered tool definitions"""
        with self._lock:
            return [entry[2] for entry in self._index.values()]