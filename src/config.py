"""Configuration management - reads from config.json"""

import json
import logging
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from .utils.path import resolve_path, get_project_root

logger = logging.getLogger(__name__)


class Config:
    """Configuration manager that reads from config.json"""

    _instance: Optional["Config"] = None
    _lock = threading.Lock()
    _config: Dict[str, Any] = {}
    _mcp_config: Dict[str, Any] = {}

    def __new__(cls) -> "Config":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._load_config()
                    cls._instance._load_mcp_config()
        return cls._instance

    def _load_config(self) -> None:
        """Load configuration from config.json"""
        config_path = resolve_path("config.json")
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                self._config = json.load(f)
        except FileNotFoundError:
            logger.warning(f"config.json not found at {config_path}, using defaults")
            self._config = {}
        except json.JSONDecodeError as e:
            logger.warning(f"config.json parse error: {e}, using defaults")
            self._config = {}

    def _load_mcp_config(self) -> None:
        """Load MCP configuration from mcp.json

        Supports two formats:
        1. {"enabled": true, "servers": [...]} - legacy format
        2. {"mcpServers": {"name": {...}}} - standard MCP config format
        """
        try:
            mcp_config_path = resolve_path("mcp.json")
            with open(mcp_config_path, "r", encoding="utf-8") as f:
                raw_config = json.load(f)

            # Convert standard MCP format to internal format
            if "mcpServers" in raw_config:
                servers = []
                for name, server_config in raw_config["mcpServers"].items():
                    servers.append({
                        "name": name,
                        "type": server_config.get("type", "stdio"),
                        "url": server_config.get("url", ""),
                        "command": server_config.get("command", ""),
                        "args": server_config.get("args", []),
                        "env": server_config.get("env", {}),
                        "headers": server_config.get("headers", {}),
                        "api_key": server_config.get("api_key", ""),
                    })
                self._mcp_config = {"enabled": True, "servers": servers}
            else:
                self._mcp_config = raw_config
        except FileNotFoundError:
            self._mcp_config = {}
        except Exception as e:
            self._mcp_config = {}

    def reload(self) -> None:
        """Reload configuration from file"""
        self._load_config()
        self._load_mcp_config()

    # OpenAI / LLM Configuration
    @property
    def api_key(self) -> str:
        return self._config.get("openai", {}).get("api_key", "")

    @property
    def base_url(self) -> str:
        return self._config.get("openai", {}).get("base_url", "https://api.deepseek.com")

    @property
    def model(self) -> str:
        return self._config.get("openai", {}).get("model", "deepseek-v4-flash")

    @property
    def temperature(self) -> float:
        return self._config.get("openai", {}).get("temperature", 0.7)

    @property
    def top_p(self) -> float:
        return self._config.get("openai", {}).get("top_p", 0.7)

    @property
    def reasoning_effort(self) -> str:
        return self._config.get("openai", {}).get("reasoning_effort", "max")

    @property
    def context_window(self) -> int:
        """context_window: 值 >= 1000 直接作为 token 数，值 < 1000 作为"K"单位（如 64 表示 64K = 64000）"""
        value = self._config.get("openai", {}).get("context_window", 64)
        if value >= 1000:
            return value
        return value * 1000

    @property
    def max_output_tokens(self) -> int:
        """最大输出 token 数，用于计算有效上下文窗口"""
        return self._config.get("openai", {}).get("max_output_tokens", 20000)

    @property
    def effective_context_window(self) -> int:
        """有效上下文 = context_window - max_output_tokens（确保输出有空间）"""
        return max(self.context_window - self.max_output_tokens, 16000)

    # Compact Configuration
    @property
    def compact_enabled(self) -> bool:
        return self._config.get("compact", {}).get("enabled", True)

    @property
    def compact_buffer_tokens(self) -> int:
        """压缩后保留的 buffer token 数"""
        return self._config.get("compact", {}).get("buffer_tokens", 13000)

    @property
    def compact_threshold(self) -> int:
        """触发压缩的 token 数阈值"""
        return self.effective_context_window - self.compact_buffer_tokens

    @property
    def compact_micro_streak(self) -> int:
        """Micro Compact 连续工具调用阈值"""
        return self._config.get("compact", {}).get("micro_compact_streak", 3)

    @property
    def compact_micro_gap_minutes(self) -> int:
        """Micro Compact 时间间隔（分钟）"""
        return self._config.get("compact", {}).get("micro_compact_gap_minutes", 5)

    @property
    def compact_auto_threshold(self) -> float:
        """Auto Compact 使用率阈值（0.0-1.0）"""
        return self._config.get("compact", {}).get("auto_compact_threshold", 0.85)

    @property
    def compact_full_threshold(self) -> float:
        """Full Compact 使用率阈值（0.0-1.0）"""
        return self._config.get("compact", {}).get("full_compact_threshold", 0.95)

    @property
    def compact_preserve_messages(self) -> int:
        """压缩后保留的最近消息数"""
        return self._config.get("compact", {}).get("preserve_recent_messages", 10)

    @property
    def compact_prompt_path(self) -> str:
        """压缩提示词文件路径"""
        return self._config.get("compact", {}).get("prompt_path", "./compact_prompt.md")

    def get_compact_prompt(self) -> str:
        """读取压缩提示词模板，支持缓存"""
        if not hasattr(self, "_compact_prompt_cache"):
            self._compact_prompt_cache: Optional[str] = None
        if self._compact_prompt_cache is None:
            try:
                path = resolve_path(self.compact_prompt_path.lstrip("./"))
                self._compact_prompt_cache = path.read_text(encoding="utf-8")
            except Exception:
                self._compact_prompt_cache = self._default_compact_prompt()
        return self._compact_prompt_cache

    def _default_compact_prompt(self) -> str:
        """默认压缩提示词（备用）"""
        return """请为以下对话历史生成简洁摘要（500 tokens以内）：

{messages}

{requirements}

摘要要求：
- 提炼核心主题和任务
- 保留重要决策和结论
- 标注涉及的文件和工具
"""

    # Agent Configuration
    @property
    def max_turns(self) -> int:
        return self._config.get("agent", {}).get("max_turns", 10)

    @property
    def max_retries(self) -> int:
        return self._config.get("agent", {}).get("max_retries", 3)

    @property
    def memory_threshold(self) -> int:
        return self._config.get("agent", {}).get("memory_threshold", 20)

    @property
    def thinking_enabled(self) -> bool:
        return self._config.get("agent", {}).get("thinking_enabled", True)

    # Display Configuration
    @property
    def show_thinking(self) -> bool:
        return self._config.get("display", {}).get("show_thinking", True)

    @property
    def thinking_indicator(self) -> str:
        return self._config.get("display", {}).get("thinking_indicator", "思考中")

    # System Prompt
    @property
    def system_prompt_path(self) -> str:
        return self._config.get("system_prompt", {}).get("path", "./systsc.md")

    def get_system_prompt(self) -> str:
        """Read system prompt from file with caching"""
        if not hasattr(self, "_system_prompt_cache"):
            self._system_prompt_cache: Optional[str] = None
        if self._system_prompt_cache is None:
            try:
                path = resolve_path(self.system_prompt_path.lstrip("./"))
                self._system_prompt_cache = path.read_text(encoding="utf-8")
            except Exception:
                self._system_prompt_cache = "You are a helpful AI assistant."
        return self._system_prompt_cache

    # Tools Configuration
    @property
    def enabled_tools(self) -> List[str]:
        return self._config.get("tools", {}).get("enabled", ["shell", "file", "grep", "glob"])

    # MCP Configuration (from mcp.json)
    @property
    def mcp_enabled(self) -> bool:
        return self._mcp_config.get("enabled", True)

    @property
    def mcp_servers(self) -> List[Dict[str, Any]]:
        return self._mcp_config.get("servers", [])

    def get_mcp_server(self, name: str) -> Optional[Dict[str, Any]]:
        """Get MCP server configuration by name"""
        for server in self.mcp_servers:
            if server.get("name") == name:
                return server
        return None

    # Memory Configuration
    @property
    def memory_path(self) -> str:
        return self._config.get("memory", {}).get("path", "./memory/conversation.json")

    @property
    def memory_auto_summary(self) -> bool:
        return self._config.get("memory", {}).get("auto_summary", True)

    # Logs Configuration
    @property
    def logs_path(self) -> str:
        return self._config.get("logs", {}).get("path", "./logs/agent.log")

    @property
    def logs_level(self) -> str:
        return self._config.get("logs", {}).get("level", "INFO")

    @property
    def logs_max_bytes(self) -> int:
        """Maximum size of each log file before rotation (default: 10MB)."""
        return self._config.get("logs", {}).get("max_bytes", 10 * 1024 * 1024)

    @property
    def logs_backup_count(self) -> int:
        """Number of backup log files to keep (default: 5)."""
        return self._config.get("logs", {}).get("backup_count", 5)


# Global config instance
config = Config()