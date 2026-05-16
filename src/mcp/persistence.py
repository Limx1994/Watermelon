"""MCP data persistence - handles mcpdata/ directory operations"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from ..utils.path import get_project_root, ensure_directory

logger = logging.getLogger(__name__)


class MCPDataStore:
    """Handles persistence of MCP server data in mcpdata/ directory"""

    def __init__(self, mcpdata_dir: str = "data/mcpdata"):
        self.mcpdata_path = get_project_root() / mcpdata_dir
        ensure_directory(str(self.mcpdata_path))
        self._errors_log = self.mcpdata_path / "errors.log"

    def _server_file(self, server_name: str, suffix: str) -> Path:
        """Get path for a server's data file"""
        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in server_name)
        return self.mcpdata_path / f"{safe_name}_{suffix}"

    def save_tools(self, server_name: str, tools: List[Dict[str, Any]]) -> None:
        """Save tool definitions to cache file"""
        try:
            path = self._server_file(server_name, "tools.json")
            data = {
                "server_name": server_name,
                "saved_at": datetime.now(timezone.utc).isoformat(),
                "tools": tools
            }
            path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            logger.debug(f"Saved {len(tools)} tools for {server_name}")
        except Exception as e:
            logger.warning(f"Failed to save tools for {server_name}: {e}")

    def save_status(self, server_name: str, status: Dict[str, Any]) -> None:
        """Save server connection status"""
        try:
            path = self._server_file(server_name, "status.json")
            full_status = {
                "server_name": server_name,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                **status
            }
            path.write_text(json.dumps(full_status, indent=2, ensure_ascii=False), encoding="utf-8")
            logger.debug(f"Saved status for {server_name}")
        except Exception as e:
            logger.warning(f"Failed to save status for {server_name}: {e}")

    def append_error(self, server_name: str, error: Dict[str, Any]) -> None:
        """Append an error to the errors log"""
        try:
            timestamp = datetime.now(timezone.utc).isoformat()
            log_entry = {
                "timestamp": timestamp,
                "server": server_name,
                **error
            }
            with open(self._errors_log, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
            logger.error(f"Error logged for {server_name}: {error.get('message', str(error)[:100])}")
        except Exception as e:
            logger.warning(f"Failed to append error log: {e}")