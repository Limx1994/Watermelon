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
            # tiktoken >=0.12 移除了 cl100k_base，使用 o200k_base 替代
            _ENCODER = tiktoken.get_encoding("o200k_base")
        except (ImportError, Exception):
            _ENCODER = False
            logger.debug("tiktoken unavailable, using estimation fallback")
    return _ENCODER


def count_tokens(text: str) -> int:
    """计算文本token数

    优先使用 tiktoken 精确计算（如果可用），否则回退到估算规则：
    - 中文字符：2.0 token/个（偏保守，避免 context overflow）
    - 英语单词：0.75 token/个（GPT 系列经验均值）
    - 其他字符：0.5 token/个
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

    # 估算规则（保守偏大，确保不超出 context window）
    chinese = len(_CHINESE_RE.findall(text))
    english_words = _ENGLISH_RE.findall(text)
    english_count = len(english_words)
    english_chars = sum(len(w) for w in english_words)
    remaining_chars = len(text) - chinese - english_chars

    return round(chinese * 2.0 + english_count * 0.75 + remaining_chars * 0.5)