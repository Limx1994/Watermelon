"""MCP client package - factory function and base class.

Note: MCPClient is a factory function alias, not a manager class.
For managing multiple MCP clients with tool indexing and persistence,
use MCPManager from .manager module.
"""

from typing import Any, Dict

from .base import BaseMCPClient
from .stdio_client import StdioMCPClient
from .http_client import HttpMCPClient


def create_mcp_client(server_config: Dict[str, Any]) -> BaseMCPClient:
    """Factory: returns the appropriate MCP client implementation based on type.

    Supported types:
        - "stdio": Generic subprocess-based MCP client (uvx, npx, python -m, etc.)
        - "http": HTTP/REST MCP client for cloud servers (requires url in config)
        - "streamable_http": Streamable HTTP MCP client (SSE compatible)
    """
    server_type = server_config.get("type", "stdio")
    if server_type == "stdio":
        return StdioMCPClient(server_config)
    elif server_type in ("http", "streamable_http"):
        return HttpMCPClient(server_config)
    else:
        raise ValueError(f"Unknown MCP server type: {server_type}")


# Backward compatibility alias
MCPClient = create_mcp_client
