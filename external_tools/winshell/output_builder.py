"""Output builder for PowerShell command results."""

import json
import re
from dataclasses import dataclass, field, asdict
from typing import Optional, List


@dataclass
class PowerShellOutput:
    """Structured output for PowerShell command execution."""
    success: bool = True
    stdout: str = ""
    stderr: str = ""
    interrupted: bool = False
    return_code_interpretation: Optional[str] = None
    is_image: bool = False
    persisted_output_path: Optional[str] = None
    background_task_id: Optional[str] = None
    backgrounded_by_user: bool = False
    assistant_auto_backgrounded: bool = False
    return_code: int = 0

    def to_dict(self) -> dict:
        """Convert to dictionary, excluding None/empty values for cleaner output."""
        result = {}
        for key, value in asdict(self).items():
            if key == "success":
                result[key] = value
            elif key == "return_code":
                # Always include return code
                result["returnCode"] = value
            elif value is not None and value != "" and value is not False:
                result[self._to_camel_case(key)] = value
        return result

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @staticmethod
    def _to_camel_case(snake_str: str) -> str:
        """Convert snake_case to camelCase for JSON output."""
        components = snake_str.split('_')
        return components[0] + ''.join(x.title() for x in components[1:])

    @staticmethod
    def from_dict(data: dict) -> 'PowerShellOutput':
        """Create from dictionary (camelCase keys)."""
        if data.get("success", True):
            return PowerShellOutput(
                stdout=data.get("stdout", ""),
                stderr=data.get("stderr", ""),
                return_code=data.get("returnCode", 0),
                interrupted=data.get("interrupted", False),
                return_code_interpretation=data.get("returnCodeInterpretation"),
                is_image=data.get("isImage", False),
                persisted_output_path=data.get("persistedOutputPath"),
                background_task_id=data.get("backgroundTaskId"),
                backgrounded_by_user=data.get("backgroundedByUser", False),
                assistant_auto_backgrounded=data.get("assistantAutoBackgrounded", False),
            )
        else:
            return PowerShellOutput(
                stdout="",
                stderr=data.get("error", ""),
                return_code=data.get("returnCode", 1),
                interrupted=False,
                return_code_interpretation="Error",
            )


# Exit code interpretations for common commands
EXIT_CODE_INTERPRETATIONS = {
    0: "Success",
    1: "General error",
    2: "Access denied",
    127: "Command not found",
    255: "Exit code out of range",
}

# Special interpretations for specific commands
COMMAND_INTERPRETATIONS = {
    "robocopy": {
        0: "No files were copied (success, source and destination are synchronized)",
        1: "All files were copied successfully",
        2: "Extra files or directories were detected and removed",
        4: "Mismatched files or directories were detected",
        8: "Some files could not be copied",
        16: "Serious error, robocopy did not proceed",
    },
    "git": {
        0: "Success",
        1: "Failure due to no changes or usage error",
        2: "Fatal error",
        128: "Invalid arguments or repository corruption",
    },
    "npm": {
        0: "Success",
        1: "General error",
        2: "xton/dependency conflict error (treated as success in watch mode)",
    },
}


def interpret_return_code(code: int, command: Optional[str] = None) -> str:
    """
    Interpret exit code with semantic meaning.

    Args:
        code: Exit code
        command: Optional command name for specialized interpretations

    Returns:
        Human-readable interpretation
    """
    # Check for command-specific interpretation
    if command and command.strip():
        parts = command.lower().split()
        cmd_lower = parts[0] if parts else ""
        for cmd_key, interpretations in COMMAND_INTERPRETATIONS.items():
            if cmd_key in cmd_lower:
                if code in interpretations:
                    return interpretations[code]

    # Fall back to generic interpretation
    return EXIT_CODE_INTERPRETATIONS.get(code, f"Exit code {code}")


def detect_image_output(stdout: str, stderr: str) -> bool:
    """
    Detect if command output contains image data.

    Checks for:
    - File extensions in output (.png, .jpg, .gif, .bmp, .webp)
    - Base64 image data patterns
    - System.Drawing.Image mentions
    """
    combined = stdout + stderr

    # Check for image file paths in output
    image_extensions = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".ico", ".svg"}
    for line in combined.splitlines():
        line_lower = line.strip().lower()
        for ext in image_extensions:
            if line_lower.endswith(ext):
                return True

    # Check for Base64 image data patterns
    # Common patterns: data:image/png;base64,... or raw base64 image data
    if re.search(r'data:image/\w+;base64,', combined):
        return True

    # Check for System.Drawing.Image mention
    if "System.Drawing.Image" in combined:
        return True

    # Check for width x height dimensions pattern (common in image info)
    if re.search(r'\d+\s*[xX]\s*\d+\s*(pixels?|px)?', combined):
        # Check if it's not just screen resolution
        if any(keyword in combined for keyword in ["Image", "Picture", "Photo", "Screenshot", "Capture"]):
            return True

    return False


def truncate_output(output: str, max_lines: int = 1000) -> str:
    """Truncate output to prevent excessive length."""
    lines = output.splitlines()
    if len(lines) <= max_lines:
        return output
    kept_lines = lines[:max_lines]
    truncated = '\n'.join(kept_lines)
    return truncated + f"\n... (truncated, {len(lines) - max_lines} more lines)"


def build_output(
    stdout: str,
    stderr: str,
    return_code: int,
    interrupted: bool = False,
    command: Optional[str] = None,
    background_task_id: Optional[str] = None,
    backgrounded_by_user: bool = False,
    assistant_auto_backgrounded: bool = False,
    max_output_lines: int = 5000,
) -> PowerShellOutput:
    """
    Build a PowerShellOutput object from execution results.

    Args:
        stdout: Standard output
        stderr: Standard error
        return_code: Process exit code
        interrupted: Whether process was interrupted
        command: Original command (for specialized exit code interpretation)
        background_task_id: UUID for background task
        backgrounded_by_user: User manually backgrounded
        assistant_auto_backgrounded: Assistant auto-backgrounded due to complexity
        max_output_lines: Maximum lines before truncation

    Returns:
        PowerShellOutput object
    """
    # Truncate if needed
    truncated_stdout = truncate_output(stdout, max_output_lines)

    # Determine success based on return code only
    is_success = (return_code == 0)

    return PowerShellOutput(
        success=is_success,
        stdout=truncated_stdout,
        stderr=stderr,
        return_code=return_code,
        interrupted=interrupted,
        return_code_interpretation=interpret_return_code(return_code, command),
        is_image=detect_image_output(stdout, stderr),
        background_task_id=background_task_id,
        backgrounded_by_user=backgrounded_by_user,
        assistant_auto_backgrounded=assistant_auto_backgrounded,
    )
