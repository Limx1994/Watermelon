"""Abstract base class for MCP clients"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseMCPClient(ABC):
    """Abstract base class defining the contract for all MCP clients."""

    def __init__(self, server_config: Dict[str, Any]):
        self.name: str = server_config.get("name", "unknown")
        self.config: Dict[str, Any] = server_config

    @staticmethod
    def _ensure_schema(schema: Any) -> Dict[str, Any]:
        """Ensure a schema dict has type: object and required fields (LLM API requirement).

        Some MCP servers return empty or minimal schemas, but OpenAI-compatible
        APIs require parameters to be a valid JSON Schema with type: 'object'.
        If the schema is missing properties or required, preserve what was provided
        since it may contain useful information from the MCP server.
        """
        if not isinstance(schema, dict):
            return {"type": "object", "properties": {}}
        if schema.get("type") != "object":
            return {"type": "object", "properties": {}}
        # Return as-is - preserve any properties, required, etc. from MCP server
        return schema

    @abstractmethod
    def connect(self) -> bool:
        """Connect to the MCP server. Returns True on success."""
        ...

    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect from the MCP server."""
        ...

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if currently connected to the MCP server."""
        ...

    @abstractmethod
    def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools from the MCP server."""
        ...

    @abstractmethod
    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on the MCP server.

        Must return dict with keys: success (bool), content (str), error (Optional[str])
        """
        ...

    @abstractmethod
    def get_all_tool_definitions(self) -> List[Dict[str, Any]]:
        """Get all tool definitions in OpenAI function-calling format."""
        ...
