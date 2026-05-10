"""Tavily MCP client - HTTP/Streamable HTTP connection via MCP protocol"""

import logging
from typing import Any, Dict, List

from .base import BaseMCPClient

logger = logging.getLogger(__name__)


class TavilyMCPClient(BaseMCPClient):
    """MCP client for Tavily web search via HTTP MCP endpoint."""

    def __init__(self, server_config: Dict[str, Any]):
        super().__init__(server_config)
        self._connected = False

    def connect(self) -> bool:
        """Connect to the Tavily MCP server"""
        self._connected = True
        logger.info("Tavily MCP client ready")
        return True

    def disconnect(self) -> None:
        """Disconnect from the Tavily MCP server"""
        self._connected = False

    def is_connected(self) -> bool:
        """Check if connected to the server"""
        return self._connected

    def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools from the Tavily MCP server"""
        if not self._connected:
            return []

        return [
            {
                "name": "tavily_search",
                "description": "Search the web using Tavily. Use this when you need to find current information or answer questions about recent events.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query"
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of results",
                            "default": 5
                        }
                    },
                    "required": ["query"]
                }
            }
        ]

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on the Tavily MCP server"""
        logger.info(f"Tavily call_tool: {tool_name}")
        if not self._connected:
            return {
                "success": False,
                "content": "",
                "error": f"Client {self.name} not connected"
            }

        if tool_name == "tavily_search":
            return self._tavily_search(arguments)

        logger.warning(f"Tavily unknown tool: {tool_name}")
        return {
            "success": False,
            "content": "",
            "error": f"Unknown tool: {tool_name}"
        }

    def _tavily_search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Placeholder - actual search handled by MCP HTTP endpoint"""
        return {
            "success": False,
            "content": "",
            "error": "Tavily search should be routed through HTTP MCP protocol"
        }

    def get_all_tool_definitions(self) -> List[Dict[str, Any]]:
        """Get all tool definitions for LLM function calling"""
        tools = self.list_tools()
        return [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": self._ensure_schema(t.get("input_schema"))
                }
            }
            for t in tools
        ]
