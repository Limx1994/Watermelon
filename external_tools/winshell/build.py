#!/usr/bin/env python
"""Build script for winshell.exe using PyInstaller."""

import subprocess
import sys
from pathlib import Path


def main():
    tool_dir = Path(__file__).parent
    spec_file = tool_dir / "winshell.spec"

    # Ensure PyInstaller is installed
    try:
        subprocess.run(["pyinstaller", "--version"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Installing PyInstaller...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)

    # Build with PyInstaller
    print("Building winshell.exe...")
    result = subprocess.run(
        ["pyinstaller", str(spec_file), "--clean", "--noconfirm"],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(f"Build failed:\n{result.stderr}")
        sys.exit(1)

    # Find the generated exe
    dist_dir = tool_dir / "dist"
    exe_path = dist_dir / "winshell.exe"

    if exe_path.exists():
        print(f"Build successful: {exe_path}")
        print(f"Size: {exe_path.stat().st_size / 1024:.1f} KB")
    else:
        print("Build completed but exe not found in dist/")
        sys.exit(1)


if __name__ == "__main__":
    main()