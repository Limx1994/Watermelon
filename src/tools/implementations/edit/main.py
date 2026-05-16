"""Edit Tool - 精确字符串替换工具，支持引号规范化和文件修改检测"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Set UTF-8 encoding for stdout to avoid GBK encoding errors on Chinese Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout = os.fdopen(os.dup(sys.stdout.fileno()), mode='w', encoding='utf-8', buffering=1)
if sys.stderr.encoding != 'utf-8':
    sys.stderr = os.fdopen(os.dup(sys.stderr.fileno()), mode='w', encoding='utf-8', buffering=1)

# ============================================================
# 常量
# ============================================================

# 弯引号和直引号映射
QUOTE_PAIRS = {
    '‘': '\'',  # 左单弯引号 → 直单引号
    '’': '\'',  # 右单弯引号 → 直单引号
    '“': '"',   # 左双弯引号 → 直双引号
    '”': '"',   # 右双弯引号 → 直双引号
}

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


# ============================================================
# 路径处理
# ============================================================

def expand_path(path: str) -> Path:
    """展开路径，不支持 ~ 简写"""
    if '~' in path:
        raise ValueError('Path cannot contain ~. Use absolute path instead.')

    p = Path(path)

    # 如果是相对路径，基于项目根目录
    if not p.is_absolute():
        root = get_project_root()
        p = root / p

    return p.resolve()


def get_project_root() -> Path:
    """获取项目根目录（查找 config.json）"""
    current = Path(__file__).resolve().parent
    while current != current.parent:
        if (current / "config.json").exists():
            return current
        current = current.parent
    return Path.cwd()


# ============================================================
# 权限检查
# ============================================================

def check_permissions(file_path: Path) -> Tuple[bool, str]:
    """检查文件读写权限"""
    if not file_path.exists():
        return False, f'File not found: {file_path}'

    if not os.access(file_path, os.R_OK):
        return False, f'File is not readable: {file_path}'

    if not os.access(file_path, os.W_OK):
        return False, f'File is not writable: {file_path}'

    return True, ''


# ============================================================
# 引号规范化
# ============================================================

def normalize_quotes(text: str) -> str:
    """将弯引号转换为直引号，用于匹配"""
    for curly, straight in QUOTE_PAIRS.items():
        text = text.replace(curly, straight)
    return text


def get_quote_style(text: str) -> Dict[str, str]:
    """检测文本中使用的引号风格"""
    style = {
        'single_curly': '‘’',  # ''
        'double_curly': '“”',  # ""
        'single_straight': "'",
        'double_straight': '"'
    }

    has_single_curly = '‘' in text or '’' in text
    has_double_curly = '“' in text or '”' in text

    return {
        'single_quote': '’' if has_single_curly else "'",
        'double_quote': '”' if has_double_curly else '"'
    }


# ============================================================
# 字符串查找
# ============================================================

def find_actual_string(content: str, old_string: str) -> List[int]:
    """查找 old_string 在 content 中的所有位置（处理引号规范化）"""
    positions = []
    normalized_content = normalize_quotes(content)
    normalized_old = normalize_quotes(old_string)

    start = 0
    while True:
        pos = normalized_content.find(normalized_old, start)
        if pos == -1:
            break
        positions.append(pos)
        start = pos + 1

    return positions


def validate_strings(old_string: str, new_string: str) -> Tuple[bool, str]:
    """验证 old_string 和 new_string 是否有效"""
    if old_string == new_string:
        return False, 'old_string and new_string must be different'

    if not old_string:
        return False, 'old_string cannot be empty'

    return True, ''


# ============================================================
# 内容替换
# ============================================================

def replace_string(content: str, old_string: str, new_string: str,
                   replace_all: bool = False) -> Tuple[str, int]:
    """
    替换字符串
    返回: (new_content, replacement_count)
    """
    positions = find_actual_string(content, old_string)

    if not positions:
        return content, 0

    if not replace_all:
        positions = positions[:1]

    # 获取引号风格
    quote_style = get_quote_style(content)

    # 构建替换后的内容
    # 保持原文件的引号风格
    new_string_normalized = normalize_quotes(new_string)

    result = content
    offset = 0

    for pos in positions:
        actual_old = content[pos:pos + len(old_string)]

        # 替换时保持原文件的引号风格
        replaced_new = new_string_normalized
        if quote_style['single_quote'] == '’':
            replaced_new = replaced_new.replace("'", '’')
        if quote_style['double_quote'] == '”':
            replaced_new = replaced_new.replace('"', '”')

        result = result[:pos + offset] + replaced_new + result[pos + offset + len(old_string):]
        offset += len(replaced_new) - len(old_string)

    return result, len(positions)


# ============================================================
# 文件操作
# ============================================================

def read_file_content(file_path: Path) -> Tuple[str, int]:
    """读取文件内容，返回 (content, mtime_ms)"""
    mtime_ms = int(file_path.stat().st_mtime * 1000)

    # 尝试 UTF-8 with BOM
    try:
        content = file_path.read_text(encoding='utf-8-sig')
    except UnicodeDecodeError:
        try:
            content = file_path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            try:
                content = file_path.read_text(encoding='gbk')
            except UnicodeDecodeError:
                content = file_path.read_text(encoding='latin-1')

    # 统一换行符
    content = content.replace('\r\n', '\n').replace('\r', '\n')

    return content, mtime_ms


def atomic_write(file_path: Path, content: str) -> bool:
    """原子写入：先写临时文件，再替换"""
    temp_path = file_path.with_suffix(file_path.suffix + '.tmp')

    try:
        temp_path.write_text(content, encoding='utf-8')
        temp_path.replace(file_path)
        return True
    except Exception as e:
        if temp_path.exists():
            temp_path.unlink()
        raise e


# ============================================================
# 主逻辑
# ============================================================

def do_edit(file_path: str, old_string: str, new_string: str,
            replace_all: bool = False) -> Dict[str, Any]:
    """执行编辑操作"""

    # 1. 路径展开
    try:
        abs_path = expand_path(file_path)
    except ValueError as e:
        return {'success': False, 'error': str(e)}

    # 2. 权限检查
    can_write, error_msg = check_permissions(abs_path)
    if not can_write:
        return {'success': False, 'error': error_msg}

    # 3. 验证字符串
    valid, error_msg = validate_strings(old_string, new_string)
    if not valid:
        return {'success': False, 'error': error_msg}

    # 4. 读取文件
    try:
        content, mtime_ms = read_file_content(abs_path)
    except Exception as e:
        return {'success': False, 'error': f'Failed to read file: {e}'}

    # 5. 查找并替换
    new_content, count = replace_string(content, old_string, new_string, replace_all)

    if count == 0:
        return {
            'success': False,
            'error': 'String to replace not found in file',
            'content': content,
            'mtimeMs': mtime_ms
        }

    # 6. 写入文件
    try:
        atomic_write(abs_path, new_content)
    except Exception as e:
        return {'success': False, 'error': f'Failed to write file: {e}'}

    # 7. 返回结果
    new_mtime_ms = int(abs_path.stat().st_mtime * 1000)

    return {
        'success': True,
        'replacements': count,
        'old_string': old_string,
        'new_string': new_string,
        'mtimeMs': new_mtime_ms
    }


def main():
    parser = argparse.ArgumentParser(description="Edit file tool")
    parser.add_argument("--file-path", required=True, help="File path (absolute)")
    parser.add_argument("--old-string", required=True, help="String to replace")
    parser.add_argument("--new-string", required=True, help="Replacement string")
    parser.add_argument("--replace-all", type=lambda x: x.lower() == 'true',
                        default=False, help="Replace all occurrences")

    args = parser.parse_args()

    result = do_edit(args.file_path, args.old_string, args.new_string, args.replace_all)

    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
