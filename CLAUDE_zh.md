# CLAUDE_zh.md

这是一个受 Claude Code 启发，使用 Python 构建的 TUI AGI 交互工具。

## 技术栈

- **TUI 框架**：prompt_toolkit 3.0.52（BufferControl + 自定义 OutputLexer 样式化输出，FormattedTextControl 用于提示符/Token）
- **LLM 客户端**：OpenAI SDK（兼容 OpenAI 协议，已在 DeepSeek API 上测试）
- **剪贴板**：pyperclip（Windows 系统剪贴板集成）
- **架构模式**：Agent Loop + MCP 协议

## 项目结构

```
AGImyCLI/
├── src/
│   ├── main.py              # 入口文件
│   ├── tui.py               # TUI 界面（SimpleTUI 类）
│   ├── agent.py             # 核心 Agent 循环（Agent 类）
│   ├── config.py            # 配置管理（Config 单例）
│   ├── memory.py            # 记忆和对话历史（Memory 单例）
│   ├── llm/
│   │   └── client.py        # LLM 客户端（LLMClient 类）
│   ├── tools/
│   │   ├── base.py          # 工具基类（BaseTool 抽象类，ToolResult）
│   │   ├── registry.py      # 工具注册表（ToolRegistry 单例）
│   │   ├── loader.py        # 外部工具加载器（load_external_tools）
│   │   ├── external.py      # ExternalTool 执行器
│   │   └── sleep.py         # Sleep 工具（自主模式空闲等待）
│   ├── commands/
│   │   ├── __init__.py      # 包初始化
│   │   ├── registry.py      # 斜杠命令注册表（CommandRegistry，SlashCommand）
│   │   ├── core.py          # 内置斜杠命令（/help，/model，/save 等）
│   │   └── completer.py     # 斜杠命令 Tab 补全（SlashCommandCompleter）
│   ├── cron/
│   │   └── scheduler.py     # Cron 调度器（CronScheduler，CronTask）
│   ├── mcp/
│   │   ├── base.py          # 抽象 MCP 客户端基类（BaseMCPClient）
│   │   ├── protocol.py      # JSON-RPC 2.0 协议（MCPProtocol，MCPError）
│   │   ├── client.py        # MCP 客户端工厂（create_mcp_client）
│   │   ├── server.py        # MCP 服务器（MCPServer）
│   │   ├── manager.py       # MCP 客户端管理器（MCPManager）
│   │   ├── index.py         # 工具索引（ToolIndex）
│   │   ├── persistence.py   # MCP 数据持久化（MCPDataStore）
│   │   ├── stdio_client.py  # Stdio MCP 客户端（StdioMCPClient）
│   │   ├── http_client.py   # HTTP MCP 客户端（HttpMCPClient）
│   │   └── tavily_client.py # Tavily MCP 客户端（TavilyMCPClient）
│   └── utils/
│       ├── path.py          # 路径工具函数（get_project_root, resolve_path）
│       ├── token_counter.py # Token 计数（count_tokens）
│       └── logging.py       # 日志工具
├── external_tools/           # 外部编译的 .exe 工具
│   ├── read_file/           # 文件读取工具
│   ├── write_file/          # 文件写入工具
│   ├── winshell/            # Shell 执行器（别名解析）
│   ├── grep/                # 内容搜索工具
│   ├── glob/                 # 文件模式匹配工具
│   └── edit/                 # 字符串替换工具
├── memory/                  # 记忆存储
├── logs/                    # 日志文件
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
├── config/                  # 配置文件
│   ├── mcp.json                 # MCP 服务器配置
│   ├── tools.json               # 工具定义
│   └── scheduled_tasks.json     # Cron 任务状态（自动生成）
├── config.json              # 应用配置
├── LICENSE                  # 许可证文件
└── requirements.txt         # 依赖
```

## 配置说明

### config.json — 应用设置

