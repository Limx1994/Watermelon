"""内置斜杠命令实现"""

import json
import logging
import threading
from typing import TYPE_CHECKING

from .utils import output as _output

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ..core.tui import SimpleTUI

# 角色映射常量
_ROLE_MAP = {"user": "用户", "assistant": "助手", "system": "系统", "tool": "工具"}


# ── /help ──────────────────────────────────────────────────

def cmd_help(tui: "SimpleTUI", args: str) -> None:
    from .registry import command_registry
    logger.debug("Command: /help")
    commands = command_registry.list_commands()
    lines = [
        "\n┌─────────────────────────────────────────────┐",
        "│  可用命令                                    │",
        "├─────────────────────────────────────────────┤\n",
    ]
    for cmd in commands:
        spec = f" {cmd.arg_spec}" if cmd.arg_spec else ""
        pad = 18 - len(cmd.name) - len(spec)
        pad = max(pad, 2)
        lines.append(f"  /{cmd.name}{spec}{' ' * pad}{cmd.description}\n")
    lines.append("└─────────────────────────────────────────────┘")
    lines.append("  输入 /命令名 参数  执行命令\n")
    lines.append("  Tab 键可自动补全命令名\n")
    _output(tui, "".join(lines))


# ── /clear ─────────────────────────────────────────────────

def cmd_clear(tui: "SimpleTUI", args: str) -> None:
    from ..memory.memory import memory
    with tui._fragments_lock:
        tui._fragments.clear()
    tui._auto_scroll = True
    memory.clear()
    logger.info("Screen and memory cleared")
    _output(tui, "\n屏幕和对话记忆已清除\n")


# ── /model ─────────────────────────────────────────────────

def cmd_model(tui: "SimpleTUI", args: str) -> None:
    from ..core.config import config
    if not args.strip():
        _output(tui, f"\n当前模型: {config.model}\n")
        return
    model_name = args.strip()
    logger.info(f"Model switch: {model_name}")
    try:
        if tui.agent and tui.agent.llm:
            tui.agent.llm.switch_model(model_name)
        config.set_model(model_name)
        _output(tui, f"\n模型已切换为: {model_name}\n")
    except Exception as e:
        logger.error(f"Model switch failed: {e}", exc_info=True)
        _output(tui, "\n模型切换失败，请查看日志\n", "class:error")


# ── /config ────────────────────────────────────────────────

def cmd_config(tui: "SimpleTUI", args: str) -> None:
    from ..core.config import config
    logger.debug("Command: /config")
    # 隐藏敏感信息
    display_config = config.to_dict()
    if "openai" in display_config and "api_key" in display_config["openai"]:
        key = display_config["openai"]["api_key"]
        if key:
            if len(key) > 8:
                display_config["openai"]["api_key"] = key[:4] + "****" + key[-4:]
            else:
                display_config["openai"]["api_key"] = "****"
    text = json.dumps(display_config, indent=2, ensure_ascii=False)
    _output(tui, f"\n当前配置:\n{text}\n")


# ── /history ───────────────────────────────────────────────

def cmd_history(tui: "SimpleTUI", args: str) -> None:
    from ..memory.memory import memory
    logger.debug("Command: /history")
    messages = memory.get_messages()
    if not messages:
        _output(tui, "\n对话历史为空\n")
        return
    lines = [f"\n对话历史 ({len(messages)} 条消息):\n"]
    for i, msg in enumerate(messages, 1):
        role = _ROLE_MAP.get(msg.get("role", ""), msg.get("role", "?"))
        content = msg.get("content", "")
        if isinstance(content, list):
            content = str(content)
        preview = content[:80].replace("\n", " ") if content else "(空)"
        if len(content) > 80:
            preview += "..."
        lines.append(f"  {i:3d}. [{role}] {preview}\n")
    _output(tui, "".join(lines))


# ── /save ──────────────────────────────────────────────────

def cmd_save(tui: "SimpleTUI", args: str) -> None:
    from ..memory.memory import memory
    logger.info("Session save requested")
    path = memory.save_current_session()
    if path:
        _output(tui, f"\n会话已保存: {path}\n")
    else:
        _output(tui, "\n没有可保存的对话内容\n", "class:error")


