"""内置斜杠命令实现"""

import json
import logging
import threading
from typing import TYPE_CHECKING

from .utils import output as _output

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ..tui import SimpleTUI

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
    """清除屏幕、对话记忆和所有会话状态。

    无论 Agent 是否运行均可执行。
    保留: 输入历史、MCP 连接、持久化记忆。
    """
    from ..memory import memory
    import queue as _queue
    logger.info("Command: /clear")

    # ── 1. 停止正在运行的 Agent ──────────────────────────
    agent_was_running = tui._agent_running
    if agent_was_running:
        tui._agent_stop_event.set()
        tui._agent_running = False
        tui._exit_requested = False
        logger.info("Agent 停止信号已发送 (/clear)")

    # ── 2. 保存旧会话 ID（memory.clear() 会重新生成）────
    old_session_id = memory._session_id

    # ── 3. 重置 TUI 显示状态 ─────────────────────────────
    tui._token_text = ""
    tui._context_usage_ratio = 0.0
    tui._compact_indicator = ""

    # ── 4. 清除屏幕输出 ─────────────────────────────────
    with tui._fragments_lock:
        tui._fragments.clear()

    # ── 5. 清空输出队列（移除残留消息）──────────────────
    drained = 0
    while not tui._output_queue.empty():
        try:
            tui._output_queue.get_nowait()
            drained += 1
        except _queue.Empty:
            break
    if drained:
        logger.debug(f"输出队列已清空: {drained} 条消息")

    # ── 6. 重置 Agent 会话状态 ──────────────────────────
    if tui.agent:
        tui.agent.reset_session_state(old_session_id)

    # ── 7. 清除对话记忆 ─────────────────────────────────
    memory.clear()

    # ── 8. 重置滚动 ──────────────────────────────────────
    # 不清除 _agent_stop_event：Agent 线程需要它来感知取消请求，
    # 下次启动 Agent 时 tui._run_agent 会自动 clear()
    tui._auto_scroll = True

    # ── 9. 输出反馈 ──────────────────────────────────────
    lines = ["\n屏幕已清除"]
    if agent_was_running:
        lines.append("Agent 已停止")
    lines.append(f"会话 ID: {memory._session_id}")
    _output(tui, "\n".join(lines) + "\n")

    logger.info(
        f"/clear 完成: agent_was_running={agent_was_running}, "
        f"new_session={memory._session_id}, queue_drained={drained}"
    )


# ── /model ─────────────────────────────────────────────────

def cmd_model(tui: "SimpleTUI", args: str) -> None:
    from ..config import config
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
    from ..config import config
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
    from ..memory import memory
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
    from ..memory import memory
    logger.info("Session save requested")
    path = memory.save_current_session()
    if path:
        _output(tui, f"\n会话已保存: {path}\n")
    else:
        _output(tui, "\n没有可保存的对话内容\n", "class:error")


# ── /load ──────────────────────────────────────────────────

def cmd_load(tui: "SimpleTUI", args: str) -> None:
    from ..memory import memory
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
        logger.warning(f"Session load failed: {filepath}")
        _output(tui, f"\n加载会话失败: {filepath}\n", "class:error")


# ── /memory ────────────────────────────────────────────────

def cmd_memory(tui: "SimpleTUI", args: str) -> None:
    from ..memory import memory
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
        from ..persistent_memory import persistent_memory
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
            from ..memory import CompactEngine
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
    from ..config import config
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
    from ..config import config
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
    from ..config import config
    prompt = config.get_system_prompt()
    max_len = 2000
    if len(prompt) > max_len:
        prompt = prompt[:max_len] + f"\n\n... (截断，共 {len(prompt)} 字符)"
    _output(tui, f"\n系统提示词:\n{'─' * 40}\n{prompt}\n{'─' * 40}\n")


# ── /version ───────────────────────────────────────────────

