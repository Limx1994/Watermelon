"""HTTP MCP client - connects to MCP servers via HTTP/REST API"""

import json
import logging
from typing import Any, Dict, List, Optional

import requests

from .base import BaseMCPClient
from .protocol import MCPProtocol


class HttpMCPClient(BaseMCPClient):
    """MCP client that communicates with a server via HTTP/REST API.

    Supports cloud MCP servers via configurable URL endpoint.
    Uses JSON-RPC 2.0 over HTTP POST requests with session support.
    """

    def __init__(self, server_config: Dict[str, Any]):
        super().__init__(server_config)
        self.url: str = server_config.get("url", "")
        self.api_key: str = server_config.get("api_key", "")
        user_headers: Dict[str, str] = server_config.get("headers", {})
        self.timeout: int = server_config.get("timeout", 30)
        self._connected = False
        self._tools: List[Dict[str, Any]] = []
        self._server_info: Dict[str, Any] = {}
        self._session_id: Optional[str] = None
        self._next_id: int = 0

        # Build headers with API key
        self._base_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }
        if self.api_key:
            self._base_headers["Authorization"] = f"Bearer {self.api_key}"
        self._base_headers.update(user_headers)

    def connect(self) -> bool:
        """Connect to the MCP server via HTTP."""
        if self._connected:
            return True

        if not self.url:
            logging.error(f"MCP HTTP client '{self.name}': no URL configured")
            return False

        try:
            # Perform initialize handshake (first request, no session ID)
            request = MCPProtocol.create_initialize_request(
                client_info={"name": "AGImyCLI", "version": "1.0.0"},
                request_id=self._next_request_id()
            )
            result = self._send_request(request, timeout=10, use_session=False)
            self._server_info = result.get("serverInfo", {})

            # Send initialized notification
            notification = MCPProtocol.create_initialized_notification()
            self._send_notification(notification)

            # Discover tools
            self._discover_tools()

            self._connected = True
            logging.info(f"MCP HTTP client '{self.name}' connected to {self.url}")
            return True
        except Exception as e:
            logging.error(f"MCP HTTP client '{self.name}' connection failed: {e}")
            return False

    def disconnect(self) -> None:
        """Disconnect from the MCP server."""
        self._connected = False
        self._session_id = None
        self._tools = []

    def is_connected(self) -> bool:
        """Check if connected to the server."""
        return self._connected

    def list_tools(self) -> List[Dict[str, Any]]:
        """Return cached tools discovered during connect()."""
        return list(self._tools)

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on the MCP server via HTTP."""
        if not self._connected:
            return {
                "success": False,
                "content": "",
                "error": f"MCP client '{self.name}' is not connected"
            }

        try:
            result = self._send_request({
                "jsonrpc": "2.0",
                "id": self._next_request_id(),
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }, timeout=self.timeout)

            # Parse MCP content items
            content_items = result.get("content", [])
            text_parts = []
            for item in content_items:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_parts.append(item.get("text", ""))

            content = "\n".join(text_parts)
            is_error = result.get("isError", False)

            return {
                "success": not is_error,
                "content": content,
                "error": content if is_error else None
            }
        except Exception as e:
            return {
                "success": False,
                "content": "",
                "error": str(e)
            }

    def get_all_tool_definitions(self) -> List[Dict[str, Any]]:
        """Get tool definitions in OpenAI function-calling format."""
        tools = self.list_tools()
        return [
            {
                "type": "function",
                "function": {
                    "name": t.get("name", ""),
                    "description": t.get("description", ""),
                    "parameters": self._ensure_schema(
                        t.get("input_schema") or t.get("inputSchema")
                    )
                }
            }
            for t in tools
        ]

    def _send_request(self, request: Dict[str, Any], timeout: int, use_session: bool = True) -> Any:
        """Send a JSON-RPC request via HTTP POST."""
        try:
            headers = dict(self._base_headers)
            if use_session and self._session_id:
                headers["MCP-Session-Id"] = self._session_id

            response = requests.post(
                self.url,
                json=request,
                headers=headers,
                timeout=timeout
            )

            # Extract session ID from response headers if present
            session_id = response.headers.get("MCP-Session-Id") or response.headers.get("mcp-session-id")
            if session_id and not self._session_id:
                self._session_id = session_id
                logging.debug(f"MCP session established: {self._session_id}")

            response.raise_for_status()
            result = response.json()

            if "error" in result:
                err = result["error"]
                raise Exception(f"MCP error {err.get('code')}: {err.get('message')}")

            return result.get("result", {})
        except requests.RequestException as e:
            raise Exception(f"HTTP request failed: {e}")

    def _send_notification(self, notification: Dict[str, Any]) -> None:
        """Send a JSON-RPC notification (no response expected)."""
        try:
            headers = dict(self._base_headers)
            if self._session_id:
                headers["MCP-Session-Id"] = self._session_id
            requests.post(
                self.url,
                json=notification,
                headers=headers,
                timeout=5
            )
        except Exception:
            pass  # Notifications don't expect responses

    def _discover_tools(self) -> None:
        """Discover available tools via tools/list."""
        result = self._send_request({
            "jsonrpc": "2.0",
            "id": self._next_request_id(),
            "method": "tools/list",
            "params": {}
        }, timeout=10)
        self._tools = result.get("tools", [])

    def _next_request_id(self) -> int:
        """Get the next monotonically increasing request ID."""
        self._next_id += 1
        return self._next_id
