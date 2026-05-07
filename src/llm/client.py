"""OpenAI compatible LLM client for DeepSeek API"""

import json
import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from openai import OpenAI

from ..config import config

logger = logging.getLogger(__name__)


def load_tools_from_json() -> List[Dict[str, Any]]:
    """Load tools definition from tools.json file"""
    tools_path = Path(__file__).parent.parent.parent / "tools.json"
    if not tools_path.exists():
        return []
    with open(tools_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("tools", [])


class LLMClient:
    """OpenAI compatible client for DeepSeek API with thinking mode support"""

    def __init__(self):
        logger.info(f"Initializing LLM client: model={config.model}, base_url={config.base_url}")
        self.client = OpenAI(
            api_key=config.api_key,
            base_url=config.base_url
        )
        self.model = config.model
        self.temperature = config.temperature
        self.top_p = config.top_p
        self.reasoning_effort = config.reasoning_effort
        self.thinking_enabled = config.thinking_enabled
        # Load tools from tools.json
        self.tools = load_tools_from_json()
        logger.debug(f"Loaded {len(self.tools)} tools from tools.json")

    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        stream: bool = True,
        callback: Optional[Callable[[str, bool], None]] = None,
        usage_callback: Optional[Callable[[Dict[str, int]], None]] = None
    ) -> Tuple[str, str, Optional[Dict[str, int]]]:
        """
        Send a chat request to the LLM.

        Args:
            messages: List of message dicts with 'role' and 'content'
            tools: Optional list of tool definitions
            stream: Whether to use streaming
            callback: Optional callback for streaming responses
            usage_callback: Optional callback for receiving usage info (prompt_tokens, completion_tokens, total_tokens)

        Returns:
            Tuple of (response_content, reasoning_content, usage_dict)
            usage_dict is only available in non-streaming mode
        """
        params: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "reasoning_effort": self.reasoning_effort,
            "stream": stream
        }

        if tools:
            params["tools"] = tools

        if stream and callback:
            logger.debug(f"Streaming chat request with {len(messages)} messages")
            response_content = ""
            reasoning_content = ""
            reasoning_buffer = ""
            in_thinking = True  # Start with thinking mode
            usage_info = None

            stream_iter = self.client.chat.completions.create(**params)
            for chunk in stream_iter:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta if chunk.choices else None
                if not delta:
                    continue

                # Handle reasoning_content (thinking process)
                if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                    reasoning_content += delta.reasoning_content
                    reasoning_buffer += delta.reasoning_content
                    # Buffer reasoning until we get final content or buffer is large enough
                    if len(reasoning_buffer) >= 50 or (reasoning_content and not in_thinking):
                        callback(reasoning_buffer, is_reasoning=True)
                        reasoning_buffer = ""

                # Handle final content - when content starts, thinking is done
                if hasattr(delta, 'content') and delta.content:
                    if in_thinking and reasoning_buffer:
                        # Flush remaining thinking buffer
                        callback(reasoning_buffer, is_reasoning=True)
                        reasoning_buffer = ""
                    in_thinking = False
                    response_content += delta.content
                    callback(delta.content, is_reasoning=False)

                # 收集 usage 信息（如果有）
                if hasattr(chunk, 'usage') and chunk.usage and usage_info is None:
                    usage_info = {
                        "prompt_tokens": chunk.usage.prompt_tokens or 0,
                        "completion_tokens": chunk.usage.completion_tokens or 0,
                        "total_tokens": chunk.usage.total_tokens or 0
                    }

            # Flush any remaining reasoning content
            if reasoning_buffer:
                callback(reasoning_buffer, is_reasoning=True)

            # 发送 usage 信息
            if usage_info and usage_callback:
                usage_callback(usage_info)

            logger.debug(f"Chat completed: {len(response_content)} chars response, {len(reasoning_content)} chars reasoning")
            return response_content, reasoning_content, usage_info
        else:
            logger.debug(f"Non-streaming chat request with {len(messages)} messages")
            response = self.client.chat.completions.create(**params)
            if not response.choices:
                raise ValueError("Empty choices in LLM non-streaming response")
            msg = response.choices[0].message
            reasoning = getattr(msg, 'reasoning_content', '') or ''
            usage = None
            if hasattr(response, 'usage') and response.usage:
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens or 0,
                    "completion_tokens": response.usage.completion_tokens or 0,
                    "total_tokens": response.usage.total_tokens or 0
                }
            logger.debug(f"Non-streaming chat completed: {len(msg.content or '')} chars")
            return msg.content or "", reasoning, usage

    def get_tool_calls(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], str]:
        """
        Get tool calls from the LLM response.

        Args:
            messages: List of message dicts
            tools: List of tool definitions

        Returns:
            Tuple of (list of tool call dicts, reasoning_content)
        """
        logger.debug(f"get_tool_calls request with {len(messages)} messages, {len(tools)} tools")
        params = {
            "model": self.model,
            "messages": messages,
            "tools": tools,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "reasoning_effort": self.reasoning_effort,
            "stream": False
        }

        response = self.client.chat.completions.create(**params)
        message = response.choices[0].message

        tool_calls = []
        if message.tool_calls:
            tool_calls = [
                {
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": tc.function.arguments
                }
                for tc in message.tool_calls
            ]

        reasoning = getattr(message, 'reasoning_content', '') or ''
        logger.debug(f"get_tool_calls response: {len(tool_calls)} tool calls, {len(reasoning)} chars reasoning")
        return tool_calls, reasoning


def create_system_message(content: str) -> Dict[str, Any]:
    """Create a system message dict"""
    return {"role": "system", "content": content}


def create_user_message(content: str) -> Dict[str, Any]:
    """Create a user message dict"""
    return {"role": "user", "content": content}


def create_assistant_message(content: str, reasoning_content: str = "") -> Dict[str, Any]:
    """Create an assistant message dict"""
    # IMPORTANT: Do NOT include reasoning_content in the message to send to API
    # It will cause a 400 error. reasoning_content is only for internal tracking.
    return {"role": "assistant", "content": content}


def create_tool_result_message(tool_call_id: str, content: str) -> Dict[str, Any]:
    """Create a tool result message dict"""
    return {
        "role": "tool",
        "tool_call_id": tool_call_id,
        "content": content
    }