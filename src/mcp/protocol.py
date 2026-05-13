"""MCP (Model Context Protocol) definitions"""

from typing import Any, Dict, Optional


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
    def is_notification(msg: Dict[str, Any]) -> bool:
        """Check if a message is a notification (no id field)"""
        return "id" not in msg

    @staticmethod
    def is_error_response(msg: Dict[str, Any]) -> bool:
        """Check if a message is an error response"""
        return "error" in msg

