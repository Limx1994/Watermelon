"""Agent core - main loop for LLM interaction with tool calling"""

import json
import logging
import threading
from typing import Any, Callable, Dict, List, Optional, Tuple

from .config import config
from .llm.client import (
    LLMClient,
    create_system_message,
    create_user_message,
    create_assistant_message,
    create_tool_result_message,
)
from .tools.registry import registry
from .tools.loader import load_external_tools
from .mcp.server import MCPServer
from .mcp.manager import MCPManager
from .memory import memory, CompactEngine
from .utils.token_counter import count_tokens, count_messages_tokens


class AgentCancelledError(Exception):
    """Raised when the agent run is cancelled (e.g. user pressed Ctrl+C)."""
    pass


class Agent:
    """Core agent that orchestrates LLM and tool interaction with thinking mode support"""

    def __init__(
        self,
        output_callback: Optional[Callable[[str, str], None]] = None,
        stop_event: Optional[threading.Event] = None,
    ):
        self.output_callback = output_callback
        self.stop_event = stop_event
        self.llm = LLMClient()
        self.mcp_server = MCPServer()
        self.mcp_manager = MCPManager(config.mcp_enabled, config.mcp_servers)
        self.mcp_manager.connect_all()
        self._setup_tools()
        # Track reasoning_content for multi-turn in thinking mode
        self._last_reasoning: str = ""
        self.total_tokens: float = 0  # 累计token消耗
        # 上下文压缩引擎
        self._compact_engine = CompactEngine(memory)
        # API 返回的 usage 信息
        self._last_usage: Optional[Dict[str, int]] = None

    def _setup_tools(self) -> None:
        """Register built-in tools"""
        registry.clear()
        load_external_tools()

    def _get_all_tool_definitions(self) -> List[Dict[str, Any]]:
        """Get all available tool definitions (built-in + MCP)"""
        definitions = self.mcp_server.get_tool_definitions()
        definitions.extend(self.mcp_manager.get_all_tool_definitions())
        # 过滤掉未启用的工具
        enabled = set(config.enabled_tools)
        definitions = [d for d in definitions if d.get("function", {}).get("name") in enabled]
        return definitions

    def _execute_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool call and return the result"""
        # Check built-in tools first
        tool = registry.get(tool_name)
        if tool:
            result = tool.execute(**arguments)
            return result.to_dict()

        # Check MCP manager (handles all external MCP clients)
        return self.mcp_manager.call_tool(tool_name, arguments)

    def _stream_output(self, text: str, msg_type: str = "text") -> None:
        """Stream output to callback with type indicator.
        Raises AgentCancelledError if stop_event is set."""
        if self.stop_event and self.stop_event.is_set():
            raise AgentCancelledError()
        if self.output_callback:
            self.output_callback(msg_type, text)

    def _calculate_context_tokens(self, messages: List[Dict[str, Any]]) -> int:
        """计算当前 context 的 token 数（system + messages）"""
        system_tokens = count_tokens(config.get_system_prompt())
        memory_messages = [m for m in messages if m.get("role") != "system"]
        memory_tokens = sum(count_tokens(m.get("content", "")) for m in memory_messages)
        return int(system_tokens + memory_tokens)

    def run(self, user_input: str) -> str:
        """
        Run the agent with a user input.
        Returns the final response text.
        """
        # Build messages for LLM
        messages: List[Dict[str, Any]] = [create_system_message(config.get_system_prompt())]

        # Add memory context
        messages.extend(memory.get_conversation_for_llm())

        # Add current user input
        messages.append(create_user_message(user_input))

        # Add user message to memory
        memory.add_message("user", user_input)
        # 记录用户消息，用于压缩触发检测
        self._compact_engine.record_user_message()

        # Get all available tools from tools.json + MCP
        tools = list(self.llm.tools)  # Start with tools from tools.json

        # Add MCP tools via manager
        tools.extend(self.mcp_manager.get_all_tool_definitions())

        # 计算当前 context token 数
        current_tokens = self._calculate_context_tokens(messages)

        # 检查是否需要压缩
        should_compact, level = self._compact_engine.should_compact(
            current_tokens,
            config.effective_context_window
        )

        if should_compact:
            result = self._compact_engine.compact(level, self.llm)
            if result["compacted"]:
                self._stream_output(
                    f"\n[上下文压缩: L{level} • 节省 ~{result['tokens_saved']} tokens • 移除 {result['messages_removed']} 条消息]\n",
                    "compact"
                )
                # 重新计算 token 并重建消息
                messages = [create_system_message(config.get_system_prompt())]
                messages.extend(memory.get_conversation_for_llm())
                # 不再重复添加 user_input，因为 get_conversation_for_llm() 已包含
                current_tokens = self._calculate_context_tokens(messages)

                # 再次检查是否还需要继续压缩（防止压缩循环）
                should_compact_again, next_level = self._compact_engine.should_compact(
                    current_tokens,
                    config.effective_context_window
                )
                while should_compact_again and next_level <= level:
                    # 升级压缩级别
                    next_level = min(next_level + 1, CompactEngine.LEVEL_FULL)
                    result = self._compact_engine.compact(next_level, self.llm)
                    if result["compacted"]:
                        self._stream_output(
                            f"\n[追加压缩: L{next_level} • 节省 ~{result['tokens_saved']} tokens]\n",
                            "compact"
                        )
                        # 重建消息
                        messages = [create_system_message(config.get_system_prompt())]
                        messages.extend(memory.get_conversation_for_llm())
                        # 不再重复添加 user_input，因为 get_conversation_for_llm() 已包含
                        current_tokens = self._calculate_context_tokens(messages)
                    should_compact_again, next_level = self._compact_engine.should_compact(
                        current_tokens,
                        config.effective_context_window
                    )

        # 发送 context 使用率到 TUI
        usage_ratio = current_tokens / config.effective_context_window if config.effective_context_window > 0 else 0
        self._stream_output(f"context_usage:{usage_ratio:.2f}", "context_usage")

        # Turn counter to prevent infinite loops
        turns = 0
        max_turns = config.max_turns

        while turns < max_turns:
            # Check cancellation between iterations
            if self.stop_event and self.stop_event.is_set():
                raise AgentCancelledError()

            turns += 1

            # Get LLM response with tool calls
            tool_calls, reasoning = self.llm.get_tool_calls(messages, tools)

            # If reasoning_content exists AND there are tool calls, we MUST pass it back
            if reasoning and tool_calls:
                # Output thinking first (if show_thinking is true)
                if config.show_thinking and reasoning:
                    for line in reasoning.split('\n'):
                        if line.strip():
                            self._stream_output(f"{line}\n", "thinking")
                    self._stream_output("\n", "thinking")

                # Create assistant message with reasoning_content
                assistant_msg = {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [{
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": tc["arguments"]
                        }
                    } for tc in tool_calls]
                }
                # Add reasoning_content for thinking mode
                assistant_msg["reasoning_content"] = reasoning
                messages.append(assistant_msg)
                self._last_reasoning = reasoning
            elif tool_calls:
                # Has tool calls but no reasoning - still need reasoning_content field for thinking mode
                messages.append({
                    "role": "assistant",
                    "content": "",
                    "reasoning_content": reasoning or "",
                    "tool_calls": [{
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": tc["arguments"]
                        }
                    } for tc in tool_calls]
                })

            if not tool_calls:
                # No tool calls, this is the final response
                break

            # Execute tool calls and collect results
            for tc in tool_calls:
                tool_name = tc["name"]
                arguments = json.loads(tc["arguments"]) if isinstance(tc["arguments"], str) else tc["arguments"]

                # Execute tool
                self._stream_output(f"\n[Calling tool: {tool_name}]\n")
                result = self._execute_tool_call(tool_name, arguments)
                # 增加工具调用连续计数
                self._compact_engine.increment_streak()

                # Add tool result message
                messages.append(create_tool_result_message(tc["id"], result.get("content", "")))

                # Display result
                if result.get("success"):
                    self._stream_output(f"[Result]:\n{result.get('content', '')[:20000]}\n")
                else:
                    self._stream_output(f"[Error]: {result.get('error', 'Unknown error')}\n")

                # Note: Don't save tool results to memory - they reference tool_call_ids
                # that won't be preserved, which would break subsequent turns

        # Get final response from LLM (after all tool executions)
        # Note: For final response without tool calls, we should NOT include reasoning_content

        # Create a wrapper callback to handle thinking indicator and formatting
        thinking_started = [False]  # Use list to allow modification in closure

        def wrap_callback(text, is_reasoning: bool = False):
            if is_reasoning:
                # Thinking content - only output when show_thinking is true
                if config.show_thinking:
                    self._stream_output(text, "thinking")
            else:
                # Final response
                if config.show_thinking and not thinking_started[0]:
                    # First final content - emit answer_start signal
                    self._stream_output("\n", "answer_start")
                    thinking_started[0] = True
                self._stream_output(text, "answer")

        def usage_callback(usage: Dict[str, int]):
            self._last_usage = usage

        final_response, final_reasoning, usage = self.llm.chat(
            messages,
            tools=tools,
            stream=True,
            callback=wrap_callback,
            usage_callback=usage_callback
        )

        # Add assistant response to memory
        memory.add_message("assistant", final_response)

        # 计算token消耗并显示
        # 各部分 token
        system_tokens = count_tokens(config.get_system_prompt())
        memory_tokens = sum(count_tokens(msg.get("content", "")) for msg in memory.get_conversation_for_llm())
        input_tokens = count_tokens(user_input)
        reasoning_tokens = count_tokens(final_reasoning) if final_reasoning else 0
        output_tokens = count_tokens(final_response)

        # 本次总消耗
        total_this = system_tokens + memory_tokens + input_tokens + reasoning_tokens + output_tokens
        self.total_tokens += total_this

        # 格式化显示
        def fmt_token(t):
            if t >= 1000:
                return f"{t/1000:.3f}K"
            return f"{t:.0f}"

        self._stream_output(f"⬆{fmt_token(system_tokens + memory_tokens + input_tokens)} ⬇{fmt_token(reasoning_tokens + output_tokens)} ∫{fmt_token(self.total_tokens)}", "token_info")

        return final_response

    def reset(self) -> None:
        """Reset agent state"""
        memory.clear()
        self._last_reasoning = ""