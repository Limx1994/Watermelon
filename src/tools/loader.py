"""Loader for external tools defined in tools.json"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, Any, List

from .external import ExternalTool
from .registry import registry
from ..utils.path import get_project_root

logger = logging.getLogger(__name__)

# 工具名格式验证正则
_TOOL_NAME_RE = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')


def load_external_tools(tools_json_path: str = None) -> None:
    """Load external tools from tools.json"""
    if tools_json_path is None:
        tools_json_path = get_project_root() / "config" / "tools.json"

    path = Path(tools_json_path)
    if not path.exists():
        logger.warning(f"tools.json not found at {path}")
        return

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse tools.json: {e}")
        return

    tools = data.get("tools", [])
    loaded = []
    skipped = []
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
                skipped.append(name)
                continue
            external_tool = ExternalTool(
                name=name,
                description=description,
                command=command,
                schema=schema
            )
            registry.register(external_tool)
            loaded.append(name)

    logger.info(f"[loader] loaded={loaded} skipped={skipped}")