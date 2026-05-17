"""Memory management for conversation history and summarization"""

import copy
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
            logger.error(f"Failed to save session (session_id={self._session_id}): {e}", exc_info=True)
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
            logger.info(f"Loaded session {self._session_id} ({len(self._history)} messages)")
            return True
        except Exception as e:
            logger.error(f"Failed to load session (path={session_path}): {e}", exc_info=True)
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
        logger.debug(f"Listed {len(sessions)} sessions")
        return sessions

    def add_message(
        self,
        role: str,
        content: str,
        tool_calls: Optional[List[Dict]] = None,
        reasoning_content: str = ""
    ) -> None:
        """Add a message to current session history.

        Args:
            role: Message role (user/assistant/system/tool)
            content: Message content
            tool_calls: Optional tool calls for assistant messages
            reasoning_content: Optional reasoning content for thinking mode
        """
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        if tool_calls:
            message["tool_calls"] = tool_calls
        if reasoning_content:
            message["reasoning_content"] = reasoning_content
        with self._rw_lock:
            self._history.append(message)
        logger.debug(f"Added {role} message, session has {len(self._history)} messages")

    def get_messages(self) -> List[Dict[str, Any]]:
        """Get current session conversation history (deep copy to prevent mutation)"""
        with self._rw_lock:
            return copy.deepcopy(self._history)

    def get_context(self, max_messages: int = 20) -> List[Dict[str, Any]]:
        """Get recent messages from current session (deep copy to prevent mutation)"""
        with self._rw_lock:
            return copy.deepcopy(self._history[-max_messages:]) if self._history else []

    def clear(self) -> None:
        """Clear current session memory only"""
        with self._rw_lock:
            msg_count = len(self._history)
            self._history = []
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
        logger.debug(f"get_conversation_for_llm: {len(messages)} messages -> {len(result)} formatted")
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
    上下文压缩引擎 - 三级压缩策略

    Level 1 (Micro): 清理旧 tool results，减少内存占用
    Level 2 (Auto):  LLM 生成摘要，保留关键信息
    Level 3 (Full):  保存会话并彻底重写上下文
    """

    LEVEL_MICRO = 1
    LEVEL_AUTO = 2
    LEVEL_FULL = 3

    def __init__(self, memory: "Memory"):
        logger.debug("CompactEngine initialized")
        self._memory = memory
        self._tool_call_streak = 0
        self._last_user_message_time: Optional[datetime] = None
        self._compact_lock = threading.Lock()
        # 电路断路器状态
        self._consecutive_compact_failures = 0
        self._compact_circuit_open = False
        self._compact_in_progress = threading.Event()
        self.MAX_CONSECUTIVE_COMPACT_FAILURES = 3

    def increment_streak(self) -> None:
        """增加工具调用连续计数（线程安全）"""
        with self._compact_lock:
            self._tool_call_streak += 1
            logger.debug(f"Tool call streak: {self._tool_call_streak}")

    def record_user_message(self) -> None:
        """记录用户消息，用于时间触发检测（线程安全）"""
        with self._compact_lock:
            self._last_user_message_time = datetime.now()
            self._tool_call_streak = 0

    def reset(self) -> None:
        """重置所有会话级压缩状态（/clear 时调用）"""
        with self._compact_lock:
            self._tool_call_streak = 0
            self._last_user_message_time = None
            self._consecutive_compact_failures = 0
            self._compact_circuit_open = False
            if self._compact_in_progress.is_set():
                logger.warning("Clearing compact_in_progress flag during /clear")
                self._compact_in_progress.clear()
        logger.info("CompactEngine session state reset")

    def should_compact(self, current_tokens: int, context_window: int) -> tuple:
        """
        检查是否需要压缩

        Returns:
            (需要压缩, 建议的压缩级别)
        """
        if not config.compact_enabled:
            return False, 0

        # 递归保护：压缩进行中不触发新的压缩
        if self._compact_in_progress.is_set():
            return False, 0

        # 电路断路器：连续失败超过阈值则跳过
        if self._compact_circuit_open:
            logger.warning("Compact circuit breaker open, skipping")
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

        # Buffer check: 剩余空间不足 buffer_tokens 时触发 Auto Compact
        remaining = context_window - current_tokens
        if remaining < config.compact_buffer_tokens:
            logger.info(f"should_compact: AUTO (buffer), remaining={remaining} < {config.compact_buffer_tokens}")
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

        Returns:
            压缩结果字典
        """
        result = {
            "compacted": False,
            "level": level,
            "tokens_saved": 0,
            "messages_removed": 0
        }

        if self._compact_in_progress.is_set():
            return result
        self._compact_in_progress.set()

        try:
            if level == self.LEVEL_MICRO:
                with self._compact_lock:
                    micro_result = self._micro_compact()
                    result.update(micro_result)
            elif level == self.LEVEL_AUTO:
                if llm_client is None:
                    logger.warning("Auto compact requires LLM client")
                    return result
                # LLM 调用在 _compact_lock 外进行，不阻塞 increment_streak()
                auto_result = self._auto_compact(llm_client)
                with self._compact_lock:
                    result.update(auto_result)
            elif level == self.LEVEL_FULL:
                if llm_client is None:
                    logger.warning("Full compact requires LLM client")
                    return result
                full_result = self._full_compact(llm_client)
                with self._compact_lock:
                    result.update(full_result)
            else:
                logger.warning(f"Unknown compact level: {level}")
                return result
        finally:
            self._compact_in_progress.clear()

        if result["compacted"]:
            # 成功：重置失败计数
            self._consecutive_compact_failures = 0
            self._compact_circuit_open = False
            # 压缩后状态清理
            self._post_compact_cleanup()
            logger.info(f"Compact done: level={result['level']}, "
                        f"removed={result['messages_removed']}, "
                        f"saved={result['tokens_saved']} tokens")
        else:
            # 失败：递增失败计数，触发电路断路器
            self._consecutive_compact_failures += 1
            if self._consecutive_compact_failures >= self.MAX_CONSECUTIVE_COMPACT_FAILURES:
                self._compact_circuit_open = True
                logger.error(
                    f"Compact circuit breaker opened after "
                    f"{self._consecutive_compact_failures} consecutive failures"
                )
        return result

    def _micro_compact(self) -> Dict[str, Any]:
        """
        微压缩：清理旧的 tool results

        保留最近 5 个工具结果，将更早的结果替换为简短提示
        """
        from .utils.token_counter import count_tokens

        cleared = 0
        cleared_tokens = 0
        with self._memory._rw_lock:
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

        1. 在锁内获取 history 快照
        2. 调用 LLM 生成摘要（锁外）
        3. 在锁内重建 history
        """
        from .utils.token_counter import count_tokens

        # 在锁内获取 history 快照，确保后续操作基于一致的数据
        with self._memory._rw_lock:
            history_snapshot = list(self._memory._history)

        original_count = len(history_snapshot)
        original_tokens = sum(
            count_tokens(m.get("content", "") or "")
            for m in history_snapshot
        )
        logger.debug(f"[compact] Auto compact start: {original_count} messages, {original_tokens} tokens")

        # 查找 boundary
        boundary_idx = None
        for i, msg in enumerate(history_snapshot):
            if is_compact_boundary(msg):
                boundary_idx = i
                logger.debug(f"[compact] Existing boundary found at index {i}")
                break

        # 确定保留消息
        preserve_count = config.compact_preserve_messages
        if boundary_idx is not None:
            preserved = history_snapshot[boundary_idx + 1:]
        else:
            preserved = history_snapshot[-preserve_count:] if history_snapshot else []
        logger.debug(f"[compact] Preserving {len(preserved)} messages after boundary")

        # 生成摘要（锁外，不阻塞并发读取）
        summary = self._generate_summary(history_snapshot, boundary_idx, llm_client)

        # 重建 history（加锁防止并发读取看到半成品）
        with self._memory._rw_lock:
            if boundary_idx is not None:
                self._memory._history = history_snapshot[:boundary_idx + 1]
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

            # 保留最近的 preserved 消息
            self._memory._history.extend(preserved)

            # 在锁内计算 token 节省量
            new_tokens = sum(
                count_tokens(m.get("content", "") or "")
                for m in self._memory._history
            )
            tokens_saved = original_tokens - new_tokens

        logger.info(f"Auto compact: {original_count} -> {len(self._memory._history)} messages, saved ~{int(tokens_saved)} tokens")
        return {
            "compacted": True,
            "tokens_saved": int(tokens_saved),
            "messages_removed": max(original_count - len(self._memory._history), 0)
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

        # 在锁内获取 history 快照，确保后续操作基于一致的数据
        from .utils.token_counter import count_tokens
        with self._memory._rw_lock:
            history_snapshot = list(self._memory._history)

        original_count = len(history_snapshot)
        original_tokens = sum(
            count_tokens(m.get("content", "") or "")
            for m in history_snapshot
        )
        logger.debug(f"[compact] Full compact start: {original_count} messages, {original_tokens} tokens")

        # 创建新的 boundary（带完整摘要）
        summary = self._generate_summary(history_snapshot, None, llm_client)
        boundary = create_compact_boundary(original_count, int(original_tokens), summary)

        # 清空并重建（加锁防止并发读取看到半成品）
        with self._memory._rw_lock:
            self._memory._history = [boundary]
            self._memory._history.append({
                "role": "system",
                "content": f"[对话摘要]\n{summary}",
                "timestamp": datetime.now().isoformat()
            })
            # 在锁内计算 token 节省量
            new_tokens = sum(
                count_tokens(m.get("content", "") or "")
                for m in self._memory._history
            )

        logger.info(f"[compact] Full compact complete: saved session, boundary created, history cleared, saved ~{max(int(original_tokens - new_tokens), 0)} tokens")
        return {
            "compacted": True,
            "tokens_saved": max(int(original_tokens - new_tokens), 0),
            "messages_removed": max(original_count - 2, 0)  # boundary + summary
        }

    def _generate_summary(self, messages: List[Dict[str, Any]], boundary_idx: Optional[int], llm_client) -> str:
        """使用 LLM 生成对话摘要"""
        from .llm.client import create_system_message, create_user_message

        # 收集要摘要的消息
        if boundary_idx is not None:
            msg_range = messages[:boundary_idx]
        else:
            msg_range = messages
        logger.debug(f"[compact] Generating summary for {len(msg_range)} messages")

        if not msg_range:
            return "[无消息可摘要]"

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
            prompt = config.get_summary_prompt(messages_content)
        except Exception as e:
            logger.warning(f"Failed to load summary template: {e}")
            prompt = f"Please generate a concise summary for the following conversation:\n\n{messages_content}"

        try:
            summary_messages = [
                create_system_message(config.summary_system_prompt),
                create_user_message(prompt)
            ]

            response, _, _, _ = llm_client.chat(summary_messages, stream=False)
            summary_text = response[:2000] if response else "[摘要生成失败: 无响应]"
            logger.debug(f"[compact] LLM summary generated: {len(summary_text)} chars")
            return summary_text
        except Exception as e:
            logger.error(f"Summary generation failed: {e}", exc_info=True)
            return f"[摘要生成失败: {str(e)[:100]}]"

    def _post_compact_cleanup(self) -> None:
        """压缩后状态清理：重置计数器，避免重复压缩"""
        self._tool_call_streak = 0
        self._last_user_message_time = datetime.now()
        logger.debug("Post-compact cleanup: reset streak and gap timer")

# Global memory instance
memory = Memory()