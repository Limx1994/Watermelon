"""TUI interface using prompt_toolkit Application + Layout"""

import asyncio
import logging
import queue
import sys
import threading
from typing import Optional

from prompt_toolkit.application import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.clipboard.pyperclip import PyperclipClipboard  # Windows system clipboard
from prompt_toolkit.document import Document
from prompt_toolkit.filters import Condition, has_focus
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys
from prompt_toolkit.layout import Layout, HSplit, VSplit, Window, ScrollOffsets
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.layout.dimension import LayoutDimension as D
from prompt_toolkit.layout.margins import ScrollbarMargin
from prompt_toolkit.completion import DynamicCompleter, DummyCompleter
from prompt_toolkit.lexers import Lexer
from prompt_toolkit.mouse_events import MouseEventType, MouseButton
from prompt_toolkit.styles import Style
from prompt_toolkit.output import create_output

from .agent import Agent, AgentCancelledError
from .config import config

logger = logging.getLogger(__name__)

# TUI constants
POLL_INTERVAL = 0.03
PROGRESS_DISPLAY_THRESHOLD = 0.5
PROGRESS_BAR_WIDTH = 20


def _clean_cr(text: str) -> str:
    """Strip \\r from text to prevent ^M display in prompt_toolkit."""
    if '\r' not in text:
        return text
    return text.replace('\r\n', '\n').replace('\r', '\n')


class OutputLexer(Lexer):
    """Custom Lexer that applies per-line styles from a line_styles list."""
    def __init__(self, get_line_styles):
        self.get_line_styles = get_line_styles

    def lex_document(self, document):
        line_styles = self.get_line_styles()
        def get_line(lineno):
            if lineno < len(line_styles) and line_styles[lineno]:
                return [(line_styles[lineno], document.lines[lineno])]
            return [("", document.lines[lineno])]
        return get_line


class _OutputWindow(Window):
    """输出窗口：agent 运行期间屏蔽全部鼠标事件；
    空闲时滚轮自行处理（始终同步移动光标 + vertical_scroll，避免被
    render loop 回退），其余事件交由 BufferControl 处理（文本选中等）。
    """

    def __init__(self, tui_ref: "SimpleTUI", **kwargs):
        super().__init__(**kwargs)
        self._tui = tui_ref

    def mouse_handler(self, mouse_event):
        # ── agent 运行中：吞掉全部鼠标事件 ──────────────────────
        if self._tui._agent_running:
            return

        # ── 空闲：滚轮 — 自行处理，始终同步移动光标和 vertical_scroll ──
        if mouse_event.event_type == MouseEventType.SCROLL_UP:
            self._tui._auto_scroll = False
            self._scroll_up()
            return
        if mouse_event.event_type == MouseEventType.SCROLL_DOWN:
            self._tui._auto_scroll = False
            self._scroll_down()
            return

        # ── 其余（点击、拖拽选文字）交给 BufferControl ────────
        return super().mouse_handler(mouse_event)

    # ── scroll helpers ────────────────────────────────────

    def _scroll_up(self) -> None:
        """Always move cursor up AND decrease vertical_scroll together.
        Parent only moves cursor when it's at the bottom edge — which
        causes scroll to be reverted by the render loop for other positions.
        """
        if self.vertical_scroll <= 0:
            return
        self.content.move_cursor_up()
        self.vertical_scroll -= 1

    def _scroll_down(self) -> None:
        """Always move cursor down AND increase vertical_scroll together.
        When reaching the bottom, snap cursor to document end to guarantee
        absolute precision regardless of content_height rounding.
        """
        info = self.render_info
        if info is None:
            return
        if self.vertical_scroll >= max(0, info.content_height - info.window_height):
            # At visual bottom — pin cursor to absolute end for precision
            buf = self._tui._output_buffer
            buf.cursor_position = len(buf.text) if buf.text else 0
            self._tui._auto_scroll = True
            # Sync vertical_scroll to actual bottom to prevent re-triggering
            self.vertical_scroll = max(0, info.content_height - info.window_height)
            return
        self.content.move_cursor_down()
        self.vertical_scroll += 1

    def _scroll_when_linewrapping(self, ui_content, width, height):
        """Override to separate auto-scroll and manual-scroll behavior.

        auto_scroll=True: delegate to parent which drives vertical_scroll
        from cursor position (cursor is at document end).

        auto_scroll=False: preserve the user's vertical_scroll exactly.
        Only clamp to [0, topmost_visible] to prevent out-of-bounds.
        Cursor position NEVER influences vertical_scroll.
        """
        if self._tui._auto_scroll:
            super()._scroll_when_linewrapping(ui_content, width, height)
            return

        # Manual scroll mode: preserve user's viewport position.
        # Reset intra-line scroll (not used with wrap_lines=True output).
        self.horizontal_scroll = 0
        self.vertical_scroll_2 = 0

        if width <= 0 or ui_content.line_count == 0:
            return

        def get_line_height(lineno):
            return ui_content.get_height_for_line(lineno, width, self.get_line_prefix)

        # Calculate topmost_visible: the highest line number that can
        # be the first visible line while still filling the window.
        prev_lineno = ui_content.line_count - 1
        used_height = 0
        for lineno in range(ui_content.line_count - 1, -1, -1):
            used_height += get_line_height(lineno)
            if used_height > height:
                break
            prev_lineno = lineno
        topmost_visible = prev_lineno

        # Clamp only to valid bounds — never force cursor-based position
        new_scroll = max(0, min(self.vertical_scroll, topmost_visible))
        if new_scroll != self.vertical_scroll:
            logger.debug(
                f"Manual scroll clamped: {self.vertical_scroll} -> "
                f"{new_scroll} (topmost_visible={topmost_visible})"
            )
        self.vertical_scroll = new_scroll


