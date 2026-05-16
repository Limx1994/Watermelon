"""Agent core - main loop for LLM interaction with tool calling"""

import json
import logging
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

logger = logging.getLogger(__name__)
from collections import deque
from typing import Any, Callable, Dict, List, Optional

# Tools that are safe to run concurrently (read-only)
CONCURRENT_SAFE_TOOLS = {"read_file", "grep", "glob", "sleep"}
MAX_CONCURRENT_TOOLS = 10
TRUNCATE_CONTENT_LENGTH = 20000

from .config import config
from src.llm.client import (
    LLMClient,
    InterruptedError,
    create_system_message,
    create_user_message,
    create_assistant_message,
    create_tool_result_message,
    is_network_error,
)
from src.tools.registry import registry
from src.tools.loader import load_external_tools
from src.mcp.manager import MCPManager
from src.memory.memory import memory, CompactEngine
from src.utils.token_counter import count_tokens
from src.utils.tool_result_persistence import ToolResultPersistence


class AgentCancelledError(Exception):
    """Raised when the agent run is cancelled (e.g. user pressed Ctrl+C)."""
    pass


def classify_error(e: Exception) -> str:
    """分类错误类型"""
    error_str = str(e).lower()

    # 网络错误
    if is_network_error(e):
        return "network"

    # API状态错误
    from openai import APIStatusError, RateLimitError
    if isinstance(e, RateLimitError):
        return "rate_limit"
    if isinstance(e, APIStatusError):
        if hasattr(e, 'status_code'):
            status_code = e.status_code
            if status_code == 400:
                if any(kw in error_str for kw in ("context", "too long", "length", "token", "max_tokens")):
                    return "context"
                return "api_client"
            elif status_code == 401:
                return "api_auth"
            elif status_code == 403:
                return "api_permission"
            elif status_code == 404:
                return "api_not_found"
            elif status_code == 408:
                return "api_timeout"
            elif status_code == 429:
                return "rate_limit"
            elif 500 <= status_code < 600:
                return "api_server"
            elif 400 <= status_code < 500:
                return "api_client"

    # 上下文相关错误
    if any(kw in error_str for kw in ("context", "too long", "length", "token", "max_tokens")):
        return "context"

    # 内存错误
    if any(kw in error_str for kw in ("memory", "out of memory", "oom")):
        return "memory"

    # 磁盘错误
    if any(kw in error_str for kw in ("disk", "no space", "write", "read-only")):
        return "disk"

    # 权限错误
    if any(kw in error_str for kw in ("permission", "access denied", "denied", "forbidden")):
        return "permission"

    # MCP错误
    if any(kw in error_str for kw in ("mcp", "json-rpc", "mcp server")):
        return "mcp"

    # 工具错误
    if any(kw in error_str for kw in ("tool", "execution", "invalid arguments")):
        return "tool"

    logger.debug(f"Error classified as 'unknown': {type(e).__name__}: {str(e)[:100]}")
    return "unknown"


def get_error_config(error_type: str) -> dict:
    """获取错误类型的配置"""
    configs = {
        "network": {"max_retries": config.network_max_retries, "base_interval": config.network_retry_interval_seconds, "max_interval": 120, "exponential": True},
        "rate_limit": {"max_retries": 5, "base_interval": 60, "max_interval": 300, "exponential": True},
        "api_server": {"max_retries": 3, "base_interval": 30, "max_interval": 60, "exponential": True},
        "api_timeout": {"max_retries": 3, "base_interval": 30, "max_interval": 60, "exponential": True},
        "context": {"max_retries": 2, "base_interval": 5, "max_interval": 10, "exponential": False},
        "memory": {"max_retries": 2, "base_interval": 10, "max_interval": 20, "exponential": False},
        "mcp": {"max_retries": 3, "base_interval": 10, "max_interval": 30, "exponential": True},
        "unknown": {"max_retries": 2, "base_interval": 30, "max_interval": 60, "exponential": True},
        # 不可重试错误
        "api_client": {"max_retries": 0},
        "api_auth": {"max_retries": 0},
        "api_permission": {"max_retries": 0},
        "api_not_found": {"max_retries": 0},
        "disk": {"max_retries": 0},
        "permission": {"max_retries": 0},
        "tool": {"max_retries": 0},
    }
    return configs.get(error_type, configs["unknown"])


