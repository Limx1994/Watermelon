"""Memory management for conversation history and summarization"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .utils.path import resolve_path, get_project_root
from .config import config

logger = logging.getLogger(__name__)


class Memory:
    """
    Manages conversation memory with automatic summarization.

    Design:
    - Current session is kept in memory only (not persisted to disk between sessions)
    - History is saved to separate files in memory/history/ folder
    - Each history file represents a completed session
    - On startup, memory starts fresh (no auto-load of history)
    """

    _instance: Optional["Memory"] = None

    def __new__(cls) -> "Memory":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self) -> None:
        """Initialize memory - starts fresh, no historical loading"""
        self._history: List[Dict[str, Any]] = []
        self._last_updated: Optional[str] = None
        self._session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._history_dir = get_project_root() / "memory" / "history"

    def save_current_session(self) -> str:
        """
        Save current session to history folder.
        Called when user ends a session or at session boundary.
        Returns the path to the saved file.
        """
        if not self._history:
            return ""

        try:
            self._history_dir.mkdir(parents=True, exist_ok=True)
            filename = f"session_{self._session_id}.json"
            filepath = self._history_dir / filename

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump({
                    "session_id": self._session_id,
                    "history": self._history,
                    "saved_at": datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)

            logger.info(f"Saved session {self._session_id} to {filename} ({len(self._history)} messages)")
            return str(filepath)
        except Exception as e:
            logger.error(f"Failed to save session: {e}")
            return ""

    def load_session(self, session_path: str) -> bool:
        """
        Load a specific session from history.
        Returns True if successful.
        """
        logger.debug(f"Loading session from {session_path}")
        try:
            path = Path(session_path)
            if not path.exists():
                logger.warning(f"Session file not found: {session_path}")
                return False

            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._history = data.get("history", [])
                self._session_id = data.get("session_id", self._session_id)
                self._last_updated = data.get("saved_at")
            logger.info(f"Loaded session {self._session_id} ({len(self._history)} messages)")
            return True
        except Exception as e:
            logger.error(f"Failed to load session: {e}")
            return False

    def list_sessions(self) -> List[Dict[str, str]]:
        """
        List all saved sessions in history folder.
        Returns list of dicts with session_id, filename, and saved_at.
        """
        sessions = []
        try:
            self._history_dir.mkdir(parents=True, exist_ok=True)
            for filepath in sorted(self._history_dir.glob("session_*.json"), reverse=True):
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    sessions.append({
                        "session_id": data.get("session_id", filepath.stem),
                        "filename": filepath.name,
                        "saved_at": data.get("saved_at", ""),
                        "message_count": len(data.get("history", []))
                    })
                except Exception:
                    continue
        except Exception:
            pass
        return sessions

    def add_message(self, role: str, content: str, tool_calls: Optional[List[Dict]] = None) -> None:
        """Add a message to current session history"""
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        if tool_calls:
            message["tool_calls"] = tool_calls
        self._history.append(message)
        self._last_updated = datetime.now().isoformat()
        logger.debug(f"Added {role} message, session has {len(self._history)} messages")

    def add_tool_result(self, tool_call_id: str, tool_name: str, result: str) -> None:
        """Add a tool execution result to current session"""
        self._history.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "tool_name": tool_name,
            "content": result,
            "timestamp": datetime.now().isoformat()
        })
        self._last_updated = datetime.now().isoformat()

    def get_messages(self) -> List[Dict[str, Any]]:
        """Get current session conversation history"""
        return self._history

    def get_context(self, max_messages: int = 20) -> List[Dict[str, Any]]:
        """Get recent messages from current session"""
        return self._history[-max_messages:] if self._history else []

    def clear(self) -> None:
        """Clear current session memory only"""
        msg_count = len(self._history)
        self._history = []
        self._last_updated = None
        self._session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        logger.info(f"Cleared {msg_count} messages, new session_id={self._session_id}")

    def get_conversation_for_llm(self, max_messages: int = 40) -> List[Dict[str, Any]]:
        """
        Get current session conversation formatted for LLM.
        Only returns current session messages, no historical loading.
        """
        messages = self.get_context(max_messages)
        result = []
        for m in messages:
            # Filter to only fields the LLM API accepts
            if m.get("role") == "tool":
                # Tool messages must only have role, tool_call_id, and content
                result.append({
                    "role": "tool",
                    "tool_call_id": m.get("tool_call_id"),
                    "content": m.get("content", "")
                })
            else:
                result.append({k: v for k, v in m.items() if k not in ["summary", "session_id", "tool_name", "timestamp"]})
        return result


# Global memory instance
memory = Memory()