| 配置项 | 键 | 说明 | 默认值 |
|--------|-----|------|--------|
| `openai` | `api_key` | API 密钥 | - |
| | `base_url` | API 地址 | `https://api.deepseek.com` |
| | `model` | 模型名称 | `deepseek-v4-flash` |
| | `fallback_model` | 跨提供商降级配置（空 = 禁用）。对象格式：`{"model": "gpt-4o", "base_url": "...", "api_key": "..."}` — 三字段必填 | `""` |
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
| `prompts` | `autonomous_instructions` | 自主模式指令文件路径 | `""` |
| | `compact_resume` | 压缩恢复提示词路径 | `""` |
| | `max_tokens_recovery` | 输出截断恢复提示词路径 | `""` |
| | `context_too_long` | 上下文过长恢复提示词路径 | `""` |
| | `token_budget_nudge` | Token 预算警告提示词路径 | `""` |
| | `summary_system` | 摘要系统提示词路径 | `""` |
| | `summary_template` | 摘要模板路径 | `""` |
| | `compact_prompt` | 压缩提示词路径 | `""` |

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

#### Cron 任务格式

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

### prompts — 提示词模板系统

`prompts` 配置段将逻辑名称映射到 `.md` 文件路径：

| 模板 | 用途 |
|------|------|
| `autonomous_instructions` | 注入系统提示词，定义自主模式行为指令 |
| `compact_resume` | 上下文压缩后发送，指示 AI 继续工作而非等待输入 |
| `max_tokens_recovery` | 输出达到 token 上限时的恢复提示 |
| `context_too_long` | 上下文窗口溢出时的恢复提示 |
| `token_budget_nudge` | 上下文使用率过高时注入的警告（支持 `{pct:.0%}` 占位符） |
| `summary_system` | 摘要生成的系统提示词 |
| `summary_template` | 摘要生成模板（支持 `{messages}` 占位符） |

`Config._load_prompt(key, default)` 从配置路径加载并缓存模板内容。路径为空或缺失时使用内置默认字符串。用户可通过编辑 `prompts/` 目录下的 `.md` 文件自定义所有行为。

### config/mcp.json — MCP 服务器配置

```json
{
  "mcpServers": {
    "server-name": {
      "type": "stdio|streamable_http|http",
      "url": "https://...",
      "command": "mcp-server-xxx",
      "args": [],
      "env": {},
      "headers": {},
      "api_key": "..."
    }
  }
}
```

## 工具系统

大部分工具为外部 .exe 程序，通过 `tools.json` 定义，由 `load_external_tools()` 加载。`sleep` 工具为内置 Python 工具，直接注册到 `ToolRegistry`，用于自主模式空闲等待。

### 外部工具 (external_tools/)

| 工具 | 类名 | 说明 |
|------|------|------|
| `read_file` | ExternalTool | 读取文件内容，支持多种格式（文本/图片/PDF/Notebook）。文本支持 offset/limit，PDF 支持 pages 参数。返回 metadata 含行数、文件大小、mtime。 |
| `write_file` | ExternalTool | 写入文件内容（UTF-8，路径安全检查） |
| `shell` | ExternalTool | 执行 PowerShell 命令（别名解析、.ps1 文件执行、后台任务、退出码解释、图片检测） |
| `grep` | ExternalTool | 正则搜索文件内容（输出模式：content/files/count，上下文行，类型过滤，head-limit/offset 分页，多行模式） |
| `glob` | ExternalTool | 文件模式匹配（最多 50 条结果） |
| `edit` | ExternalTool | 精确替换文件中的字符串。old_string 必须与文件内容完全一致，支持引号规范化（弯引号/直引号），支持 replace_all 批量替换。 |

### 工具基类 (base.py)

```python
class ToolResult:
    success: bool
    content: str
    error: Optional[str]
    metadata: Dict[str, Any]

class BaseTool(ABC):
    name: str

    @abstractmethod
    def execute(**kwargs) -> ToolResult

    @abstractmethod
    def get_schema() -> Dict[str, Any]

    def validate_args(args: Dict[str, Any]) -> List[str]  # 返回错误列表（空 = 有效）

    def get_definition() -> Dict[str, Any]  # 返回 LLM 函数调用格式
```

### 工具注册表 (registry.py)

管理工具的单例注册表：
- `register(tool: BaseTool)` - 注册工具
- `unregister(name: str)` - 注销工具
- `get(name: str)` - 获取工具
- `list_tools()` - 列出所有工具
- `get_all_definitions()` - 获取所有工具定义
- `execute_tool(name, **kwargs)` - 执行工具

### ExternalTool 执行器 (external.py)

外部工具是编译后的 .exe 程序，通过 `ExternalTool` 类调用：