# ── /load ──────────────────────────────────────────────────

def cmd_load(tui: "SimpleTUI", args: str) -> None:
    from ..memory.memory import memory
    logger.debug(f"Command: /load {args.strip()}")
    sessions = memory.list_sessions()
    if not sessions:
        _output(tui, "\n没有已保存的会话\n")
        return

    if not args.strip():
        # 列出可用会话
        lines = [f"\n已保存的会话 ({len(sessions)} 个):\n"]
        for i, s in enumerate(sessions, 1):
            lines.append(f"  {i}. {s['session_id']} ({s['message_count']} 条消息, {s['saved_at'][:19]})\n")
        lines.append("\n  用法: /load <session_id 或序号>\n")
        _output(tui, "".join(lines))
        return

    # 按序号或 session_id 查找
    keyword = args.strip()
    target = None
    try:
        idx = int(keyword) - 1
        if 0 <= idx < len(sessions):
            target = sessions[idx]
    except ValueError:
        for s in sessions:
            if s["session_id"] == keyword:
                target = s
                break

    if not target:
        _output(tui, f"\n未找到匹配的会话: {keyword}\n", "class:error")
        return

    # 加载会话
    history_dir = memory._history_dir
    filepath = history_dir / target["filename"]
    if memory.load_session(str(filepath)):
        logger.info(f"Session loaded: {target['session_id']}")
        _output(tui, f"\n已加载会话: {target['session_id']} ({target['message_count']} 条消息)\n")
        # 显示前 5 条消息摘要
        recent = memory.get_context(5)
        if recent:
            lines = ["\n最近消息:\n"]
            for msg in recent:
                role = _ROLE_MAP.get(msg.get("role", ""), msg.get("role", "?"))
                content = (msg.get("content", "") or "")
                if isinstance(content, list):
                    content = str(content)
                content = content[:80].replace("\n", " ")
                lines.append(f"  [{role}] {content}\n")
            _output(tui, "".join(lines))
    else:
        _output(tui, f"\n加载会话失败: {filepath}\n", "class:error")


# ── /memory ────────────────────────────────────────────────

def cmd_memory(tui: "SimpleTUI", args: str) -> None:
    from ..memory.memory import memory
    logger.debug(f"Command: /memory {args.strip()}")
    count = 20
    if args.strip():
        try:
            count = int(args.strip())
            if count <= 0:
                count = 20
        except ValueError:
            _output(tui, f"\n无效参数: {args.strip()}，使用默认值 20\n", "class:error")
            count = 20
    messages = memory.get_context(count)
    if not messages:
        _output(tui, "\n内存中没有消息\n")
        return
    lines = [f"\n最近 {len(messages)} 条记忆:\n"]
    for msg in messages:
        role = _ROLE_MAP.get(msg.get("role", ""), msg.get("role", "?"))
        content = msg.get("content", "")
        if isinstance(content, list):
            content = str(content)
        preview = content[:100].replace("\n", " ") if content else "(空)"
        if len(content) > 100:
            preview += "..."
        lines.append(f"  [{role}] {preview}\n")
    # 持久化记忆提示
    try:
        from ..memory.persistent_memory import persistent_memory
        pm_count = persistent_memory.count()
        if pm_count > 0:
            lines.append(f"\n  提示: 还有 {pm_count} 条持久化记忆，用 /remember 查看\n")
    except Exception:
        pass
    _output(tui, "".join(lines))


# ── /compact ───────────────────────────────────────────────

