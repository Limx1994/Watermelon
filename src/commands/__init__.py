"""斜杠命令系统"""

from .registry import CommandRegistry, SlashCommand, command_registry
from .completer import SlashCommandCompleter
from .core import register_core_commands


def init_commands():
    """注册所有内置命令。TUI 启动时调用一次。"""
    register_core_commands(command_registry)