```python
class ExternalTool:
    name: str
    description: str
    command: str  # 相对或绝对路径
    schema: Dict[str, Any]
```

路径解析：
- **相对路径**：与 project_root 拼接
- **绝对路径**：直接使用

通信方式：JSON 通过 stdin/stdout
- 输入：`--key value` 格式
- 输出：`{"success": bool, "content": str, "error": str, "metadata": {...}}`

输出类型：
- **文本**：`{"success": true, "type": "text", "content": "1| 第一行\n2| 第二行...", "metadata": {"numLines": 10, "totalLines": 100, ...}}`
- **图片**：`{"success": true, "type": "image", "base64": "...", "dimensions": {"width": 800, "height": 600}}`
- **PDF**：`{"success": true, "type": "pdf", "base64": "...", "totalPages": 10}`
- **Notebook**：`{"success": true, "type": "notebook", "cells": [...]}`

Stderr 检测：当工具返回 `success: true` 但 `stderr` 非空时，`ExternalTool` 将 `success` 覆写为 `false`（winshell 的 stderr = PowerShell 错误）。

### tools.json 格式

```json
{
  "tools": [
    {
      "function": {
        "name": "tool_name",
        "description": "工具描述",
        "command": "path/to/executable",
        "parameters": {
          "type": "object",
          "properties": {...},
          "required": [...]
        }
      }
    }
  ]
}
```

### read_file 工具 Schema

```json
{
  "function": {
    "name": "read_file",
    "description": "读取文件内容，支持多种格式",
    "parameters": {
      "type": "object",
      "properties": {
        "path": { "type": "string", "description": "文件路径（绝对路径或相对于项目根目录）" },
        "offset": { "type": "number", "description": "起始行号（从0开始，仅对文本文件有效）", "default": 0 },
        "limit": { "type": "number", "description": "读取行数（仅对文本文件有效）" },
        "pages": { "type": "string", "description": "PDF页码范围，如 '1-5'（仅对PDF有效）" }
      },
      "required": ["path"]
    }
  }
}
```

### shell 工具 Schema

```json
{
  "function": {
    "name": "shell",
    "description": "执行 PowerShell 命令（别名解析）。复杂脚本（包含 $_、$() 等变量引用）自动使用 .ps1 文件执行。",
    "parameters": {
      "type": "object",
      "properties": {
        "command": { "type": "string", "description": "要执行的 PowerShell 命令" },
        "timeout": { "type": "number", "description": "超时时间（毫秒），最大 600000", "default": 30000 },
        "description": { "type": "string", "description": "命令描述（用于日志）" },
        "run_in_background": { "type": "boolean", "description": "后台运行", "default": false },
        "dangerously_disable_sandbox": { "type": "boolean", "description": "禁用沙箱（危险 - 跳过所有验证）", "default": false }
      },
      "required": ["command"]
    }
  }
}
```

### edit 工具 Schema

```json
{
  "function": {
    "name": "edit",
    "description": "精确替换文件中的字符串。需先 Read 文件才能编辑。",
    "parameters": {
      "type": "object",
      "properties": {
        "file_path": { "type": "string", "description": "文件绝对路径（不支持 ~ 路径简写）" },
        "old_string": { "type": "string", "description": "要替换的文本（必须与文件内容完全一致）" },
        "new_string": { "type": "string", "description": "替换文本（必须与 old_string 不同）" },
        "replace_all": { "type": "boolean", "description": "是否替换所有出现（默认 false）", "default": false }
      },
      "required": ["file_path", "old_string", "new_string"]
    }
  }
}
```

### sleep 工具 Schema

```json
{
  "function": {
    "name": "sleep",
    "description": "Pause autonomous operation when idle. Wait for new cron tasks or user input.",
    "parameters": {
      "type": "object",
      "properties": {
        "duration_seconds": {
          "type": "integer",
          "description": "Maximum seconds to sleep (1-3600, default 300)",
          "default": 300,
          "minimum": 1,
          "maximum": 3600
        },
        "reason": {
          "type": "string",
          "description": "Brief reason for sleeping (for logging)"
        }
      },
      "required": []
    }
  }
}
```

## MCP 协议实现 (src/mcp/)

### 协议 (protocol.py)

JSON-RPC 2.0 协议工具：
- `MCPProtocol.create_request()` - 创建请求
- `MCPProtocol.create_response()` - 创建响应
- `MCPProtocol.create_error()` - 创建错误响应

