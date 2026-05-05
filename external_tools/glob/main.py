#!/usr/bin/env python
"""glob - Find files by filename pattern within the project directory."""

import argparse
import json
import sys
from pathlib import Path


def get_project_root() -> Path:
    """Get the project root directory (where config.json is located)."""
    current = Path(__file__).resolve().parent
    while current != current.parent:
        if (current / "config.json").exists():
            return current
        current = current.parent
    return Path.cwd()


def glob_search(pattern: str, root: Path) -> list:
    """Perform glob search."""
    matches = list(root.glob(pattern))
    return [str(m.relative_to(root)) for m in matches[:50]]


def main():
    parser = argparse.ArgumentParser(description="glob - Find files by filename pattern")
    parser.add_argument("--pattern", required=True, help="Filename pattern (e.g., *.py)")
    parser.add_argument("--path", default=".", help="Directory path to search in")
    args = parser.parse_args()

    root = get_project_root()
    resolved = (root / args.path.lstrip("./")).resolve()

    # Security check: ensure resolved path is within project root
    try:
        resolved.relative_to(root)
    except ValueError:
        result = {"success": False, "content": "", "error": f"Path '{args.path}' is outside project directory"}
        print(json.dumps(result))
        return

    if not resolved.is_dir():
        result = {"success": False, "content": "", "error": f"Not a directory: {args.path}"}
        print(json.dumps(result))
        return

    try:
        matches = glob_search(args.pattern, resolved)
        if not matches:
            result = {"success": True, "content": "No files found matching pattern.", "error": ""}
        else:
            result = {"success": True, "content": "\n".join(matches), "error": ""}
    except Exception as e:
        result = {"success": False, "content": "", "error": str(e)}

    print(json.dumps(result))


if __name__ == "__main__":
    main()