def get_error_message(error_type: str, e: Exception, retry_count: int = 0, max_retries: int = 0) -> str:
    """获取用户友好的错误消息"""
    error_msg = str(e)[:200]
    retry_info = f" ({retry_count}/{max_retries})" if max_retries > 0 else ""

    messages = {
        "network": f"[网络错误] {error_msg}{retry_info}\n正在重试...",
        "rate_limit": f"[速率限制] {error_msg}{retry_info}\n等待后重试...",
        "api_server": f"[API服务器错误] {error_msg}{retry_info}\n服务器暂时不可用，请稍后重试",
        "api_timeout": f"[请求超时] {error_msg}{retry_info}\n正在重试...",
        "api_client": f"[API客户端错误] {error_msg}\n请检查API配置",
        "api_auth": f"[认证失败] {error_msg}\n请检查API密钥",
        "api_permission": f"[权限不足] {error_msg}\n请检查账户权限",
        "api_not_found": f"[模型不存在] {error_msg}\n请检查模型名称",
        "context": f"[上下文过长] {error_msg}{retry_info}\n正在压缩上下文...",
        "memory": f"[内存不足] {error_msg}{retry_info}\n正在释放资源...",
        "disk": f"[磁盘错误] {error_msg}\n请检查磁盘空间",
        "permission": f"[权限错误] {error_msg}\n请检查文件权限",
        "mcp": f"[MCP错误] {error_msg}{retry_info}\n正在重连MCP服务器...",
        "tool": f"[工具错误] {error_msg}\n请检查工具参数",
        "unknown": f"[未知错误] {error_msg}{retry_info}\n详情见日志",
    }
    return messages.get(error_type, messages["unknown"])


def get_retry_interval(error_type: str, retry_count: int) -> int:
    """计算重试间隔（秒）"""
    err_config = get_error_config(error_type)
    if not err_config.get("exponential", False):
        return err_config.get("base_interval", 30)

    base = err_config.get("base_interval", 30)
    max_interval = err_config.get("max_interval", 120)
    return int(min(base * (2 ** max(retry_count - 1, 0)), max_interval))


