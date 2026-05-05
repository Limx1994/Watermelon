# Grep Tool

正则表达式文件内容搜索工具，编译后的 Windows 可执行文件。

## 使用方法

```bash
external_tools\grep\dist\grep.exe --pattern <regex> [--path <directory>] [options]
```

## 参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--pattern` | 正则表达式搜索模式 | 必需 |
| `--path` | 搜索目录 | 当前目录 |
| `--glob` | Glob 模式过滤（如 `*.py`, `*.{js,ts}`） | - |
| `--output-mode` | 输出模式：`content`（默认）、`files_with_matches`、`count` | content |
| `-B` | 显示匹配前的 N 行 | 0 |
| `-A` | 显示匹配后的 N 行 | 0 |
| `-C` | 显示前后各 N 行 | 0 |
| `-n` | 显示行号 | true |
| `--no-line-number` | 隐藏行号 | - |
| `-i` | 大小写不敏感搜索 | false |
| `--type` | 按文件类型过滤（如 `py`, `js`, `ts`） | - |
| `--head-limit` | 限制结果数（0=无限制） | 250 |
| `--offset` | 跳过前 N 个结果 | 0 |
| `--multiline` | 启用多行模式（. 匹配换行符） | false |
| `--recursive` | 是否递归搜索 | true |

## 输出格式

### JSON 输出

```json
{
  "success": true,
  "content": "匹配结果内容",
  "error": ""
}
```

### content 模式（默认）

每行格式：`<文件路径>:<行号>: <行内容>`

```
src/main.py:10: import sys
src/main.py:15: from pathlib import Path
```

### files_with_matches 模式

只返回文件名列表（按修改时间排序，最新在前）：
```
src/main.py
src/config.py
tests/test_main.py
```

### count 模式

每个文件的匹配次数：
```
src/main.py: 5
src/config.py: 3
```

## 输出类型

| 类型 | 触发条件 | 输出格式 |
|------|----------|----------|
| content | 默认 | `path:line: content` |
| files_with_matches | `--output-mode files_with_matches` | 文件路径列表 |
| count | `--output-mode count` | `path: 数量` |

## 上下文行

使用 `-B`、`-A`、`-C` 参数显示匹配行的上下文：

```bash
# 显示匹配行前2行和后3行
grep.exe --pattern "def main" -C 3

# 显示匹配前2行
grep.exe --pattern "class Foo" -B 2

# 显示匹配后2行
grep.exe --pattern "return" -A 2
```

## 文件类型过滤

使用 `--type` 参数按文件类型过滤：

| 类型 | 匹配模式 |
|------|----------|
| `py` | `*.py`, `*.pyw` |
| `js` | `*.js`, `*.jsx`, `*.mjs` |
| `ts` | `*.ts`, `*.tsx`, `*.mts` |
| `rust` | `*.rs` |
| `go` | `*.go` |
| `java` | `*.java` |
| `html` | `*.html`, `*.htm` |
| `css` | `*.css`, `*.scss`, `*.sass`, `*.less` |
| `json` | `*.json` |
| `yaml` | `*.yaml`, `*.yml` |
| `md` | `*.md`, `*.markdown` |

## 分页

使用 `--head-limit` 和 `--offset` 实现分页：

```bash
# 获取前50条
grep.exe --pattern "import" --head-limit 50

# 获取第51-100条
grep.exe --pattern "import" --head-limit 50 --offset 50
```

## 搜索规则

**跳过的目录:**
- `.git`, `__pycache__`, `node_modules`, `.venv`, `venv`, `.claude`, `.hg`, `.svn`

**跳过的文件扩展名:**
- `.pyc`, `.exe`, `.dll`, `.so`, `.bin`, `.pdb`, `.class`, `.o`, `.obj`

**跳过的文件:**
- `.DS_Store`, `thumbs.db`

## 示例

```bash
# 基本搜索
grep.exe --pattern "def main"

# 递归搜索 Python 文件
grep.exe --pattern "import" --type py

# 多模式匹配
grep.exe --pattern "TODO|FIXME" --glob "*.{py,js,ts}"

# 忽略大小写
grep.exe --pattern "error" -i

# 带上下文
grep.exe --pattern "class Main" -C 3

# 文件列表模式
grep.exe --pattern "TODO" --output-mode files_with_matches

# 计数模式
grep.exe --pattern "import" --output-mode count

# 多行模式
grep.exe --pattern "def.*\\n.*return" --multiline
```

## 构建

如需重新编译：

```bash
cd external_tools/grep
pip install -r requirements.txt
python build.py
```

输出：`dist/grep.exe`