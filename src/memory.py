"""Memory management for conversation history and summarization"""

import json
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .utils.path import get_project_root
from .config import config

logger = logging.getLogger(__name__)

# Compact constants
MICRO_COMPACT_KEEP_COUNT = 5
SUMMARY_TRUNCATE_LENGTH = 500


class Memory:
    """
    Manages conversation memory with automatic summarization.

    Design:
    - Current session is kept in memory only (not persisted to disk between sessions)
    - History is saved to separate files in memory/history/ folder
    - Each history file represents a completed session
    - On startup, memory starts fresh (no auto-load of history)
    """

    _instance: Optional["Memory"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "Memory":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialize()
        return cls._instance

    def _initialize(self) -> None:
        """Initialize memory - starts fresh, no historical loading"""
        self._history: List[Dict[str, Any]] = []
        self._last_updated: Optional[str] = None
        self._session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._history_dir = get_project_root() / "memory" / "history"
        self._rw_lock = threading.RLock()
        logger.debug(f"Memory initialized: session_id={self._session_id}")

    def save_current_session(self) -> str:
        """
        Save current session to history folder.
        Called when user ends a session or at session boundary.
        Returns the path to the saved file.
        """
        if not self._history:
            return ""

        try:
            self._history_dir.mkdir(parents=True, exist_ok=True)
            filename = f"session_{self._session_id}.json"
            filepath = self._history_dir / filename

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump({
                    "session_id": self._session_id,
                    "history": self._history,
                    "saved_at": datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)

            logger.info(f"Saved session {self._session_id} to {filename} ({len(self._history)} messages)")
            return str(filepath)
        except Exception as e:
            logger.error(f"Failed to save session: {e}")
            return ""

    def load_session(self, session_path: str) -> bool:
        """
        Load a specific session from history.
        Returns True if successful.
        """
        logger.debug(f"Loading session from {session_path}")
        try:
            path = Path(session_path)
            if not path.exists():
                logger.warning(f"Session file not found: {session_path}")
                return False

            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._history = data.get("history", [])
                self._session_id = data.get("session_id", self._session_id)
                self._last_updated = data.get("saved_at")
            logger.info(f"Loaded session {self._session_id} ({len(self._history)} messages)")
            return True
        except Exception as e:
            logger.error(f"Failed to load session: {e}")
            return False

    def list_sessions(self) -> List[Dict[str, str]]:
        """
        List all saved sessions in history folder.
        Returns list of dicts with session_id, filename, and saved_at.
        """
        sessions = []
        try:
            self._history_dir.mkdir(parents=True, exist_ok=True)
            for filepath in sorted(self._history_dir.glob("session_*.json"), reverse=True):
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    sessions.append({
                        "session_id": data.get("session_id", filepath.stem),
                        "filename": filepath.name,
                        "saved_at": data.get("saved_at", ""),
                        "message_count": len(data.get("history", []))
                    })
                except Exception as e:
                    logger.warning(f"Failed to read session file {filepath.name}: {e}")
                    continue
        except Exception as e:
            logger.warning(f"Failed to list sessions in {self._history_dir}: {e}")
        return sessions

    def add_message(self, role: str, content: str, tool_calls: Optional[List[Dict]] = None) -> None:
        """Add a message to current session history"""
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        if tool_calls:
            message["tool_calls"] = tool_calls
        with self._rw_lock:
            self._history.append(message)
            self._last_updated = datetime.now().isoformat()
        logger.debug(f"Added {role} message, session has {len(self._history)} messages")

    def add_tool_result(self, tool_call_id: str, tool_name: str, result: str) -> None:
        """Add a tool execution result to current session"""
        logger.debug(f"Adding tool result: {tool_name}, {len(result or '')} chars")
        with self._rw_lock:
            self._history.append({
                "role": "tool",
                "tool_call_id": tool_call_id,
                "tool_name": tool_name,
                "content": result,
                "timestamp": datetime.now().isoformat()
            })
            self._last_updated = datetime.now().isoformat()

    def get_messages(self) -> List[Dict[str, Any]]:
        """Get current session conversation history"""
        with self._rw_lock:
            return list(self._history)

    def get_context(self, max_messages: int = 20) -> List[Dict[str, Any]]:
        """Get recent messages from current session"""
        with self._rw_lock:
            return self._history[-max_messages:] if self._history else []

    def clear(self) -> None:
        """Clear current session memory only"""
        with self._rw_lock:
            msg_count = len(self._history)
            self._history = []
            self._last_updated = None
            self._session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        logger.info(f"Cleared {msg_count} messages, new session_id={self._session_id}")

    def get_conversation_for_llm(self, max_messages: int = 40) -> List[Dict[str, Any]]:
        """
        Get current session conversation formatted for LLM.
        Only returns current session messages, no historical loading.
        """
        messages = self.get_context(max_messages)
        result = []
        for m in messages:
            # Filter to only fields the LLM API accepts
            if m.get("role") == "tool":
                # Tool messages must only have role, tool_call_id, and content
                result.append({
                    "role": "tool",
                    "tool_call_id": m.get("tool_call_id"),
                    "content": m.get("content", "")
                })
            else:
                result.append({k: v for k, v in m.items() if k in ("role", "content", "tool_calls", "tool_call_id", "reasoning_content")})
        return result


def is_compact_boundary(message: Dict[str, Any]) -> bool:
    """检查消息是否为压缩边界标记"""
    is_boundary = (
        message.get("role") == "system"
        and message.get("content") == "[COMPACT_BOUNDARY]"
        and "compact_boundary" in message
    )
    if not is_boundary and message.get("content") == "[COMPACT_BOUNDARY]":
        logger.warning(f"Partial compact boundary match: role={message.get('role')}, "
                      f"has_compact_boundary={'compact_boundary' in message}")
    return is_boundary


def create_compact_boundary(
    original_message_count: int,
    original_token_estimate: int,
    summary: str = ""
) -> Dict[str, Any]:
    """创建压缩边界标记消息"""
    return {
        "role": "system",
        "content": "[COMPACT_BOUNDARY]",
        "compact_boundary": {
            "version": 1,
            "original_count": original_message_count,
            "original_tokens": original_token_estimate,
            "created_at": datetime.now().isoformat(),
            "summary": summary
        }
    }


class CompactEngine:
    """
    上下文压缩引擎 - 三层压缩策略

    Level 1 (Micro): 清理旧 tool results，减少内存占用
    Level 2 (Auto):  LLM 生成摘要，保留关键信息
    Level 3 (Full):  彻底重写上下文
    """

    LEVEL_MICRO = 1
    LEVEL_AUTO = 2
    LEVEL_FULL = 3

    def __init__(self, memory: "Memory"):
        logger.debug("CompactEngine initialized")
        self._memory = memory
        self._compact_count = 0
        self._last_compact_at: Optional[str] = None
        self._tool_call_streak = 0
        self._last_user_message_time: Optional[datetime] = None
        self._pending_summary: Optional[str] = None

    def increment_streak(self) -> None:
        """增加工具调用连续计数"""
        self._tool_call_streak += 1

    def record_user_message(self) -> None:
        """记录用户消息，用于时间触发检测"""
        self._last_user_message_time = datetime.now()
        self._tool_call_streak = 0

    def should_compact(self, current_tokens: int, context_window: int) -> tuple:
        """
        检查是否需要压缩

        Returns:
            (需要压缩, 建议的压缩级别)
        """
        if not config.compact_enabled:
            return False, 0

        usage_ratio = current_tokens / context_window if context_window > 0 else 0

        # Full Compact: 使用率 >= 95%
        if usage_ratio >= config.compact_full_threshold:
            logger.info(f"should_compact: FULL, ratio={usage_ratio:.2f}")
            return True, self.LEVEL_FULL

        # Auto Compact: 使用率 >= 85%
        if usage_ratio >= config.compact_auto_threshold:
            logger.info(f"should_compact: AUTO, ratio={usage_ratio:.2f}")
            return True, self.LEVEL_AUTO

        # Micro Compact: 连续工具调用 >= 阈值
        if self._tool_call_streak >= config.compact_micro_streak:
            logger.debug(f"should_compact: MICRO (streak={self._tool_call_streak})")
            return True, self.LEVEL_MICRO

        # Micro Compact: 距离上次用户消息超过时间阈值
        if self._last_user_message_time:
            elapsed = (datetime.now() - self._last_user_message_time).total_seconds() / 60
            if elapsed >= config.compact_micro_gap_minutes:
                logger.debug(f"should_compact: MICRO (gap={elapsed:.1f}min)")
                return True, self.LEVEL_MICRO

        return False, 0

    def compact(self, level: int, llm_client=None) -> Dict[str, Any]:
        """
        执行压缩

        Args:
            level: 压缩级别 (1=Micro, 2=Auto, 3=Full)
            llm_client: LLM 客户端（Auto/Full 级别需要）
            level: 压缩级别 (1=Micro, 2=Auto, 3=Full)
            llm_client: LLM 客户端（Auto/Full 级别需要）

        Returns:
            压缩结果字典
        """
        result = {
            "compacted": False,
            "level": level,
            "tokens_saved": 0,
            "messages_removed": 0
        }

        if level == self.LEVEL_MICRO:
            micro_result = self._micro_compact()
            result.update(micro_result)
        elif level == self.LEVEL_AUTO:
            if llm_client is None:
                logger.warning("Auto compact requires LLM client")
                return result
            auto_result = self._auto_compact(llm_client)
            result.update(auto_result)
        elif level == self.LEVEL_FULL:
            if llm_client is None:
                logger.warning("Full compact requires LLM client")
                return result
            full_result = self._full_compact(llm_client)
            result.update(full_result)

        if result["compacted"]:
            self._compact_count += 1
            self._last_compact_at = datetime.now().isoformat()

        return result

    def _micro_compact(self) -> Dict[str, Any]:
        """
        微压缩：清理旧的 tool results

        保留最近 5 个工具结果，将更早的结果替换为简短提示
        """
        from .utils.token_counter import count_tokens

        cleared = 0
        cleared_tokens = 0
        tool_results = [
            (i, m) for i, m in enumerate(self._memory._history)
            if m.get("role") == "tool" and m.get("_cleared") is not True
        ]

        # 保留最近的 tool_results
        keep_recent = MICRO_COMPACT_KEEP_COUNT
        # 正确处理 keep_recent=0 的情况（Python 中 :-0 等于 :0，返回空列表）
        if keep_recent > 0:
            to_clear = tool_results[:-keep_recent]
        else:
            to_clear = tool_results[:] if tool_results else []
        for i, msg in to_clear:
            msg_tokens = count_tokens(msg.get("content", ""))
            cleared_tokens += msg_tokens
            msg["content"] = f"[工具结果已清理 • 约 {int(msg_tokens)} tokens]"
            msg["_cleared"] = True
            cleared += 1

        if cleared > 0:
            logger.info(f"Micro compact: cleared {cleared} tool results")
        return {
            "compacted": cleared > 0,
            "tokens_saved": int(cleared_tokens),
            "messages_removed": cleared
        }

    def _auto_compact(self, llm_client) -> Dict[str, Any]:
        """
        自动压缩：使用 LLM 生成摘要

        1. 找到/创建 compact boundary
        2. 调用 LLM 生成摘要
        3. 保留 boundary 之后的消息
        4. 插入摘要
        """
        from .utils.token_counter import count_tokens

        # 统计当前状态
        original_count = len(self._memory._history)
        original_tokens = sum(
            count_tokens(m.get("content", "") or "")
            for m in self._memory._history
        )

        # 查找或创建 boundary
        boundary_idx = None
        for i, msg in enumerate(self._memory._history):
            if is_compact_boundary(msg):
                boundary_idx = i
                break

        # 确定保留消息的起始位置
        preserve_count = config.compact_preserve_messages
        if boundary_idx is not None:
            start_idx = boundary_idx + 1
            preserved = self._memory._history[start_idx:]
        else:
            preserved = self._memory._history[-preserve_count:] if self._memory._history else []

        # 生成摘要
        summary = self._generate_summary(self._memory._history, boundary_idx, llm_client)

        # 重建 history
        if boundary_idx is not None:
            self._memory._history = self._memory._history[:boundary_idx + 1]
        else:
            self._memory._history = []

        # 添加 boundary（如果没有的话）
        if boundary_idx is None:
            boundary = create_compact_boundary(original_count, int(original_tokens), summary)
            self._memory._history.append(boundary)

        # 添加摘要消息
        self._memory._history.append({
            "role": "system",
            "content": f"[对话摘要]\n{summary}",
            "timestamp": datetime.now().isoformat()
        })

        # 保留最近的 preserved 消息 (already sliced to preserve_count above)
        self._memory._history.extend(preserved)

        tokens_saved = original_tokens - sum(
            count_tokens(m.get("content", "") or "")
            for m in self._memory._history
        )

        logger.info(f"Auto compact: {original_count} -> {len(self._memory._history)} messages")
        return {
            "compacted": True,
            "tokens_saved": int(tokens_saved),
            "messages_removed": original_count - len(self._memory._history)
        }

    def _full_compact(self, llm_client) -> Dict[str, Any]:
        """
        完全压缩：保存会话并重置

        1. 保存当前会话到历史
        2. 清空 memory
        3. 保留 compact boundary 和任务描述
        """
        # 保存当前会话
        self._memory.save_current_session()

        # 统计
        original_count = len(self._memory._history)
        from .utils.token_counter import count_tokens
        original_tokens = sum(
            count_tokens(m.get("content", "") or "")
            for m in self._memory._history
        )

        # 创建新的 boundary（带完整摘要）
        summary = self._generate_summary(self._memory._history, None, llm_client)
        boundary = create_compact_boundary(original_count, int(original_tokens), summary)

        # 清空并重建
        self._memory._history = [boundary]
        self._memory._history.append({
            "role": "system",
            "content": f"[对话摘要]\n{summary}",
            "timestamp": datetime.now().isoformat()
        })

        logger.info(f"Full compact: saved session with {original_count} messages")
        new_tokens = sum(
            count_tokens(m.get("content", "") or "")
            for m in self._memory._history
        )
        return {
            "compacted": True,
            "tokens_saved": max(int(original_tokens - new_tokens), 0),
            "messages_removed": original_count - 2  # boundary + summary
        }

    def _generate_summary(self, messages: List[Dict[str, Any]], boundary_idx: Optional[int], llm_client) -> str:
        """使用 LLM 生成对话摘要"""
        from .llm.client import create_system_message, create_user_message

        # 收集要摘要的消息
        if boundary_idx is not None:
            msg_range = messages[:boundary_idx]
        else:
            msg_range = messages

        # 构建摘要请求
        msg_texts = []
        for m in msg_range:
            role = m.get("role", "?")
            content = m.get("content", "")
            if content:
                msg_texts.append(f"{role}: {content[:SUMMARY_TRUNCATE_LENGTH]}")

        messages_content = f"{'='*60}\n{chr(10).join(msg_texts[-20:])}\n{'='*60}"

        # Load prompt template from config
        try:
            prompt_template = config.get_summary_template()
            if "(对话历史将自动插入)" in prompt_template:
                prompt = prompt_template.replace("(对话历史将自动插入)", messages_content)
            else:
                prompt = f"{prompt_template}\n\n{messages_content}"
        except Exception as e:
            logger.warning(f"Failed to load summary template: {e}")
            prompt = f"Please generate a concise summary for the following conversation:\n\n{messages_content}"

        try:
            summary_messages = [
                create_system_message(config.summary_system_prompt),
                create_user_message(prompt)
            ]

            # 使用真正的 LLM 生成摘要
            if llm_client is not None:
                response, _, _, _ = llm_client.chat(summary_messages, stream=False)
                return response[:2000] if response else "[摘要生成失败: 无响应]"
            else:
                # fallback 到简单摘要，传入原始对话历史
                response, _ = self._llm_fallback_summary(summary_messages, original_history=msg_range)
                return response[:2000]
        except Exception as e:
            logger.error(f"Summary generation failed: {e}")
            return f"[摘要生成失败: {str(e)[:100]}]"

    def _llm_fallback_summary(self, messages: List[Dict[str, Any]], original_history: Optional[List[Dict[str, Any]]] = None) -> tuple:
        """基于规则的简单摘要生成（不使用LLM）"""
        # 使用原始对话历史（如果提供），否则使用传入的摘要请求消息
        source = original_history if original_history else messages

        # 提取关键信息：用户消息、工具调用、结果
        user_inputs = []
        tool_calls = []
        last_tool = None

        for m in source:
            role = m.get("role", "")
            content = m.get("content", "") or ""
            tool_name = m.get("tool_name", "")

            if role == "user" and content:
                user_inputs.append(content[:100])
            elif role == "tool" and tool_name:
                tool_calls.append(tool_name)
                last_tool = tool_name

        # 构建简单摘要
        summary_parts = []

        if user_inputs:
            recent = user_inputs[-3:]
            summary_parts.append(f"用户输入({len(user_inputs)}条): {' | '.join(recent[:2])}")

        if tool_calls:
            from collections import Counter
            tool_counts = Counter(tool_calls)
            top_tools = tool_counts.most_common(3)
            tools_str = ", ".join([f"{t}({c})" for t, c in top_tools])
            summary_parts.append(f"工具调用({len(tool_calls)}次): {tools_str}")

        if last_tool:
            summary_parts.append(f"最近工具: {last_tool}")

        if not summary_parts:
            return "[对话摘要 - 无足够内容生成摘要]", ""

        summary = "; ".join(summary_parts)
        return f"[对话摘要] {summary}", ""


# Global memory instance
memory = Memory()