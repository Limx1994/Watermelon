#!/usr/bin/env python
"""glob - Find files by filename pattern using ripgrep."""

import argparse
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

DEFAULT_MAX_RESULTS = 100
DEFAULT_TIMEOUT = 30.0


def get_project_root() -> Path:
    """Get the project root directory (where config.json is located)."""
    current = Path(__file__).resolve().parent
    while current != current.parent:
        if (current / "config.json").exists():
            return current
        current = current.parent
    return Path.cwd()


def is_unc_path(path: str) -> bool:
    """Check if path is a UNC path."""
    return path.startswith("\\\\") or path.startswith("//")


def get_rg_path() -> str:
    """Get ripgrep path, check common Windows locations."""
    # 1. Check if rg is in PATH
    rg = shutil.which("rg")
    if rg:
        return rg
    # 2. Common Windows installation paths
    program_files = os.environ.get("ProgramFiles", "C:\\Program Files")
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    candidates = [
        os.path.join(program_files, "ripgrep", "rg.exe"),
        os.path.join(local_app_data, "Programs", "ripgrep", "rg.exe"),
    ]
    for candidate in candidates:
        if os.path.isfile(candidate):
            return candidate
    return "rg"  # Fallback to PATH lookup


def normalize_path(path: str) -> str:
    """Normalize path to forward slashes for consistent output."""
    return path.replace("\\", "/")


def build_rg_command(pattern: str, search_path: Path) -> list:
    """Build ripgrep command list."""
    rg_path = get_rg_path()
    cmd = [
        rg_path,
        "--files",
        "--glob",
        pattern,
        "--sort=modified",
        "--no-ignore",
        "--hidden",
        str(search_path),
    ]
    return cmd


def python_glob_search(pattern: str, search_path: Path) -> list:
    """Fallback glob search using Python's pathlib."""
    try:
        # Handle recursive patterns
        if "**" in pattern:
            matches = list(search_path.glob(pattern))
        else:
            matches = list(search_path.glob(pattern))
        return [normalize_path(str(m.relative_to(search_path))) for m in matches[:100]]
    except Exception:
        return []


def run_glob_search(
    pattern: str, search_path: Path, timeout: float
) -> tuple:
    """Run ripgrep and return (filenames, duration_ms, error). Falls back to Python glob."""
    cmd = build_rg_command(pattern, search_path)

    start_time = time.time()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        duration_ms = int((time.time() - start_time) * 1000)

        if result.returncode == 0:
            filenames = result.stdout.strip().split("\n")
            filenames = [normalize_path(f) for f in filenames if f]
            return filenames, duration_ms, None
        elif result.returncode == 1:
            # No matches
            return [], duration_ms, None
        else:
            # ripgrep error, try fallback
            filenames = python_glob_search(pattern, search_path)
            if filenames:
                return filenames, duration_ms, None
            return [], duration_ms, f"ripgrep error: {result.stderr}"

    except subprocess.TimeoutExpired:
        # Timeout, try fallback
        filenames = python_glob_search(pattern, search_path)
        return filenames, int((time.time() - start_time) * 1000), None
    except FileNotFoundError:
        # ripgrep not found, try Python fallback
        filenames = python_glob_search(pattern, search_path)
        return filenames, int((time.time() - start_time) * 1000), None
    except Exception as e:
        return [], int((time.time() - start_time) * 1000), str(e)


def truncate_filenames(filenames: list, max_results: int) -> tuple:
    """Truncate filename list if needed."""
    if len(filenames) <= max_results:
        return filenames, False
    return filenames[:max_results], True


def main():
    parser = argparse.ArgumentParser(
        description="glob - Find files by filename pattern using ripgrep"
    )
    parser.add_argument(
        "--pattern", required=True, help="Filename pattern (e.g., *.py)"
    )
    parser.add_argument(
        "--path", default=".", help="Directory path to search in"
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=DEFAULT_MAX_RESULTS,
        help=f"Maximum number of results (default: {DEFAULT_MAX_RESULTS})",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT,
        help=f"Search timeout in seconds (default: {DEFAULT_TIMEOUT})",
    )

    args = parser.parse_args()

    root = get_project_root()
    path_arg = args.path.lstrip("./")

    # Security check: UNC path rejection
    if is_unc_path(path_arg) or is_unc_path(args.path):
        result = {
            "success": False,
            "content": "",
            "error": "UNC paths are not allowed",
            "metadata": {},
        }
        print(json.dumps(result))
        return

    # Resolve search path
    if path_arg:
        resolved = (root / path_arg).resolve()
    else:
        resolved = root.resolve()

    if not resolved.is_dir():
        result = {
            "success": False,
            "content": "",
            "error": f"Not a directory: {args.path}",
            "metadata": {},
        }
        print(json.dumps(result))
        return

    # Run search
    filenames, duration_ms, error = run_glob_search(
        args.pattern, resolved, args.timeout
    )

    if error:
        result = {"success": False, "content": "", "error": error, "metadata": {}}
        print(json.dumps(result))
        return

    # Truncate results
    truncated_filenames, truncated = truncate_filenames(
        filenames, args.max_results
    )
    num_files = len(filenames)

    relative_path = (
        str(resolved.relative_to(root)) if resolved != root else "."
    )

    result = {
        "success": True,
        "content": (
            "\n".join(truncated_filenames)
            if truncated_filenames
            else "No files found matching pattern."
        ),
        "error": "",
        "metadata": {
            "durationMs": duration_ms,
            "numFiles": num_files,
            "truncated": truncated,
            "pattern": args.pattern,
            "path": relative_path,
        },
    }

    print(json.dumps(result))


if __name__ == "__main__":
    main()