def cmd_compact(tui: "SimpleTUI", args: str) -> None:
    if not tui.agent or not tui.agent._compact_engine:
        _output(tui, "\nAgent 未初始化，无法压缩\n", "class:error")
        return

    logger.info("Manual compact triggered")
    _output(tui, "\n正在压缩上下文...\n")

    def _run():
        try:
            from ..memory.memory import CompactEngine
            # 获取 _run_lock 防止与 agent._run_inner() 并发修改 history
            with tui.agent._run_lock:
                result = tui.agent._compact_engine.compact(
                    CompactEngine.LEVEL_FULL, tui.agent.llm
                )
            if result.get("compacted"):
                logger.info(f"Manual compact done: saved ~{result['tokens_saved']} tokens, removed {result['messages_removed']} msgs")
                tui._output_queue.put(("command",
                    f"\n压缩完成: 节省约 {result['tokens_saved']} tokens, "
                    f"移除 {result['messages_removed']} 条消息\n"))
            else:
                logger.info("Manual compact: no compression needed")
                tui._output_queue.put(("command", "\n无需压缩\n"))
            # 清除压缩指示器
            tui._output_queue.put(("compact", ""))
        except Exception as e:
            logger.error(f"Manual compact failed: {e}", exc_info=True)
            tui._output_queue.put(("error", "\n压缩失败，请查看日志\n"))

    threading.Thread(target=_run, daemon=True).start()


# ── /mcp ───────────────────────────────────────────────────

def cmd_mcp(tui: "SimpleTUI", args: str) -> None:
    from ..core.config import config
    servers = config.mcp_servers
    if not servers:
        _output(tui, "\n未配置 MCP 服务器\n")
        return
    lines = [f"\nMCP 服务器 ({len(servers)} 个):\n"]
    for s in servers:
        name = s.get("name", "unknown")
        stype = s.get("type", "stdio")
        url = s.get("url", "")
        cmd = s.get("command", "")
        status = "已配置"
        # 检查连接状态
        if tui.agent and tui.agent.mcp_manager:
            client = tui.agent.mcp_manager.get_client(name)
            if client and getattr(client, '_connected', False):
                status = "已连接"
            elif client:
                status = "已断开"
        detail = url or cmd or "(无)"
        lines.append(f"  {name} [{stype}] — {status}\n")
        lines.append(f"    {detail}\n")
    _output(tui, "".join(lines))


# ── /tools ─────────────────────────────────────────────────

def cmd_tools(tui: "SimpleTUI", args: str) -> None:
    from ..core.config import config
    from ..tools.registry import registry
    enabled = config.enabled_tools
    all_tools = registry.list_tools()
    all_tools_set = set(all_tools)
    enabled_set = set(enabled)

    lines = [f"\n已启用的工具 ({len(enabled)} 个):\n"]
    for name in enabled:
        tool = registry.get(name)
        desc = tool.description if tool else "(未加载)"
        lines.append(f"  {name:<16s} {desc}\n")

    builtin = [n for n in all_tools if n not in enabled_set]
    if builtin:
        lines.append(f"\n内置工具 ({len(builtin)} 个):\n")
        for name in builtin:
            tool = registry.get(name)
            desc = tool.description if tool else ""
            lines.append(f"  {name:<16s} {desc}\n")

    disabled = [n for n in enabled if n not in all_tools_set]
    if disabled:
        lines.append(f"\n  未加载: {', '.join(disabled)}\n")
    _output(tui, "".join(lines))


# ── /system ────────────────────────────────────────────────

def cmd_system(tui: "SimpleTUI", args: str) -> None:
    from ..core.config import config
    prompt = config.get_system_prompt()
    max_len = 2000
    if len(prompt) > max_len:
        prompt = prompt[:max_len] + f"\n\n... (截断，共 {len(prompt)} 字符)"
    _output(tui, f"\n系统提示词:\n{'─' * 40}\n{prompt}\n{'─' * 40}\n")


# ── /version ───────────────────────────────────────────────

def cmd_version(tui: "SimpleTUI", args: str) -> None:
    from ..core.config import config
    lines = [
        "\n┌─────────────────────────────────────────────┐",
        "│  AGImyCLI - TUI AGI Interaction Tool         │",
        "├─────────────────────────────────────────────┤\n",
        f"  模型:      {config.model}\n",
        f"  API:       {config.base_url}\n",
        f"  上下文窗口: {config.context_window // 1000}K tokens\n",
        f"  最大输出:   {config.max_output_tokens} tokens\n",
        f"  温度:      {config.temperature}\n",
        f"  推理深度:   {config.reasoning_effort}\n",
        "└─────────────────────────────────────────────┘\n",
    ]
    _output(tui, "".join(lines))


