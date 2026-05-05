# WinShell Tool

PowerShell 命令执行器，带白名单验证。编译后的 Windows 可执行文件。

## 使用方法

```bash
external_tools\winshell\dist\winshell.exe --command <command> [--timeout <seconds>]
```

## 参数

- `--command`: 要执行的 PowerShell 命令
- `--timeout`: 超时时间（秒），默认 30

## 输出格式

JSON 格式：
- 成功: `{"success": true, "content": "命令输出", "error": ""}`
- 失败: `{"success": false, "content": "", "error": "错误信息"}`

## 白名单验证

仅允许以下命令：

**PowerShell cmdlets:**
- Get-ChildItem, Get-Content, Remove-Item, Copy-Item, Move-Item
- New-Item, Set-Content, Write-Output, Get-Location, Set-Location

**Unix 命令别名:**
- `dir`, `type`, `echo`, `mkdir`, `cd`, `pwd`, `ls`, `rm`, `cp`, `mv`
- `python`, `pip`, `node`, `npm`

## 安全特性

- 白名单验证：仅执行授权命令
- 路径限制：必须在项目根目录内执行
- 超时保护：防止命令无限挂起

## 构建

如需重新编译：

```bash
cd external_tools/winshell
python build.py
```

输出：`dist/winshell.exe`
