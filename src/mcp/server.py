"""MCP Server implementation for exposing built-in tools"""

import logging
from typing import Any, Dict, List

from .protocol import MCPProtocol
from ..tools.registry import registry

logger = logging.getLogger(__name__)


class MCPServer:
    """MCP Server that exposes built-in tools"""

    def __init__(self):
        self.protocol = MCPProtocol()

    def list_tools(self) -> List[Dict[str, Any]]:
        """List all tools available on this server"""
        tool_names = registry.list_tools()
        tools = []

        for name in tool_names:
            tool = registry.get(name)
            if tool:
                tools.append({
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.get_schema()
                })

        return tools

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool and return the result"""
        logger.info(f"MCP call_tool: {tool_name}")
        result = registry.execute_tool(tool_name, **arguments)
        return result.to_dict()

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Get tool definitions for LLM function calling"""
        return registry.get_all_definitions()

    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle an MCP request"""
        method = request.get("method")
        req_id = request.get("id")
        params = request.get("params", {})
        logger.debug(f"MCP server handle_request: method={method} id={req_id}")

        if method == self.protocol.TOOL_LIST:
            tools = self.list_tools()
            return self.protocol.create_response(req_id, {"tools": tools})

        elif method == self.protocol.TOOL_CALL:
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            result = self.call_tool(tool_name, arguments)
            return self.protocol.create_response(req_id, result)

        elif method == self.protocol.TOOL_DEFINITIONS:
            definitions = self.get_tool_definitions()
            return self.protocol.create_response(req_id, {"definitions": definitions})

        else:
            logger.warning(f"Unknown method: {method}")
            return self.protocol.create_error(
                req_id,
                self.protocol.METHOD_NOT_FOUND,
                f"Method not found: {method}"
            )