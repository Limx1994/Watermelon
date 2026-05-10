"""斜杠命令补全器"""

from prompt_toolkit.completion import Completer, Completion


class SlashCommandCompleter(Completer):
    """斜杠命令补全器 — 仅在输入以 / 开头时激活"""

    def __init__(self, registry):
        self._registry = registry

    def get_completions(self, document, complete_event):
        if document.cursor_position_row > 0:
            return
        first_line = document.text_before_cursor.split('\n')[0]
        if not first_line.startswith('/'):
            return

        parts = first_line.split()
        cmd_part = parts[0] if parts else '/'

        if len(parts) <= 1:
            prefix = cmd_part[1:]
            for cmd in self._registry.list_commands():
                if cmd.name.startswith(prefix):
                    yield Completion(
                        text='/' + cmd.name,
                        start_position=-len(cmd_part),
                        display_meta=cmd.description,
                    )
