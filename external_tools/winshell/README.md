# WinShell Tool

PowerShell 命令执行器，支持别名解析和复杂脚本自动使用 .ps1 文件执行。

## 功能特点

- **别名解析**：Unix 风格命令自动转换为 PowerShell cmdlet
- **复杂脚本处理**：包含变量引用（`$_`、`$()`、`.Path` 等）的命令自动使用 .ps1 文件执行
- **后台执行**：支持后台任务模式
- **退出码解释**：提供退出码的语义解释
- **图片检测**：自动检测输出中的图片数据
- **UTF-8 支持**：正确处理中文等 Unicode 字符

## 使用方法

```bash
external_tools\winshell\dist\winshell.exe --command <command> [--timeout <ms>] [--description <desc>] [--run-in-background <true|false>] [--dangerously-disable-sandbox <true|false>]
```

## 输入参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--command` | string | 必需 | 要执行的 PowerShell 命令 |
| `--timeout` | number | 30000 | 超时时间（毫秒），最大 600000 |
| `--description` | string | "" | 命令描述（用于日志） |
| `--run-in-background` | boolean | false | 后台运行 |
| `--dangerously-disable-sandbox` | boolean | false | 禁用所有验证（危险） |

## 输出格式

```json
{
  "stdout": "命令输出",
  "stderr": "错误输出",
  "interrupted": false,
  "returnCodeInterpretation": "Success",
  "isImage": false,
  "backgroundTaskId": null,
  "backgroundedByUser": false,
  "assistantAutoBackgrounded": false
}
```

### 输出字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `stdout` | string | 标准输出 |
| `stderr` | string | 错误输出 |
| `interrupted` | boolean | 命令是否被中断（超时） |
| `returnCodeInterpretation` | string | 退出码的语义解释（如 "Success", "General error"） |
| `isImage` | boolean | 输出是否包含图片数据 |
| `backgroundTaskId` | string/null | 后台任务 ID（后台执行时） |
| `backgroundedByUser` | boolean | 是否用户手动后台 |
| `assistantAutoBackgrounded` | boolean | 是否助手自动后台（复杂脚本） |

## 别名解析

支持以下别名映射：

### 文件操作
| 别名 | 转换为 |
|------|--------|
| `ls`, `dir`, `gci` | `Get-ChildItem` |
| `cat`, `type`, `gc` | `Get-Content` |
| `rm`, `rmdir`, `del`, `erase` | `Remove-Item` |
| `cp`, `copy`, `cpi` | `Copy-Item` |
| `mv`, `move`, `mi` | `Move-Item` |
| `mkdir` | `New-Item -ItemType Directory` |
| `md`, `ni` | `New-Item` |

### 目录操作
| 别名 | 转换为 |
|------|--------|
| `pwd`, `gl` | `Get-Location` |
| `cd`, `chdir`, `sl` | `Set-Location` |

### 进程操作
| 别名 | 转换为 |
|------|--------|
| `ps` | `Get-Process` |
| `kill`, `stop` | `Stop-Process` |
| `start` | `Start-Process` |

### 管道操作
| 别名 | 转换为 |
|------|--------|
| `?`, `where` | `Where-Object` |
| `%`, `foreach` | `ForEach-Object` |

### 其他
| 别名 | 转换为 |
|------|--------|
| `echo`, `write` | `Write-Output` |
| `clear`, `cls` | `Clear-Host` |
| `date` | `Get-Date` |
| `sleep` | `Start-Sleep` |
| `history`, `h` | `Get-History` |
| `sc`, `services` | `Get-Service` |
| `which` | `Get-Command` |

## 复杂脚本处理

根据跨项目记忆规范，复杂 PowerShell 脚本必须使用 .ps1 文件执行。

以下情况自动使用 .ps1 文件：

1. **变量引用**：`$_`、`$var`、`${var}` 等
2. **成员访问**：`$var.Path`、`$obj.Name` 等
3. **子表达式**：`$(...)` 语法
4. **脚本块**：`& {...}` 语法
5. **多语句**：`;` 分隔的多个语句
6. **命令链**：`&&` 或 `||` 操作符

### 示例

```bash
# 简单命令 - 使用 -Command
winshell.exe --command "Get-ChildItem"

# 别名解析 - ls 自动转为 Get-ChildItem
winshell.exe --command "ls"

# 复杂脚本（包含 $_）- 自动使用 .ps1 文件
winshell.exe --command "Get-Process | Where-Object { $_.Name -like '*Python*' }"

# 变量引用 - 自动使用 .ps1 文件
winshell.exe --command "echo $HOME"

# 后台执行
winshell.exe --command "Start-Sleep 10" --run-in-background true
```

## 后台执行

使用 `--run-in-background true` 启动后台任务：

```bash
winshell.exe --command "Start-Sleep 60" --run-in-background true
```

返回：
```json
{
  "stdout": "Background task started: <uuid>\nScript: <uuid>.ps1",
  "backgroundTaskId": "<uuid>"
}
```

后台任务使用 UUID 命名临时 .ps1 文件，进程退出时自动清理。

## 安全特性

- **别名规范化**：所有别名在执行前规范化为 canonical cmdlet 名称
- **.ps1 文件执行**：复杂脚本避免直接在 `-Command` 中执行，防止变量解析问题
- **超时保护**：防止命令无限挂起
- **UTF-8 编码**：正确处理所有 Unicode 字符

**注意**：`--dangerously-disable-sandbox` 设为 true 时跳过所有验证，直接执行命令。

## 构建

如需重新编译：

```bash
cd external_tools/winshell
python build.py
```

输出：`dist/winshell.exe`
