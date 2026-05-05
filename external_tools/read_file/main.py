"""Read File Tool - 优化的文件读取工具，支持多种文件类型"""

import argparse
import base64
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

# ============================================================
# 常量
# ============================================================

MAX_FILE_SIZE = 512 * 1024  # 512KB
MAX_TOKENS = 180_000

# 二进制文件扩展名黑名单
BINARY_EXTENSIONS = {
    '.exe', '.dll', '.bin', '.sys', '.obj', '.o', '.a', '.lib',
    '.so', '.dylib', '.pyd', '.pyc', '.pyo', '.class', '.jar',
    '.zip', '.tar', '.gz', '.bz2', '.7z', '.rar',
    '.iso', '.img', '.dmg', '.vhd', '.vmdk',
    '.ttf', '.otf', '.woff', '.woff2', '.eot',
}

# 魔数签名
BINARY_SIGNATURES = {
    b'MZ': 'exe/dll',
    b'%PDF': 'pdf',
    b'\x89PNG': 'png',
    b'\xFF\xD8\xFF': 'jpeg',
    b'GIF8': 'gif',
    b'RIFF': 'webp',
    b'BM': 'bmp',
    b'II\x2a\x00': 'tiff',
    b'MM\x00\x2a': 'tiff',
}

# 图片扩展名
IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp'}

# ============================================================
# 工具函数
# ============================================================

def get_project_root() -> Path:
    """获取项目根目录（查找 config.json）"""
    current = Path(__file__).resolve().parent
    while current != current.parent:
        if (current / "config.json").exists():
            return current
        current = current.parent
    return Path.cwd()


def detect_binary(file_path: Path) -> Optional[str]:
    """使用魔数检测文件类型"""
    try:
        with open(file_path, 'rb') as f:
            header = f.read(16)

        for signature, file_type in BINARY_SIGNATURES.items():
            if header.startswith(signature):
                return file_type

        # 检查扩展名
        ext = file_path.suffix.lower()
        if ext in BINARY_EXTENSIONS:
            return 'binary'
        if ext in IMAGE_EXTENSIONS:
            return 'image'
        if ext == '.pdf':
            return 'pdf'

        return None
    except Exception:
        return None


def read_text_file(file_path: Path, offset: int = 0, limit: Optional[int] = None) -> Dict[str, Any]:
    """读取文本文件，支持 offset/limit"""
    content = file_path.read_text(encoding='utf-8-sig')  # 尝试 UTF-8 with BOM

    # 如果失败，尝试其他编码
    if '�' in content:
        try:
            content = file_path.read_text(encoding='gbk')
        except Exception:
            content = file_path.read_text(encoding='latin-1')

    # 统一换行符
    content = content.replace('\r\n', '\n').replace('\r', '\n')

    lines = content.split('\n')
    total_lines = len(lines)

    # 应用 offset/limit
    start_line = offset
    if offset >= total_lines:
        return {
            'type': 'text',
            'content': '',
            'metadata': {
                'numLines': 0,
                'totalLines': total_lines,
                'startLine': offset,
                'fileSize': file_path.stat().st_size,
                'mtimeMs': int(file_path.stat().st_mtime * 1000)
            }
        }

    end_line = total_lines if limit is None else min(offset + limit, total_lines)
    selected_lines = lines[offset:end_line]

    # 构建带行号的内容
    line_width = len(str(total_lines))
    numbered_lines = []
    for i, line in enumerate(selected_lines, start=offset + 1):
        numbered_lines.append(f"{i:>{line_width}}| {line}")

    result_content = '\n'.join(numbered_lines)

    return {
        'type': 'text',
        'content': result_content,
        'metadata': {
            'numLines': len(selected_lines),
            'totalLines': total_lines,
            'startLine': offset + 1,
            'fileSize': file_path.stat().st_size,
            'mtimeMs': int(file_path.stat().st_mtime * 1000)
        }
    }


