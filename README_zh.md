# AGImyCLI

一款受 Claude Code 启发，使用 Python 构建的 TUI（文本用户界面）AGI 交互工具。

## 功能特点

- **REPL 风格交互**：通过终端界面与 AI 对话
- **工具系统**：所有工具通过 tools.json 配置为外部可执行文件（read_file、write_file、shell、grep、glob、edit）
- **MCP 支持**：连接 Model Context Protocol 服务器（Tavily 搜索、Sequential Thinking 等）
- **鼠标交互**：鼠标滚轮滚动、文本选择、点击聚焦输入
- **记忆持久化**：会话历史持久保存，长对话自动摘要
- **中文输入**：优化中文语言输入体验，支持 IME
- **流式输出**：实时逐 token 显示响应，带样式化片段
- **样式化显示**：思考内容灰色斜体显示，回答带青色分隔线，Token 栏固定在底部（独立行，靠右对齐）
- **Token 统计**：实时显示上传/下载/累计 Token，固定在底栏右下角
- **自主模式**：持久化 Agent 循环，支持 tick 醒醒、proactive 指令、Sleep 工具空闲等待
- **模型降级恢复**：主模型失败时自动切换备用模型，恢复后自动切回
- **标准 Cron 调度**：支持 5-field cron 表达式（via croniter），带抖动避免同时触发
- **斜杠命令**：13 个内置命令（/help、/model、/save、/compact 等），支持 Tab 补全
- **上下文进度条**：上下文使用率 >= 50% 时显示进度条，带颜色编码（绿/黄/橙/红）
- **项目上下文注入**：自动将 CLAUDE.md 和 git status 注入每次 LLM 调用

## 快速开始

1. 安装依赖：
```bash
pip install -r requirements.txt
```

