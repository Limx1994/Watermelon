import re

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
    chinese = len(re.findall(r'[一-龥]', text))
    # 英语单词
    english = len(re.findall(r'[a-zA-Z]+', text))
    # 标点符号
    punctuation_chars = '.,;:!?，。；：！？""''《》（）[]'
    punctuation = sum(1 for c in text if c in punctuation_chars)
    # 数字
    digits = len(re.findall(r'\d', text))

    # 总字符数 - 已计算的各类 = 其他字符
    other = len(text) - chinese - english - punctuation - digits
    return chinese * 1.3 + english * 1.1 + (punctuation + digits + other) * 1.0