def cmd_version(tui: "SimpleTUI", args: str) -> None:
    from ..config import config
    lines = [
        "\n┌─────────────────────────────────────────────┐",
        "│  Watermelon - TUI AGI Interaction Tool         │",
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


# ── /status ────────────────────────────────────────────────

def cmd_status(tui: "SimpleTUI", args: str) -> None:
    """显示系统状态概览：会话、模型、Agent、上下文、工具、记忆。"""
    from ..config import config
    from ..memory import memory
    logger.debug("Command: /status")

    lines = []

    # ── Section 1: Session ──
    with memory._rw_lock:
        msg_count = len(memory._history)
    lines.append("\n┌─ 会话 ──────────────────────────────────────┐")
    lines.append(f"│  会话 ID:     {memory._session_id}\n")
    lines.append(f"│  消息数:       {msg_count}\n")
    lines.append("└─────────────────────────────────────────────┘\n")

    # ── Section 2: Model / API ──
    api_key = config.api_key
    if not api_key:
        masked_key = "未设置"
    elif len(api_key) > 8:
        masked_key = api_key[:4] + "****" + api_key[-4:]
    else:
        masked_key = "****"

    fb = config.fallback_config
    fb_desc = fb["model"] if fb else "无"

    ctx_k = config.context_window // 1000

    lines.append("┌─ 模型 / API ──────────────────────────────────┐")
    lines.append(f"│  模型:         {config.model}\n")
    lines.append(f"│  API:          {config.base_url}\n")
    lines.append(f"│  API 密钥:     {masked_key}\n")
    lines.append(f"│  上下文窗口:   {ctx_k}k\n")
    lines.append(f"│  最大输出:     {config.max_output_tokens}\n")
    lines.append(f"│  温度:         {config.temperature}\n")
    lines.append(f"│  Top P:        {config.top_p}\n")
    lines.append(f"│  推理深度:     {config.reasoning_effort}\n")
    lines.append(f"│  备用模型:     {fb_desc}\n")
    lines.append("└─────────────────────────────────────────────┘\n")

    # ── Section 3: Agent ──
    lines.append("┌─ Agent ───────────────────────────────────────┐")
    if tui.agent:
        agent_state = "运行中" if tui._agent_running else "空闲"
        auto_mode = "开启" if tui.agent._autonomous_mode else "关闭"
        auto_run = "活跃" if tui.agent._autonomous_running else "空闲"
        lines.append(f"│  状态:         {agent_state}\n")
        lines.append(f"│  自主模式:     {auto_mode}\n")
        lines.append(f"│  自主运行:     {auto_run}\n")
    else:
        lines.append("│  状态:         未初始化\n")
    lines.append(f"│  最大轮次:     {config.max_turns}\n")
    lines.append("└─────────────────────────────────────────────┘\n")

    # ── Section 4: Context ──
    lines.append("┌─ 上下文 ─────────────────────────────────────┐")
    ratio_pct = int(tui._context_usage_ratio * 100)
    lines.append(f"│  使用率:       {ratio_pct}%\n")
    compact_text = tui._compact_indicator or "无"
    lines.append(f"│  压缩状态:     {compact_text}\n")
    lines.append(f"│  压缩启用:     {'是' if config.compact_enabled else '否'}\n")
    lines.append("└─────────────────────────────────────────────┘\n")

    # ── Section 5: Tools & MCP ──
    lines.append("┌─ 工具 & MCP ──────────────────────────────────┐")
    enabled = config.enabled_tools
    if enabled:
        lines.append(f"│  启用工具:     {len(enabled)} 个\n")
        for tool_name in enabled:
            lines.append(f"│    - {tool_name}\n")
    else:
        lines.append("│  启用工具:     无\n")
    lines.append(f"│  技能系统:     {'启用' if config.skills_enabled else '禁用'}\n")
    lines.append(f"│  MCP:          {'启用' if config.mcp_enabled else '禁用'}\n")
    servers = config.mcp_servers
    if servers and tui.agent and tui.agent.mcp_manager:
        for s in servers:
            srv_name = s.get("name", "?")
            client = tui.agent.mcp_manager.get_client(srv_name)
            connected = client and getattr(client, '_connected', False)
            srv_status = "已连接" if connected else "未连接"
            lines.append(f"│    {srv_name}: {srv_status}\n")
    elif servers:
        lines.append(f"│    {len(servers)} 个服务器 (Agent 未初始化)\n")
    lines.append("└─────────────────────────────────────────────┘\n")

    # ── Section 6: Memory ──
    lines.append("┌─ 记忆 ───────────────────────────────────────┐")
    lines.append(f"│  持久化记忆:   {'启用' if config.persistent_memory_enabled else '禁用'}\n")
    try:
        from ..persistent_memory import persistent_memory
        pm_count = persistent_memory.count()
    except Exception:
        pm_count = "未知"
    lines.append(f"│  记忆条数:     {pm_count}\n")
    try:
        from ..persistent_memory import persistent_memory as _pm
        _pm._ensure_initialized()
        gdir = str(_pm._global_dir) if _pm._global_dir else "未设置"
    except Exception:
        gdir = config.persistent_memory_global_dir or "未设置"
    lines.append(f"│  全局目录:     {gdir}\n")
    lines.append("└─────────────────────────────────────────────┘\n")

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
    from ..persistent_memory import persistent_memory
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
    from ..persistent_memory import persistent_memory
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
    registry.register("status", "显示系统状态概览", cmd_status)
    registry.register("remember", "显示持久化记忆列表或详情", cmd_remember, arg_spec="[name]")
    registry.register("forget", "删除指定持久化记忆", cmd_forget, arg_spec="<name>")
    registry.register("exit", "退出程序", cmd_exit)
