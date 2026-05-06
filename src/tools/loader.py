"""Loader for external tools defined in tools.json"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, Any, List

from .external import ExternalTool
from .registry import registry

logger = logging.getLogger(__name__)

# 工具名格式验证正则
_TOOL_NAME_RE = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')


def get_project_root() -> Path:
    """Get the project root directory"""
    current = Path(__file__).resolve().parent
    while current != current.parent:
        if (current / "config.json").exists():
            return current
        current = current.parent
    return Path.cwd()


def load_external_tools(tools_json_path: str = None) -> None:
    """Load external tools from tools.json"""
    if tools_json_path is None:
        tools_json_path = get_project_root() / "tools.json"

    path = Path(tools_json_path)
    if not path.exists():
        logger.debug(f"tools.json not found at {path}")
        return

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse tools.json: {e}")
        return

    tools = data.get("tools", [])
    for tool_def in tools:
        func = tool_def.get("function", {})
        command = func.get("command")

        if not command:
            continue

        name = func.get("name")
        description = func.get("description", "")
        schema = func.get("parameters", {})

        if name:
            if not _TOOL_NAME_RE.match(name):
                logger.warning(f"Invalid tool name format: {name}, skipping")
                continue
            external_tool = ExternalTool(
                name=name,
                description=description,
                command=command,
                schema=schema
            )
            registry.register(external_tool)
            logger.debug(f"Loaded external tool: {name}")

    logger.info(f"Loaded {len(tools)} external tools from tools.json")


def get_external_tool_definitions() -> List[Dict[str, Any]]:
    """Get tool definitions for external tools"""
    definitions = []
    for name in registry.list_tools():
        tool = registry.get(name)
        if isinstance(tool, ExternalTool):
            definitions.append(tool.get_definition())
    return definitions