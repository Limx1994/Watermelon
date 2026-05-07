# Edit Tool

精确字符串替换工具，编译后的 Windows 可执行文件。

## 功能特点

- **精确替换**：old_string 必须与文件内容完全一致
- **批量替换**：支持 replace_all 替换所有出现
- **引号规范化**：自动处理弯引号（""）和直引号（""）的转换
- **路径安全**：仅支持项目目录内的文件

## 使用方法

```bash
external_tools\edit\dist\edit.exe --file-path <path> --old-string <text> --new-string <text> [--replace-all <true|false>]
```

## 参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--file-path` | string | 必需 | 文件绝对路径（不支持 ~ 路径简写） |
| `--old-string` | string | 必需 | 要替换的文本（必须与文件内容完全一致） |
| `--new-string` | string | 必需 | 替换文本（必须与 old_string 不同） |
| `--replace-all` | boolean | false | 是否替换所有出现 |

## 输出格式

JSON 格式：
```json
{
  "success": true,
  "content": "文件已更新: path/to/file.txt",
  "error": ""
}
```

失败响应：
```json
{
  "success": false,
  "content": "",
  "error": "错误信息"
}
```

## 错误类型

| 错误 | 说明 |
|------|------|
| `File not found` | 文件不存在 |
| `old_string not found` | 文件中未找到要替换的字符串 |
| `No changes needed` | old_string 与 new_string 相同 |
| `Path outside project` | 路径在项目目录外 |

## 使用规则

根据跨项目记忆规范：
- **old_string 必须匹配**：必须与文件内容完全一致才能替换
- **replace_all**：设为 true 时替换所有出现，设为 false 时只替换第一处
- **引号处理**：弯引号会自动转换为直引号进行匹配

## 示例

```bash
# 基本替换
edit.exe --file-path "C:\project\file.txt" --old-string "Hello" --new-string "World"

# 替换所有出现
edit.exe --file-path "C:\project\file.txt" --old-string "foo" --new-string "bar" --replace-all true
```

## 构建

如需重新编译：

```bash
cd external_tools/edit
pip install -r requirements.txt
python build.py
```

输出：`dist/edit.exe`
