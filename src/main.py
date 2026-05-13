"""AGImyCLI - Main entry point"""

import logging
import platform

# Initialize logging BEFORE any other imports
from src.utils.logging import setup_logging
setup_logging()

logger = logging.getLogger(__name__)

from src.tui import run_tui


def main():
    """Main entry point"""
    logger.info(f"AGImyCLI starting | Python {platform.python_version()} | {platform.system()} {platform.release()}")

    # Ensure required directories exist
    from src.utils.path import ensure_directory
    try:
        ensure_directory("./memory")
        ensure_directory("./logs")
    except Exception as e:
        logger.warning(f"Failed to create directories: {e}")

    # Run TUI
    try:
        run_tui()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
    logger.info("AGImyCLI exit")


if __name__ == "__main__":
    main()