"""AGImyCLI - Main entry point"""

import logging
import sys
import os

# Initialize logging BEFORE any other imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from src.utils.logging import setup_logging
setup_logging()

logger = logging.getLogger(__name__)

from src.tui import run_tui


def main():
    """Main entry point"""
    logger.info("AGImyCLI starting")
    print("Initializing AGImyCLI...")

    # Ensure required directories exist
    from src.utils.path import ensure_directory
    try:
        ensure_directory("./memory")
        ensure_directory("./logs")
    except Exception as e:
        logger.warning(f"Failed to create directories: {e}")

    # Run TUI
    run_tui()
    logger.info("AGImyCLI exit")


if __name__ == "__main__":
    main()