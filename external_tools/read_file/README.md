# Read File Tool

独立的文件读取工具，编译后的 Windows 可执行文件。

## 功能特点

- **多格式支持**：文本、图片（PNG/JPG/GIF/WEBP）、PDF、Jupyter Notebook
- **文本分页**：通过 offset/limit 参数支持分页读取
- **PDF 页码**：通过 pages 参数指定页码范围（如 "1-5"）
- **行号输出**：文本文件以 `行号|` 格式输出
- **Token 限制**：自动计算 token 数量，超限返回错误（限制 180,000 tokens）
- **文件大小限制**：最大 512KB（超出返回错误）

## 使用方法

```bash
external_tools\read_file\dist\read_file.exe --path <file_path> [--offset <n>] [--limit <n>] [--pages <range>]
```

## 参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--path` | 文件路径（绝对路径或相对于项目根目录） | 必需 |
| `--offset` | 起始行号（从0开始，仅对文本文件有效） | 0 |
| `--limit` | 读取行数（仅对文本文件有效） | 全部 |
| `--pages` | PDF页码范围，如 "1-5"（仅对PDF有效） | 全部 |

## 输出格式

### 文本文件

```json
{
  "success": true,
  "type": "text",
  "content": "  1| 第一行内容\n  2| 第二行内容\n  3| 第三行内容",
  "metadata": {
    "numLines": 3,
    "totalLines": 100,
    "startLine": 1,
    "fileSize": 1234,
    "mtimeMs": 1234567890123
  }
}
```

### 图片文件

```json
{
  "success": true,
  "type": "image",
  "filePath": "C:\\path\\to\\image.png",
  "base64": "iVBORw0KGgoAAAANSUhEUgAAAA...",
  "originalSize": 12345,
  "dimensions": {
    "width": 800,
    "height": 600
  }
}
```

### PDF 文件

```json
{
  "success": true,
  "type": "pdf",
  "filePath": "C:\\path\\to\\file.pdf",
  "base64": "JVBERi0xLjQK...",
  "originalSize": 123456,
  "totalPages": 10
}
```

### Notebook 文件

```json
{
  "success": true,
  "type": "notebook",
  "filePath": "C:\\path\\to\\notebook.ipynb",
  "cells": [
    {
      "cell_type": "code",
      "source": "print('Hello')",
      "outputs": [{"type": "stream", "text": "Hello\n"}],
      "execution_count": 1
    },
    {
      "cell_type": "markdown",
      "source": "# Title"
    }
  ]
}
```

### 错误响应

```json
{
  "success": false,
  "error": "File not found: path/to/file.txt"
}
```

## 依赖

- PyPDF2>=3.0.0（PDF处理）
- Pillow>=10.0.0（图片处理）
- nbformat>=5.9.0（Notebook解析）

## 构建

如需重新编译：

```bash
cd external_tools/read_file
pip install -r requirements.txt
python build.py
```

输出：`dist/read_file.exe`

## 安全限制

| 限制 | 值 |
|------|-----|
| 最大文件大小 | 512KB |
| 最大 Token 数 | 180,000 |

二进制文件（.exe, .dll, .bin 等）会被拒绝读取。