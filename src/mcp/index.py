"""MCP tool index - O(1) tool to client lookup"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from .base import BaseMCPClient


class ToolIndex:
    """Fast in-memory index for tool name to client lookup"""

    def __init__(self):
        # Maps tool_name -> (server_name, client, tool_def)
        self._index: Dict[str, Tuple[str, BaseMCPClient, Dict[str, Any]]] = {}
        self._servers: Dict[str, List[str]] = {}  # server_name -> list of tool names

    def register(self, server_name: str, client: BaseMCPClient, tools: List[Dict[str, Any]]) -> None:
        """Register tools from a server.

        Supports two tool formats:
        - Raw format: {"name": "...", "description": "...", ...}
        - OpenAI format: {"type": "function", "function": {"name": "...", ...}}
        """
        tool_names = []
        for tool in tools:
            # Handle both raw format and OpenAI function-calling format
            tool_name = tool.get("name") or tool.get("function", {}).get("name")
            if not tool_name:
                logging.warning(f"Tool missing name in {server_name}, skipping")
                continue
            self._index[tool_name] = (server_name, client, tool)
            tool_names.append(tool_name)
        self._servers[server_name] = tool_names
        logging.debug(f"Registered {len(tool_names)} tools for {server_name}")

    def unregister(self, server_name: str) -> None:
        """Unregister all tools from a server"""
        tool_names = self._servers.pop(server_name, [])
        for name in tool_names:
            self._index.pop(name, None)
        logging.debug(f"Unregistered {len(tool_names)} tools for {server_name}")

    def find(self, tool_name: str) -> Optional[Tuple[str, BaseMCPClient]]:
        """Find client for a tool by name. Returns (server_name, client) or None."""
        entry = self._index.get(tool_name)
        if entry:
            return (entry[0], entry[1])  # server_name, client
        return None

    def get_tool_def(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get full tool definition by name"""
        entry = self._index.get(tool_name)
        return entry[2] if entry else None

    def get_all_definitions(self) -> List[Dict[str, Any]]:
        """Get all registered tool definitions"""
        return [entry[2] for entry in self._index.values()]

    def has_tool(self, tool_name: str) -> bool:
        """Check if a tool is registered"""
        return tool_name in self._index

    def get_server_tools(self, server_name: str) -> List[str]:
        """Get all tool names registered by a server"""
        return self._servers.get(server_name, [])

    def clear(self) -> None:
        """Clear all registrations"""
        self._index.clear()
        self._servers.clear()