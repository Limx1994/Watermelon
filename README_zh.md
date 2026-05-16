# AGImyCLI

一款受 Claude Code 启发，使用 Python 构建的 TUI（文本用户界面）AGI 交互工具。

## 功能特点

- **REPL 风格交互**：通过终端界面与 AI 对话
- **工具系统**：所有工具通过 tools.json 配置为外部可执行文件（read_file、write_file、shell、grep、glob、edit）
- **MCP 支持**：连接 Model Context Protocol 服务器（Sequential Thinking 等）
- **鼠标交互**：鼠标滚轮滚动、文本选择、点击聚焦输入
- **记忆持久化**：会话历史持久保存，长对话自动摘要
- **跨会话记忆**：基于文件的持久化记忆，支持全局/项目双层作用域，LLM 可调用记忆工具，MEMORY.md 索引注入
- **中文输入**：优化中文语言输入体验，支持 IME
- **流式输出**：实时逐 token 显示响应，带样式化片段
- **样式化显示**：思考内容灰色斜体显示，回答带青色分隔线，Token 栏固定在底部（独立行，靠右对齐）
- **Token 统计**：实时显示上传/下载/累计 Token，固定在底栏右下角
- **自主模式**：持久化 Agent 循环，支持 tick 唤醒、proactive 指令、Sleep 工具空闲等待
- **模型降级恢复**：主模型失败时自动切换备用模型，恢复后自动切回
- **快速 Ctrl+C 取消**：重试期间可中断 sleep（0.2 秒响应），SIGINT handler 确保 agent 可靠取消
- **标准 Cron 调度**：支持 5-field cron 表达式（via croniter），带抖动避免同时触发
- **斜杠命令**：16 个内置命令（/help、/model、/save、/compact 等），支持 Tab 补全
- **技能系统**：通过 SKILL.md 文件实现可扩展的 prompt 注入，支持 YAML frontmatter 配置、参数替换和工具过滤
- **上下文进度条**：上下文使用率 >= 50% 时显示进度条，带颜色编码（绿/黄/橙/红）
- **项目上下文注入**：自动将项目上下文和 git status 注入每次 LLM 调用

## 前置条件

- **Python** >= 3.10
- **Windows**（见下方平台支持说明）

### 平台支持

本项目目前仅支持 **Windows**。所有外部工具均为 Windows `.exe` 可执行文件，shell 工具需要 PowerShell。

## 快速开始

1. 安装依赖：
```bash
pip install -r requirements.txt
```

2. 在 `config.json` 中配置 API 凭据（注意：`config.json` 已被 .gitignore 排除以保护安全；`config/` 包含非敏感的工具/MCP 定义，受版本控制）：
```json
{
  "openai": {
    "api_key": "your-api-key",
    "base_url": "https://api.deepseek.com",
    "model": "deepseek-v4-flash"
  }
}
```

3. 运行：
```bash
python -m src.main
# 或
python -m src
```

## 依赖项

