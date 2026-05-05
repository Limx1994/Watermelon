"""Base class for all tools"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class ToolResult:
    """Result returned by a tool execution"""

    def __init__(
        self,
        success: bool,
        content: str,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.success = success
        self.content = content
        self.error = error
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "content": self.content,
            "error": self.error,
            "metadata": self.metadata
        }

    def __str__(self) -> str:
        if self.success:
            return self.content
        return f"Error: {self.error}\n{self.content}"


class BaseTool(ABC):
    """Abstract base class for all tools"""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with given arguments"""
        pass

    @abstractmethod
    def get_schema(self) -> Dict[str, Any]:
        """Get the JSON schema for this tool's parameters"""
        pass

    def get_definition(self) -> Dict[str, Any]:
        """Get the full tool definition for LLM function calling"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.get_schema()
            }
        }