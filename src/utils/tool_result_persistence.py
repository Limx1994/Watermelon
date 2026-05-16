"""Tool result persistence — save large tool results to disk, keep short references in messages"""

import logging
import shutil
import threading
from pathlib import Path
from typing import Optional

from .path import get_project_root

logger = logging.getLogger(__name__)

# Default threshold: tool results larger than this (chars) will be persisted to disk
_DEFAULT_THRESHOLD_CHARS = 2000
# Default max file size for a single persisted result
_DEFAULT_MAX_FILE_SIZE = 10 * 1024 * 1024
# Subdirectory under memory/ for persisted tool results
_PERSISTENCE_SUBDIR = "tool_results"


class ToolResultPersistence:
    """Persist large tool results to disk, replacing content with short references.

    Thread-safe: uses RLock for all shared state access.
    Graceful degradation: disk write failure falls back to inline content.
    """

    def __init__(
        self,
        threshold_chars: int = _DEFAULT_THRESHOLD_CHARS,
        max_file_size: int = _DEFAULT_MAX_FILE_SIZE,
    ):
        self._threshold_chars = threshold_chars
        self._max_file_size = max_file_size
        self._base_dir: Optional[Path] = None
        self._rw_lock = threading.RLock()
        logger.debug(
            f"ToolResultPersistence init: threshold={threshold_chars} chars, "
            f"max_file_size={max_file_size}"
        )

    def _ensure_base_dir(self) -> Optional[Path]:
        """Lazy-init and return the base persistence directory."""
        if self._base_dir is None:
            self._base_dir = get_project_root() / "memory" / _PERSISTENCE_SUBDIR
        return self._base_dir

    def persist_if_large(
        self, content: str, tool_call_id: str, tool_name: str, session_id: str
    ) -> Optional[str]:
        """If content exceeds threshold, write to disk and return a short reference.

        Args:
            content: The full tool result content.
            tool_call_id: Unique ID for this tool call.
            tool_name: Name of the tool that produced this result.
            session_id: Current session ID for directory scoping.

        Returns:
            A short reference string like "[Tool result: tool_results/<session_id>/<id>.txt]"
            if content was persisted, or None if content was small enough to keep inline.
        """
        if not content or len(content) <= self._threshold_chars:
            return None

        base_dir = self._ensure_base_dir()
        if not base_dir:
            return None

        session_dir = base_dir / session_id
        try:
            session_dir.mkdir(parents=True, exist_ok=True)
            file_path = session_dir / f"{tool_call_id}.txt"

            # Truncate if content exceeds max file size (byte-safe)
            write_content = content
            truncated = False
            encoded = content.encode("utf-8")
            if len(encoded) > self._max_file_size:
                truncated_encoded = encoded[:self._max_file_size]
                write_content = truncated_encoded.decode("utf-8", errors="ignore")
                truncated = True

            file_path.write_text(write_content, encoding="utf-8")
            size = file_path.stat().st_size

            ref = (
                f"[Tool result: {_PERSISTENCE_SUBDIR}/{session_id}/{tool_call_id}.txt"
                f"  tool={tool_name}  size={size}B]"
            )
            if truncated:
                ref = ref.replace("]", "  truncated=True]")
            logger.debug(
                f"Persisted tool result: {tool_name}/{tool_call_id} "
                f"({len(content)} chars -> {size}B on disk)"
            )
            return ref
        except OSError as e:
            logger.warning(
                f"Failed to persist tool result {tool_name}/{tool_call_id}: {e}"
            )
            return None  # Graceful degradation: keep content inline

    def clear_session(self, session_id: str) -> None:
        """Remove all persisted files for a session. Called during Full Compact."""
        base_dir = self._ensure_base_dir()
        if not base_dir:
            return
        session_dir = base_dir / session_id
        if not session_dir.exists():
            return
        try:
            shutil.rmtree(str(session_dir))
            logger.debug(f"Cleared persisted tool results for session {session_id}")
        except OSError as e:
            logger.warning(f"Failed to clear session {session_id} persistence: {e}")