class _InputWindow(Window):
    """自定义输入窗口，支持右键粘贴"""
    def mouse_handler(self, mouse_event):
        logger.debug(f"[MOUSE] _InputWindow: type={mouse_event.event_type} "
                     f"button={mouse_event.button} pos={mouse_event.position}")
        if (mouse_event.event_type == MouseEventType.MOUSE_DOWN
            and mouse_event.button == MouseButton.RIGHT):  # 右键
            try:
                buf = self.content.buffer
                clipboard_data = self.app.clipboard.get_data()
                if clipboard_data and hasattr(clipboard_data, 'text') and clipboard_data.text:
                    buf.insert_text(_clean_cr(clipboard_data.text))
                    logger.debug(f"[MOUSE] 右键粘贴成功: {clipboard_data.text[:30]}")
                else:
                    logger.debug("[MOUSE] 右键粘贴: 剪切板为空")
            except Exception as e:
                logger.warning(f"右键粘贴失败: {e}")
            return None  # 事件已处理
        return super().mouse_handler(mouse_event)


def _create_platform_output():
    """Create platform-appropriate prompt_toolkit Output.

    Uses SafeWin10Output on Windows to handle NoConsoleScreenBufferError
    during window resize in exe builds.
    """
    if sys.platform == "win32":
        try:
            from .safe_output import SafeWin10Output
            return SafeWin10Output(sys.stdout)
        except Exception as e:
            logger.warning(f"SafeWin10Output creation failed: {e}")

    try:
        return create_output()
    except Exception:
        logger.warning("create_output() failed, falling back to Vt100_Output")
        from prompt_toolkit.output.vt100 import Vt100_Output
        return Vt100_Output.from_pty(sys.stdout)


