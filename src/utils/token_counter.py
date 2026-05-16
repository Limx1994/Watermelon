"""Token counting utilities — tiktoken with estimation fallback"""

import logging
import re

logger = logging.getLogger(__name__)

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
            _ENCODER = False
            logger.debug("tiktoken unavailable, using estimation fallback")
    return _ENCODER


def count_tokens(text: str) -> int:
    """计算文本token数

    优先使用 tiktoken 精确计算（如果可用），否则回退到估算规则：
    - 中文字符：1.3 token/个
    - 英语单词：1.1 token/个
    - 标点符号：1 token/个
    - 数字：1 token/个
    """
    if not text:
        return 0

    # 尝试使用 tiktoken
    encoder = _get_encoder()
    if encoder:
        try:
            return len(encoder.encode(text))
        except Exception:
            logger.debug("tiktoken encode failed, using estimation fallback")

    # 估算规则
    chinese = len(_CHINESE_RE.findall(text))
    english = len(_ENGLISH_RE.findall(text))
    punctuation = sum(1 for c in text if c in _PUNCTUATION_SET)
    digits = len(_DIGIT_RE.findall(text))
    classified = chinese + english + punctuation + digits
    other = len(text) - classified

    return round(chinese * 1.3 + english * 1.1 + (punctuation + digits + other) * 1.0)