# Glob Tool

文件模式匹配工具，基于 ripgrep (`rg`) 实现。

## 依赖

- **ripgrep**: 必须在 PATH 中或安装在常见 Windows 路径
  - 安装方式: `winget install BurntSushi.ripgrep`
  - 安装后需重启终端使 PATH 生效

## 使用方法

```bash
external_tools\glob\dist\glob.exe --pattern <pattern> [--path <directory>] [--max-results <n>] [--timeout <seconds>]
```

## 参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--pattern` | string | 必需 | 文件名模式（如 `*.py`, `**/*.json`） |
| `--path` | string | `.` | 搜索目录 |
| `--max-results` | int | 100 | 最大结果数 |
| `--timeout` | float | 30.0 | 超时秒数 |

## 输出格式

JSON 格式：
```json
{
  "success": true,
  "content": "file1.py\nfile2.py",
  "error": "",
  "metadata": {
    "durationMs": 45,
    "numFiles": 2,
    "truncated": false,
    "pattern": "*.py",
    "path": "src"
  }
}
```

失败响应：
```json
{
  "success": false,
  "content": "",
  "error": "错误信息",
  "metadata": {}
}
```

## 特性

- **基于 ripgrep**: 使用 `rg --files --glob` 进行高性能文件搜索
- **默认包含隐藏文件**: `--hidden` 默认启用
- **忽略 .gitignore**: `--no-ignore` 默认启用
- **Windows 优化**: 自动检测 ripgrep 安装位置
- **路径规范化**: 输出使用正斜杠 `/`

## 安全检查

- **UNC 路径拒绝**: 不允许 `\\` 或 `//` 开头的路径

## 示例

```bash
# 查找所有 Python 文件
external_tools\glob\dist\glob.exe --pattern "*.py"

# 在 src 目录中查找
external_tools\glob\dist\glob.exe --pattern "*.py" --path "src"

# 查找所有 JSON 文件（递归）
external_tools\glob\dist\glob.exe --pattern "**/*.json"

# 限制结果数量
external_tools\glob\dist\glob.exe --pattern "*" --max-results 10

# 设置超时
external_tools\glob\dist\glob.exe --pattern "**/*" --timeout 60
```

## 构建

如需重新编译：

```bash
cd external_tools/glob
python build.py
```

输出：`dist/glob.exe`
