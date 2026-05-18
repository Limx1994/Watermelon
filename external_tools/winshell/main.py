#!/usr/bin/env python
"""winshell - PowerShell command executor with alias resolution and .ps1 file support."""

import argparse
import atexit
import json
import os
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Optional, Tuple

# Set UTF-8 encoding for stdout before any output
if sys.stdout.encoding != 'utf-8':
    sys.stdout = os.fdopen(os.dup(sys.stdout.fileno()), mode='w', encoding='utf-8', buffering=1)
if sys.stderr.encoding != 'utf-8':
    sys.stderr = os.fdopen(os.dup(sys.stderr.fileno()), mode='w', encoding='utf-8', buffering=1)

from alias_resolver import resolve_alias_with_detection
from output_builder import build_output, PowerShellOutput


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
        return {"aliases": {}}
    with open(whitelist_path, "r", encoding="utf-8") as f:
        return json.load(f)


# Background task management
BACKGROUND_SCRIPT_DIR: Optional[Path] = None
BACKGROUND_PROCESSES = {}


def init_background_dir() -> Path:
    """Initialize the background script directory."""
    global BACKGROUND_SCRIPT_DIR
    if BACKGROUND_SCRIPT_DIR is None:
        BACKGROUND_SCRIPT_DIR = Path(tempfile.gettempdir()) / "winshell_bg"
        BACKGROUND_SCRIPT_DIR.mkdir(exist_ok=True)
    return BACKGROUND_SCRIPT_DIR


@atexit.register
def cleanup():
    """Cleanup temporary .ps1 files and terminate background processes."""
    global BACKGROUND_PROCESSES, BACKGROUND_SCRIPT_DIR

    # Terminate all background processes
    for task_id, proc in list(BACKGROUND_PROCESSES.items()):
        if proc.poll() is None:
            try:
                proc.terminate()
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()

    # Clean up temporary script files
    if BACKGROUND_SCRIPT_DIR and BACKGROUND_SCRIPT_DIR.exists():
        for f in BACKGROUND_SCRIPT_DIR.glob("*.ps1"):
            try:
                f.unlink()
            except Exception:
                pass


def _decode_ps_output(raw_bytes: bytes) -> str:
    """Decode PowerShell output bytes, trying UTF-8 first then system encoding."""
    if not raw_bytes:
        return ""
    # PowerShell on Windows often outputs system encoding (GBK on Chinese Windows)
    # Try UTF-8 first, fallback to system default
    try:
        decoded = raw_bytes.decode("utf-8")
        # Check if result contains replacement characters (UTF-8 decode of GBK bytes)
        if "�" not in decoded:
            return decoded.replace('\r\n', '\n').replace('\r', '\n')
    except UnicodeDecodeError:
        pass
    # Fallback: decode using system default encoding
    import locale
    sys_enc = locale.getpreferredencoding(False) or "utf-8"
    return raw_bytes.decode(sys_enc, errors="replace").replace('\r\n', '\n').replace('\r', '\n')


def execute_simple_command(command: str, timeout_ms: int, cwd: str) -> Tuple[subprocess.CompletedProcess, bool]:
    """
    Execute a simple command via powershell -Command.

    Returns:
        Tuple of (CompletedProcess, interrupted)
    """
    timeout_sec = max(1, timeout_ms // 1000)

    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-NoLogo", "-Command", command],
            cwd=cwd,
            capture_output=True,
            timeout=timeout_sec,
        )
        proc.stdout = _decode_ps_output(proc.stdout)
        proc.stderr = _decode_ps_output(proc.stderr)
        return proc, False
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(args=[], returncode=124, stdout="", stderr="Command timed out"), True
    except Exception as e:
        return subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr=str(e)), False


def create_temp_script(content: str) -> Tuple[Path, str]:
    """
    Create a temporary .ps1 script file.

    Returns:
        Tuple of (script_path, task_id)
    """
    bg_dir = init_background_dir()
    task_id = str(uuid.uuid4())
    script_path = bg_dir / f"{task_id}.ps1"

    # Write script with UTF-8 BOM (PowerShell default encoding)
    # The script content might contain special characters
    script_path.write_bytes(b'\xef\xbb\xbf' + content.encode('utf-8'))

    return script_path, task_id


def execute_script_file(script_path: Path, timeout_ms: int, cwd: str) -> Tuple[subprocess.CompletedProcess, bool]:
    """
    Execute a .ps1 script file via powershell -File.

    Returns:
        Tuple of (CompletedProcess, interrupted)
    """
    timeout_sec = max(1, timeout_ms // 1000)

    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-NoLogo", "-File", str(script_path)],
            cwd=cwd,
            capture_output=True,
            timeout=timeout_sec,
        )
        proc.stdout = _decode_ps_output(proc.stdout)
        proc.stderr = _decode_ps_output(proc.stderr)
        return proc, False
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(args=[], returncode=124, stdout="", stderr="Command timed out"), True
    except Exception as e:
        return subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr=str(e)), False