# ── /exit ──────────────────────────────────────────────────

def cmd_exit(tui: "SimpleTUI", args: str) -> None:
    logger.info("Exit command received")
    if tui.app:
        tui.app.exit()
    else:
        import sys
        sys.exit(0)


# ── /remember ──────────────────────────────────────────────

def cmd_remember(tui: "SimpleTUI", args: str) -> None:
    from ..memory.persistent_memory import persistent_memory
    arg = args.strip()
    logger.info(f"Command: /remember {arg}")

    if not arg:
        memories = persistent_memory.load_all()
        logger.debug(f"/remember list -> {len(memories)} memories")
        if not memories:
            _output(tui, "\n没有持久化记忆\n")
            return
        lines = [f"\n持久化记忆 ({len(memories)} 条):\n"]
        for mem in memories:
            age = mem.get("age_days", 0)
            age_str = f"{age}天前" if age > 0 else "今天"
            scope_tag = mem.get("scope", "?")
            preview = mem.get("content", "")[:80].replace("\n", " ")
            if len(mem.get("content", "")) > 80:
                preview += "..."
            lines.append(
                f"  [{mem.get('type', '?')}/{scope_tag}] {mem.get('name', '?')}\n"
                f"    {mem.get('description', '(无描述)')}\n"
                f"    更新: {age_str} | 内容: {preview}\n"
            )
        _output(tui, "".join(lines))
    else:
        mem = persistent_memory.load(arg)
        if not mem:
            logger.info(f"/remember: '{arg}' not found")
            _output(tui, f"\n未找到记忆: {arg}\n", "class:error")
            return
        logger.debug(f"/remember load '{arg}' -> found")
        lines = [
            f"\n记忆: {mem.get('name', '?')}\n",
            f"  类型: {mem.get('type', '?')}\n",
            f"  作用域: {mem.get('scope', '?')}\n",
            f"  描述: {mem.get('description', '(无)')}\n",
            f"  创建: {mem.get('created', '?')}\n",
            f"  更新: {mem.get('updated', '?')}\n",
            f"\n--- 内容 ---\n{mem.get('content', '')}\n---\n",
        ]
        _output(tui, "".join(lines))


# ── /forget ────────────────────────────────────────────────

def cmd_forget(tui: "SimpleTUI", args: str) -> None:
    from ..memory.persistent_memory import persistent_memory
    name = args.strip()
    if not name:
        _output(tui, "\n用法: /forget <记忆名称>\n", "class:error")
        return
    logger.info(f"Command: /forget {name}")
    if persistent_memory.delete(name):
        _output(tui, f"\n已删除记忆: {name}\n")
    else:
        logger.warning(f"/forget failed: memory '{name}' not found")
        _output(tui, f"\n未找到记忆: {name}\n", "class:error")


# ── 注册 ───────────────────────────────────────────────────

def register_core_commands(registry) -> None:
    """注册所有内置命令"""
    logger.debug("Registering core commands")
    registry.register("help", "显示所有可用命令", cmd_help)
    registry.register("clear", "清除屏幕和对话记忆", cmd_clear)
    registry.register("model", "显示或切换当前模型", cmd_model, arg_spec="[name]")
    registry.register("config", "显示当前配置", cmd_config)
    registry.register("history", "显示对话历史", cmd_history)
    registry.register("save", "保存当前会话", cmd_save)
    registry.register("load", "加载已保存的会话", cmd_load, arg_spec="[id]")
    registry.register("memory", "显示最近记忆内容", cmd_memory, arg_spec="[count]")
    registry.register("compact", "手动压缩上下文", cmd_compact)
    registry.register("mcp", "显示 MCP 服务器状态", cmd_mcp)
    registry.register("tools", "列出可用工具", cmd_tools)
    registry.register("system", "显示系统提示词", cmd_system)
    registry.register("version", "显示版本信息", cmd_version)
    registry.register("remember", "显示持久化记忆列表或详情", cmd_remember, arg_spec="[name]")
    registry.register("forget", "删除指定持久化记忆", cmd_forget, arg_spec="<name>")
    registry.register("exit", "退出程序", cmd_exit)