错误码：
- `METHOD_NOT_FOUND = -32601`

方法：
- `initialize` - 初始化连接
- `notifications/initialized` - 初始化完成
- `tools/list` - 列出可用工具
- `tools/call` - 调用工具
- `tools/definitions` - 获取工具定义

### MCP 客户端

| 客户端 | 文件 | 说明 |
|--------|------|------|
| BaseMCPClient | base.py | 抽象基类 |
| StdioMCPClient | stdio_client.py | 子进程 stdin/stdout |
| HttpMCPClient | http_client.py | HTTP/REST API |
| TavilyMCPClient | tavily_client.py | Tavily 网页搜索 |

### MCP 管理器 (manager.py)

管理所有 MCP 客户端连接：
- `connect_all()` - 连接所有配置的服务器
- `disconnect_all()` - 断开所有连接
- `get_client(name)` - 获取指定客户端
- `get_all_tool_definitions()` - 聚合工具定义
- `call_tool(name, arguments)` - 将工具调用路由到相应客户端
- `reload()` - 重新加载配置

### 工具索引 (index.py)

O(1) 工具名到客户端的查找：
- `register(server_name, client, tools)` - 注册工具
- `find(tool_name)` - 查找工具对应的客户端
- `has_tool(tool_name)` - 检查工具是否存在

### 数据持久化 (persistence.py)

在 `mcpdata/` 目录存储 MCP 数据：
- `{server_name}_tools.json` - 工具定义缓存
- `{server_name}_status.json` - 连接状态
- `errors.log` - 错误日志

## LLM 客户端 (src/llm/client.py)

兼容 DeepSeek API 的客户端：
- `chat()` - 发送聊天请求，返回 `(response_content, reasoning_content, usage_dict, finish_reason)`（支持流式）
- `get_tool_calls()` - 从响应中提取工具调用
- `switch_model(model_name)` - 运行时切换模型（用于降级恢复）
- `restore_model()` - 恢复原始模型

消息创建辅助函数：
- `create_system_message()` - 系统消息
- `create_user_message()` - 用户消息
- `create_assistant_message()` - 助手消息（带思考内容）
- `create_tool_result_message()` - 工具结果消息

工具加载：
- `load_tools_from_json()` - 从 tools.json 加载工具

## Agent (src/agent.py)

核心 Agent 循环，协调 LLM 和工具交互：

- **项目上下文注入**：`_build_project_context()` 将 CLAUDE.md 内容（前 3000 字符）、当前日期和 `git status --short` 输出作为 `<system-reminder>` 注入每次 LLM 调用
- **连续错误追踪**：`MAX_CONSECUTIVE_ERRORS = 3` — 连续 3 次 API 错误后停止；上下文过长错误触发完整压缩；模型失败触发降级切换
- **并发工具执行**：只读工具通过 `ThreadPoolExecutor` 并行执行；写入工具串行执行
- **Stop hooks**：`register_stop_hook(callback)` — 每轮工具执行后运行回调；返回错误字符串时注入为用户消息强制 AI 继续

## 记忆系统 (src/memory.py)

### Memory 类
对话管理的单例：
- `add_message(role, content, tool_calls)` - 添加消息
- `add_tool_result(tool_call_id, tool_name, result)` - 添加工具结果
- `get_messages()` - 获取当前会话消息
- `get_context(max_messages)` - 获取最近的 N 条消息
- `get_conversation_for_llm(max_messages)` - 获取 LLM 格式的消息
- `clear()` - 清空当前会话
- `save_current_session()` - 保存到历史
- `load_session(session_path)` - 加载历史会话
- `list_sessions()` - 列出所有会话

### CompactEngine 类
三层上下文压缩引擎：
- **Level 1 (Micro)**：当连续工具调用 >= 3 或时间间隔 >= 5分钟时，清除旧工具结果
- **Level 2 (Auto)**：当使用率 >= 85% 时，LLM 生成摘要
- **Level 3 (Full)**：当使用率 >= 95% 时，保存会话并重置

压缩行为可通过 `config.json` 的 `compact` 配置段调整。
通过编辑 `prompts/compact_prompt.md` 自定义压缩摘要提示词。

## 关键设计决策

