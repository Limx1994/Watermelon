"""Logging system initialization for AGImyCLI"""

import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler

from ..config import config


DEFAULT_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def _ensure_log_directory() -> Path:
    """Ensure the log directory exists and return the resolved path."""
    log_path = config.logs_path
    log_dir = Path(log_path).parent
    from .path import get_project_root
    resolved_dir = (get_project_root() / log_dir).resolve()
    resolved_dir.mkdir(parents=True, exist_ok=True)
    return resolved_dir


def _get_log_level() -> int:
    """Convert log level string to logging constant."""
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    return level_map.get(config.logs_level.upper(), logging.INFO)


def setup_logging() -> None:
    """
    Initialize the logging system for AGImyCLI.

    Configures:
    - RotatingFileHandler for file output with automatic rotation
    - Consistent format across all modules

    NOTE: No console handler — prompt_toolkit full-screen TUI is incompatible
    with raw stderr writes. All user-visible output flows through the TUI.
    """
    level = _get_log_level()
    max_bytes = config.logs_max_bytes
    backup_count = config.logs_backup_count

    _ensure_log_directory()

    from .path import resolve_path
    resolved_log_file = resolve_path(config.logs_path)

    file_handler = RotatingFileHandler(
        filename=str(resolved_log_file),
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(logging.Formatter(DEFAULT_FORMAT, DEFAULT_DATE_FORMAT))

    # No console_handler: prompt_toolkit full-screen TUI is incompatible with
    # raw stderr writes. All user-visible output flows through the TUI's
    # _output_queue. File logging preserves all diagnostic information.

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(file_handler)

    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("charset_normalizer").setLevel(logging.WARNING)

    root_logger.info(f"Logging initialized: level={config.logs_level}, file={resolved_log_file}")