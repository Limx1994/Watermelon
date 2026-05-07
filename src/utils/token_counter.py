import re
from typing import Any, Dict, List

# 模块级预编译正则，避免重复编译开销
_CHINESE_RE = re.compile(r'[一-龥]')
_ENGLISH_RE = re.compile(r'[a-zA-Z]+')
_DIGIT_RE = re.compile(r'\d')
_PUNCTUATION_SET = frozenset('.,;:!?，。；：！？""''《》（）[]{}()')

# tiktoken 编码器（可选）
_ENCODER = None


def _get_encoder():
    """获取 tiktoken 编码器（延迟加载）"""
    global _ENCODER
    if _ENCODER is None:
        try:
            import tiktoken
            _ENCODER = tiktoken.get_encoding("cl100k_base")
        except ImportError:
            _ENCODER = False  # 标记为不可用
    return _ENCODER


def count_tokens(text: str) -> float:
    """计算文本token数

    优先使用 tiktoken 精确计算（如果可用），否则回退到估算规则：
    - 中文字符：1.3 token/个
    - 英语单词：1.1 token/个
    - 标点符号：1 token/个
    - 数字：1 token/个
    """
    if not text:
        return 0.0

    # 尝试使用 tiktoken
    encoder = _get_encoder()
    if encoder:
        try:
            return float(len(encoder.encode(text)))
        except Exception:
            pass  # 回退到估算

    # 估算规则
    chinese = len(_CHINESE_RE.findall(text))
    english = len(_ENGLISH_RE.findall(text))
    punctuation = sum(1 for c in text if c in _PUNCTUATION_SET)
    digits = len(_DIGIT_RE.findall(text))

    classified_chars = set(_CHINESE_RE.findall(text)) | set(_ENGLISH_RE.findall(text))
    classified_chars.update(c for c in text if c in _PUNCTUATION_SET or c.isdigit())
    other = len(text) - len(classified_chars)

    return chinese * 1.3 + english * 1.1 + (punctuation + digits + other) * 1.0


def count_messages_tokens(messages: List[Dict[str, Any]], system_prompt: str) -> Dict[str, int]:
    """计算消息列表的总 token 数

    Args:
        messages: 消息列表
        system_prompt: 系统提示词

    Returns:
        包含各部分 token 数的字典
    """
    total = count_tokens(system_prompt)
    details = {"system": count_tokens(system_prompt)}

    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "") or ""
        tool_calls = msg.get("tool_calls", [])

        msg_tokens = count_tokens(content)

        # tool_calls 的 arguments 也消耗 token
        for tc in tool_calls:
            if isinstance(tc, dict):
                import json
                args = tc.get("arguments", "")
                if isinstance(args, str):
                    args = json.loads(args) if args else {}
                msg_tokens += count_tokens(json.dumps(args))

        total += msg_tokens
        details[role] = details.get(role, 0) + msg_tokens

    details["total"] = total
    return details