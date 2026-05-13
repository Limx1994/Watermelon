"""斜杠命令注册表"""

import logging
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class SlashCommand:
    """单个斜杠命令定义"""
    name: str
    description: str
    handler: Callable  # handler(tui, args) -> None
    arg_spec: str = ""
    enabled: bool = True


class CommandRegistry:
    """命令注册表 — 管理所有已注册的斜杠命令"""

    def __init__(self):
        self._commands: Dict[str, SlashCommand] = {}

    def register(self, name: str, description: str, handler: Callable,
                 arg_spec: str = "", enabled: bool = True) -> None:
        logger.debug(f"Command registered: {name}")
        self._commands[name] = SlashCommand(
            name=name, description=description,
            handler=handler, arg_spec=arg_spec, enabled=enabled,
        )

    def get(self, name: str) -> Optional[SlashCommand]:
        return self._commands.get(name)

    def list_commands(self) -> List[SlashCommand]:
        return sorted(self._commands.values(), key=lambda c: c.name)


command_registry = CommandRegistry()
