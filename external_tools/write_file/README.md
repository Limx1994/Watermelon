# Write File Tool

独立文件写入工具，编译后的 Windows 可执行文件。

## 使用方法

```bash
external_tools\write_file\dist\write_file.exe --path <file_path> --content <content>
```

## 参数

- `--path`: 文件路径（相对于项目根目录）
- `--content`: 要写入的内容

## 输出格式

JSON 格式：
- 成功: `{"success": true, "content": "Successfully wrote to <path>", "error": ""}`
- 失败: `{"success": false, "content": "", "error": "错误信息"}`

## 安全检查

- 路径必须在项目根目录内（防止目录遍历攻击）
- 自动创建父目录

## 构建

如需重新编译：

```bash
cd external_tools/write_file
python build.py
```

输出：`dist/write_file.exe`