class SimpleTUI:
    """Terminal UI for AGI interaction using prompt_toolkit TUI layout"""

    MAX_FRAGMENTS = 5000

    def __init__(self):
        self.agent: Optional[Agent] = None

        # Styled output fragments — intermediate storage for queue messages
        self._fragments: list[tuple[str, str]] = []
        self._fragments_lock = threading.Lock()

        # Per-line styles for the Lexer (rebuilt each poll cycle from fragments)
        self._line_styles: list[str] = []

        # Incremental rebuild cache
        self._cached_frag_count: int = 0
        self._cached_full_text: str = ""

        # Agent safety
        self._agent_running = False
        self._agent_generation: int = 0
        self._agent_stop_event = threading.Event()
        self._exit_requested = False
        self._poll_task: Optional[asyncio.Task] = None

        # Read-only Buffer for output text with native selection support
        self._output_buffer = Buffer(read_only=True)

        # BufferControl with custom Lexer for per-line styling
        self._output_control = BufferControl(
            buffer=self._output_buffer,
            lexer=OutputLexer(lambda: self._line_styles),
            focusable=Condition(lambda: not self._agent_running),
            focus_on_click=Condition(lambda: not self._agent_running),
        )

        # Output window — _OutputWindow handles mouse event gating.
        # Scroll is driven by window.vertical_scroll, NOT buffer cursor position,
        # because prompt_toolkit only adjusts vertical_scroll when the cursor
        # leaves the visible area — making cursor-based scroll unreliable.
        self.output_window = _OutputWindow(
            tui_ref=self,
            content=self._output_control,
            wrap_lines=True,
            allow_scroll_beyond_bottom=False,
            scroll_offsets=ScrollOffsets(top=0, bottom=0),
            right_margins=[ScrollbarMargin(display_arrows=True)],
            style="class:output_area",
        )

        # Token display — fixed text shown at bottom-right
        self._token_text: str = ""
        self._token_control = FormattedTextControl(text=self._get_token_display, focusable=False)
        # Context usage tracking
        self._context_usage_ratio: float = 0.0  # 0.0 ~ 1.0
        self._compact_indicator: str = ""  # 压缩状态指示器

        # Input buffer - handles user input with history
        from .commands import command_registry, SlashCommandCompleter, init_commands
        init_commands()
        self._slash_completer = SlashCommandCompleter(command_registry)
        self._dummy_completer = DummyCompleter()
        self.input_buffer = Buffer(
            name="input_buffer",
            multiline=True,
            history=None,
            completer=DynamicCompleter(lambda: (
                self._slash_completer
                if self.input_buffer.text.startswith('/')
                else self._dummy_completer
            )),
            complete_while_typing=True,
        )

        # Queue for thread-safe output from Agent -> UI
        self._output_queue: queue.Queue = queue.Queue()

        # Scroll tracking
        self._auto_scroll = True      # True = follow latest output

        # Style definitions
        self._style = self._create_style()

        # Layout and key bindings
        self._layout = self._create_layout()
        self._kb = self._create_key_bindings()

        logger.info("TUI initialized")

        # Enable mouse support for scroll + text selection via BufferControl
        # Use PyperclipClipboard for real Windows clipboard integration
        self.app = Application(
            layout=self._layout,
            style=self._style,
            key_bindings=self._kb,
            full_screen=True,
            mouse_support=True,
            clipboard=PyperclipClipboard(),
            output=_create_platform_output(),
        )

        # Input history list for up/down navigation
        self._input_history: list[str] = []
        self._history_index = -1

    # ── Style ────────────────────────────────────────────

    def _create_style(self) -> Style:
        """Define color styles"""
        return Style.from_dict({
            "output_area": "bg:#1a1a2e",
            "input_area": "bg:#16213e",
            "prompt": "fg:cyan bold",
            "divider": "fg:#444444",
            "separator": "fg:cyan",
            "tool_call": "fg:red bold",
            "tool_result": "fg:blue",
            "thinking": "fg:#888888 italic",
            "token_info": "fg:green",
            "user": "fg:cyan bold",
            "error": "fg:red",
            # Context usage colors
            "context_usage_low": "fg:#00ff00",     # green - < 50%
            "context_usage_medium": "fg:yellow",   # yellow - 50-84%
            "context_usage_high": "fg:#ff8800",   # orange - 85-94%
            "context_usage_critical": "fg:red bold",  # red - >= 95%
            "compact_indicator": "fg:cyan italic",
            "autonomous": "fg:magenta bold",
            # 斜杠命令样式
            "command": "fg:green bold",
            "command_header": "fg:cyan bold",
            # 补全菜单样式
            "completion-menu": "bg:#1a1a2e",
            "completion-menu.completion": "fg:white",
            "completion-menu.completion.meta": "fg:#888888",
            "completion-menu.completion.selected": "bg:#16213e fg:cyan bold",
        })

    # ── Helpers ──────────────────────────────────────────

    def _get_token_display(self) -> list[tuple[str, str]]:
        """Return token display as styled fragment (called by FormattedTextControl)"""
        parts = []

        # Context usage progress bar (show when >= 50%)
        if self._context_usage_ratio >= PROGRESS_DISPLAY_THRESHOLD:
            filled = int(self._context_usage_ratio * PROGRESS_BAR_WIDTH)
            bar = "█" * filled + "░" * (PROGRESS_BAR_WIDTH - filled)
            ratio_pct = int(self._context_usage_ratio * 100)

            # 颜色根据使用率变化
            if ratio_pct >= 95:
                color = "context_usage_critical"
            elif ratio_pct >= 85:
                color = "context_usage_high"
            elif ratio_pct >= 50:
                color = "context_usage_medium"
            else:
                color = "context_usage_low"

            parts.append((f"class:{color}", f"[{bar}] {ratio_pct}%"))

        # Token 信息
        if self._token_text:
            parts.append(("class:token_info", f" {self._token_text}"))

        # 压缩指示器
        if self._compact_indicator:
            parts.append(("class:compact_indicator", f" {self._compact_indicator}"))

        # Autonomous mode status
        if self.agent and getattr(self.agent, '_autonomous_running', False):
            pending = self.agent.get_pending_count()
            if pending > 0:
                parts.append(("class:autonomous", f" [AUTO:{pending}]"))
            else:
                parts.append(("class:autonomous", " [AUTO:idle]"))

        return parts if parts else []

    def _get_prompt_fragments(self) -> list[tuple[str, str]]:
        """Return prompt text, changing indicator when agent is running."""
        if self.agent and getattr(self.agent, '_autonomous_running', False):
            return [("class:autonomous", "[AUTO]>")]
        if self._agent_running:
            return [("class:prompt", ">>>")]
        # 斜杠命令模式 — 动态提示符
        if self.input_buffer.text.startswith('/'):
            return [("class:prompt", "/ ")]
        return [("class:prompt", "> ")]

    def _line_to_cursor_pos(self, line: int, full_text: str) -> int:
        """Convert logical line number to character position in buffer text."""
        lines = full_text.split('\n')
        if line <= 0:
            return 0
        if line > len(lines):
            return len(full_text)
        return sum(len(line_text) + 1 for line_text in lines[:line])

    # ── Scroll ───────────────────────────────────────────

    def _scroll_to_bottom(self) -> None:
        """Scroll to latest content and re-enable auto-follow."""
        self._auto_scroll = True
        buf = self._output_buffer
        buf.cursor_position = len(buf.text) if buf.text else 0
        self.app.invalidate()

    def _scroll_up(self, lines: int) -> None:
        """Scroll up N logical lines (keyboard only — large steps)."""
        self._auto_scroll = False
        doc = self._output_buffer.document
        new_line = max(0, doc.cursor_position_row - lines)
        self._output_buffer.cursor_position = self._line_to_cursor_pos(new_line, doc.text)
        self.app.invalidate()

    def _scroll_down(self, lines: int) -> None:
        """Scroll down N logical lines (keyboard only)."""
        if self._auto_scroll:
            return
        doc = self._output_buffer.document
        total = doc.line_count
        new_line = min(total - 1, doc.cursor_position_row + lines)
        if new_line >= total - 1:
            self._scroll_to_bottom()
        else:
            self._output_buffer.cursor_position = self._line_to_cursor_pos(new_line, doc.text)
            self.app.invalidate()

    # ── Fragments ────────────────────────────────────────

    def _prune_fragments(self) -> None:
        """Trim fragment list if it exceeds MAX_FRAGMENTS to prevent unbounded growth."""
        with self._fragments_lock:
            if len(self._fragments) > self.MAX_FRAGMENTS:
                old_count = len(self._fragments)
                self._fragments = self._fragments[-self.MAX_FRAGMENTS:]
                logger.warning(f"Fragments pruned: {old_count} -> {self.MAX_FRAGMENTS}")

    def _rebuild_buffer(self) -> None:
        """Rebuild Buffer document and line_styles from fragments.

        Takes an atomic snapshot of fragments under lock, then builds
        line_styles and full_text from the snapshot to ensure consistency.
        Uses incremental updates when only new fragments are appended.
        """
        with self._fragments_lock:
            fragments = list(self._fragments)
            auto_scroll = self._auto_scroll
            cursor_pos_current = self._output_buffer.cursor_position

        if not fragments:
            if self._line_styles:
                self._line_styles = []
                self._cached_frag_count = 0
                self._cached_full_text = ""
                sel_state = self._output_buffer.selection_state
                self._output_buffer.set_document(Document(""), bypass_readonly=True)
                self._output_buffer.selection_state = sel_state
                self.app.invalidate()
            return

        full_text = ''.join(text for _, text in fragments)

        # Skip rebuild if text unchanged
        if full_text == self._cached_full_text:
            return

        # Determine if we can do incremental update
        can_incremental = (
            self._cached_frag_count > 0
            and len(fragments) >= self._cached_frag_count
            and full_text.startswith(self._cached_full_text)
        )

        if can_incremental:
            old_line_count = len(self._line_styles)
            old_text_len = len(self._cached_full_text)

            # Determine where re-processing starts.
            # If old text did not end with '\n', the last line is incomplete
            # and must be re-processed alongside new text.
            start_offset = old_text_len
            if (self._cached_full_text
                    and not self._cached_full_text.endswith('\n')):
                last_line = self._cached_full_text.split('\n')[-1]
                start_offset = old_text_len - len(last_line)
                old_line_count = max(0, old_line_count - 1)

            new_text = full_text[start_offset:]
            logger.debug(
                f"Incremental rebuild: start_offset={start_offset}, "
                f"old_line_count={old_line_count}, "
                f"new_text_len={len(new_text)}"
            )

            # Find the fragment containing start_offset
            new_styles = []
            frag_idx = 0
            frag_offset = 0
            current_style = ""
            for i, (style, text) in enumerate(fragments):
                if frag_offset + len(text) > start_offset:
                    frag_idx = i
                    current_style = style
                    break
                frag_offset += len(text)

            # Process each character from start_offset onward
            for ch_idx, ch in enumerate(new_text):
                abs_idx = start_offset + ch_idx
                while (frag_idx < len(fragments)
                       and abs_idx >= frag_offset
                           + len(fragments[frag_idx][1])):
                    frag_offset += len(fragments[frag_idx][1])
                    frag_idx += 1
                if frag_idx < len(fragments):
                    current_style = fragments[frag_idx][0]
                if ch == '\n' or abs_idx == len(full_text) - 1:
                    new_styles.append(current_style)

            line_styles = self._line_styles[:old_line_count] + new_styles
        else:
            # Full rebuild -- O(N) in line count
            line_styles = []
            frag_idx = 0
            frag_offset = 0
            current_style = fragments[0][0] if fragments else ""

            lines = full_text.split('\n')
            line_start = 0
            for line_idx, line in enumerate(lines):
                while (frag_idx < len(fragments)
                       and line_start >= frag_offset
                           + len(fragments[frag_idx][1])):
                    frag_offset += len(fragments[frag_idx][1])
                    frag_idx += 1
                if frag_idx < len(fragments):
                    current_style = fragments[frag_idx][0]
                line_styles.append(current_style)
                line_start += len(line) + 1

            # Remove trailing empty string from split if text ends with \n
            if full_text.endswith('\n') and line_styles:
                line_styles = line_styles[:-1]

        # Update cache
        self._cached_frag_count = len(fragments)
        self._cached_full_text = full_text

        # Save scroll position before cursor_pos computation (needed for
        # pruning case where cursor might exceed new document length)
        saved_vertical_scroll = self.output_window.vertical_scroll

        if auto_scroll:
            cursor_pos = len(full_text)
        else:
            if cursor_pos_current <= len(full_text):
                cursor_pos = cursor_pos_current
            else:
                # Pruning shortened the document beyond cursor.
                # Anchor cursor to the first visible line to keep
                # scroll and cursor synchronized.
                cursor_pos = self._line_to_cursor_pos(
                    saved_vertical_scroll, full_text
                )
                logger.debug(
                    f"Pruning cursor anchor: old_pos={cursor_pos_current}, "
                    f"new_doc_len={len(full_text)}, "
                    f"scroll_line={saved_vertical_scroll}, "
                    f"cursor_pos={cursor_pos}"
                )

        # Apply computed state atomically
        self._line_styles = line_styles
        # Preserve selection state when agent is idle and content unchanged
        sel_state = None
        if not self._agent_running:
            sel_state = self._output_buffer.selection_state
            if sel_state is not None:
                current_text = self._output_buffer.document.text
                if current_text != full_text:
                    sel_state = None  # Content changed, selection is stale
        # Use set_document to properly fire on_text_changed event chain
        new_doc = Document(text=full_text, cursor_position=cursor_pos)
        self._output_buffer.set_document(new_doc, bypass_readonly=True)
        # Restore selection only if agent is idle and positions are valid
        if sel_state is not None:
            try:
                if (0 <= sel_state.original_cursor_position <= len(full_text)
                        and 0 <= self._output_buffer.cursor_position <= len(full_text)):
                    self._output_buffer.selection_state = sel_state
            except (AttributeError, TypeError):
                pass
        # Restore scroll position when user has manually scrolled
        if not auto_scroll:
            self.output_window.vertical_scroll = saved_vertical_scroll
        self.app.invalidate()

    # ── Layout ───────────────────────────────────────────

    def _create_layout(self) -> Layout:
        """Create the TUI layout with output above and input below"""
        # Token display window (bottom-right, min-width for visibility)
        token_window = Window(
            content=self._token_control,
            style="class:input_area",
            dont_extend_height=True,
            width=D(min=15),
        )

        # Input row: "> " prompt + editable buffer
        input_row = VSplit([
            Window(
                content=FormattedTextControl(self._get_prompt_fragments, focusable=False),
                width=9,
                style="class:prompt",
                dont_extend_height=True,
            ),
            _InputWindow(
                content=BufferControl(buffer=self.input_buffer, focus_on_click=True),
                style="class:input_area",
                dont_extend_height=True,
                height=D(min=2, max=2),
                wrap_lines=True,
            ),
        ])

        # Token row: spacer (left) + token (right)
        token_row = VSplit([
            Window(width=D(weight=999)),  # Large weight spacer — pushes token to right
            token_window,                 # Token info — rightmost
        ])

        # Full layout: output window | divider | input row | token row
        root = HSplit([
            self.output_window,                                   # Output fills remaining space
            Window(height=1, char="─", style="class:divider"),   # Divider line
            input_row,                                            # Input row (prompt + buffer)
            token_row,                                            # Token row (1 row, right-aligned)
        ])

        return Layout(root, focused_element=self.input_buffer)

    # ── Key Bindings ─────────────────────────────────────

    def _create_key_bindings(self) -> KeyBindings:
        """Create keyboard shortcuts"""
        kb = KeyBindings()

        @kb.add(Keys.ControlC, eager=True)
        def copy_or_quit(event):
            try:
                # 优先处理输入框的选中文本
                if self.input_buffer.selection_state is not None:
                    data = self.input_buffer.copy_selection()
                    if data and data.text:
                        event.app.clipboard.set_data(data)
                    self.input_buffer.selection_state = None
                    event.app.invalidate()
                    return
                # 然后处理输出区的选中文本 — 直接读取 selection_state 并一次性完成复制
                buf = self._output_buffer
                sel_state = buf.selection_state
                if sel_state is not None:
                    data = buf.copy_selection()
                    if data and data.text:
                        event.app.clipboard.set_data(data)
                    buf.selection_state = None
                    event.app.invalidate()
                    return
            except Exception as e:
                logger.error(f"[KEY] Ctrl+C 异常: {type(e).__name__}: {e}", exc_info=True)
            # No selection — exit or cancel agent
            if self._agent_running:
                logger.info("User requested exit via Ctrl+C")
                self._agent_stop_event.set()
                self._output_queue.put(("text", "\n[Cancelling agent...]\n"))
                if hasattr(self, '_cron_scheduler') and self._cron_scheduler:
                    self._cron_scheduler.stop()
                self._exit_requested = True
            else:
                event.app.exit()

        @kb.add(Keys.ControlQ, eager=True)
        def quit(event):
            logger.info("User requested quit via Ctrl+Q")
            if self._agent_running:
                self._agent_stop_event.set()
                self._output_queue.put(("text", "\n[Cancelling agent...]\n"))
                if hasattr(self, '_cron_scheduler') and self._cron_scheduler:
                    self._cron_scheduler.stop()
                self._exit_requested = True
            else:
                event.app.exit()

        @kb.add(Keys.ControlL)
        def clear_output(event):
            with self._fragments_lock:
                self._fragments.clear()
            self._auto_scroll = True
            self._rebuild_buffer()

        @kb.add(Keys.Up)
        def history_up(event):
            if not self._input_history:
                return
            if self._history_index <= 0:
                return  # 已在顶部，不再环绕
            self._history_index -= 1
            self.input_buffer.text = self._input_history[self._history_index]

        @kb.add(Keys.Down)
        def history_down(event):
            if self._input_history and self._history_index < len(self._input_history) - 1:
                self._history_index += 1
                self.input_buffer.text = self._input_history[self._history_index]
            # else: stay at current text, do nothing

        # ── Keyboard Scrolling ──

        @kb.add(Keys.PageUp)
        def pgup(event):
            rows = event.app.renderer.output.get_size().rows
            self._scroll_up(max(3, rows // 2))

        @kb.add(Keys.PageDown)
        def pgdn(event):
            rows = event.app.renderer.output.get_size().rows
            self._scroll_down(max(3, rows // 2))

        @kb.add(Keys.ControlUp)
        def line_up(event):
            self._scroll_up(1)

        @kb.add(Keys.ControlDown)
        def line_down(event):
            self._scroll_down(1)

        @kb.add(Keys.Home)
        def home(event):
            self._auto_scroll = False
            self.output_window.vertical_scroll = 0
            self._output_buffer.cursor_position = 0
            self.app.invalidate()

        @kb.add(Keys.End)
        def end(event):
            self._scroll_to_bottom()

        # Enter: send all content (agent idle)
        @kb.add(Keys.Enter, filter=Condition(lambda: not self._agent_running))
        def enter_send(event):
            """Send all content (Enter)"""
            buf = event.app.current_buffer
            text = buf.text
            if not text:
                return
            if text.strip().lower() in ("exit", "quit", "q"):
                event.app.exit()
                return
            # ── 斜杠命令拦截 — 始终可用 ──
            if text.strip().startswith('/'):
                cmd_text = text.strip()
                buf.text = ""
                self._input_history.append(cmd_text)
                self._history_index = len(self._input_history)
                self._execute_slash_command(cmd_text)
                return
            buf.text = ""
            self._compact_indicator = ""
            self._input_history.append(text)
            self._history_index = len(self._input_history)
            self._output_queue.put(("user_input", text))
            self._scroll_to_bottom()

            if self.agent and self.agent._autonomous_mode:
                self._agent_stop_event.clear()
                self.agent.submit_work(text, source="user")
                self._agent_running = True
                self._agent_generation = self.agent._run_generation
                logger.debug("Agent running: True (autonomous submit)")
                self._output_queue.put(("token_info", f" {config.thinking_indicator}... "))
            else:
                self._agent_running = True
                self._agent_generation = self.agent._run_generation
                logger.debug("Agent running: True (new thread)")
                self._agent_stop_event.clear()
                self._output_queue.put(("token_info", f" {config.thinking_indicator}... "))
                threading.Thread(target=self._run_agent, args=(text,), daemon=True).start()

        # Agent 运行时 — 仅允许斜杠命令，阻塞普通输入
        @kb.add(Keys.Enter, filter=Condition(lambda: self._agent_running))
        def enter_while_busy(event):
            """Agent 运行时允许斜杠命令和转发普通输入到自主循环。"""
            buf = event.app.current_buffer
            text = buf.text
            if not text:
                return
            if text.strip().startswith('/'):
                cmd_text = text.strip()
                buf.text = ""
                self._input_history.append(cmd_text)
                self._history_index = len(self._input_history)
                self._execute_slash_command(cmd_text)
            elif self.agent and self.agent._autonomous_mode:
                buf.text = ""
                self._input_history.append(text)
                self._history_index = len(self._input_history)
                self._output_queue.put(("user_input", text))
                self.agent.submit_work(text, source="user")
                self._scroll_to_bottom()

        # Ctrl+J: insert newline (for multiline input)
        @kb.add(Keys.ControlJ, filter=Condition(lambda: not self._agent_running))
        def ctrl_j_newline(event):
            """Insert newline into input buffer"""
            buf = self.input_buffer
            pos = buf.cursor_position
            new_text = buf.text[:pos] + "\n" + buf.text[pos:]
            new_doc = Document(text=new_text, cursor_position=pos + 1)
            buf.set_document(new_doc, bypass_readonly=True)

        # Ctrl+V: paste from clipboard
        @kb.add(Keys.ControlV, eager=True)
        def ctrl_v_paste(event):
            """Ctrl+V paste from clipboard"""
            try:
                # 清除选择状态（粘贴时替换选中文本）
                self.input_buffer.selection_state = None
                data = event.app.clipboard.get_data()
                if data and hasattr(data, 'text'):
                    event.app.current_buffer.insert_text(_clean_cr(data.text))
                    logger.debug(f"[KEY] Ctrl+V: 粘贴 {len(data.text)} 字符")
            except Exception as e:
                logger.warning(f"[KEY] Ctrl+V 粘贴失败: {e}")

        # Left: move cursor,跨行移动到上一行末尾
        @kb.add(Keys.Left, filter=has_focus(self.input_buffer))
        def move_left(event):
            buf = event.app.current_buffer
            text = buf.text
            pos = buf.cursor_position
            if pos == 0:
                return
            if text[pos - 1] == '\n':
                # 在第二行开头，按左键跳到第一行末尾
                prev_nl = text.rfind('\n', 0, pos - 1)
                if prev_nl >= 0:
                    # 从pos-1向前找第一个非\n字符，即上一行末尾
                    target = pos - 1
                    while target > prev_nl and text[target] == '\n':
                        target -= 1
                    buf._set_cursor_position(max(prev_nl, target))
                else:
                    buf._set_cursor_position(0)
            else:
                buf.cursor_left()

        # Right: move cursor,跨行移动到下一行开头
        @kb.add(Keys.Right, filter=has_focus(self.input_buffer))
        def move_right(event):
            buf = event.app.current_buffer
            text = buf.text
            pos = buf.cursor_position
            if pos >= len(text):
                return
            if text[pos] == '\n':
                # 在第一行末尾，按右键跳到第二行开头
                next_nl = text.find('\n', pos + 1)
                if next_nl == -1:
                    # 没有下一个换行符，到文本末尾
                    buf._set_cursor_position(len(text))
                else:
                    buf._set_cursor_position(pos + 1)
            else:
                buf.cursor_right()

        # Ctrl+A: select all text in input buffer
        @kb.add(Keys.ControlA, filter=has_focus(self.input_buffer))
        def select_all_input(event):
            buf = self.input_buffer
            text_len = len(buf.text)
            if text_len == 0:
                logger.debug("[KEY] Ctrl+A: 输入框为空，忽略")
                return
            from prompt_toolkit.selection import SelectionState
            buf.selection_state = SelectionState(original_cursor_position=0)
            buf.cursor_position = text_len
            logger.debug(f"[KEY] Ctrl+A: 全选 {text_len} 个字符")
            event.app.invalidate()

        # Delete: delete selected text or character after cursor
        @kb.add(Keys.Delete, filter=has_focus(self.input_buffer))
        def delete_selected(event):
            buf = self.input_buffer
            if buf.selection_state is not None:
                buf.cut_selection()
                buf.selection_state = None
                logger.debug("[KEY] Delete: 删除选中文本")
                event.app.invalidate()
            else:
                buf.delete(1)

        # Backspace: delete selected text or character before cursor
        @kb.add(Keys.Backspace, filter=has_focus(self.input_buffer))
        def backspace_selected(event):
            buf = self.input_buffer
            if buf.selection_state is not None:
                buf.cut_selection()
                buf.selection_state = None
                logger.debug("[KEY] Backspace: 删除选中文本")
                event.app.invalidate()
            else:
                buf.delete_before_cursor(1)

        return kb

    # ── Output Handling ──────────────────────────────────

    def _on_output(self, msg_type: str, text: str) -> None:
        """Agent output callback - thread safe via queue"""
        self._output_queue.put((msg_type, text))

    # ── Agent Execution ──────────────────────────────────

    def _run_agent(self, user_input: str) -> None:
        """Run agent in background thread"""
        import time as _time
        t0 = _time.monotonic()
        logger.info(f"Agent execution started: {user_input[:80]}")
        try:
            self.agent.run(user_input)
        except AgentCancelledError:
            self._output_queue.put(("text", "\n[Agent cancelled]\n"))
        except Exception as e:
            logger.error(f"Agent execution failed: {e}", exc_info=True)
            self._output_queue.put(("text", f"\n执行出错: {e}\n"))
        finally:
            elapsed = _time.monotonic() - t0
            logger.info(f"Agent execution finished in {elapsed:.1f}s")
            self._output_queue.put(("_agent_done", str(self.agent._run_generation)))

    def _execute_slash_command(self, cmd_text: str) -> None:
        """解析并执行斜杠命令。主线程同步执行。"""
        logger.info(f"Slash command: {cmd_text}")
        from .commands import command_registry

        parts = cmd_text.split(None, 1)
        cmd_name = parts[0].lstrip('/')  # 去掉前导 /（支持 "/ command" 写法）
        args = parts[1] if len(parts) > 1 else ""

        # 在输出中显示命令
        with self._fragments_lock:
            self._fragments.append(("class:user", f"\n{cmd_text}\n"))

        cmd = command_registry.get(cmd_name)
        if cmd is None:
            with self._fragments_lock:
                logger.warning(f"Unknown command: /{cmd_name}")
                self._fragments.append(("class:error",
                    f"未知命令: /{cmd_name}\n输入 /help 查看可用命令\n"))
            # 失败命令从历史记录中移除
            if self._input_history and self._input_history[-1] == cmd_text:
                self._input_history.pop()
                self._history_index = len(self._input_history)
            self._rebuild_buffer()
            return

        try:
            cmd.handler(self, args)
        except Exception as e:
            logger.error(f"Command error ({cmd_text}): {e}", exc_info=True)
            with self._fragments_lock:
                self._fragments.append(("class:error",
                    f"命令错误: {e}\n"))
            # 执行失败也从历史记录中移除
            if self._input_history and self._input_history[-1] == cmd_text:
                self._input_history.pop()
                self._history_index = len(self._input_history)

        self._scroll_to_bottom()
        self._rebuild_buffer()

    # ── Queue Polling ────────────────────────────────────

    async def _poll_output_queue(self) -> None:
        """Background async task: poll queue and update UI.

        Drains ALL available items each cycle to avoid per-token latency.
        Only rebuilds buffer when fragment-modifying messages are processed.
        """
        while True:
            has_fragment_update = False
            agent_done = False
            while True:
                try:
                    msg_type, text = self._output_queue.get_nowait()
                except queue.Empty:
                    break

                text = _clean_cr(text)

                # Process one message
                if msg_type == "_agent_done":
                    done_gen = int(text) if text.isdigit() else -1
                    if done_gen == self._agent_generation:
                        agent_done = True
                    continue

                elif msg_type == "thinking":
                    with self._fragments_lock:
                        self._fragments.append(("class:thinking", text))
                    has_fragment_update = True
                elif msg_type == "answer_start":
                    with self._fragments_lock:
                        self._fragments.append(("class:separator", "\n━━━ 回答 ━━━\n"))
                    has_fragment_update = True
                elif msg_type == "answer":
                    with self._fragments_lock:
                        self._fragments.append(("", text))
                    has_fragment_update = True
                elif msg_type == "user_input":
                    with self._fragments_lock:
                        self._fragments.append(("class:user", f"\n> {text}\n"))
                    has_fragment_update = True
                elif msg_type == "tool_call":
                    with self._fragments_lock:
                        self._fragments.append(("class:tool_call", text))
                    has_fragment_update = True
                elif msg_type == "tool_result":
                    with self._fragments_lock:
                        self._fragments.append(("class:tool_result", text))
                    has_fragment_update = True
                elif msg_type == "token_info":
                    self._token_text = text
                    self.app.invalidate()
                elif msg_type == "context_usage":
                    try:
                        self._context_usage_ratio = float(text)
                    except (ValueError, IndexError):
                        logger.warning(f"Failed to parse context_usage: {text!r}")
                    self.app.invalidate()
                elif msg_type == "compact":
                    self._compact_indicator = text
                    self.app.invalidate()
                elif msg_type == "cron_notify":
                    with self._fragments_lock:
                        self._fragments.append(("class:autonomous", f"\n[Cron: {text}]\n"))
                    has_fragment_update = True
                elif msg_type == "sleep_status":
                    with self._fragments_lock:
                        self._fragments.append(("class:thinking", f"\n[Sleep: {text}]\n"))
                    has_fragment_update = True
                elif msg_type == "command":
                    with self._fragments_lock:
                        self._fragments.append(("class:command", text))
                    has_fragment_update = True
                elif msg_type == "error":
                    with self._fragments_lock:
                        self._fragments.append(("class:error", text))
                    has_fragment_update = True
                elif msg_type == "_autonomous_done":
                    self._agent_running = False
                    logger.debug("Agent running: False (_autonomous_done)")
                    if self._exit_requested:
                        self._exit_requested = False
                        self.app.exit()
                else:
                    with self._fragments_lock:
                        self._fragments.append(("", text))
                    has_fragment_update = True

            # After draining: prune fragments and rebuild buffer only if needed
            if has_fragment_update:
                self._prune_fragments()
                self._rebuild_buffer()

            # Set agent_running=False after buffer rebuild to preserve selection
            if agent_done:
                self._agent_running = False
                logger.debug("Agent running: False (_agent_done)")
                if self._exit_requested:
                    self._exit_requested = False
                    self.app.exit()

            await asyncio.sleep(POLL_INTERVAL)

    # ── Welcome ──────────────────────────────────────────

    def _print_welcome(self) -> None:
        """Output welcome message"""
        scroll_hint = "Mouse wheel / PgUp:PgDn:scroll"
        lines = [
            "=" * 60,
            "  Watermelon - TUI AGI Interaction Tool",
            f"  Model: {config.model}",
            f"  {scroll_hint}  Ctrl+C:quit",
        ]
        lines.append("  Mode: Autonomous (Ctrl+C to stop)")
        lines.extend([
            "=" * 60,
            "",
            "I fully understand and will strictly adhere to all Core Operational Guidelines.",
            "",
        ])
        with self._fragments_lock:
            self._fragments.append(("", "\n".join(lines)))

    # ── Run ──────────────────────────────────────────────

    def run(self) -> None:
        """Run the TUI Application"""
        logger.info("TUI application starting")

        # Register SIGINT handler to ensure Ctrl+C sets stop_event
        import signal

        def _sigint_handler(signum, frame):
            logger.info("SIGINT signal received")
            self._agent_stop_event.set()
            raise KeyboardInterrupt("SIGINT received")

        signal.signal(signal.SIGINT, _sigint_handler)
        logger.debug("SIGINT handler registered")

        self.agent = Agent(
            output_callback=self._on_output,
            stop_event=self._agent_stop_event,
        )
        logger.info("Agent created")
        self._print_welcome()
        self._rebuild_buffer()

        from .cron.scheduler import CronScheduler
        self._cron_scheduler = CronScheduler(
            self.agent, config.cron_tasks,
            tick_interval_minutes=config.tick_interval_minutes
        )
        self._cron_scheduler.start()
        logger.info("CronScheduler started")
        with self._fragments_lock:
            self._fragments.append(("class:autonomous",
                f"\n[自主模式已启用 — {len(config.cron_tasks)} 个定时任务]\n"))

        async def _main():
            self._poll_task = asyncio.create_task(self._poll_output_queue())
            try:
                await self.app.run_async()
            finally:
                if self._poll_task:
                    self._poll_task.cancel()
                if self._cron_scheduler:
                    self._cron_scheduler.stop()

        try:
            asyncio.run(_main())
        except KeyboardInterrupt:
            if self._cron_scheduler:
                self._cron_scheduler.stop()
        finally:
            if self._cron_scheduler:
                self._cron_scheduler.stop()


def run_tui() -> None:
    """Entry point for TUI"""
    try:
        tui = SimpleTUI()
        tui.run()
    except KeyboardInterrupt:
        logger.info("TUI exited via KeyboardInterrupt")
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        logger.error(f"TUI fatal error: {e}\n{tb}")
    finally:
        logger.info("TUI exited")