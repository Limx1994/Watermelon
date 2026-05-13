"""命令系统公共工具函数"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..tui import SimpleTUI


def output(tui: "SimpleTUI", text: str, style: str = "class:command") -> None:
    """向输出区域追加一条消息"""
    with tui._fragments_lock:
        tui._fragments.append((style, text))
