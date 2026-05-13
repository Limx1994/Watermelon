"""Base class for all tools"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


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
        self.content = content or ""
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

    def validate_args(self, args: Dict[str, Any]) -> List[str]:
        """Validate arguments against the tool's schema.

        Returns a list of error messages (empty = valid).
        Only checks required fields and basic type matching.
        """
        schema = self.get_schema()
        if not schema or schema.get("type") != "object":
            return []

        errors: List[str] = []
        properties = schema.get("properties", {})
        required = schema.get("required", [])

        # Check required fields
        for field in required:
            if field not in args:
                errors.append(f"Missing required parameter: {field}")

        # Basic type checking
        type_map = {"string": str, "number": (int, float), "integer": int, "boolean": bool, "array": list, "object": dict}
        for field, value in args.items():
            if field in properties:
                expected_type = properties[field].get("type")
                if expected_type and expected_type in type_map:
                    py_type = type_map[expected_type]
                    if not isinstance(value, py_type):
                        errors.append(f"Parameter '{field}' should be {expected_type}, got {type(value).__name__}")

        if errors:
            logger.warning(f"Validation failed for {self.name}: {'; '.join(errors)}")
        return errors