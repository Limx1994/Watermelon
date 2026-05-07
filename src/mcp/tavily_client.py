"""Tavily MCP client - direct SDK connection (no subprocess)"""

from typing import Any, Dict, List

from .base import BaseMCPClient


class TavilyMCPClient(BaseMCPClient):
    """MCP client for Tavily web search via direct SDK calls."""

    def __init__(self, server_config: Dict[str, Any]):
        super().__init__(server_config)
        self.server_type = server_config.get("type", "tavily")
        self.api_key = server_config.get("api_key", "")
        self._connected = False
        self._client = None

    def connect(self) -> bool:
        """Connect to the Tavily MCP server"""
        try:
            if self.server_type == "tavily":
                from tavily import TavilyClient
                self._client = TavilyClient(api_key=self.api_key)
                self._connected = True
                return True
            return False
        except ImportError:
            self._connected = False
            return False
        except Exception:
            return False

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

        if self.server_type == "tavily":
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

        return []

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on the Tavily MCP server"""
        if not self._connected:
            return {
                "success": False,
                "content": "",
                "error": f"Client {self.name} not connected"
            }

        if self.server_type == "tavily":
            return self._call_tavily(tool_name, arguments)

        return {
            "success": False,
            "content": "",
            "error": f"Unknown tool: {tool_name}"
        }

    def _call_tavily(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call Tavily tool"""
        if tool_name == "tavily_search":
            return self._tavily_search(
                query=arguments.get("query", ""),
                max_results=arguments.get("max_results", 5)
            )

        return {
            "success": False,
            "content": "",
            "error": f"Unknown Tavily tool: {tool_name}"
        }

    def _tavily_search(self, query: str, max_results: int) -> Dict[str, Any]:
        """Perform Tavily search"""
        try:
            if self._client is None:
                from tavily import TavilyClient
                self._client = TavilyClient(api_key=self.api_key)
            results = self._client.search(query=query, max_results=max_results)

            # Format results
            formatted = []
            for r in results.get("results", []):
                formatted.append(f"Title: {r.get('title', 'N/A')}\nURL: {r.get('url', 'N/A')}\nContent: {r.get('content', 'N/A')[:200]}...")

            content = "\n\n".join(formatted)
            return {
                "success": True,
                "content": content,
                "error": None
            }
        except ImportError:
            return {
                "success": False,
                "content": "",
                "error": "Tavily client not installed. Run: pip install tavily-python"
            }
        except Exception as e:
            return {
                "success": False,
                "content": "",
                "error": str(e)
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