1. **单一配置文件**：应用设置在 `config.json`
2. **分离 MCP 配置**：服务器连接在 `config/mcp.json`
3. **相对路径**：所有路径相对于项目根目录
4. **本地工作**：仅在项目目录内工作
5. **MCP 协议**：工具通过 JSON-RPC 2.0 暴露
6. **样式化流式输出（BufferControl）**：使用 BufferControl + 自定义 OutputLexer 实时输出，思考用灰色斜体，回答用青色分隔线
7. **思考模式**：`reasoning_effort` 参数控制思考深度
8. **固定 Token 栏**：Token 统计固定在底栏右下角显示
9. **鼠标事件屏蔽**：Agent 运行期间，`_OutputWindow.mouse_handler` 屏蔽输出窗口的全部鼠标事件，防止滚动/选中操作干扰流式输出
10. **自定义滚动处理**：`_OutputWindow` 覆盖 `_scroll_up()`/`_scroll_down()`，无条件同步光标移动与 `vertical_scroll`（父类仅在光标触及视口边缘时才移动）。使用 `ScrollOffsets(top=0, bottom=0)` 实现精确的滚轮响应
11. **并发工具执行**：只读工具（`read_file`、`grep`、`glob`、`sleep`）通过 `ThreadPoolExecutor` 并行执行；写入工具（`shell`、`write_file`、`edit`）串行执行
12. **Token 预算警告**：当上下文使用率达到 `nudge_threshold`（默认 90%）时，注入 nudge 消息防止过早摘要
13. **Stop hooks**：可注册回调（`register_stop_hook`），每轮工具执行后运行；返回错误字符串时注入为用户消息强制 AI 继续
14. **模型降级**：主模型失败后自动切换到降级模型（通过 `fallback_config` 支持跨提供商切换），恢复后自动切回。两级机制：重试级（`_call_with_retry` 内）和循环级（Agent 继续使用降级模型）
15. **Schema 验证**：工具参数在执行前通过 JSON schema 验证（必填字段、基本类型检查）
16. **Tick 醒醒**：CronScheduler 定期发送 `<tick>` 提示保持自主 Agent 存活。首次 tick 问候用户；后续 tick 触发自主工作
17. **Sleep 状态感知**：Sleep 工具激活时抑制 tick，但 cron 任务仍可唤醒 Agent
18. **Proactive 指令**：自主模式向系统提示词注入行为指令（行动优先、首次问候、通过 Sleep 控制节奏）
19. **标准 Cron 表达式**：CronScheduler 通过 `croniter` 支持 5-field cron，带抖动避免同时触发
20. **自主模式压缩续接**：压缩后续接提示词包含自主模式感知 — AI 继续工作循环而非等待用户输入
21. **斜杠命令系统**：`CommandRegistry` 单例管理 `SlashCommand` 数据类实例，每个命令通过 `handler(tui, args)` 回调执行。`SlashCommandCompleter` 通过 `DynamicCompleter` 在输入 `BufferControl` 中提供 Tab 补全。斜杠命令在 TUI 的 Enter 键处理器中拦截，即使 Agent 运行期间也可同步执行（通过 `enter_while_busy` 绑定）
22. **引号感知操作符转换**：`convert_operators()` 使用状态机跳过引号内的 `&&`/`||`，生成的 `if/else` 块是合法的 PowerShell `-Command` 输入，不会强制使用 `.ps1` 执行
23. **Stderr 成功覆写**：`ExternalTool` 在 `stderr` 非空时将 `success=true` 覆写为 `false`，确保 PowerShell 错误即使在进程退出码为 0 时也能正确报告
24. **错误分类与自动恢复**：错误按类型分类（network、rate_limit、api_server、api_client、context、memory、disk、permission、mcp、tool、unknown），每种类型有特定恢复策略。可重试错误（network、rate_limit、api_server、api_timeout、context、memory、mcp）自动指数退避重试。不可重试错误（api_client、api_auth、api_permission、api_not_found、disk、permission、tool）立即报告。
25. **网络状态监控**：CronScheduler 每 30 秒检查网络连通性。断网恢复后立即触发 tick 恢复自主操作，无需等待下一次计划 tick。
26. **可配置重试参数**：重试行为通过 `config.json` 中的 `retry_interval_seconds`（默认 60s）、`network_max_retries`（默认 10）和 `network_retry_interval_seconds`（默认 30s）配置。

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
- **模型降级**：失败时自动切换到降级模型（支持跨提供商），恢复后自动切回
- **自主压缩续接**：压缩后 Agent 继续工作循环

