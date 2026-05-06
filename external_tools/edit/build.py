#!/usr/bin/env python
"""Build script for edit.exe using PyInstaller."""

import subprocess
import sys
import os
from pathlib import Path


def main():
    spec_file = Path(__file__).parent / "edit.spec"

    # Ensure PyInstaller is installed
    try:
        subprocess.run(["pyinstaller", "--version"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Installing PyInstaller...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)

    # Build with PyInstaller
    print("Building edit.exe...")
    result = subprocess.run(
        ["pyinstaller", str(spec_file), "--clean", "--noconfirm"],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(f"Build failed:\n{result.stderr}")
        sys.exit(1)

    # Find the generated exe
    dist_dir = Path(__file__).parent / "dist"
    exe_path = dist_dir / "edit.exe"

    if exe_path.exists():
        print(f"Build successful: {exe_path}")
        print(f"Size: {exe_path.stat().st_size / 1024:.1f} KB")
    else:
        print("Build completed but exe not found in dist/")
        sys.exit(1)


if __name__ == "__main__":
    main()