2. 在 `config.json` 中配置 API 凭据（注意：`config.json` 和 `config/` 已被 .gitignore 排除以保护安全）：
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
```

## 依赖项

| 包 | 版本 | 用途 |
|---|------|------|
| [prompt-toolkit](https://github.com/prompt-toolkit/prompt-toolkit) | 3.0.52 | TUI 框架（BufferControl、FormattedTextControl） |
| [openai](https://github.com/openai/openai-python) | 1.109.1 | 兼容 OpenAI 协议的 LLM 客户端（DeepSeek API） |
| [pyperclip](https://github.com/asweigart/pyperclip) | 1.11.0 | Windows 剪贴板集成 |
| [requests](https://github.com/psf/requests) | 2.33.1 | HTTP 客户端（MCP/HTTP 客户端） |
| [tavily-python](https://github.com/tavily-ai/tavily-python) | 0.7.24 | Tavily 网页搜索 MCP 客户端 |
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
│   ├── llm/
│   │   └── client.py        # LLM 客户端（兼容 DeepSeek API）
│   ├── tools/
│   │   ├── base.py          # 工具基类和 ToolResult
│   │   ├── registry.py      # 工具注册表（单例模式）
│   │   ├── loader.py        # 外部工具加载器
│   │   ├── external.py      # 外部 CLI 工具执行器
│   │   └── sleep.py         # Sleep 工具（自主模式空闲等待）
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
│   │   ├── server.py        # MCP 服务器（暴露内置工具）
│   │   ├── manager.py       # MCP 客户端管理器
│   │   ├── index.py         # 工具名到客户端的索引
│   │   ├── persistence.py   # MCP 数据持久化
│   │   ├── stdio_client.py  # 基于 Stdio 的 MCP 客户端
│   │   ├── http_client.py   # 基于 HTTP 的 MCP 客户端
│   │   └── tavily_client.py # Tavily MCP 客户端
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
├── prompts/                 # 提示词模板
│   ├── systsc.md                # 系统提示词
│   ├── compact_prompt.md        # 压缩提示词模板
│   ├── autonomous_instructions.md  # 自主模式行为指令
│   ├── compact_resume.md           # 压缩后续接
│   ├── max_tokens_recovery.md      # 输出截断恢复
│   ├── context_too_long.md         # 上下文过长恢复
│   ├── token_budget_nudge.md       # Token 预算警告
│   ├── summary_system.md           # 摘要生成系统提示
│   └── summary_template.md         # 摘要模板
├── memory/                  # 对话存储
│   ├── conversation.json    # 当前会话历史
│   └── history/             # 归档会话
├── logs/                    # 日志文件
├── config/                  # 配置文件
│   ├── mcp.json                 # MCP 服务器配置
│   ├── tools.json               # 工具定义
│   └── scheduled_tasks.json     # Cron 任务状态（自动生成）
├── config.json              # 应用配置
├── requirements.txt         # Python 依赖
├── CLAUDE.md                # 项目说明（英文）
├── CLAUDE_zh.md            # 项目说明（中文）
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
| | `fallback_model` | 降级备用模型（空 = 禁用）。对象格式：`{"model": "gpt-4o", "base_url": "...", "api_key": "..."}` — 三字段必填 | `""` |
| | `temperature` | 采样温度 | `0.7` |
| | `top_p` | 核采样参数 | `0.7` |
| | `reasoning_effort` | 思考深度 | `max` |
| | `context_window` | 最大上下文窗口（单位为千，如 128 = 128K） | `128` |
| | `max_output_tokens` | 最大输出 Token 数 | `20000` |
| `agent` | `max_turns` | 最大对话轮次 | `50` |
| | `max_retries` | 失败最大重试次数 | `3` |
| | `retry_interval_seconds` | 失败重试间隔（秒） | `60` |
| | `network_max_retries` | 网络错误最大重试次数 | `10` |
| | `network_retry_interval_seconds` | 网络错误重试间隔（秒） | `30` |
| | `memory_threshold` | 触发自动摘要的轮次 | `20` |
| | `thinking_enabled` | 启用思考模式 | `true` |
| | `nudge_threshold` | Token 预算警告触发比例（0.0-1.0） | `0.90` |
| `display` | `show_thinking` | 显示思考过程 | `true` |
| | `thinking_indicator` | 思考指示器文字 | `思考中` |
| `system_prompt` | `path` | 系统提示词文件路径 | `./prompts/systsc.md` |
| `tools` | `enabled` | 启用的外部工具列表（在 tools.json 中配置） | `["shell", "read_file", "write_file", "grep", "glob", "edit"]` |
| `memory` | `path` | 对话存储路径 | `./memory/conversation.json` |
| | `auto_summary` | 长历史自动摘要 | `true` |
| `logs` | `path` | 日志文件路径 | `./logs/agent.log` |
| | `level` | 日志级别 | `INFO` |
| | `max_bytes` | 单个日志文件最大字节数（轮转前） | `10485760`（10MB） |
| | `backup_count` | 日志备份数量 | `5` |
| `prompts` | `autonomous_instructions` | 自主模式指令文件路径 | `./prompts/autonomous_instructions.md` |
| | `compact_resume` | 压缩恢复提示词路径 | `./prompts/compact_resume.md` |
| | `max_tokens_recovery` | 输出截断恢复提示词路径 | `./prompts/max_tokens_recovery.md` |
| | `context_too_long` | 上下文过长恢复提示词路径 | `./prompts/context_too_long.md` |
| | `token_budget_nudge` | Token 预算警告提示词路径 | `./prompts/token_budget_nudge.md` |
| | `summary_system` | 摘要系统提示词路径 | `./prompts/summary_system.md` |
| | `summary_template` | 摘要模板路径 | `./prompts/summary_template.md` |
| | `compact_prompt` | 压缩提示词路径 | `./prompts/compact_prompt.md` |

### compact — 上下文压缩设置

| 配置项 | 键 | 说明 | 默认值 |
|--------|-----|------|--------|
| `compact` | `enabled` | 启用上下文压缩 | `true` |
| | `prompt_path` | 压缩提示词模板路径 | `./prompts/compact_prompt.md` |
| | `buffer_tokens` | 压缩后目标缓冲区大小 | `13000` |
| | `micro_compact_streak` | 微型压缩触发连续数 | `3` |
| | `micro_compact_gap_minutes` | 微型压缩时间间隔（分钟） | `5` |
| | `auto_compact_threshold` | 自动压缩触发比例 | `0.85` |
| | `full_compact_threshold` | 完整压缩触发比例 | `0.95` |
| | `preserve_recent_messages` | 保留的最近消息数 | `10` |

### autonomous — 自主模式设置

| 配置项 | 键 | 说明 | 默认值 |
|--------|-----|------|--------|
| `autonomous` | `tick_interval_minutes` | Tick 醒醒间隔（分钟） | `10` |
| | `cron_tasks` | 定时任务定义列表 | `[]` |

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
| `shell` | `external_tools/winshell/dist/winshell.exe` | 执行 PowerShell 命令（别名解析、引号感知操作符转换、复杂脚本使用 .ps1） |
| `grep` | `external_tools/grep/dist/grep.exe` | 搜索文件内容（正则，输出模式，上下文，类型过滤，分页） |
| `glob` | `external_tools/glob/dist/glob.exe` | 按模式查找文件（最多 50 条） |
| `edit` | `external_tools/edit/dist/edit.exe` | 精确字符串替换（引号规范化，replace_all 支持） |

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
- `⬆`：上传 Token（系统提示词 + 记忆 + 用户输入）
- `⬇`：下载 Token（思考过程 + 回复）
- `∫`：累计总 Token

Token 计算规则：
- 中文字符：1.3 token/个
- 英语单词：1.1 token/个
- 标点符号、数字、其他：1.0 token/个

## 键盘快捷键

| 快捷键 | 功能 |
|--------|------|
| `Enter` | 发送所有内容（支持多行） |
| `Ctrl+J` | 插入换行符 |
| `Left` / `Right` | 光标移动（跨行导航） |
| `Up` / `Down` | 输入历史 / 输出滚动（取决于焦点区域） |
| `PageUp` / `PageDown` | 大步滚动 |
| `Ctrl+Up` / `Ctrl+Down` | 单行滚动 |
| `Home` / `End` | 跳转到开头/末尾 |
| `Ctrl+C` | 复制选中文本（如有选中文本）/ 退出（若无选中文本） |
| `Ctrl+Q` | 退出 |
| `Ctrl+L` | 清屏并清空记忆 |
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
| `/compact` | 手动触发上下文压缩 |
| `/mcp` | 显示 MCP 服务器状态 |
| `/tools` | 列出可用工具 |
| `/system` | 显示系统提示词 |
| `/version` | 显示版本信息 |

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
- **Tick 醒醒**：`<tick>` 提示保持 Agent 在轮次间存活
- **Sleep 状态**：Sleep 工具激活时，tick 被抑制；cron 任务仍可唤醒
- **首次 tick**：输出问候，询问用户需求
- **后续 tick**：Agent 寻找有用工作（读文件、搜索、测试、提交）
- **行动优先**：Agent 基于判断行动，而非请求确认
- **模型降级**：失败时自动切换备用模型，恢复后自动切回
- **自主压缩续接**：压缩后 Agent 继续工作循环

## 许可证

BUSL-1.0
