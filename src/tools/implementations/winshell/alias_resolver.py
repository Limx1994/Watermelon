"""PowerShell alias resolver - converts Unix-style commands to PowerShell cmdlets."""

import re
from typing import Optional, Tuple


STANDARD_ALIASES = {
    # Unix commands -> PowerShell cmdlets
    "rm": "Remove-Item",
    "rmdir": "Remove-Item",
    "del": "Remove-Item",
    "erase": "Remove-Item",
    "rd": "Remove-Item",
    "ls": "Get-ChildItem",
    "dir": "Get-ChildItem",
    "gci": "Get-ChildItem",
    "cat": "Get-Content",
    "type": "Get-Content",
    "gc": "Get-Content",
    "get": "Get-Content",
    "pwd": "Get-Location",
    "gl": "Get-Location",
    "cd": "Set-Location",
    "chdir": "Set-Location",
    "sl": "Set-Location",
    "cp": "Copy-Item",
    "copy": "Copy-Item",
    "cpi": "Copy-Item",
    "mv": "Move-Item",
    "move": "Move-Item",
    "mi": "Move-Item",
    "ren": "Rename-Item",
    "rename": "Rename-Item",
    "rni": "Rename-Item",
    "mkdir": "New-Item -ItemType Directory",
    "md": "New-Item",
    "ni": "New-Item",
    "echo": "Write-Output",
    "write": "Write-Output",
    "write-host": "Write-Host",
    "print": "Write-Output",
    "printf": "Write-Output",
    # PowerShell common aliases
    "?": "Where-Object",
    "where": "Where-Object",
    "where-object": "Where-Object",
    "%": "ForEach-Object",
    "foreach": "ForEach-Object",
    "foreach-object": "ForEach-Object",
    "select": "Select-Object",
    "sort": "Sort-Object",
    "group": "Group-Object",
    "measure": "Measure-Object",
    "compare": "Compare-Object",
    # Process commands
    "ps": "Get-Process",
    "kill": "Stop-Process",
    "stop": "Stop-Process",
    "start": "Start-Process",
    "ipconfig": "Get-NetIPConfiguration",
    "nslookup": "Resolve-DnsName",
    "ping": "Test-Connection",
    "tracert": "Test-NetConnection",
    # Service commands
    "netstat": "Get-NetTCPConnection",
    "sc": "Get-Service",
    "services": "Get-Service",
    # Other common commands
    "which": "Get-Command",
    "which": "Get-Command",
    "history": "Get-History",
    "h": "Get-History",
    "clear": "Clear-Host",
    "cls": "Clear-Host",
    "date": "Get-Date",
    "sleep": "Start-Sleep",
    "ni": "New-Item",
}


def resolve_alias(command: str) -> str:
    """
    Resolve aliases in a command string.

    Args:
        command: Original command string

    Returns:
        Command with aliases resolved to canonical PowerShell cmdlets
    """
    if not command or not command.strip():
        return command

    original = command.strip()
    parts = original.split(None, 1)
    base_cmd = parts[0]
    args = parts[1] if len(parts) > 1 else ""

    # Case-insensitive lookup
    base_lower = base_cmd.lower()

    # Check if it's a mkdir variant that needs special handling
    if base_lower == "mkdir":
        # mkdir -> New-Item -ItemType Directory
        return f"New-Item -ItemType Directory {args}".strip()

    # Check if base command is an alias
    if base_lower in STANDARD_ALIASES:
        resolved = STANDARD_ALIASES[base_lower]
        # If we have arguments, append them
        if args:
            return f"{resolved} {args}"
        return resolved

    return original


def is_complex_script(command: str) -> Tuple[bool, str]:
    """
    Detect if a command requires .ps1 file execution.

    According to cross-project memory:
    - Complex PowerShell scripts must use .ps1 files
    - Variables like $_ in -Command get incorrectly parsed by bash
    - Subexpressions $(...) must be in .ps1 files

    Returns:
        Tuple of (is_complex, reason)
    """
    # Check for variable references that would be problematic
    # $_ , $var , ${var} patterns
    if re.search(r'\$_\b', command):
        return True, "Contains $_ variable reference"

    if re.search(r'\$\{[\w]+\}', command):
        return True, "Contains variable reference"

    if re.search(r'\$[a-zA-Z_][\w]*', command) and not command.strip().startswith('$'):
        # Only flag if not just a variable declaration like $var = value
        # But flag if it's a reference like $var.Path
        if re.search(r'\$[a-zA-Z_][\w]*\.[\w]+', command):
            return True, "Contains member access on variable"

    # Check for subexpressions
    if "$(" in command:
        return True, "Contains subexpression $(...)"

    # Check for script blocks
    if re.search(r'&\s*\{', command):
        return True, "Contains script block"

    # Check for semicolon-separated commands (multiple statements)
    if ";" in command and not command.strip().startswith(";"):
        return True, "Contains multiple statements"

    # Check for && or || operators
    if "&&" in command or "||" in command:
        return True, "Contains command chaining operators"

    return False, ""


def convert_operators(command: str) -> str:
    """
    Convert && and || to PowerShell 5.1 compatible syntax.

    PowerShell 5.1 does not support && / || as pipeline chain operators.
    This converts them to native if-condition syntax.

    Uses a state machine to skip && / || inside quoted strings.
    """
    if "&&" not in command and "||" not in command:
        return command

    # State machine: split on && / || while skipping quoted regions
    segments: list = []
    current: list = []
    i = 0
    in_single = False
    in_double = False

    while i < len(command):
        ch = command[i]
        if ch == "'" and not in_double:
            in_single = not in_single
            current.append(ch)
        elif ch == '"' and not in_single:
            in_double = not in_double
            current.append(ch)
        elif not in_single and not in_double:
            if command[i:].startswith("&&"):
                segments.append("".join(current))
                segments.append("&&")
                current = []
                i += 2
                continue
            elif command[i:].startswith("||"):
                segments.append("".join(current))
                segments.append("||")
                current = []
                i += 2
                continue
        current.append(ch)
        i += 1

    segments.append("".join(current))

    if len(segments) < 3:
        return command

    # Build result using $Error.Count for robust error detection
    result = f"$__ec0=$Error.Count; {segments[0].strip()}"
    idx = 1
    while idx < len(segments) - 1:
        op = segments[idx].strip()
        nxt = segments[idx + 1].strip()
        if op == "&&":
            result += f'; if($Error.Count -eq $__ec0) {{ $__ec0=$Error.Count; {nxt} }}'
        elif op == "||":
            result += f'; if($Error.Count -ne $__ec0) {{ $__ec0=$Error.Count; {nxt} }}'
        idx += 2

    return result


def resolve_alias_with_detection(command: str) -> Tuple[str, bool]:
    """
    Resolve aliases and detect if script is complex.

    Returns:
        Tuple of (resolved_command, needs_ps1_file)
    """
    resolved = resolve_alias(command)
    # Detect complexity BEFORE converting operators
    # (convert_operators always adds semicolons, which would false-positive)
    is_complex, _ = is_complex_script(resolved)
    # Convert && / || — the generated if/else is valid -Command input
    resolved = convert_operators(resolved)
    return resolved, is_complex
