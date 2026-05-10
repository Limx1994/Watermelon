"""MCP client manager - orchestrates all MCP clients"""

import logging
import threading
from typing import Any, Dict, List, Optional

from .base import BaseMCPClient
from .client import create_mcp_client
from .persistence import MCPDataStore
from .index import ToolIndex

logger = logging.getLogger(__name__)


class MCPManager:
    """Manages all MCP clients with tool indexing and persistence"""

    def __init__(self, config_enabled: bool, server_configs: List[Dict[str, Any]]):
        self.config_enabled = config_enabled
        self.server_configs = server_configs
        self._clients: Dict[str, BaseMCPClient] = {}
        self._index = ToolIndex()
        self._datastore = MCPDataStore()
        self._connected = False
        self._lock = threading.Lock()

    @property
    def is_connected(self) -> bool:
        return self._connected

    def connect_all(self) -> bool:
        """Connect to all configured MCP servers"""
        if not self.config_enabled:
            logger.info("MCP is disabled in configuration")
            return False

        success_count = 0
        for server_config in self.server_configs:
            server_name = server_config.get("name", "unnamed")
            try:
                client = create_mcp_client(server_config)
                if client.connect():
                    self._clients[server_name] = client
                    # Get and register tools
                    tools = client.get_all_tool_definitions()
                    self._index.register(server_name, client, tools)
                    # Persist tools and status
                    self._datastore.save_tools(server_name, tools)
                    self._datastore.save_status(server_name, {
                        "connected": True,
                        "connected_at": None,  # Will be set by datastore
                    })
                    success_count += 1
                    logger.info(f"Connected to MCP server: {server_name}")
                else:
                    logger.warning(f"Failed to connect to MCP server: {server_name}")
                    self._datastore.save_status(server_name, {"connected": False})
                    self._datastore.append_error(server_name, {
                        "error": "connection_failed",
                        "message": f"Failed to connect to {server_name}"
                    })
            except Exception as e:
                logger.error(f"Error connecting to {server_name}: {e}")
                self._datastore.append_error(server_name, {
                    "error": "connection_exception",
                    "message": str(e)
                })

        self._connected = success_count > 0
        total = len(self.server_configs)
        logger.info(f"MCP connect_all: {success_count}/{total} servers connected")
        return self._connected

    def disconnect_all(self) -> None:
        """Disconnect all MCP clients"""
        for server_name, client in self._clients.items():
            try:
                client.disconnect()
                logger.info(f"Disconnected from MCP server: {server_name}")
            except Exception as e:
                logger.warning(f"Error disconnecting {server_name}: {e}")
        self._clients.clear()
        self._index.clear()
        self._connected = False

    def get_client(self, name: str) -> Optional[BaseMCPClient]:
        """Get a connected client by server name"""
        return self._clients.get(name)

    def get_all_tool_definitions(self) -> List[Dict[str, Any]]:
        """Get all registered tool definitions from all clients"""
        return self._index.get_all_definitions()

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool by name, delegating to the appropriate client"""
        result = self._index.find(tool_name)
        if not result:
            return {
                "success": False,
                "content": "",
                "error": f"Tool '{tool_name}' not found"
            }

        if not isinstance(arguments, dict):
            return {
                "success": False,
                "content": "",
                "error": f"Invalid arguments type: {type(arguments).__name__}"
            }

        server_name, client = result
        try:
            logger.debug(f"MCP call_tool: {tool_name} -> server={server_name}")
            return client.call_tool(tool_name, arguments)
        except Exception as e:
            logger.error(f"Tool call failed for {tool_name}: {e}")
            self._datastore.append_error(server_name, {
                "error": "tool_call_failed",
                "tool": tool_name,
                "message": str(e)
            })
            return {
                "success": False,
                "content": "",
                "error": str(e)
            }

    def reload(self) -> None:
        """Reload configuration and reconnect"""
        self.disconnect_all()
        self.connect_all()