| 包 | 版本 | 用途 |
|---|------|------|
| [prompt-toolkit](https://github.com/prompt-toolkit/prompt-toolkit) | 3.0.52 | TUI 框架（BufferControl、FormattedTextControl） |
| [openai](https://github.com/openai/openai-python) | 1.109.1 | 兼容 OpenAI 协议的 LLM 客户端（DeepSeek API） |
| [pyperclip](https://github.com/asweigart/pyperclip) | 1.11.0 | Windows 剪贴板集成 |
| [requests](https://github.com/psf/requests) | 2.33.1 | HTTP 客户端（MCP/HTTP 客户端） |
| [tiktoken](https://github.com/openai/tiktoken) | 0.12.0 | Token 计数 |
| [croniter](https://github.com/kiorky/croniter) | 6.0.0 | 标准 5-field cron 表达式解析 |

## 项目结构

```
AGImyCLI/
├── src/
│   ├── main.py              # 入口文件
│   ├── tui.py               # TUI 界面
│   ├── agent.py             # 核心 Agent 循环
│   ├── config.py            # 配置管理
│   ├── memory.py            # 记忆和对话历史
│   ├── persistent_memory.py # 跨会话持久化记忆引擎
│   ├── llm/
│   │   └── client.py        # LLM 客户端（兼容 DeepSeek API，可中断 sleep）
│   ├── tools/
│   │   ├── base.py          # 工具基类和 ToolResult
│   │   ├── registry.py      # 工具注册表（单例模式）
│   │   ├── loader.py        # 外部工具加载器
│   │   ├── external.py      # 外部 CLI 工具执行器
│   │   ├── sleep.py         # Sleep 工具（自主模式空闲等待）
│   │   └── memory_tool.py   # 持久化记忆工具（LLM 可调用）
│   ├── commands/
│   │   ├── __init__.py      # 包初始化
│   │   ├── registry.py      # 斜杠命令注册表（CommandRegistry，SlashCommand）
│   │   ├── core.py          # 内置斜杠命令（/help，/model，/save 等）
│   │   └── completer.py     # 斜杠命令 Tab 补全（SlashCommandCompleter）
│   ├── cron/
│   │   └── scheduler.py     # Cron 调度器（CronScheduler，CronTask）
│   ├── mcp/
│   │   ├── base.py          # 抽象 MCP 客户端基类
│   │   ├── protocol.py      # JSON-RPC 2.0 协议
│   │   ├── client.py        # MCP 客户端工厂（create_mcp_client）
│   │   ├── manager.py       # MCP 客户端管理器
│   │   ├── index.py         # 工具名到客户端的索引
│   │   ├── persistence.py   # MCP 数据持久化
│   │   ├── stdio_client.py  # 基于 Stdio 的 MCP 客户端
│   │   └── http_client.py   # 基于 HTTP 的 MCP 客户端
│   ├── skills/
│   │   ├── __init__.py      # 技能系统初始化（init_skills）
│   │   ├── definition.py    # SkillDefinition 数据类
│   │   ├── loader.py        # SKILL.md 解析和加载器
│   │   ├── registry.py      # SkillRegistry 单例
│   │   ├── commands.py      # 技能执行处理器 + /skills 命令
│   │   └── tool.py          # SkillTool（LLM 可调用的技能工具）
│   └── utils/
│       ├── path.py          # 路径工具函数
│       ├── token_counter.py # Token 计数
│       └── logging.py       # 日志工具
├── external_tools/           # 外部编译的 .exe 工具
│   ├── read_file/           # 文件读取工具
│   ├── write_file/          # 文件写入工具
│   ├── winshell/            # Shell 执行器（别名解析）
│   ├── grep/                # 内容搜索工具
│   ├── glob/                 # 文件模式匹配工具
│   └── edit/                 # 字符串替换工具
├── skills/                   # 技能定义（SKILL.md 文件）
│   └── code-review/         # 示例：代码审查技能
│       └── SKILL.md
├── prompts/                 # 提示词模板
│   ├── system/              # 系统提示词（6 个文件）
│   │   ├── intro.md
│   │   ├── system_rules.md
│   │   ├── doing_tasks.md
│   │   ├── tool_usage.md
│   │   ├── tone_style.md
│   │   └── output_efficiency.md
│   ├── service/             # 服务提示词
│   │   ├── compact_resume.md
│   │   ├── summary_system.md
│   │   └── summary_template.md
│   ├── recovery/            # 恢复提示词
│   │   ├── max_tokens_recovery.md
│   │   ├── context_too_long.md
│   │   └── token_budget_nudge.md
│   └── autonomous/
│       └── instructions.md  # 自主模式行为指令
├── memory/                  # 对话和持久化记忆存储
│   ├── *.md                 # 持久化记忆文件（YAML frontmatter）
│   ├── MEMORY.md            # 持久化记忆索引（自动生成）
│   └── history/             # 归档会话历史
├── mcpdata/                 # MCP 持久化数据
├── logs/                    # 日志文件
├── config/                  # 配置文件
│   ├── mcp.json                 # MCP 服务器配置
│   ├── tools.json               # 工具定义
│   └── scheduled_tasks.json     # Cron 任务状态（自动生成）
├── config.json              # 应用配置
├── requirements.txt         # Python 依赖
├── README.md                # 说明文档（英文）
├── README_zh.md            # 本文件
└── LICENSE                  # 许可证文件
```

## 配置说明

### config.json — 应用设置

| 配置项 | 键 | 说明 | 默认值 |
|--------|-----|------|--------|
| `openai` | `api_key` | API 密钥 | - |
| | `base_url` | API 地址 | `https://api.deepseek.com` |
| | `model` | 模型名称 | `deepseek-v4-flash` |
| | `fallback_model` | 降级备用模型（空 = 禁用） | `""` |
| | `temperature` | 采样温度 | `0.7` |
| | `top_p` | 核采样参数 | `0.7` |
| | `reasoning_effort` | 思考深度 | `max` |
| | `context_window` | 最大上下文窗口（单位为千，如 128 = 128K；>= 1000 按原始 token 数计算）。有效上下文窗口 = `context_window - max_output_tokens`。代码回退默认值：64K | `128` |
| | `max_output_tokens` | 最大输出 Token 数 | `20000` |
| `agent` | `max_turns` | 最大对话轮次 | `50` |
| | `max_retries` | 失败最大重试次数 | `3` |
| | `network_max_retries` | 网络错误最大重试次数 | `10` |
| | `network_retry_interval_seconds` | 网络错误重试间隔（秒） | `30` |
| | `nudge_threshold` | Token 预算警告触发比例（0.0-1.0） | `0.90` |
| `display` | `show_thinking` | 显示思考过程 | `true` |
| | `thinking_indicator` | 思考指示器文字 | `思考中` |
| `tools` | `enabled` | 启用的外部工具列表（在 tools.json 中配置） | `["shell", "read_file", "write_file", "grep", "glob", "edit"]` |
| `logs` | `path` | 日志文件路径 | `./logs/agent.log` |
| | `level` | 日志级别 | `INFO` |
| | `max_bytes` | 单个日志文件最大字节数（轮转前） | `10485760`（10MB） |
| | `backup_count` | 日志备份数量 | `5` |
| `prompts` | `autonomous_instructions` | 自主模式指令文件路径 | `./prompts/autonomous/instructions.md` |
| | `compact_resume` | 压缩恢复提示词路径 | `./prompts/service/compact_resume.md` |
| | `max_tokens_recovery` | 输出截断恢复提示词路径 | `./prompts/recovery/max_tokens_recovery.md` |
| | `context_too_long` | 上下文过长恢复提示词路径 | `./prompts/recovery/context_too_long.md` |
| | `token_budget_nudge` | Token 预算警告提示词路径 | `./prompts/recovery/token_budget_nudge.md` |
| | `summary_system` | 摘要系统提示词路径 | `./prompts/service/summary_system.md` |
| | `summary_template` | 摘要模板路径 | `./prompts/service/summary_template.md` |
| | `system_intro` | 系统提示词 intro 段落路径 | `./prompts/system/intro.md` |
| | `system_rules` | 系统规则路径 | `./prompts/system/system_rules.md` |
| | `system_doing_tasks` | 任务执行指南路径 | `./prompts/system/doing_tasks.md` |
| | `system_tool_usage` | 工具使用规则路径 | `./prompts/system/tool_usage.md` |
| | `system_tone_style` | 语气风格指南路径 | `./prompts/system/tone_style.md` |
| | `system_output_efficiency` | 输出效率规则路径 | `./prompts/system/output_efficiency.md` |

### compact — 上下文压缩设置

| 配置项 | 键 | 说明 | 默认值 |
|--------|-----|------|--------|
| `compact` | `enabled` | 启用上下文压缩 | `true` |
| | `buffer_tokens` | 压缩后目标缓冲区大小 | `13000` |
| | `micro_compact_streak` | 微型压缩触发连续数 | `3` |
| | `micro_compact_gap_minutes` | 微型压缩时间间隔（分钟） | `5` |
| | `auto_compact_threshold` | 自动压缩触发比例 | `0.85` |
| | `full_compact_threshold` | 完整压缩触发比例 | `0.95` |
| | `preserve_recent_messages` | 保留的最近消息数 | `10` |

### autonomous — 自主模式设置

| 配置项 | 键 | 说明 | 默认值 |
|--------|-----|------|--------|
| `autonomous` | `tick_interval_minutes` | Tick 唤醒间隔（分钟） | `10` |
| | `cron_tasks` | 定时任务定义列表 | `[]` |
| `skills` | `enabled` | 启用技能系统 | `true` |
| | `dirs` | 扫描 SKILL.md 文件的目录列表（相对于项目根目录） | `["skills"]` |
| `persistent_memory` | `enabled` | 启用跨会话持久化记忆 | `true` |
| | `global_dir` | 全局记忆目录路径（空 = 禁用） | `""` |
| | `max_index_chars` | 从 MEMORY.md 注入上下文的最大字符数 | `4000` |
| | `types` | 允许的记忆类型 | `["user", "feedback", "project", "reference"]` |

#### Cron 任务格式

`cron_tasks` 列表中每个任务遵循以下格式：

```json
{
  "name": "task-name",
  "prompt": "AI 应该做什么",
  "cron_expression": "*/5 * * * *",
  "interval_minutes": 30,
  "enabled": true
}
```

- `cron_expression`：标准 5-field cron（via croniter）。优先于 `interval_minutes`。
- `interval_minutes`：无 cron_expression 时的简单间隔回退。

### Prompts — 提示词模板系统

`prompts` 配置段将逻辑名称映射到 `.md` 文件路径。系统提示词由 6 个段落文件组装而成：

| 模板 | 用途 |
|------|------|
| `system_intro` | Agent 身份和角色定义 |
| `system_rules` | 系统行为规则 |
| `system_doing_tasks` | 任务执行指南 |
| `system_tool_usage` | 工具使用规则 |
| `system_tone_style` | 语气风格指南 |
| `system_output_efficiency` | 输出效率规则 |
| `autonomous_instructions` | 自主模式行为指令（追加到系统提示词） |

服务和恢复提示词：

| 模板 | 用途 |
|------|------|
| `compact_resume` | 上下文压缩后发送，指示 AI 继续工作而非等待输入 |
| `max_tokens_recovery` | 输出达到 token 上限时的恢复提示 |
| `context_too_long` | 上下文窗口溢出时的恢复提示 |
| `token_budget_nudge` | 上下文使用率过高时注入的警告（支持 `{pct:.0%}` 占位符） |
| `summary_system` | 摘要生成的系统提示词 |
| `summary_template` | 摘要生成模板（支持 `{messages}` 占位符） |

所有提示词可通过编辑 `prompts/` 目录下的 `.md` 文件自定义。路径为空或文件缺失时使用内置默认字符串。

### config/mcp.json — MCP 服务器配置

```json
{
  "mcpServers": {
    "server-name": {
      "type": "stdio|streamable_http|http",
      "url": "https://...",           // HTTP 类型必需
      "command": "mcp-server-xxx",    // stdio 类型必需
      "args": [],
      "env": {},
      "headers": {},
      "api_key": "..."
    }
  }
}
```

支持的 MCP 服务器类型：
- **stdio**：通过 stdio 的外部 MCP 服务器（如 npx 启动的服务器）
- **http** / **streamable_http**：HTTP/REST API 通信

## 外部工具

外部工具是编译后的 .exe 程序，在 `tools.json` 中定义，通过 JSON 在 stdin/stdout 上通信。

| 工具 | 命令 | 说明 |
|------|------|------|
| `read_file` | `external_tools/read_file/dist/read_file.exe` | 读取文件内容（文本/图片/PDF/Notebook，支持 offset/limit/pages） |
| `write_file` | `external_tools/write_file/dist/write_file.exe` | 写入文件内容 |
| `shell` | `external_tools/winshell/dist/winshell.exe` | 执行 PowerShell 命令（别名解析、引号感知操作符转换、复杂脚本使用 .ps1，超时单位为秒） |
| `grep` | `external_tools/grep/dist/grep.exe` | 搜索文件内容（正则，输出模式，上下文，类型过滤，分页） |
| `glob` | `external_tools/glob/dist/glob.exe` | 按模式查找文件（最多 50 条） |
| `edit` | `external_tools/edit/dist/edit.exe` | 精确字符串替换（引号规范化，replace_all 支持） |
| `memory` | 内置工具 | 跨会话持久化记忆（save/load/list/search，支持全局/项目作用域） |

`tools.json` 示例：
```json
{
  "tools": [
    {
      "function": {
        "name": "read_file",
        "description": "读取文件内容，支持多种格式",
        "command": "external_tools/read_file/dist/read_file.exe",
        "parameters": {
          "type": "object",
          "properties": {
            "path": { "type": "string", "description": "文件路径（绝对或相对）" },
            "offset": { "type": "number", "description": "起始行号（从0开始）", "default": 0 },
            "limit": { "type": "number", "description": "读取行数" },
            "pages": { "type": "string", "description": "PDF页码范围，如 '1-5'" }
          },
          "required": ["path"]
        }
      }
    },
    {
      "function": {
        "name": "shell",
        "description": "执行 PowerShell 命令（别名解析）。复杂脚本自动使用 .ps1 文件执行。",
        "command": "external_tools/winshell/dist/winshell.exe",
        "parameters": {
          "type": "object",
          "properties": {
            "command": { "type": "string", "description": "要执行的 PowerShell 命令" },
            "timeout": { "type": "number", "description": "超时时间（毫秒），最大 600000", "default": 30000 },
            "description": { "type": "string", "description": "命令描述（用于日志）" },
            "run_in_background": { "type": "boolean", "description": "后台运行", "default": false },
            "dangerously_disable_sandbox": { "type": "boolean", "description": "禁用沙箱（危险）", "default": false }
          },
          "required": ["command"]
        }
      }
    }
  ]
}
```

路径支持：
- **相对路径**：与项目根目录拼接
- **绝对路径**：直接使用

## Token 消耗统计

Token 消耗显示在屏幕底部（独立行，靠右对齐）：
- `⬆`：上传 Token（系统提示词 + 记忆）
- `⬇`：下载 Token（思考过程）
- `∫`：累计总 Token

Token 计算规则（结果取整）：
- 中文字符：1.3 token/个
- 英语单词：1.1 token/个
- 标点符号、数字、其他：1.0 token/个

## 键盘快捷键

| 快捷键 | 功能 |
|--------|------|
| `Enter` | 发送所有内容（支持多行） |
| `Ctrl+J` | 插入换行符 |
| `Left` / `Right` | 光标移动（跨行导航） |
| `Up` / `Down` | 输入历史 |
| `Ctrl+V` | 从剪贴板粘贴 |
| `PageUp` / `PageDown` | 大步滚动 |
| `Ctrl+Up` / `Ctrl+Down` | 单行滚动 |
| `Home` / `End` | 跳转到开头/末尾 |
| `Ctrl+C` | 复制选中文本 / 取消 agent 或退出 |
| `Ctrl+Q` | 退出 |
| `Ctrl+L` | 清屏 |
| `Tab` | 补全斜杠命令名称（输入以 / 开头时） |

## 斜杠命令

输入 `/` 后跟命令名即可执行。按 Tab 键可自动补全命令名。命令在 Agent 运行期间也可使用。

| 命令 | 说明 |
|------|------|
| `/help` | 显示所有可用命令 |
| `/clear` | 清除屏幕和对话记忆 |
| `/model [name]` | 显示或切换当前模型 |
| `/config` | 显示当前配置 |
| `/history` | 显示对话历史 |
| `/save` | 保存当前会话 |
| `/load [id]` | 加载已保存的会话 |
| `/memory [count]` | 显示最近记忆内容 |
| `/remember [name]` | 显示持久化记忆列表或详情 |
| `/forget <name>` | 删除指定持久化记忆 |
| `/compact` | 手动触发上下文压缩 |
| `/mcp` | 显示 MCP 服务器状态 |
| `/tools` | 列出可用工具（已配置 + 内置） |
| `/system` | 显示系统提示词 |
| `/version` | 显示版本信息 |
| `/skills` | 列出所有可用技能 |

## 技能系统

技能是可扩展的 prompt 注入机制。每个技能是一个 Markdown 文件（`SKILL.md`），包含 YAML frontmatter 定义元数据和 markdown 正文。通过 `/skill-name` 触发时，技能的指令被注入到对话上下文中，指导模型执行特定任务。

### 创建技能

1. 在项目根目录的 `skills/` 下创建目录：
```
skills/
  my-skill/
    SKILL.md
```

2. 编写 `SKILL.md` 文件，包含 YAML frontmatter 和 markdown 正文：

```markdown
---
name: my-skill
description: 技能功能描述
allowed-tools:
  - read_file
  - grep
  - shell
when_to_use: "当用户想要...时使用"
argument-hint: "[file-pattern]"
arguments:
  - file-pattern
user-invocable: true
context: inline
---

# 技能名称

## 输入
- `$file-pattern`: 输入参数说明

## 目标
技能要完成的任务。

## 步骤

### 1. 第一步
第一步的说明。

### 2. 第二步
第二步的说明。
```

### SKILL.md Frontmatter 字段

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `name` | string | 目录名 | 唯一标识符（映射 `/name`） |
| `description` | string | - | 简短描述，用于帮助文本 |
| `allowed-tools` | list | `[]`（所有工具） | 技能允许使用的工具 |
| `when_to_use` | string | - | 触发条件说明（供模型参考） |
| `argument-hint` | string | - | 参数提示，如 `"[file]"` |
| `arguments` | list | `[]` | 命名参数占位符列表 |
| `user-invocable` | boolean | `true` | 是否允许用户通过 `/name` 调用 |
| `context` | string | `"inline"` | 执行模式（目前仅支持 `"inline"`） |
| `model` | string | - | 可选模型覆盖 |
| `effort` | string | - | 可选思考努力级别覆盖 |
| `paths` | list | `[]` | 条件激活的 glob 模式 |

### 使用技能

- 输入 `/skill-name` 触发技能
- 输入 `/skills` 列出所有可用技能
- Tab 补全支持技能名称
- 技能会出现在 `/help` 输出中

### 参数替换

在 markdown 正文中使用 `$argument-name` 占位符。触发技能时，用户输入的位置参数会替换这些占位符：

```
/code-review src/main.py
```

如果技能定义了 `arguments: [file-pattern]`，则正文中的 `$file-pattern` 会被替换为 `src/main.py`。

### 工具过滤

当技能指定了 `allowed-tools` 时，技能执行期间只有这些工具可用。这防止模型使用技能范围外的工具。

### 示例：代码审查技能

参见 `skills/code-review/SKILL.md`，这是一个完整的示例，使用 git diff 审查代码变更并提供反馈。

## 自主工作流程

在首次用户交互后，Agent 进入持久化自主循环：

```
用户发送输入 → Agent 处理 → 进入自主循环
                                          ↓
                              CronScheduler 每 N 分钟发送 tick
                                          ↓
                              ┌─── <tick> 收到 ──────────────┐
                              │ 首次 tick：问候用户            │
                              │ 后续 tick：自主工作            │
                              │ 无事可做 → Sleep 工具          │
                              └───────────────────────────────┘
```

**核心行为：**
- **Tick 唤醒**：`<tick>` 提示保持 Agent 在轮次间存活
- **Sleep 状态**：Sleep 工具激活时，tick 被抑制；cron 任务仍可唤醒
- **首次 tick**：输出问候，询问用户需求
- **后续 tick**：Agent 寻找有用工作（读文件、搜索、测试、提交）
- **行动优先**：Agent 基于判断行动，而非请求确认
- **模型降级**：失败时自动切换备用模型，恢复后自动切回
- **自主压缩续接**：压缩后 Agent 继续工作循环

## 许可证

BUSL-1.0