def execute_background(script_path: Path, timeout_ms: int, cwd: str) -> Tuple[str, subprocess.Popen]:
    """
    Start a background task.

    Returns:
        Tuple of (task_id, Popen process)
    """
    task_id = str(uuid.uuid4())
    bg_dir = init_background_dir()
    task_script = bg_dir / f"{task_id}.ps1"

    # Copy the script content
    content = script_path.read_bytes()
    task_script.write_bytes(content)

    timeout_sec = max(1, timeout_ms // 1000)

    proc = subprocess.Popen(
        ["powershell", "-NoProfile", "-NoLogo", "-File", str(task_script)],
        cwd=cwd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    BACKGROUND_PROCESSES[task_id] = proc

    return task_id, proc


def execute_command(
    command: str,
    timeout_ms: int,
    run_in_background: bool,
    dangerously_disable_sandbox: bool,
    cwd: str,
) -> PowerShellOutput:
    """
    Execute a PowerShell command with alias resolution.

    Args:
        command: Original command
        timeout_ms: Timeout in milliseconds
        run_in_background: Run as background task
        dangerously_disable_sandbox: Skip all checks
        cwd: Working directory

    Returns:
        PowerShellOutput object
    """
    # Resolve aliases and check complexity
    resolved_command, needs_ps1 = resolve_alias_with_detection(command)

    # If command contains special characters that need .ps1, force ps1 mode
    if not needs_ps1:
        # Double check: any $ in command suggests variable usage
        if '$' in resolved_command and not resolved_command.strip().startswith('$'):
            needs_ps1 = True

    if needs_ps1:
        # Create temporary script
        script_content = resolved_command
        script_path, task_id = create_temp_script(script_content)

        if run_in_background:
            bg_task_id, _ = execute_background(script_path, timeout_ms, cwd)
            return build_output(
                stdout=f"Background task started: {bg_task_id}\nScript: {script_path.name}",
                stderr="",
                return_code=0,
                command=command,
                background_task_id=bg_task_id,
                backgrounded_by_user=True,
            )
        else:
            proc, interrupted = execute_script_file(script_path, timeout_ms, cwd)

            # Clean up script after execution (immediate execution mode)
            try:
                script_path.unlink()
            except Exception:
                pass

            return build_output(
                stdout=proc.stdout,
                stderr=proc.stderr,
                return_code=proc.returncode,
                interrupted=interrupted,
                command=command,
            )
    else:
        # Simple command execution via -Command
        if run_in_background:
            # For simple commands in background, still use .ps1 file
            script_content = resolved_command
            script_path, task_id = create_temp_script(script_content)
            bg_task_id, _ = execute_background(script_path, timeout_ms, cwd)
            return build_output(
                stdout=f"Background task started: {bg_task_id}",
                stderr="",
                return_code=0,
                command=command,
                background_task_id=bg_task_id,
                backgrounded_by_user=True,
            )
        else:
            proc, interrupted = execute_simple_command(resolved_command, timeout_ms, cwd)
            return build_output(
                stdout=proc.stdout,
                stderr=proc.stderr,
                return_code=proc.returncode,
                interrupted=interrupted,
                command=command,
            )


def main():
    parser = argparse.ArgumentParser(
        description="winshell - PowerShell executor with alias resolution and .ps1 support",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--command", required=True, help="PowerShell command to execute")
    parser.add_argument(
        "--timeout",
        type=int,
        default=30000,
        help="Timeout in milliseconds (default: 30000, max: 600000)",
    )
    parser.add_argument("--description", default="", help="Command description (for logging)")
    parser.add_argument(
        "--run-in-background",
        action="store_true",
        default=False,
        help="Run command in background",
    )
    parser.add_argument(
        "--dangerously-disable-sandbox",
        action="store_true",
        default=False,
        help="Disable all validation (dangerous)",
    )

    args = parser.parse_args()

    # Clamp timeout to valid range
    timeout_ms = max(1000, min(args.timeout, 600000))

    root = get_project_root()

    # Execute command
    output = execute_command(
        command=args.command,
        timeout_ms=timeout_ms,
        run_in_background=args.run_in_background,
        dangerously_disable_sandbox=args.dangerously_disable_sandbox,
        cwd=str(root),
    )

    # Print output as JSON
    print(output.to_json(), flush=True)


if __name__ == "__main__":
    main()
