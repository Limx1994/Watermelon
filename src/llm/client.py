"""OpenAI compatible LLM client for DeepSeek API"""

import json
import logging
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from openai import OpenAI

from ..config import config

logger = logging.getLogger(__name__)

# LLM constants
REASONING_BUFFER_THRESHOLD = 50


class NetworkError(Exception):
    """网络错误基类"""
    pass


class NetworkDisconnectedError(NetworkError):
    """网络断开错误"""
    pass


def is_network_error(e: Exception) -> bool:
    """判断是否为网络错误"""
    from openai import APIConnectionError
    if isinstance(e, APIConnectionError):
        return True
    if isinstance(e, (ConnectionError, TimeoutError, OSError)):
        return True
    if isinstance(e, NetworkError):
        return True
    error_str = str(e).lower()
    return any(kw in error_str for kw in ("connection", "timeout", "network", "dns", "connect"))


def load_tools_from_json() -> List[Dict[str, Any]]:
    """Load tools definition from tools.json file"""
    tools_path = Path(__file__).parent.parent.parent / "config" / "tools.json"
    if not tools_path.exists():
        logger.debug("tools.json not found")
        return []
    try:
        with open(tools_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        tools = data.get("tools", [])
        logger.debug(f"Loaded {len(tools)} tools from tools.json")
        return tools
    except Exception as e:
        logger.warning(f"Failed to load tools.json: {e}")
        return []


class LLMClient:
    """OpenAI compatible client for DeepSeek API with thinking mode support"""

    def __init__(self):
        logger.info(f"Initializing LLM client: model={config.model}, base_url={config.base_url}")
        self.client = OpenAI(
            api_key=config.api_key,
            base_url=config.base_url
        )
        self.model = config.model
        self._original_model = config.model
        self._active_client = None  # Saved primary client when degraded
        self._fallback_client = None
        fb = config.fallback_config
        if fb:
            self._fallback_client = OpenAI(
                api_key=fb["api_key"],
                base_url=fb["base_url"]
            )
            logger.info(f"Fallback client ready: model={fb['model']}, base_url={fb['base_url']}")
        self.temperature = config.temperature
        self.top_p = config.top_p
        self.reasoning_effort = config.reasoning_effort
        # Load tools from tools.json
        self.tools = load_tools_from_json()
        logger.debug(f"Loaded {len(self.tools)} tools from tools.json")

    def switch_model(self, model_name: str, client=None) -> None:
        """Switch to a different model at runtime (for degradation recovery).

        Args:
            model_name: The model name to switch to
            client: Optional OpenAI client for a different API provider
        """
        old = self.model
        self.model = model_name
        if client:
            self._active_client = self.client
            self.client = client
        logger.info(f"Model switched: {old} -> {model_name}")

    def restore_model(self) -> None:
        """Restore the original model after degradation recovery."""
        if self.model != self._original_model:
            old = self.model
            self.model = self._original_model
            if self._active_client:
                self.client = self._active_client
                self._active_client = None
            logger.info(f"Model restored: {old} -> {self._original_model}")

    def _call_with_retry(self, params: dict):
        """Call the API with exponential backoff retry and model degradation.

        Uses config.max_retries (default 3). On RateLimitError uses longer backoff.
        If all retries fail and fallback_config is configured, retries with fallback client.
        """
        try:
            return self._call_with_retries(params)
        except Exception as primary_error:
            fb = config.fallback_config
            if not fb:
                raise
            logger.warning(f"Primary model {self.model} failed: {primary_error}. Trying fallback: {fb['model']}")
            fallback_params = {**params, "model": fb["model"]}
            try:
                return self._call_with_retries(fallback_params, client=self._fallback_client)
            except Exception:
                raise primary_error

    def _call_with_retries(self, params: dict, client=None):
        """Call the API with exponential backoff retry for a specific model."""
        from openai import APIStatusError, APIConnectionError, RateLimitError

        api_client = client or self.client
        last_error = None

        # 判断是否为网络错误，使用更长的重试窗口
        for attempt in range(config.max_retries):
            try:
                return api_client.chat.completions.create(**params)
            except RateLimitError as e:
                wait = min(2 ** attempt * 2, 60)
                logger.warning(f"Rate limited, retry in {wait}s (attempt {attempt+1}/{config.max_retries})")
                time.sleep(wait)
                last_error = e
            except (APIStatusError, APIConnectionError) as e:
                # Don't retry client errors (4xx except 429)
                if isinstance(e, APIStatusError) and hasattr(e, 'status_code') and 400 <= e.status_code < 500 and e.status_code != 429:
                    raise
                wait = min(2 ** attempt, 30)
                logger.warning(f"API error {e}, retry in {wait}s (attempt {attempt+1}/{config.max_retries})")
                time.sleep(wait)
                last_error = e
            except Exception as e:
                wait = min(2 ** attempt, 30)
                logger.warning(f"Unexpected error {e}, retry in {wait}s (attempt {attempt+1}/{config.max_retries})")
                time.sleep(wait)
                last_error = e
        raise last_error

    def _call_with_network_retry(self, params: dict, client=None):
        """Call the API with extended retry for network errors."""
        from openai import APIStatusError, APIConnectionError, RateLimitError

        api_client = client or self.client
        last_error = None

        for attempt in range(config.network_max_retries):
            try:
                return api_client.chat.completions.create(**params)
            except RateLimitError as e:
                wait = min(config.retry_interval_seconds * (2 ** attempt), 300)
                logger.warning(f"Rate limited, retry in {wait}s (attempt {attempt+1}/{config.network_max_retries})")
                time.sleep(wait)
                last_error = e
            except (APIStatusError, APIConnectionError) as e:
                # Don't retry client errors (4xx except 429)
                if isinstance(e, APIStatusError) and hasattr(e, 'status_code') and 400 <= e.status_code < 500 and e.status_code != 429:
                    raise

                if is_network_error(e):
                    wait = min(config.network_retry_interval_seconds * (2 ** attempt), 120)
                    logger.warning(f"Network error, retry in {wait}s (attempt {attempt+1}/{config.network_max_retries})")
                else:
                    wait = min(config.retry_interval_seconds * (2 ** attempt), 60)
                    logger.warning(f"API error {e}, retry in {wait}s (attempt {attempt+1}/{config.network_max_retries})")
                time.sleep(wait)
                last_error = e
            except Exception as e:
                if is_network_error(e):
                    wait = min(config.network_retry_interval_seconds * (2 ** attempt), 120)
                else:
                    wait = min(config.retry_interval_seconds * (2 ** attempt), 60)
                logger.warning(f"Unexpected error {e}, retry in {wait}s (attempt {attempt+1}/{config.network_max_retries})")
                time.sleep(wait)
                last_error = e
        raise last_error

    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        stream: bool = True,
        callback: Optional[Callable[[str, bool], None]] = None,
        usage_callback: Optional[Callable[[Dict[str, int]], None]] = None
    ) -> Tuple[str, str, Optional[Dict[str, int]], Optional[str]]:
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

        if config.max_output_tokens:
            params["max_tokens"] = config.max_output_tokens

        if stream and callback:
            logger.debug(f"Streaming chat request with {len(messages)} messages")
            response_content = ""
            reasoning_content = ""
            reasoning_buffer = ""
            in_thinking = True  # Start with thinking mode
            usage_info = None
            finish_reason = None

            stream_iter = self._call_with_retry(params)
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
                    if len(reasoning_buffer) >= REASONING_BUFFER_THRESHOLD or (reasoning_content and not in_thinking):
                        callback(reasoning_buffer, is_reasoning=True)
                        reasoning_buffer = ""

                # Handle final content - when content starts, thinking is done
                if hasattr(delta, 'content') and delta.content:
                    if in_thinking:
                        # Flush any remaining thinking buffer when transitioning
                        if reasoning_buffer:
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

                # Capture finish_reason from final chunk
                if chunk.choices and chunk.choices[0].finish_reason:
                    finish_reason = chunk.choices[0].finish_reason

            # Flush any remaining reasoning content
            if reasoning_buffer:
                callback(reasoning_buffer, is_reasoning=True)

            # 发送 usage 信息
            if usage_info and usage_callback:
                usage_callback(usage_info)

            logger.debug(f"Chat completed: {len(response_content)} chars response, {len(reasoning_content)} chars reasoning")
            return response_content, reasoning_content, usage_info, finish_reason
        else:
            logger.debug(f"Non-streaming chat request with {len(messages)} messages")
            response = self._call_with_retry(params)
            if not response.choices:
                logger.warning("Empty choices in non-streaming chat response")
                return "", "", None, None
            msg = response.choices[0].message
            reasoning = getattr(msg, 'reasoning_content', '') or ''
            finish_reason = response.choices[0].finish_reason if response.choices else None
            usage = None
            if hasattr(response, 'usage') and response.usage:
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens or 0,
                    "completion_tokens": response.usage.completion_tokens or 0,
                    "total_tokens": response.usage.total_tokens or 0
                }
            logger.debug(f"Non-streaming chat completed: {len(msg.content or '')} chars")
            if usage and usage_callback:
                usage_callback(usage)
            return msg.content or "", reasoning, usage, finish_reason

    def get_tool_calls(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], str, str, str]:
        """
        Get tool calls from the LLM response.

        Args:
            messages: List of message dicts
            tools: List of tool definitions

        Returns:
            Tuple of (tool_calls, content, reasoning_content, finish_reason)
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

        if config.max_output_tokens:
            params["max_tokens"] = config.max_output_tokens

        response = self._call_with_retry(params)
        if not response.choices:
            logger.warning("Empty choices in get_tool_calls response")
            return [], "", "", ""
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

        content = message.content or ''
        reasoning = getattr(message, 'reasoning_content', '') or ''
        finish_reason = response.choices[0].finish_reason if response.choices else ""
        logger.debug(f"get_tool_calls response: {len(tool_calls)} tool calls, finish_reason={finish_reason}")
        return tool_calls, content, reasoning, finish_reason


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