def count_tokens(text: str) -> int:
    """计算文本的 token 数量"""
    tokens = 0

    # 中文字符: 1.3 token/char
    chinese_chars = len(re.findall(r'[一-鿿　-〿＀-￯]', text))
    tokens += chinese_chars * 1.3

    # 英文单词: 1.1 token/word
    english_words = len(re.findall(r'[a-zA-Z]+', text))
    tokens += english_words * 1.1

    # 其他字符: 1.0 token/char
    other_chars = len(text) - chinese_chars - sum(len(w) for w in re.findall(r'[a-zA-Z]+', text))
    tokens += other_chars * 1.0

    return int(tokens)


def read_image_file(file_path: Path) -> Dict[str, Any]:
    """读取图片文件，返回 base64 和尺寸"""
    try:
        from PIL import Image
    except ImportError:
        return {'error': 'Pillow not installed, cannot read image files'}

    try:
        with Image.open(file_path) as img:
            width, height = img.size

        file_size = file_path.stat().st_size
        with open(file_path, 'rb') as f:
            img_base64 = base64.b64encode(f.read()).decode('ascii')

        return {
            'type': 'image',
            'filePath': str(file_path),
            'base64': img_base64,
            'originalSize': file_size,
            'dimensions': {'width': width, 'height': height}
        }
    except Exception as e:
        return {'error': f'Failed to read image: {e}'}


def read_pdf_file(file_path: Path, pages: Optional[str] = None) -> Dict[str, Any]:
    """读取 PDF 文件"""
    try:
        from PyPDF2 import PdfReader
    except ImportError:
        return {'error': 'PyPDF2 not installed, cannot read PDF files'}

    try:
        reader = PdfReader(file_path)
        total_pages = len(reader.pages)

        # 解析页码范围
        page_range = None
        if pages:
            if '-' in pages:
                start, end = pages.split('-')
                page_range = (int(start.strip()) - 1, int(end.strip()) - 1)
            else:
                page_range = (int(pages.strip()) - 1, int(pages.strip()) - 1)

        # 检查页数决定处理方式
        if total_pages <= 10:
            # 小 PDF: 直接返回 base64
            with open(file_path, 'rb') as f:
                pdf_base64 = base64.b64encode(f.read()).decode('ascii')

            return {
                'type': 'pdf',
                'filePath': str(file_path),
                'base64': pdf_base64,
                'originalSize': file_path.stat().st_size,
                'totalPages': total_pages
            }
        else:
            # 大 PDF: 提取页面为图像
            if page_range:
                start_idx = max(0, page_range[0])
                end_idx = min(total_pages - 1, page_range[1])
            else:
                start_idx = 0
                end_idx = min(19, total_pages - 1)  # 最多20页

            images = []
            for i in range(start_idx, end_idx + 1):
                page = reader.pages[i]
                # 将页面转换为图像
                from io import BytesIO
                from PIL import Image

                # 渲染页面
                media_box = page.mediabox
                width = int(media_box.width)
                height = int(media_box.height)

                # 创建高分辨率图像
                scale = 2
                img = Image.new('RGB', (width * scale, height * scale))
                # 注意: PyPDF2 不直接支持渲染，需要用其他方式

                images.append({
                    'pageNumber': i + 1,
                    'text': page.extract_text()[:1000] if page.extract_text() else ''
                })

            return {
                'type': 'pdf_parts',
                'filePath': str(file_path),
                'totalPages': total_pages,
                'pageRange': f"{start_idx + 1}-{end_idx + 1}",
                'pages': images[:20]  # 最多20页
            }

    except Exception as e:
        return {'error': f'Failed to read PDF: {e}'}


