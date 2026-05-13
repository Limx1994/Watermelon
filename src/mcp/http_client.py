"""HTTP MCP client - connects to MCP servers via HTTP/REST API"""

import json
import logging
import threading
import time
from typing import Any, Dict, List, Optional

from .base import BaseMCPClient
from .protocol import MCPProtocol

logger = logging.getLogger(__name__)


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
        self._session_id: Optional[str] = None
        self._next_id: int = 0
        self._id_lock: threading.Lock = threading.Lock()

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

        try:
            import requests as _requests
            self._requests = _requests
        except ImportError:
            logger.error(f"MCP HTTP client '{self.name}': requests library not installed")
            return False

        if not self.url:
            logger.error(f"MCP HTTP client '{self.name}': no URL configured")
            return False

        try:
            # Perform initialize handshake (first request, no session ID)
            request = MCPProtocol.create_initialize_request(
                client_info={"name": "AGImyCLI", "version": "1.0.0"},
                request_id=self._next_request_id()
            )
            result = self._send_request(request, timeout=10, use_session=False)

            # Send initialized notification
            notification = MCPProtocol.create_initialized_notification()
            self._send_notification(notification)

            # Discover tools
            self._discover_tools()

            self._connected = True
            logger.info(f"MCP HTTP client '{self.name}' connected to {self.url}")
            return True
        except Exception as e:
            logger.error(f"MCP HTTP client '{self.name}' connection failed: {e}")
            return False

    def disconnect(self) -> None:
        """Disconnect from the MCP server."""
        logger.info(f"MCP HTTP client '{self.name}' disconnected")
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
            result = self._send_request(
                MCPProtocol.create_request(
                    "tools/call",
                    {"name": tool_name, "arguments": arguments},
                    self._next_request_id()
                ),
                timeout=self.timeout
            )

            # Parse MCP content items
            content_items = result.get("content", [])
            text_parts = []
            for item in content_items:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_parts.append(item.get("text", ""))

            content = "\n".join(text_parts)
            is_error = result.get("isError", False)
            logger.debug(f"MCP HTTP call_tool: {tool_name} -> success={not is_error}, content={len(content)}B")

            return {
                "success": not is_error,
                "content": content,
                "error": content if is_error else None
            }
        except Exception as e:
            logger.error(f"MCP HTTP call_tool '{tool_name}' failed: {e}")
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
        """Send a JSON-RPC request via HTTP POST with retry."""
        if not hasattr(self, '_requests'):
            raise Exception("requests library not installed")

        last_error = None
        for attempt in range(3):
            try:
                headers = dict(self._base_headers)
                if use_session and self._session_id:
                    headers["MCP-Session-Id"] = self._session_id

                response = self._requests.post(
                    self.url,
                    json=request,
                    headers=headers,
                    timeout=timeout
                )

                # Extract session ID from response headers if present
                session_id = response.headers.get("MCP-Session-Id") or response.headers.get("mcp-session-id")
                if session_id and not self._session_id:
                    self._session_id = session_id
                    logger.debug(f"MCP session established: {self._session_id}")

                response.raise_for_status()
                result = response.json()

                if "error" in result:
                    err = result["error"]
                    raise Exception(f"MCP error {err.get('code')}: {err.get('message')}")

                logger.debug(f"HTTP MCP request OK: method={request.get('method')}")
                return result.get("result", {})
            except self._requests.RequestException as e:
                # Don't retry client errors (4xx) - they won't succeed on retry
                if hasattr(e, 'response') and e.response is not None:
                    if 400 <= e.response.status_code < 500:
                        raise Exception(f"MCP client error {e.response.status_code}: {e}")
                wait = min(2 ** attempt, 10)
                logger.warning(f"HTTP MCP request failed (attempt {attempt+1}/3): {e}")
                last_error = e
                if attempt < 2:
                    time.sleep(wait)
        raise Exception(f"HTTP request failed after 3 attempts: {last_error}")

    def _send_notification(self, notification: Dict[str, Any]) -> None:
        """Send a JSON-RPC notification (no response expected)."""
        if not hasattr(self, '_requests'):
            return
        try:
            headers = dict(self._base_headers)
            if self._session_id:
                headers["MCP-Session-Id"] = self._session_id
            self._requests.post(
                self.url,
                json=notification,
                headers=headers,
                timeout=5
            )
        except Exception as e:
            logger.warning(f"MCP HTTP notification failed: {e}")

    def _discover_tools(self) -> None:
        """Discover available tools via tools/list."""
        result = self._send_request(
            MCPProtocol.create_request("tools/list", request_id=self._next_request_id()),
            timeout=10
        )
        self._tools = result.get("tools", [])
        logger.info(f"MCP HTTP discovered {len(self._tools)} tools for '{self.name}'")

    def _next_request_id(self) -> int:
        """Get the next monotonically increasing request ID."""
        with self._id_lock:
            self._next_id += 1
            return self._next_id
