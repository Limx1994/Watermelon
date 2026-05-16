#!/usr/bin/env python
"""write_file - Write content to a file within the project directory."""

import argparse
import json
from pathlib import Path


def get_project_root() -> Path:
    """Get the project root directory (where config.json is located)."""
    current = Path(__file__).resolve().parent
    while current != current.parent:
        if (current / "config.json").exists():
            return current
        current = current.parent
    return Path.cwd()


def main():
    parser = argparse.ArgumentParser(description="Write file tool")
    parser.add_argument("--path", required=True, help="File path relative to project root")
    parser.add_argument("--content", required=True, help="Content to write to file")
    args = parser.parse_args()

    root = get_project_root()
    resolved = (root / args.path).resolve()

    # Security check: ensure resolved path is within project root
    try:
        resolved.relative_to(root)
    except ValueError:
        result = {"success": False, "content": "", "error": f"Path '{args.path}' is outside project directory"}
        print(json.dumps(result))
        return

    # Write file
    try:
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(args.content, encoding="utf-8")
        result = {"success": True, "content": f"Successfully wrote to {args.path}", "error": ""}
    except Exception as e:
        result = {"success": False, "content": "", "error": f"Failed to write file: {e}"}

    print(json.dumps(result))


if __name__ == "__main__":
    main()