def read_notebook(file_path: Path) -> Dict[str, Any]:
    """读取 Jupyter Notebook"""
    try:
        import nbformat
    except ImportError:
        return {'error': 'nbformat not installed, cannot read notebook files'}

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            nb = nbformat.read(f, as_version=4)

        cells = []
        for cell in nb.cells:
            cell_data = {
                'cell_type': cell.cell_type,
                'source': cell.source,
            }
            if cell.cell_type == 'code' and hasattr(cell, 'outputs'):
                cell_data['outputs'] = []
                for output in cell.outputs:
                    if output.get('output_type') == 'stream':
                        cell_data['outputs'].append({
                            'type': 'stream',
                            'text': ''.join(output.get('text', []))
                        })
                    elif output.get('output_type') == 'execute_result':
                        cell_data['outputs'].append({
                            'type': 'execute_result',
                            'data': output.get('data', {}),
                            'execution_count': output.get('execution_count')
                        })
                    elif output.get('output_type') == 'error':
                        cell_data['outputs'].append({
                            'type': 'error',
                            'ename': output.get('ename', ''),
                            'evalue': output.get('evalue', ''),
                            'traceback': output.get('traceback', [])
                        })

            if cell.cell_type == 'code' and hasattr(cell, 'execution_count'):
                cell_data['execution_count'] = cell.execution_count

            cells.append(cell_data)

        return {
            'type': 'notebook',
            'filePath': str(file_path),
            'cells': cells
        }
    except Exception as e:
        return {'error': f'Failed to read notebook: {e}'}


def main():
    parser = argparse.ArgumentParser(description="Read file tool (enhanced)")
    parser.add_argument("--path", required=True, help="File path")
    parser.add_argument("--offset", type=int, default=0, help="Starting line number (0-based)")
    parser.add_argument("--limit", type=int, default=None, help="Number of lines to read")
    parser.add_argument("--pages", type=str, default=None, help="PDF page range (e.g., '1-5')")

    args = parser.parse_args()

    # 解析路径
    root = get_project_root()
    file_path = Path(args.path)

    # 如果是相对路径，从项目根目录解析
    if not file_path.is_absolute():
        file_path = root / file_path

    # 检查文件是否存在
    if not file_path.exists():
        result = {
            'success': False,
            'error': f'File not found: {args.path}'
        }
        print(json.dumps(result))
        return

    # 检查文件大小
    try:
        file_size = file_path.stat().st_size
        if file_size > MAX_FILE_SIZE:
            result = {
                'success': False,
                'error': f'File too large: {file_size} bytes (max {MAX_FILE_SIZE} bytes)'
            }
            print(json.dumps(result))
            return
    except Exception:
        pass

    # 检测文件类型（优先使用扩展名，因为编译后魔数可能不准确）
    ext = file_path.suffix.lower()

    # 处理不同文件类型
    if ext in IMAGE_EXTENSIONS:
        read_result = read_image_file(file_path)
        if 'error' in read_result:
            result = {'success': False, 'error': read_result['error']}
        else:
            result = {'success': True, **read_result}

    elif ext == '.pdf' or detect_binary(file_path) == 'pdf':
        read_result = read_pdf_file(file_path, args.pages)
        if 'error' in read_result:
            result = {'success': False, 'error': read_result['error']}
        else:
            result = {'success': True, **read_result}

    elif ext == '.ipynb':
        read_result = read_notebook(file_path)
        if 'error' in read_result:
            result = {'success': False, 'error': read_result['error']}
        else:
            result = {'success': True, **read_result}

    elif ext in BINARY_EXTENSIONS:
        result = {
            'success': False,
            'error': f'Binary file type not supported: {ext}'
        }
        print(json.dumps(result))
        return

    else:
        # 文本文件
        read_result = read_text_file(file_path, args.offset, args.limit)

        # 检查 token 限制
        tokens = count_tokens(read_result['content'])
        if tokens > MAX_TOKENS:
            result = {
                'success': False,
                'error': f'File content too large: {tokens} tokens (max {MAX_TOKENS} tokens)'
            }
            print(json.dumps(result))
            return

        result = {'success': True, **read_result}

    print(json.dumps(result))


if __name__ == "__main__":
    main()