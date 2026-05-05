"""MCP data persistence - handles mcpdata/ directory operations"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..utils.path import get_project_root, ensure_directory


class MCPDataStore:
    """Handles persistence of MCP server data in mcpdata/ directory"""

    def __init__(self, mcpdata_dir: str = "mcpdata"):
        self.mcpdata_path = get_project_root() / mcpdata_dir
        ensure_directory(str(mcpdata_dir))
        self._errors_log = self.mcpdata_path / "errors.log"

    def _server_file(self, server_name: str, suffix: str) -> Path:
        """Get path for a server's data file"""
        # Sanitize server name for filesystem safety
        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in server_name)
        return self.mcpdata_path / f"{safe_name}_{suffix}"

    # Tool definitions persistence
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
            logging.debug(f"Saved {len(tools)} tools for {server_name}")
        except Exception as e:
            logging.warning(f"Failed to save tools for {server_name}: {e}")

    def load_tools(self, server_name: str) -> Optional[List[Dict[str, Any]]]:
        """Load cached tool definitions"""
        try:
            path = self._server_file(server_name, "tools.json")
            if not path.exists():
                return None
            data = json.loads(path.read_text(encoding="utf-8"))
            return data.get("tools")
        except Exception as e:
            logging.warning(f"Failed to load tools for {server_name}: {e}")
            return None

    # Status persistence
    def save_status(self, server_name: str, status: Dict[str, Any]) -> None:
        """Save server connection status"""
        try:
            path = self._server_file(server_name, "status.json")
            # Always include server_name and timestamp
            full_status = {
                "server_name": server_name,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                **status
            }
            path.write_text(json.dumps(full_status, indent=2, ensure_ascii=False), encoding="utf-8")
            logging.debug(f"Saved status for {server_name}")
        except Exception as e:
            logging.warning(f"Failed to save status for {server_name}: {e}")

    def load_status(self, server_name: str) -> Optional[Dict[str, Any]]:
        """Load cached server status"""
        try:
            path = self._server_file(server_name, "status.json")
            if not path.exists():
                return None
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            logging.warning(f"Failed to load status for {server_name}: {e}")
            return None

    def get_all_servers_status(self) -> Dict[str, Dict[str, Any]]:
        """Load status for all servers from cache"""
        result = {}
        if not self.mcpdata_path.exists():
            return result
        for path in self.mcpdata_path.glob("*_status.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                server_name = data.get("server_name", path.stem.replace("_status", ""))
                result[server_name] = data
            except Exception:
                continue
        return result

    # Error logging
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
        except Exception as e:
            logging.warning(f"Failed to append error log: {e}")

    def get_errors(self, server_name: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent errors, optionally filtered by server"""
        if not self._errors_log.exists():
            return []
        try:
            lines = self._errors_log.read_text(encoding="utf-8").strip().split("\n")
            errors = []
            for line in reversed(lines):
                if not line.strip():
                    continue
                try:
                    entry = json.loads(line)
                    if server_name is None or entry.get("server") == server_name:
                        errors.append(entry)
                        if len(errors) >= limit:
                            break
                except json.JSONDecodeError:
                    continue
            return list(reversed(errors))
        except Exception:
            return []

    def clear_server_data(self, server_name: str) -> None:
        """Clear all cached data for a server"""
        for suffix in ["tools.json", "status.json"]:
            path = self._server_file(server_name, suffix)
            try:
                if path.exists():
                    path.unlink()
            except Exception as e:
                logging.warning(f"Failed to delete {path}: {e}")