## 运行方式

```bash
pip install -r requirements.txt
python -m src.main
```

## TUI 布局 (src/tui.py)

```
┌─────────────────────────────────────┐
│         输出区域（Window）              │
│  深蓝背景（#1a1a2e）                   │
│  可滚动、可选中文本                     │
├─────────────────────────────────────┤
│  > [输入（2行，多行）]                │
│  提示符 + 多行输入                     │
├─────────────────────────────────────┤
│               [████░░░░] 72%  ⬆⬇∫  │
│  上下文进度条（>=50%）+ Token 显示     │
└─────────────────────────────────────┘
```

上下文使用率进度条在 >= 50% 时显示，颜色编码：
绿色（< 50%）、黄色（50-84%）、橙色（85-94%）、红色加粗（>= 95%）。

### OutputLexer 样式

| 样式 | 颜色 | 用途 |
|------|------|------|
| `output_area` | `#1a1a2e` 背景 | 输出区域背景 |
| `input_area` | `#16213e` 背景 | 输入区域背景 |
| `prompt` | cyan bold | 提示符文本 |
| `divider` | `#444444` | 分隔线 |
| `separator` | cyan | 回答分隔线 |
| `tool_call` | red bold | 工具调用名称 |
| `tool_result` | blue | 工具结果 |
| `thinking` | gray italic | 思考内容 / Sleep 状态 |
| `token_info` | green | Token 统计 |
| `user` | cyan bold | 用户输入 |
| `error` | red | 错误消息 |
| `context_usage_low` | green | 上下文 < 50% |
| `context_usage_medium` | yellow | 上下文 50-84% |
| `context_usage_high` | orange | 上下文 85-94% |
| `context_usage_critical` | red bold | 上下文 >= 95% |
| `compact_indicator` | cyan italic | 压缩状态指示器 |
| `autonomous` | magenta bold | Cron/自主模式通知 |
| `command` | green bold | 斜杠命令输出 |
| `command_header` | cyan bold | 斜杠命令标题 |
| `completion-menu` | `#1a1a2e` 背景 | 补全菜单背景 |
| `completion-menu.completion` | white | 补全项 |
| `completion-menu.completion.selected` | `#16213e` 背景 cyan bold | 选中的补全项 |

### 键盘快捷键

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

## 斜杠命令系统 (src/commands/)

### CommandRegistry (registry.py)

单例命令注册表，管理所有斜杠命令：
- `register(name, description, handler, arg_spec)` — 注册命令
- `get(name)` — 按名称获取命令
- `list_commands()` — 列出所有已注册命令

### SlashCommand 数据类

```python
@dataclass
class SlashCommand:
    name: str           # 命令名（不含 /）
    description: str    # 命令描述
    handler: Callable   # handler(tui, args) -> None
    arg_spec: str       # 参数说明（如 "[name]"）
    enabled: bool       # 是否启用
```

### 内置命令 (core.py)

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

### SlashCommandCompleter (completer.py)

基于 `BufferControl` 的 Tab 补全器，输入 `/` 时触发命令名补全。

## Token 消耗统计

Token 消耗显示在屏幕底部独立行，靠右显示：
- `⬆`：上传 Token（系统提示词 + 记忆 + 用户输入）
- `⬇`：下载 Token（思考过程 + 回复）
- `∫`：累计总 Token

Token 计算规则：
- 中文字符：1.3 token/个
- 英语单词：1.1 token/个
- 标点符号、数字、其他：1.0 token/个

## 注意事项

- 已启用中文 IME 支持
- 对话超过 `memory_threshold` 时自动摘要
- **可自定义压缩**：编辑 `prompts/compact_prompt.md` 自定义摘要生成提示词
- MCP 服务器：Tavily 搜索 + 任何 stdio/HTTP MCP 服务器
- 外部工具使用 PyInstaller 编译
- 自定义 `_OutputWindow(Window)` 子类处理 Agent 运行期间的鼠标事件屏蔽和同步光标+vertical_scroll 滚动

## 环境

- Windows 10 + PowerShell+windows Terminal


每次修改完子工程都要重新编译后再测试