class Agent:
    """Core agent that orchestrates LLM and tool interaction with thinking mode support"""

    def __init__(
        self,
        output_callback: Optional[Callable[[str, str], None]] = None,
        stop_event: Optional[threading.Event] = None,
    ):
        self.output_callback = output_callback
        self.stop_event = stop_event
        self.llm = LLMClient(stop_event=self.stop_event)
        self.mcp_manager = MCPManager(config.mcp_enabled, config.mcp_servers)
        threading.Thread(target=self.mcp_manager.connect_all, daemon=True, name="mcp-connect").start()
        logger.info("MCP connection started in background thread")
        # Autonomous mode infrastructure (must init before _setup_tools)
        self._pending_inputs: deque = deque()
        self._pending_lock = threading.Lock()
        self._work_event = threading.Event()
        self._sleep_event = threading.Event()
        self._autonomous_mode = False
        self._autonomous_running = False
        self._is_sleeping = False
        self._first_tick = True
        self._run_lock = threading.RLock()
        self._setup_tools()
        self.total_tokens: float = 0  # 累计token消耗
        # 上下文压缩引擎
        self._compact_engine = CompactEngine(memory)
        # 工具结果持久化
        self._tool_persistence = ToolResultPersistence(
            threshold_chars=config.tool_result_persistence_threshold_chars,
            max_file_size=config.tool_result_persistence_max_file_size,
        )
        logger.info(f"Agent initialized: model={config.model}, "
                    f"tool_persistence={config.tool_result_persistence_enabled}")
        # Stop hooks: callable(messages, tool_calls) -> Optional[str]
        self._stop_hooks: list = []
        # Skill allowed-tools override (set by skill handler)
        self._allowed_tools_override: Optional[List[str]] = None

    def _interruptible_sleep(self, seconds: float) -> None:
        """Sleep for up to seconds, checking stop_event every 0.2s.

        Raises AgentCancelledError if stop_event is set during sleep.
        """
        elapsed = 0.0
        step = 0.2
        while elapsed < seconds:
            if self.stop_event and self.stop_event.is_set():
                logger.info(f"Agent sleep interrupted: {elapsed:.1f}s/{seconds:.1f}s")
                raise AgentCancelledError()
            remaining = min(step, seconds - elapsed)
            time.sleep(remaining)
            elapsed += remaining

    def _setup_tools(self) -> None:
        """Register built-in tools"""
        registry.clear()
        logger.debug("Tool registry cleared")
        load_external_tools()
        from src.tools.sleep import SleepTool
        sleep_tool = SleepTool(self._sleep_event, agent=self)
        registry.register(sleep_tool)
        # Register skill tool if skills are loaded
        self._try_register_skill_tool()
        # Register persistent memory tool
        if config.persistent_memory_enabled:
            try:
                from src.tools.memory_tool import MemoryTool
                registry.register(MemoryTool())
                logger.debug("MemoryTool registered")
            except Exception as e:
                logger.warning(f"MemoryTool registration failed: {e}", exc_info=True)
        else:
            logger.debug("MemoryTool skipped: persistent_memory disabled")
        logger.info(f"Tools registered: {registry.list_tools()}")

    def _try_register_skill_tool(self) -> None:
        """Register SkillTool if skills are loaded but tool not yet registered."""
        try:
            from src.skills.tool import SkillTool
            from src.skills.registry import skill_registry
            if skill_registry.is_loaded() and registry.get("invoke_skill") is None:
                registry.register(SkillTool())
                logger.info("SkillTool registered (deferred)")
        except ImportError:
            pass

    def _execute_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool call and return the result. Never raises."""
        try:
            tool = registry.get(tool_name)
            if tool:
                logger.info(f"[agent] calling {tool_name}({list(arguments.keys())})")
                result = tool.execute(**arguments)
                logger.info(f"[agent] {tool_name} -> success={result.success} content={len(result.content or '')}B")
                return result.to_dict()
            logger.info(f"[agent] routing {tool_name} to MCP")
            return self.mcp_manager.call_tool(tool_name, arguments)
        except AgentCancelledError:
            raise
        except Exception as e:
            logger.error(f"[agent] {tool_name} failed: {type(e).__name__}: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Tool execution error: {str(e)[:500]}"
            }

    def submit_work(self, text: str, source: str = "cron") -> None:
        """Submit work to the agent's pending queue. Thread-safe."""
        with self._pending_lock:
            self._pending_inputs.append({"text": text, "source": source})
            queue_size = len(self._pending_inputs)
        self._work_event.set()
        self._sleep_event.set()
        logger.info(f"Work submitted: source={source}, queue_size={queue_size}")

    def get_pending_count(self) -> int:
        """Get number of pending autonomous tasks. Thread-safe."""
        with self._pending_lock:
            return len(self._pending_inputs)

    def _run_stop_hooks(self, messages: list, tool_calls: list) -> Optional[str]:
        """Run all stop hooks. Returns first blocking error message, or None."""
        for hook in self._stop_hooks:
            try:
                error = hook(messages, tool_calls)
                if error:
                    logger.debug(f"Stop hook triggered: {error[:100]}")
                    return error
            except Exception as e:
                logger.error(f"Stop hook error: {e}", exc_info=True)
        return None

    def register_stop_hook(self, callback: Callable) -> None:
        """Register a callback to run after each tool round.

        Args:
            callback: callable(messages, tool_calls) -> Optional[str]
                      Return a non-empty string to inject as a blocking error message.
        """
        if callback not in self._stop_hooks:
            self._stop_hooks.append(callback)

    def _stream_output(self, text: str, msg_type: str = "text", force: bool = False) -> None:
        """Stream output to callback with type indicator.
        Raises AgentCancelledError if stop_event is set.
        Use force=True to bypass stop_event check (for cleanup code)."""
        if not force and self.stop_event and self.stop_event.is_set():
            raise AgentCancelledError()
        if self.output_callback:
            self.output_callback(msg_type, text)

    def _build_project_context(self) -> str:
        """Build project context injection message (CLAUDE.md + date + gitStatus)."""
        from src.utils.path import resolve_path
        parts = ["<system-reminder>"]
        parts.append(f"Current date: {datetime.now().strftime('%Y-%m-%d')}")

        # Inject CLAUDE.md
        claude_md = resolve_path("CLAUDE.md")
        if claude_md.exists():
            try:
                content = claude_md.read_text(encoding="utf-8")[:3000]
                parts.append(f"Project instructions:\n{content}")
                logger.debug(f"Project context: CLAUDE.md loaded ({len(content)} chars)")
            except Exception as e:
                logger.warning(f"Project context: failed to read CLAUDE.md: {e}")
        else:
            logger.debug("Project context: CLAUDE.md not found")

        # Inject persistent memory index (global + project)
        if config.persistent_memory_enabled:
            try:
                from src.memory.persistent_memory import persistent_memory
                mem_idx = persistent_memory.load_index()
                if mem_idx:
                    max_chars = config.persistent_memory_max_index_chars
                    if len(mem_idx) > max_chars:
                        mem_idx = mem_idx[:max_chars] + "\n\n... (truncated)"
                    parts.append(f"Cross-session memories:\n{mem_idx}")
                    logger.debug(
                        f"Project context: memory index injected ({len(mem_idx)} chars)"
                    )
            except Exception as e:
                logger.warning(f"Project context: memory index injection failed: {e}", exc_info=True)

        # Inject git status
        try:
            result = subprocess.run(
                ["git", "status", "--short"],
                capture_output=True, text=True,
                encoding="utf-8", errors="replace",
                timeout=5,
                cwd=str(resolve_path("."))
            )
            if result.returncode == 0 and result.stdout.strip():
                parts.append(f"Git status:\n{result.stdout[:1000]}")
                logger.debug(f"Project context: git status captured ({len(result.stdout)} chars)")
        except Exception as e:
            logger.debug(f"Project context: git status failed: {e}")

        # Inject available skills listing
        try:
            from src.skills.registry import skill_registry
            if skill_registry.is_loaded():
                skill_lines = []
                for s in skill_registry.list_skills():
                    hint = f" ({s.argument_hint})" if s.argument_hint else ""
                    skill_lines.append(f"  - /{s.name}: {s.description}{hint}")
                if skill_lines:
                    skills_text = "\n".join(skill_lines)
                    parts.append(f"Available skills:\n{skills_text}")
                    logger.debug(f"Project context: {len(skill_lines)} skills injected")
        except ImportError:
            pass

        parts.append("</system-reminder>")
        context_str = "\n".join(parts)
        logger.debug(f"Project context built: {len(parts)} parts, {len(context_str)} chars")
        return context_str

    def _calculate_context_tokens(self, messages: List[Dict[str, Any]]) -> int:
        """计算当前 context 的 token 数（system + messages + tool_calls arguments）"""
        system_tokens = count_tokens(config.get_system_prompt())
        memory_tokens = 0
        for m in messages:
            if m.get("role") == "system":
                continue
            content = m.get("content", "") or ""
            memory_tokens += count_tokens(content)
            reasoning = m.get("reasoning_content", "") or ""
            if reasoning:
                memory_tokens += count_tokens(reasoning)
            for tc in m.get("tool_calls", []):
                args = tc.get("function", {}).get("arguments", "")
                if args:
                    memory_tokens += count_tokens(args)
        result = int(system_tokens + memory_tokens)
        logger.debug(f"Context tokens: system={system_tokens}, memory={memory_tokens}, total={result}")
        return result

    def run(self, user_input: str) -> str:
        """Run the agent with a user input. Returns the final response text."""
        with self._run_lock:
            result = self._run_inner(user_input)
            if not self._autonomous_mode:
                self.start_autonomous_loop()
            return result

    def _apply_tool_result_budget(self, messages: list) -> int:
        """Enforce per-message tool result budget. Replaces oversized results.

        Returns number of tokens saved.
        """
        if not config.tool_result_budget_max_chars:
            return 0
        from src.utils.token_counter import count_tokens
        saved = 0
        for m in messages:
            if m.get("role") != "tool":
                continue
            content = m.get("content", "") or ""
            if len(content) <= config.tool_result_budget_max_chars:
                continue
            tokens = count_tokens(content)
            m["content"] = f"[Tool result truncated: ~{int(tokens)} tokens]"
            saved += tokens
            logger.debug(f"Tool result budget: truncated {len(content)} -> {len(m['content'])}")
        if saved > 0:
            logger.info(f"Tool result budget: saved ~{saved} tokens")
        return saved

    def _run_inner(self, user_input: str) -> str:
        """Internal run logic (called with _run_lock held)."""
        logger.info(f"_run_inner start: input={user_input[:80]}...")
        # Retry SkillTool registration in case skills loaded after _setup_tools
        self._try_register_skill_tool()
        # Build messages for LLM
        messages: List[Dict[str, Any]] = [create_system_message(config.get_system_prompt())]

        # Inject project context (CLAUDE.md + date + gitStatus)
        project_context = self._build_project_context()
        if project_context:
            messages.append(create_user_message(project_context))

        messages.extend(memory.get_conversation_for_llm())
        messages.append(create_user_message(user_input))
        memory.add_message("user", user_input)
        self._compact_engine.record_user_message()

        # Get all available tools from registry + MCP
        tools = []
        for tool_name in registry.list_tools():
            tool_obj = registry.get(tool_name)
            if tool_obj and hasattr(tool_obj, 'get_schema'):
                tools.append({
                    "type": "function",
                    "function": {
                        "name": tool_name,
                        "description": tool_obj.description,
                        "parameters": tool_obj.get_schema()
                    }
                })
        tools.extend(self.mcp_manager.get_all_tool_definitions())

        # Apply allowed-tools filter for skills
        if self._allowed_tools_override is not None:
            allowed = set(self._allowed_tools_override)
            tools = [t for t in tools if t.get("function", {}).get("name") in allowed]
            logger.debug(f"Skill tool filter: {len(tools)} tools allowed")

        # Session ID for persistence and cleanup
        session_id = memory._session_id

        # Pre-loop compression check
        current_tokens = self._calculate_context_tokens(messages)
        should_compact, level = self._compact_engine.should_compact(
            current_tokens, config.effective_context_window
        )

        if should_compact:
            result = self._compact_engine.compact(level, self.llm)
            if result["compacted"]:
                self._stream_output(
                    f"\n[上下文压缩: L{level} • 节省 ~{result['tokens_saved']} tokens • 移除 {result['messages_removed']} 条消息]\n",
                    "compact"
                )
                # Full Compact: 清理持久化工具结果
                if level == CompactEngine.LEVEL_FULL and config.tool_result_persistence_enabled:
                    self._tool_persistence.clear_session(session_id)
                messages = [create_system_message(config.get_system_prompt())]
                messages.extend(memory.get_conversation_for_llm())
                messages.append(create_user_message(config.compact_resume_prompt))
                if project_context:
                    messages.append(create_user_message(project_context))
                current_tokens = self._calculate_context_tokens(messages)

                # Escalation loop — forced level-up on each iteration
                should_compact, suggested_level = self._compact_engine.should_compact(
                    current_tokens, config.effective_context_window
                )
                while should_compact and suggested_level < CompactEngine.LEVEL_FULL and not self.stop_event.is_set():
                    target_level = min(suggested_level + 1, CompactEngine.LEVEL_FULL)
                    logger.debug(f"Compact escalation: level {suggested_level} -> {target_level}")
                    result = self._compact_engine.compact(target_level, self.llm)
                    if result["compacted"]:
                        self._stream_output(
                            f"\n[追加压缩: L{target_level} • 节省 ~{result['tokens_saved']} tokens]\n",
                            "compact"
                        )
                        if target_level == CompactEngine.LEVEL_FULL and config.tool_result_persistence_enabled:
                            self._tool_persistence.clear_session(session_id)
                        messages = [create_system_message(config.get_system_prompt())]
                        messages.extend(memory.get_conversation_for_llm())
                        messages.append(create_user_message(config.compact_resume_prompt))
                        if project_context:
                            messages.append(create_user_message(project_context))
                        current_tokens = self._calculate_context_tokens(messages)
                    should_compact, suggested_level = self._compact_engine.should_compact(
                        current_tokens, config.effective_context_window
                    )

        # Send context usage to TUI
        usage_ratio = current_tokens / config.effective_context_window if config.effective_context_window > 0 else 0
        self._stream_output(f"{usage_ratio:.2f}", "context_usage")

        # Tool-call loop with needsFollowUp + error recovery
        turns = 0
        max_turns = config.max_turns
        final_response = ""
        final_reasoning = ""
        thinking_started = [False]

        def wrap_callback(text, is_reasoning: bool = False):
            if is_reasoning:
                if config.show_thinking:
                    self._stream_output(text, "thinking")
            else:
                if config.show_thinking and not thinking_started[0]:
                    self._stream_output("\n", "answer_start")
                    thinking_started[0] = True
                self._stream_output(text, "answer")

        consecutive_errors = 0
        MAX_CONSECUTIVE_ERRORS = 3

        while turns < max_turns:
            if self.stop_event and self.stop_event.is_set():
                logger.info("Agent cancelled by stop event")
                raise AgentCancelledError()

            # Warn when approaching turn limit
            remaining = max_turns - turns
            if remaining <= 5 and remaining > 0:
                self._stream_output(f"\n[Warning: {remaining} turns remaining]\n", "compact")

            turns += 1
            logger.debug(f"Turn {turns}/{max_turns}, tool_calls={len(tool_calls) if 'tool_calls' in locals() else 0}")

            # Apply tool result budget before sending to LLM
            if config.tool_result_persistence_enabled:
                self._apply_tool_result_budget(messages)

            # API call with error recovery for prompt-too-long and model degradation
            try:
                tool_calls, llm_content, llm_reasoning, finish_reason = self.llm.get_tool_calls(messages, tools)
                consecutive_errors = 0
                # Restore original model if it was degraded and succeeded
                if self.llm.model != self.llm._original_model:
                    self.llm.restore_model()
                    logger.info(f"Model restored to {self.llm.model}")
                    self._stream_output(f"\n[模型已恢复: {self.llm.model}]\n", "compact")
            except InterruptedError:
                logger.info("LLM call interrupted by stop_event")
                raise AgentCancelledError()
            except Exception as e:
                error_str = str(e).lower()
                error_type = classify_error(e)
                # Model degradation: try fallback model on first error
                if config.fallback_config and consecutive_errors == 0:
                    fb = config.fallback_config
                    logger.warning(f"Model degradation triggered: {error_type}: {type(e).__name__}: {str(e)[:200]}")
                    self.llm.switch_model(fb["model"], client=self.llm._fallback_client)
                    self._stream_output(f"\n[模型降级: {fb['model']}]\n", "compact")
                    consecutive_errors += 1
                    continue
                if error_type == "context":
                    consecutive_errors += 1
                    if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                        logger.warning(f"Too many consecutive errors ({consecutive_errors}), stopping")
                        self._stream_output("\n[Error]: Too many consecutive errors, stopping.\n")
                        break
                    self._stream_output(f"\n{config.context_too_long_prompt}\n", "compact")
                    # 多级恢复：先尝试剥离旧消息（零成本），再 Auto/Full Compact
                    recovered = False
                    # Step 1: 尝试剥离旧工具结果（零成本）
                    stripped = self._apply_tool_result_budget(messages)
                    if stripped > 0:
                        current_tokens = self._calculate_context_tokens(messages)
                        usage_ratio = current_tokens / config.effective_context_window if config.effective_context_window > 0 else 0
                        if usage_ratio < config.compact_auto_threshold:
                            self._stream_output(f"[剥离旧结果 — 节省 ~{stripped} tokens]\n", "compact")
                            recovered = True
                    # Step 2: 尝试 Auto Compact
                    if not recovered:
                        result = self._compact_engine.compact(CompactEngine.LEVEL_AUTO, self.llm)
                        if result["compacted"]:
                            recovered = True
                    # Step 3: 尝试 Full Compact
                    if not recovered:
                        result = self._compact_engine.compact(CompactEngine.LEVEL_FULL, self.llm)
                        if result["compacted"]:
                            if config.tool_result_persistence_enabled:
                                self._tool_persistence.clear_session(session_id)
                            recovered = True
                    if recovered:
                        messages = [create_system_message(config.get_system_prompt())]
                        messages.extend(memory.get_conversation_for_llm())
                        messages.append(create_user_message(config.compact_resume_prompt))
                        if project_context:
                            messages.append(create_user_message(project_context))
                        self._stream_output("[压缩完成 — 重试中...]\n", "compact")
                        continue
                raise

            # Handle tool calls (with optional reasoning/content display)
            if tool_calls:
                if config.show_thinking and llm_reasoning:
                    for line in llm_reasoning.split('\n'):
                        if line.strip():
                            self._stream_output(f"{line}\n", "thinking")
                    self._stream_output("\n", "thinking")
                if llm_content:
                    self._stream_output(llm_content + "\n", "answer")
                assistant_msg: Dict[str, Any] = {
                    "role": "assistant", "content": llm_content,
                    "tool_calls": [{
                        "id": tc["id"], "type": "function",
                        "function": {"name": tc["name"], "arguments": tc["arguments"]}
                    } for tc in tool_calls]
                }
                if llm_reasoning:
                    assistant_msg["reasoning_content"] = llm_reasoning
                    logger.debug(f"Tool-call assistant msg: included reasoning_content ({len(llm_reasoning)} chars)")
                messages.append(assistant_msg)

            # needsFollowUp: no tool calls = final response (reuse content from get_tool_calls)
            if not tool_calls:
                final_response = llm_content
                final_reasoning = llm_reasoning
                # Stream the response via callback (already received from get_tool_calls)
                if final_reasoning and config.show_thinking:
                    for line in final_reasoning.split('\n'):
                        if line.strip():
                            self._stream_output(f"{line}\n", "thinking")
                    self._stream_output("\n", "thinking")
                if final_response:
                    wrap_callback(final_response, is_reasoning=False)
                # Max output tokens recovery
                if finish_reason == "length":
                    messages.append(create_assistant_message(final_response, final_reasoning))
                    messages.append(create_user_message(config.max_tokens_recovery_prompt))
                    self._stream_output("\n[输出截断 — 继续...]\n", "compact")
                    thinking_started[0] = False
                    continue
                break

            # Execute tool calls - concurrent for read-only, serial for write tools
            # First, parse and validate all arguments
            parsed_calls = []
            for tc in tool_calls:
                tool_name = tc["name"]
                try:
                    args_raw = tc["arguments"]
                    if isinstance(args_raw, str):
                        arguments = json.loads(args_raw) if args_raw.strip() else {}
                    else:
                        arguments = args_raw if args_raw else {}
                except (json.JSONDecodeError, TypeError) as e:
                    logger.warning(f"Failed to parse tool arguments for {tool_name}: {e}")
                    self._stream_output(f"[Error]: Invalid arguments for {tool_name}: {e}\n")
                    messages.append(create_tool_result_message(tc["id"], f"Error: Invalid JSON arguments: {e}"))
                    continue

                # Schema validation
                tool = registry.get(tool_name)
                if tool:
                    validation_errors = tool.validate_args(arguments)
                    if validation_errors:
                        err_msg = f"Schema validation failed: {'; '.join(validation_errors)}"
                        self._stream_output(f"[Error]: {err_msg}\n")
                        messages.append(create_tool_result_message(tc["id"], f"Error: {err_msg}"))
                        continue

                parsed_calls.append((tc, tool_name, arguments))

            # Separate into concurrent-safe and serial batches
            concurrent_batch = [(tc, name, args) for tc, name, args in parsed_calls if name in CONCURRENT_SAFE_TOOLS]
            serial_batch = [(tc, name, args) for tc, name, args in parsed_calls if name not in CONCURRENT_SAFE_TOOLS]

            # Execute concurrent-safe tools in parallel
            if concurrent_batch:
                # First, send all calling messages in submission order
                for tc, tool_name, arguments in concurrent_batch:
                    self._stream_output(f"\n[Calling tool: {tool_name}]\n", "tool_call")

                # Execute all tools in parallel
                def _exec_one(tc_name_args):
                    tc, tool_name, arguments = tc_name_args
                    result = self._execute_tool_call(tool_name, arguments)
                    self._compact_engine.increment_streak()
                    return tc, result

                # Collect results preserving submission order
                ordered_results = []
                with ThreadPoolExecutor(max_workers=min(len(concurrent_batch), MAX_CONCURRENT_TOOLS)) as pool:
                    futures = [pool.submit(_exec_one, item) for item in concurrent_batch]
                    for future in futures:
                        ordered_results.append(future.result())

                # Output results in submission order
                for tc, result in ordered_results:
                    content = result.get("content", "")
                    if config.tool_result_persistence_enabled:
                        ref = self._tool_persistence.persist_if_large(
                            content, tc["id"], tc.get("name", "?"), session_id
                        )
                        if ref:
                            content = ref
                    messages.append(create_tool_result_message(tc["id"], content))
                    if result.get("success"):
                        self._stream_output(f"[Result]:\n{result.get('content', '')[:TRUNCATE_CONTENT_LENGTH]}\n", "tool_result")
                    else:
                        self._stream_output(f"[Error]: {result.get('error') or 'Unknown error'}\n", "tool_result")

            # Execute write tools serially
            for tc, tool_name, arguments in serial_batch:
                self._stream_output(f"\n[Calling tool: {tool_name}]\n", "tool_call")
                result = self._execute_tool_call(tool_name, arguments)
                self._compact_engine.increment_streak()
                content = result.get("content", "")
                if config.tool_result_persistence_enabled:
                    ref = self._tool_persistence.persist_if_large(
                        content, tc["id"], tool_name, session_id
                    )
                    if ref:
                        content = ref
                messages.append(create_tool_result_message(tc["id"], content))
                if result.get("success"):
                    self._stream_output(f"[Result]:\n{result.get('content', '')[:TRUNCATE_CONTENT_LENGTH]}\n", "tool_result")
                else:
                    self._stream_output(f"[Error]: {result.get('error') or 'Unknown error'}\n", "tool_result")

            # Stop hook check: run registered hooks, inject blocking errors
            blocking_error = self._run_stop_hooks(messages, tool_calls)
            if blocking_error:
                messages.append(create_user_message(blocking_error))
                self._stream_output(f"\n[Stop hook: {blocking_error[:200]}]\n", "compact")

            # In-loop compression check
            current_tokens = self._calculate_context_tokens(messages)
            should_compact, level = self._compact_engine.should_compact(
                current_tokens, config.effective_context_window
            )
            if should_compact:
                result = self._compact_engine.compact(level, self.llm)
                if result["compacted"]:
                    self._stream_output(
                        f"\n[上下文压缩: L{level} • 节省 ~{result['tokens_saved']} tokens]\n",
                        "compact"
                    )
                    if level == CompactEngine.LEVEL_FULL and config.tool_result_persistence_enabled:
                        self._tool_persistence.clear_session(session_id)
                    messages = [create_system_message(config.get_system_prompt())]
                    messages.extend(memory.get_conversation_for_llm())
                    messages.append(create_user_message(config.compact_resume_prompt))
                    if project_context:
                        messages.append(create_user_message(project_context))
                    current_tokens = self._calculate_context_tokens(messages)

            self._stream_output(f"{current_tokens / config.effective_context_window if config.effective_context_window > 0 else 0:.2f}", "context_usage")

            # Token budget nudge: inject message to keep AI working (avoid duplicates)
            usage_ratio = current_tokens / config.effective_context_window if config.effective_context_window > 0 else 0
            if usage_ratio >= config.nudge_threshold and not any(
                m.get("content", "").startswith("Context at") for m in messages if m.get("role") == "user"
            ):
                nudge_msg = config.get_nudge_prompt(usage_ratio)
                messages.append(create_user_message(nudge_msg))
                logger.info(f"Token nudge injected: usage={usage_ratio:.0%} threshold={config.nudge_threshold:.0%}")
                self._stream_output(f"\n[Token 预算警告: {usage_ratio:.0%} — 注入 nudge 消息]\n", "compact")
            elif usage_ratio >= config.nudge_threshold:
                logger.debug(f"Token nudge skipped: duplicate exists, usage={usage_ratio:.0%}")

        if turns >= max_turns:
            logger.warning(f"Agent max_turns reached: {turns}/{max_turns}")

        # Save assistant response to memory (only if valid)
        if final_response and final_response.strip():
            memory.add_message("assistant", final_response, reasoning_content=final_reasoning)

        # Clear skill tools override
        self._allowed_tools_override = None

        # Token display
        system_tokens = count_tokens(config.get_system_prompt())
        # memory already contains user_input and final_response, so memory_tokens covers both
        memory_tokens = sum(count_tokens(msg.get("content", "")) for msg in memory.get_conversation_for_llm())
        reasoning_tokens = count_tokens(final_reasoning) if final_reasoning else 0
        total_this = system_tokens + memory_tokens + reasoning_tokens
        self.total_tokens += total_this

        def fmt_token(t):
            if t >= 1000:
                return f"{t/1000:.3f}K"
            return f"{t:.0f}"

        logger.info(f"Agent response: {len(final_response)} chars, {turns} turns, tokens={fmt_token(total_this)}")

        self._stream_output(
            f"⬆{fmt_token(system_tokens + memory_tokens)} "
            f"⬇{fmt_token(reasoning_tokens)} "
            f"∫{fmt_token(self.total_tokens)}",
            "token_info"
        )

        logger.info(f"_run_inner end: turns={turns}, response_len={len(final_response)}")
        return final_response

    def start_autonomous_loop(self) -> None:
        """Start autonomous loop in a separate daemon thread."""
        if self._autonomous_running:
            return
        self._autonomous_mode = True
        threading.Thread(target=self._autonomous_loop, daemon=True).start()

    def _autonomous_loop(self) -> None:
        """Persistent loop for autonomous mode. Runs until stop_event is set."""
        self._autonomous_running = True
        self._stream_output("\n[自主模式已激活 — 等待任务...]\n", "compact")
        logger.info("Autonomous mode activated")
        _cancelled = False

        try:
            while not (self.stop_event and self.stop_event.is_set()):
                got_event = self._work_event.wait(timeout=1.0)
                if got_event:
                    self._work_event.clear()

                while True:
                    with self._pending_lock:
                        if not self._pending_inputs:
                            break
                        item = self._pending_inputs.popleft()

                    source = item["source"]
                    text = item["text"]
                    is_tick = (text == "<tick>")

                    # First tick: greet user
                    if is_tick and self._first_tick:
                        self._first_tick = False
                        self._stream_output("\n[自主模式就绪 — 有什么需要我帮忙的吗？]\n", "autonomous")
                        continue

                    self._stream_output(f"\n{'='*40}\n[任务来源: {source}]\n", "user_input")
                    logger.info(f"Processing autonomous task: source={source}")

                    self._is_sleeping = False
                    try:
                        with self._run_lock:
                            self._run_inner(text)
                    except AgentCancelledError:
                        _cancelled = True
                        logger.info("Autonomous task cancelled")
                        self._stream_output("\n[任务已取消]\n", force=True)
                        # 不 send _autonomous_done — 外层 finally 会 send _agent_done
                        return
                    except Exception as e:
                        error_type = classify_error(e)
                        error_config = get_error_config(error_type)
                        retry_count = item.get("retry_count", 0)
                        max_retries = error_config.get("max_retries", 0)

                        # 判断是否应该重试
                        if max_retries > 0 and retry_count < max_retries:
                            # 可重试错误：重新入队，等待后重试
                            new_retry_count = retry_count + 1
                            wait_time = get_retry_interval(error_type, new_retry_count)

                            error_msg = get_error_message(error_type, e, new_retry_count, max_retries)
                            self._stream_output(f"\n{error_msg}\n", "error")
                            logger.warning(f"Retryable error: {error_type}, retry {new_retry_count}/{max_retries}")

                            try:
                                self._interruptible_sleep(wait_time)
                            except AgentCancelledError:
                                _cancelled = True
                                raise
                            with self._pending_lock:
                                self._pending_inputs.append({"text": text, "source": source, "retry_count": new_retry_count})
                            self._work_event.set()
                        else:
                            # 不可重试错误或达到最大重试次数
                            error_msg = get_error_message(error_type, e)
                            if max_retries > 0 and retry_count >= max_retries:
                                error_msg += f"\n已达到最大重试次数 ({max_retries})"
                            self._stream_output(f"\n{error_msg}\n", "error", force=True)
                            logger.error(f"Task failed: {error_type}: {e}", exc_info=True)
                            try:
                                self._interruptible_sleep(1)
                            except AgentCancelledError:
                                _cancelled = True
                                raise
                    finally:
                        if not _cancelled and self.output_callback and self.get_pending_count() == 0:
                            self.output_callback("_autonomous_done", "")

                if self.stop_event and self.stop_event.is_set():
                    break
        finally:
            self._autonomous_running = False
            self._autonomous_mode = False
            self._is_sleeping = False
            self._stream_output("\n[自主模式已退出]\n", "compact", force=True)
            logger.info("Autonomous mode deactivated")
            if self.output_callback:
                self.output_callback("_agent_done", "")