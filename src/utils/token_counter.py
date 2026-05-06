import re

# 模块级预编译正则，避免重复编译开销
_CHINESE_RE = re.compile(r'[一-龥]')
_ENGLISH_RE = re.compile(r'[a-zA-Z]+')
_DIGIT_RE = re.compile(r'\d')
_PUNCTUATION_SET = frozenset('.,;:!?，。；：！？""''《》（）[]{}()')

def count_tokens(text: str) -> float:
    """计算文本token数

    计算规则：
    - 中文字符：1.3 token/个
    - 英语单词：1.1 token/个
    - 标点符号：1 token/个
    - 数字：1 token/个
    """
    if not text:
        return 0.0

    # 中文字符 (Unicode 范围一-龥)
    chinese = len(_CHINESE_RE.findall(text))
    # 英语单词
    english = len(_ENGLISH_RE.findall(text))
    # 标点符号
    punctuation = sum(1 for c in text if c in _PUNCTUATION_SET)
    # 数字
    digits = len(_DIGIT_RE.findall(text))

    # 使用frozenset确保不重复计算同字符
    classified_chars = set(_CHINESE_RE.findall(text)) | set(_ENGLISH_RE.findall(text))
    classified_chars.update(c for c in text if c in _PUNCTUATION_SET or c.isdigit())
    other = len(text) - len(classified_chars)

    return chinese * 1.3 + english * 1.1 + (punctuation + digits + other) * 1.0