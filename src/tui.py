"""TUI interface using prompt_toolkit Application + Layout"""

import asyncio
import logging
import queue
import threading
from typing import Optional

from prompt_toolkit.application import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.clipboard.pyperclip import PyperclipClipboard  # Windows system clipboard
from prompt_toolkit.document import Document
from prompt_toolkit.filters import Condition
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys
from prompt_toolkit.layout import Layout, HSplit, VSplit, Window, ScrollOffsets
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.layout.dimension import LayoutDimension as D
from prompt_toolkit.layout.margins import ScrollbarMargin
from prompt_toolkit.lexers import Lexer
from prompt_toolkit.mouse_events import MouseEventType
from prompt_toolkit.styles import Style

from .agent import Agent, AgentCancelledError
from .config import config
from .memory import memory

logger = logging.getLogger(__name__)


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
        info = self.render_info
        if info is None or info.vertical_scroll <= 0:
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
        if info.vertical_scroll >= info.content_height - info.window_height:
            # At visual bottom — pin cursor to absolute end for precision
            buf = self._tui._output_buffer
            buf.cursor_position = len(buf.text) if buf.text else 0
            self._tui._auto_scroll = True
            return
        self.content.move_cursor_down()
        self.vertical_scroll += 1


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

        # Agent safety
        self._agent_running = False
        self._agent_stop_event = threading.Event()

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

        # Input buffer - handles user input with history
        self.input_buffer = Buffer(
            name="input_buffer",
            multiline=True,
            history=None,
        )

        # Queue for thread-safe output from Agent -> UI
        self._output_queue: queue.Queue = queue.Queue()

        # Scroll tracking
        self._auto_scroll = True      # True = follow latest output

        # Style definitions
        self._style = self._create_style()

        # Layout and key bindings
        # Filter for Ctrl+C: skip exit if output has selection (allows copy)
        self._exit_filter = Condition(lambda: not self._output_has_selection())
        self._layout = self._create_layout()
        self._kb = self._create_key_bindings()

        # Enable mouse support for scroll + text selection via BufferControl
        # Use PyperclipClipboard for real Windows clipboard integration
        self.app = Application(
            layout=self._layout,
            style=self._style,
            key_bindings=self._kb,
            full_screen=True,
            mouse_support=True,
            clipboard=PyperclipClipboard(),
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
        })

    # ── Helpers ──────────────────────────────────────────

    def _get_token_display(self) -> list[tuple[str, str]]:
        """Return token display as styled fragment (called by FormattedTextControl)"""
        if not self._token_text:
            return []
        return [("class:token_info", f" {self._token_text} ")]

    def _get_prompt_fragments(self) -> list[tuple[str, str]]:
        """Return prompt text, changing indicator when agent is running."""
        if self._agent_running:
            return [("class:prompt", ">>>")]
        return [("class:prompt", "> ")]

    def _output_has_selection(self) -> bool:
        """Check if output buffer has text selection (for Ctrl+C copy vs exit)."""
        return self._output_buffer.selection_state is not None

    def _line_to_cursor_pos(self, line: int, full_text: str) -> int:
        """Convert logical line number to character position in buffer text."""
        lines = full_text.split('\n')
        if line <= 0:
            return 0
        if line >= len(lines):
            return len(full_text)
        return sum(len(l) + 1 for l in lines[:line])

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
                self._fragments = self._fragments[-self.MAX_FRAGMENTS:]

    def _rebuild_buffer(self) -> None:
        """Rebuild Buffer document and line_styles from fragments."""
        with self._fragments_lock:
            fragments = list(self._fragments)

        if not fragments:
            self._line_styles = []
            self._output_buffer.reset(Document(""), append_to_history=False)
            self.app.invalidate()
            return

        full_text = ''.join(text for _, text in fragments)

        # Build line_styles: each \n completes a line styled by the current fragment
        self._line_styles = []
        for style, text in fragments:
            self._line_styles.extend([style] * text.count('\n'))
        self._line_styles.append(fragments[-1][0])  # style for final line

        if self._auto_scroll:
            cursor_pos = len(full_text)
        else:
            # Preserve cursor position (pinned to vertical_scroll top line).
            # New content only appends at the end, so existing line offsets
            # are stable and the stored cursor_position remains valid.
            cursor_pos = min(self._output_buffer.cursor_position, len(full_text))

        self._output_buffer.reset(
            Document(text=full_text, cursor_position=cursor_pos),
            append_to_history=False,
        )
        if self._auto_scroll:
            self._output_buffer.selection_state = None

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
                width=3,
                style="class:prompt",
                dont_extend_height=True,
            ),
            Window(
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
            # If output has selection, copy text instead of exiting
            if self._output_has_selection():
                buf = self._output_buffer
                if buf.selection_state is not None:
                    data = buf.copy_selection()
                    if data and data.text:
                        event.app.clipboard.set_data(data)
                return
            if self._agent_running:
                self._agent_stop_event.set()
                self._output_queue.put(("text", "\n[Cancelling agent...]\n"))
            event.app.exit()

        @kb.add(Keys.ControlQ, eager=True)
        def quit(event):
            if self._agent_running:
                self._agent_stop_event.set()
                self._output_queue.put(("text", "\n[Cancelling agent...]\n"))
            event.app.exit()

        @kb.add(Keys.ControlL)
        def clear_output(event):
            with self._fragments_lock:
                self._fragments.clear()
            self._auto_scroll = True
            self._rebuild_buffer()
            memory.clear()

        @kb.add(Keys.Up)
        def history_up(event):
            if not self._input_history:
                return
            if self._history_index <= 0:
                self._history_index = len(self._input_history) - 1
            else:
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

        # Block Enter while agent is running
        @kb.add(Keys.Enter, filter=Condition(lambda: self._agent_running))
        def enter_while_busy(event):
            """Prevent Enter from being processed while agent is running."""
            pass

        # Enter: send all content
        @kb.add(Keys.Enter, filter=Condition(lambda: not self._agent_running))
        def enter_send(event):
            """Send all content (Enter)"""
            buf = event.app.current_buffer
            text = buf.text
            if not text:
                return
            buf.text = ""
            self._input_history.append(text)
            self._history_index = len(self._input_history)
            self._output_queue.put(("user_input", text))
            self._scroll_to_bottom()
            self._agent_running = True
            self._agent_stop_event.clear()
            self._output_queue.put(("token_info", f" {config.thinking_indicator}... "))
            threading.Thread(target=self._run_agent, args=(text,), daemon=True).start()

        # Ctrl+J: insert newline (for multiline input)
        @kb.add(Keys.ControlJ, filter=Condition(lambda: not self._agent_running))
        def ctrl_j_newline(event):
            """Insert newline into input buffer"""
            from prompt_toolkit.document import Document
            buf = self.input_buffer
            pos = buf.cursor_position
            new_text = buf.text[:pos] + "\n" + buf.text[pos:]
            new_doc = Document(text=new_text, cursor_position=pos + 1)
            buf.set_document(new_doc, bypass_readonly=True)

        # Left: move cursor,跨行移动到上一行末尾
        @kb.add(Keys.Left)
        def move_left(event):
            buf = event.app.current_buffer
            text = buf.text
            pos = buf.cursor_position
            if pos == 0:
                return
            if text[pos - 1] == '\n':
                # 在第二行开头，按左键跳到第一行末尾
                prev_nl = text.rfind('\n', 0, pos - 1)  # 找上一个换行符
                if prev_nl >= 0:
                    # 上一行末尾是 prev_nl 之后到当前换行符之前的最长行
                    line_end = prev_nl + 1
                    while line_end < pos - 1 and text[line_end] == '\n':
                        line_end += 1
                    buf._set_cursor_position(line_end - 1)
                else:
                    buf._set_cursor_position(0)
            else:
                buf.cursor_left()

        # Right: move cursor,跨行移动到下一行开头
        @kb.add(Keys.Right)
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

        return kb

    # ── Input Handling ───────────────────────────────────

    def _on_submit(self, buf: Buffer) -> bool:
        """Called when user presses Ctrl+J (send) in the input buffer"""
        text = buf.text
        if not text:
            return True

        buf.text = ""

        # Reject concurrent agent runs
        if self._agent_running:
            self._output_queue.put(("text", "\n[Agent is already running -- wait for completion]\n"))
            return True

        self._input_history.append(text)
        self._history_index = len(self._input_history)

        if text.lower() in ["exit", "quit", "q"]:
            self.app.exit()
            return True

        # Queue user input for thread-safe processing in poll loop
        self._output_queue.put(("user_input", text))
        self._scroll_to_bottom()

        self._agent_running = True
        self._agent_stop_event.clear()
        self._output_queue.put(("token_info", f" {config.thinking_indicator}... "))
        threading.Thread(target=self._run_agent, args=(text,), daemon=True).start()
        return True

    # ── Output Handling ──────────────────────────────────

    def _on_output(self, msg_type: str, text: str) -> None:
        """Agent output callback - thread safe via queue"""
        self._output_queue.put((msg_type, text))

    # ── Agent Execution ──────────────────────────────────

    def _run_agent(self, user_input: str) -> None:
        """Run agent in background thread"""
        try:
            self.agent.run(user_input)
        except AgentCancelledError:
            self._output_queue.put(("text", "\n[Agent cancelled]\n"))
        except Exception as e:
            self._output_queue.put(("text", f"\nError: {e}\n"))
        finally:
            self._output_queue.put(("_agent_done", ""))

    # ── Queue Polling ────────────────────────────────────

    async def _poll_output_queue(self) -> None:
        """Background async task: poll queue and update UI.

        Drains ALL available items each cycle to avoid per-token latency.
        """
        while True:
            processed_any = False
            while True:
                try:
                    msg_type, text = self._output_queue.get_nowait()
                    processed_any = True
                except queue.Empty:
                    break

                # Process one message
                if msg_type == "_agent_done":
                    self._agent_running = False
                    continue

                elif msg_type == "thinking":
                    with self._fragments_lock:
                        self._fragments.append(("class:thinking", text))
                elif msg_type == "answer_start":
                    with self._fragments_lock:
                        self._fragments.append(("class:separator", "\n━━━ 回答 ━━━\n"))
                elif msg_type == "answer":
                    with self._fragments_lock:
                        self._fragments.append(("", text))
                elif msg_type == "user_input":
                    with self._fragments_lock:
                        self._fragments.append(("class:user", f"\n> {text}\n"))
                elif msg_type == "token_info":
                    self._token_text = text
                else:
                    with self._fragments_lock:
                        self._fragments.append(("", text))

            # After draining: prune fragments and rebuild buffer + line styles
            if processed_any:
                self._prune_fragments()
                self._rebuild_buffer()

            await asyncio.sleep(0.03)

    # ── Welcome ──────────────────────────────────────────

    def _print_welcome(self) -> None:
        """Output welcome message"""
        scroll_hint = "Mouse wheel / PgUp:PgDn:scroll"
        lines = [
            "=" * 60,
            "  AGImyCLI - TUI AGI Interaction Tool",
            f"  Model: {config.model}",
            f"  {scroll_hint}  Ctrl+C:quit",
            "=" * 60,
            "",
            "I fully understand and will strictly adhere to all Core Operational Guidelines.",
            "",
        ]
        self._fragments.append(("", "\n".join(lines)))

    # ── Run ──────────────────────────────────────────────

    def run(self) -> None:
        """Run the TUI Application"""
        self.agent = Agent(
            output_callback=self._on_output,
            stop_event=self._agent_stop_event,
        )
        self._print_welcome()
        self._rebuild_buffer()

        async def _main():
            asyncio.create_task(self._poll_output_queue())
            await self.app.run_async()

        try:
            asyncio.run(_main())
        except KeyboardInterrupt:
            pass


def run_tui() -> None:
    """Entry point for TUI"""
    try:
        tui = SimpleTUI()
        tui.run()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        import traceback
        traceback.print_exc()