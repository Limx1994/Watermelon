"""Safe Windows10_Output wrapper that handles NoConsoleScreenBufferError."""

import logging
from prompt_toolkit.output.windows10 import Windows10_Output
from prompt_toolkit.output.win32 import NoConsoleScreenBufferError

logger = logging.getLogger(__name__)


class SafeWin10Output(Windows10_Output):
    """Windows10_Output that handles NoConsoleScreenBufferError gracefully.

    During window resize, GetConsoleScreenBufferInfo can fail temporarily.
    This wrapper catches the error and returns the last known good value.
    """

    def __init__(self, stdout, default_color_depth=None):
        super().__init__(stdout, default_color_depth)
        self._last_screen_buffer_info = None
        _orig_sbi = self.win32_output.get_win32_screen_buffer_info

        def _safe_get_sbi():
            try:
                info = _orig_sbi()
                self._last_screen_buffer_info = info
                return info
            except NoConsoleScreenBufferError:
                if self._last_screen_buffer_info is not None:
                    logger.debug(
                        "NoConsoleScreenBufferError caught, "
                        "using cached screen info"
                    )
                    return self._last_screen_buffer_info
                logger.warning(
                    "NoConsoleScreenBufferError on first call, re-raising"
                )
                raise

        self.win32_output.get_win32_screen_buffer_info = _safe_get_sbi
