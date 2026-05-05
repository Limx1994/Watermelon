"""Path utility functions for relative path handling"""

import os
from pathlib import Path

_PROJECT_ROOT = None


def get_project_root() -> Path:
    """Get the project root directory (where config.json is located)"""
    global _PROJECT_ROOT
    if _PROJECT_ROOT is None:
        # Start from this file's location and traverse up
        current = Path(__file__).resolve().parent
        # Traverse up to find project root (contains config.json)
        while current != current.parent:
            if (current / "config.json").exists():
                _PROJECT_ROOT = current
                break
            current = current.parent
        if _PROJECT_ROOT is None:
            # Fallback to current directory
            _PROJECT_ROOT = Path.cwd()
    return _PROJECT_ROOT


def resolve_path(relative_path: str) -> Path:
    """
    Resolve a relative path from project root.
    Prevents path traversal outside project directory.
    """
    root = get_project_root()
    # Clean the path to prevent directory traversal
    resolved = (root / relative_path).resolve()
    # Security check: ensure resolved path is within project root
    try:
        resolved.relative_to(root)
    except ValueError:
        raise ValueError(f"Path '{relative_path}' is outside project directory")
    return resolved


def ensure_directory(path: str) -> None:
    """Ensure a directory exists, create if necessary"""
    resolved = resolve_path(path)
    resolved.mkdir(parents=True, exist_ok=True)


def safe_read_file(path: str, encoding: str = "utf-8") -> str:
    """Safely read a file within project directory"""
    resolved = resolve_path(path)
    if not resolved.exists():
        raise FileNotFoundError(f"File not found: {path}")
    return resolved.read_text(encoding=encoding)


def safe_write_file(path: str, content: str, encoding: str = "utf-8") -> None:
    """Safely write a file within project directory"""
    resolved = resolve_path(path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(content, encoding=encoding)