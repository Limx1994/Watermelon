# Glob Tool

文件模式匹配工具，编译后的 Windows 可执行文件。

## 使用方法

```bash
external_tools\glob\dist\glob.exe --pattern <pattern> [--path <directory>]
```

## 参数

- `--pattern`: 文件名模式（如 `*.py`, `**/*.json`）
- `--path`: 搜索目录（默认当前目录）

## 输出格式

JSON 格式：
- 成功: `{"success": true, "content": "匹配文件列表", "error": ""}`
- 失败: `{"success": false, "content": "", "error": "错误信息"}`

每行一个文件路径

## 结果限制

- 最多返回 50 条匹配

## 示例

```bash
# 查找所有 Python 文件
external_tools\glob\dist\glob.exe --pattern "*.py"

# 在 src 目录中查找
external_tools\glob\dist\glob.exe --pattern "*.py" --path "src"

# 查找所有 JSON 文件（递归）
external_tools\glob\dist\glob.exe --pattern "**/*.json"
```

## 安全检查

- 路径必须在项目根目录内

## 构建

如需重新编译：

```bash
cd external_tools/glob
python build.py
```

输出：`dist/glob.exe`
