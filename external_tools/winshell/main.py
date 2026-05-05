#!/usr/bin/env python
"""winshell - Shell command executor with whitelist validation."""

import argparse
import json
import subprocess
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


def get_tool_dir() -> Path:
    """Get the winshell tool directory."""
    return Path(__file__).resolve().parent


def load_whitelist() -> dict:
    """Load whitelist configuration from whitelist.json."""
    whitelist_path = get_tool_dir() / "whitelist.json"
    if not whitelist_path.exists():
        return {"allowed_commands": [], "aliases": {}}
    with open(whitelist_path, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize_command(command: str, whitelist: dict) -> str:
    """
    Normalize command by resolving aliases to PowerShell cmdlets.
    Returns the normalized command string.
    """
    parts = command.strip().split()
    if not parts:
        return command

    base_cmd = parts[0]
    aliases = whitelist.get("aliases", {})

    # Resolve alias
    if base_cmd in aliases:
        resolved = aliases[base_cmd]
        # For commands like "mkdir" -> "New-Item -ItemType Directory"
        # we need to transform the entire command
        if base_cmd == "mkdir":
            # mkdir -> New-Item -ItemType Directory
            return f"New-Item -ItemType Directory {' '.join(parts[1:])}"
        elif base_cmd in ("cd", "pwd", "ls", "cat", "rm", "cp", "mv"):
            # These need to replace the first word
            return resolved + " " + " ".join(parts[1:])

    return command


def is_command_allowed(command: str, whitelist: dict) -> tuple[bool, str]:
    """
    Check if command is allowed by whitelist.
    Returns (allowed, error_message).
    """
    allowed_commands = set(whitelist.get("allowed_commands", []))
    aliases = whitelist.get("aliases", {})

    # Resolve the base command
    parts = command.strip().split()
    if not parts:
        return False, "Empty command"

    base_cmd = parts[0]

    # Check if base command is in whitelist (directly or as alias)
    # First check if it's a PowerShell cmdlet in whitelist
    if base_cmd in allowed_commands:
        return True, ""

    # Check if it's an alias that resolves to a whitelisted command
    if base_cmd in aliases:
        resolved = aliases[base_cmd]
        # For mkdir, it becomes New-Item
        if base_cmd == "mkdir":
            if "New-Item" in allowed_commands:
                return True, ""
        elif resolved in allowed_commands:
            return True, ""

    return False, f"Command '{base_cmd}' is not allowed"


def main():
    parser = argparse.ArgumentParser(description="winshell - Shell executor with whitelist")
    parser.add_argument("--command", required=True, help="Command to execute")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout in seconds")
    args = parser.parse_args()

    root = get_project_root()
    whitelist = load_whitelist()

    # Check whitelist
    allowed, error_msg = is_command_allowed(args.command, whitelist)
    if not allowed:
        result = {"success": False, "content": "", "error": error_msg}
        print(json.dumps(result))
        return

    # Normalize command
    normalized = normalize_command(args.command, whitelist)

    # Execute
    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-Command", normalized],
            cwd=str(root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=args.timeout
        )

        output = proc.stdout if proc.stdout else proc.stderr

        if proc.returncode != 0:
            result = {
                "success": False,
                "content": output,
                "error": f"Command failed with exit code {proc.returncode}"
            }
        else:
            result = {"success": True, "content": output, "error": ""}

    except subprocess.TimeoutExpired:
        result = {"success": False, "content": "", "error": f"Command timed out after {args.timeout} seconds"}
    except Exception as e:
        result = {"success": False, "content": "", "error": str(e)}

    print(json.dumps(result))


if __name__ == "__main__":
    main()