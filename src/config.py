"""Configuration management - reads from config.json"""

import json
import logging
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from .utils.path import resolve_path

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
        else:
            model = self._config.get("openai", {}).get("model", "?")
            base_url = self._config.get("openai", {}).get("base_url", "?")
            ctx = self._config.get("openai", {}).get("context_window", "?")
            logger.info(f"Config loaded: model={model} base_url={base_url} context_window={ctx}")

    def _load_mcp_config(self) -> None:
        """Load MCP configuration from mcp.json

        Supports two formats:
        1. {"enabled": true, "servers": [...]} - legacy format
        2. {"mcpServers": {"name": {...}}} - standard MCP config format
        """
        try:
            mcp_config_path = resolve_path("config/mcp.json")
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
            logger.debug("mcp.json not found, using defaults")
            self._mcp_config = {}
        except Exception as e:
            logger.warning(f"MCP config load failed: {e}")
            self._mcp_config = {}

    def reload(self) -> None:
        """Reload configuration from file"""
        self._load_config()
        self._load_mcp_config()
        self._system_prompt_cache = None
        logger.info(f"Configuration reloaded: model={self.model} context_window={self.context_window}")

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
    def fallback_config(self) -> Optional[Dict[str, str]]:
        """Fallback model config for cross-provider degradation.

        Returns dict with model/base_url/api_key if fully configured, None otherwise.
        Supports legacy empty string format (returns None = disabled).
        """
        fb = self._config.get("openai", {}).get("fallback_model", "")
        if not fb:
            return None
        if isinstance(fb, str):
            return None
        if not fb.get("model") or not fb.get("base_url") or not fb.get("api_key"):
            return None
        return {
            "model": fb["model"],
            "base_url": fb["base_url"],
            "api_key": fb["api_key"],
        }

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
        try:
            value = int(self._config.get("openai", {}).get("context_window", 64))
        except (ValueError, TypeError):
            value = 64
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
        return self._config.get("compact", {}).get("prompt_path", "./prompts/compact_prompt.md")

    def get_compact_prompt(self) -> str:
        """Read compact prompt template from configured path, with caching."""
        return self._load_prompt("compact_prompt",
            "Please generate a concise summary for the following conversation:\n{messages}\n{requirements}")

    # Agent Configuration
    @property
    def max_turns(self) -> int:
        return self._config.get("agent", {}).get("max_turns", 50)

    @property
    def max_retries(self) -> int:
        return self._config.get("agent", {}).get("max_retries", 3)

    @property
    def retry_interval_seconds(self) -> int:
        """重试间隔秒数（默认60秒=1分钟）"""
        return self._config.get("agent", {}).get("retry_interval_seconds", 60)

    @property
    def network_max_retries(self) -> int:
        """网络错误最大重试次数（默认10次）"""
        return self._config.get("agent", {}).get("network_max_retries", 10)

    @property
    def network_retry_interval_seconds(self) -> int:
        """网络错误重试间隔秒数（默认30秒）"""
        return self._config.get("agent", {}).get("network_retry_interval_seconds", 30)

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
        return self._config.get("system_prompt", {}).get("path", "./prompts/systsc.md")

    def get_system_prompt(self) -> str:
        """Read system prompt from file with caching. Appends autonomous instructions if enabled."""
        if not hasattr(self, "_system_prompt_cache"):
            self._system_prompt_cache: Optional[str] = None
        if self._system_prompt_cache is None:
            try:
                path = resolve_path(self.system_prompt_path.removeprefix("./"))
                self._system_prompt_cache = path.read_text(encoding="utf-8")
            except Exception:
                self._system_prompt_cache = "You are a helpful AI assistant."
        logger.debug(f"System prompt loaded from {self.system_prompt_path}")
        base = self._system_prompt_cache
        base += "\n\n" + self.autonomous_instructions_prompt
        return base

    # Tools Configuration
    @property
    def enabled_tools(self) -> List[str]:
        return self._config.get("tools", {}).get("enabled", ["read_file", "write_file", "shell", "grep", "glob", "edit"])

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

    # Prompt File Configuration
    @property
    def prompts_dir(self) -> dict:
        return self._config.get("prompts", {})

    def _load_prompt(self, key: str, default: str = "") -> str:
        """Load a prompt from external .md file with caching."""
        cache_key = f"_prompt_cache_{key}"
        if not hasattr(self, cache_key):
            setattr(self, cache_key, None)
        cached = getattr(self, cache_key)
        if cached is not None:
            return cached

        path_str = self.prompts_dir.get(key, "")
        if not path_str:
            setattr(self, cache_key, default)
            return default
        try:
            path = resolve_path(path_str.removeprefix("./"))
            content = path.read_text(encoding="utf-8").strip()
            setattr(self, cache_key, content)
            return content
        except Exception:
            logger.warning(f"Failed to load prompt {key} from {path_str}, using default")
            setattr(self, cache_key, default)
            return default

    @property
    def autonomous_instructions_prompt(self) -> str:
        return self._load_prompt("autonomous_instructions",
            "You are running in autonomous mode.")

    @property
    def compact_resume_prompt(self) -> str:
        return self._load_prompt("compact_resume",
            "Continue the conversation from where it left off.")

    @property
    def max_tokens_recovery_prompt(self) -> str:
        return self._load_prompt("max_tokens_recovery",
            "Output token limit hit. Resume directly.")

    @property
    def context_too_long_prompt(self) -> str:
        return self._load_prompt("context_too_long",
            "Context too long — compressing and retrying.")

    @property
    def summary_system_prompt(self) -> str:
        return self._load_prompt("summary_system",
            "You are a summary generation expert.")

    def get_summary_template(self) -> str:
        """Read summary template, with placeholder support."""
        template = self._load_prompt("summary_template",
            "Please generate a concise summary for the following conversation:\n{messages}\n{requirements}")
        return template

    # Autonomous Configuration
    # Token Budget Nudge Configuration
    @property
    def nudge_threshold(self) -> float:
        """Token usage ratio threshold to inject nudge message (default 0.90)"""
        return self._config.get("agent", {}).get("nudge_threshold", 0.90)

    @property
    def nudge_prompt(self) -> str:
        """Nudge message injected when token budget is near limit"""
        return self._load_prompt("token_budget_nudge",
            "Context at {pct:.0%}. Keep working — do not summarize.")

    # Autonomous Configuration
    @property
    def cron_tasks(self) -> list:
        """Cron task definitions for autonomous mode"""
        return self._config.get("autonomous", {}).get("cron_tasks", [])

    @property
    def tick_interval_minutes(self) -> int:
        """Tick interval in minutes for proactive wake-up (default 10)"""
        return self._config.get("autonomous", {}).get("tick_interval_minutes", 10)


# Global config instance
config = Config()