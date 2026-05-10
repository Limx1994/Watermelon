"""MCP (Model Context Protocol) definitions"""

import json
from typing import Any, Dict, List, Optional


class MCPError(Exception):
    """Exception raised by JSON-RPC error responses."""

    def __init__(self, message: str, code: int = -1, data: Any = None):
        self.code = code
        self.message = message
        self.data = data
        super().__init__(f"MCP error [{code}]: {message}")


class MCPProtocol:
    """MCP Protocol implementation using JSON-RPC 2.0"""

    @staticmethod
    def create_request(method: str, params: Optional[Dict[str, Any]] = None, request_id: int = 1) -> Dict[str, Any]:
        """Create a JSON-RPC request with explicit request_id"""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params or {}
        }

    @staticmethod
    def create_response(id: Any, result: Any) -> Dict[str, Any]:
        """Create a JSON-RPC response"""
        return {
            "jsonrpc": "2.0",
            "id": id,
            "result": result
        }

    @staticmethod
    def create_error(id: Any, code: int, message: str, data: Any = None) -> Dict[str, Any]:
        """Create a JSON-RPC error response"""
        error = {
            "jsonrpc": "2.0",
            "id": id,
            "error": {
                "code": code,
                "message": message
            }
        }
        if data is not None:
            error["error"]["data"] = data
        return error

    @staticmethod
    def create_initialize_request(
        protocol_version: str = "2024-11-05",
        client_info: Optional[Dict[str, Any]] = None,
        capabilities: Optional[Dict[str, Any]] = None,
        request_id: int = 1
    ) -> Dict[str, Any]:
        """Create an MCP initialize request"""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "initialize",
            "params": {
                "protocolVersion": protocol_version,
                "capabilities": capabilities or {},
                "clientInfo": client_info or {"name": "AGImyCLI", "version": "1.0.0"}
            }
        }

    @staticmethod
    def create_initialized_notification() -> Dict[str, Any]:
        """Create an MCP initialized notification (no id = JSON-RPC notification)"""
        return {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }

    @staticmethod
    def parse_response_message(line: str) -> Dict[str, Any]:
        """Parse a JSON-RPC response line"""
        return json.loads(line)

    @staticmethod
    def is_notification(msg: Dict[str, Any]) -> bool:
        """Check if a message is a notification (no id field)"""
        return "id" not in msg

    @staticmethod
    def is_error_response(msg: Dict[str, Any]) -> bool:
        """Check if a message is an error response"""
        return "error" in msg

    @staticmethod
    def get_result(msg: Dict[str, Any]) -> Any:
        """Get result from response, raising MCPError if it's an error"""
        if "error" in msg:
            err = msg["error"]
            raise MCPError(
                message=err.get("message", "Unknown error"),
                code=err.get("code", -1),
                data=err.get("data")
            )
        return msg.get("result")

    # Tool-related methods
    TOOL_CALL = "tools/call"
    TOOL_LIST = "tools/list"
    TOOL_DEFINITIONS = "tools/definitions"

    # Lifecycle methods
    INITIALIZE = "initialize"
    NOTIFICATIONS_INITIALIZED = "notifications/initialized"

    # Error codes
    METHOD_NOT_FOUND = -32601
