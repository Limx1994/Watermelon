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
│   │   ├── shell.py         #（已废弃，使用 winshell.exe）
│   │   ├── grep.py          #（已废弃，使用 grep.exe）
│   │   ├── glob.py          #（已废弃，使用 glob.exe）
│   │   └── external.py      # ExternalTool 执行器
│   ├── mcp/
│   │   ├── base.py          # 抽象 MCP 客户端基类（BaseMCPClient）
│   │   ├── protocol.py      # JSON-RPC 2.0 协议（MCPProtocol，MCPError）
│   │   ├── server.py        # MCP 服务器（MCPServer）
│   │   ├── manager.py       # MCP 客户端管理器（MCPManager）
│   │   ├── index.py         # 工具索引（ToolIndex）
│   │   ├── persistence.py   # MCP 数据持久化（MCPDataStore）
│   │   ├── stdio_client.py  # Stdio MCP 客户端（StdioMCPClient）
│   │   ├── http_client.py   # HTTP MCP 客户端（HttpMCPClient）
│   │   └── tavily_client.py # Tavily MCP 客户端（TavilyMCPClient）
│   └── utils/
│       ├── path.py          # 路径工具函数（get_project_root, resolve_path）
│       └── token_counter.py # Token 计数（count_tokens）
├── external_tools/           # 外部编译的 .exe 工具
│   ├── read_file/           # 文件读取工具
│   ├── write_file/          # 文件写入工具
│   ├── winshell/            # Shell 执行器（带白名单验证）
│   ├── grep/                # 内容搜索工具
│   └── glob/                 # 文件模式匹配工具
├── manual/                  # 参考手册
├── memory/                  # 记忆存储
├── logs/                    # 日志文件
├── config.json              # 应用配置
├── mcp.json                 # MCP 服务器配置
├── tools.json                # 工具定义
├── systsc.md                # 系统提示词
└── requirements.txt         # 依赖
```

## 配置说明

### config.json — 应用设置

| 配置项 | 键 | 说明 | 默认值 |
|--------|-----|------|--------|
| `openai` | `api_key` | API 密钥 | - |
| | `base_url` | API 地址 | `https://api.deepseek.com` |
| | `model` | 模型名称 | `deepseek-v4-flash` |
| | `temperature` | 采样温度 | `0.7` |
| | `top_p` | 核采样参数 | `0.7` |
| | `reasoning_effort` | 思考深度 | `max` |
| | `context_window` | 最大上下文窗口 | `1000` |
| `agent` | `max_turns` | 最大对话轮次 | `10` |
| | `max_retries` | 失败最大重试次数 | `3` |
| | `memory_threshold` | 触发自动摘要的轮次 | `20` |
| | `thinking_enabled` | 启用思考模式 | `true` |
| `display` | `show_thinking` | 显示思考过程 | `true` |
| | `thinking_indicator` | 思考指示器文字 | `思考中` |
| `system_prompt` | `path` | 系统提示词文件路径 | `./systsc.md` |
| `tools` | `enabled` | 启用的外部工具列表（在 tools.json 中配置） | `["shell", "read_file", "write_file", "grep", "glob"]` |
| `memory` | `path` | 对话存储路径 | `./memory/conversation.json` |
| | `auto_summary` | 长历史自动摘要 | `true` |
| `logs` | `path` | 日志文件路径 | `./logs/agent.log` |
| | `level` | 日志级别 | `INFO` |

### mcp.json — MCP 服务器配置

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

所有工具均为外部 .exe 程序，通过 `tools.json` 定义，由 `load_external_tools()` 加载。不再存在内置 Python 工具。

### 外部工具 (external_tools/)

| 工具 | 类名 | 说明 |
|------|------|------|
| `read_file` | ExternalTool | 读取文件内容，支持多种格式（文本/图片/PDF/Notebook）。文本支持 offset/limit，PDF 支持 pages 参数。返回 metadata 含行数、文件大小、mtime。 |
| `write_file` | ExternalTool | 写入文件内容（UTF-8，路径安全检查） |
| `shell` | ExternalTool | 执行 PowerShell 命令（白名单验证） |
| `grep` | ExternalTool | 正则搜索文件内容（输出模式：content/files/count，上下文行，类型过滤，head-limit/offset 分页，多行模式） |
| `glob` | ExternalTool | 文件模式匹配（最多 50 条结果） |

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

### 外部工具 (external_tools/)

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

## MCP 协议实现 (src/mcp/)

### 协议 (protocol.py)

JSON-RPC 2.0 协议工具：
- `MCPProtocol.create_request()` - 创建请求
- `MCPProtocol.create_response()` - 创建响应
- `MCPProtocol.create_error()` - 创建错误响应

错误码：
- `PARSE_ERROR = -32700`
- `INVALID_REQUEST = -32600`
- `METHOD_NOT_FOUND = -32601`
- `INVALID_PARAMS = -32602`
- `INTERNAL_ERROR = -32603`

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
- `chat()` - 发送聊天请求（支持流式）
- `get_tool_calls()` - 从响应中提取工具调用

消息创建辅助函数：
- `create_system_message()` - 系统消息
- `create_user_message()` - 用户消息
- `create_assistant_message()` - 助手消息（带思考内容）
- `create_tool_result_message()` - 工具结果消息

工具加载：
- `load_tools_from_json()` - 从 tools.json 加载工具

## 记忆系统 (src/memory.py)

对话管理的单例：
- `add_message(role, content, tool_calls)` - 添加消息
- `add_tool_result(tool_call_id, tool_name, result)` - 添加工具结果
- `get_messages()` - 获取当前会话消息
- `get_conversation_for_llm(max_messages)` - 获取 LLM 格式的消息
- `clear()` - 清空当前会话
- `save_current_session()` - 保存到历史
- `load_session(session_path)` - 加载历史会话
- `list_sessions()` - 列出所有会话

## 关键设计决策

1. **单一配置文件**：应用设置在 `config.json`
2. **分离 MCP 配置**：服务器连接在 `mcp.json`
3. **相对路径**：所有路径相对于项目根目录
4. **本地工作**：仅在项目目录内工作
5. **MCP 协议**：工具通过 JSON-RPC 2.0 暴露
6. **样式化流式输出（BufferControl）**：使用 BufferControl + 自定义 OutputLexer 实时输出，思考用灰色斜体，回答用青色分隔线
7. **思考模式**：`reasoning_effort` 参数控制思考深度
8. **固定 Token 栏**：Token 统计固定在底栏右下角显示
9. **鼠标事件屏蔽**：Agent 运行期间，`_OutputWindow.mouse_handler` 屏蔽输出窗口的全部鼠标事件，防止滚动/选中操作干扰流式输出
10. **自定义滚动处理**：`_OutputWindow` 覆盖 `_scroll_up()`/`_scroll_down()`，无条件同步光标移动与 `vertical_scroll`（父类仅在光标触及视口边缘时才移动）。使用 `ScrollOffsets(top=0, bottom=0)` 实现精确的滚轮响应

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
│                    [Token: ⬆⬇∫]    │
│  Token 显示（底部右侧独立行）           │
└─────────────────────────────────────┘
```

### OutputLexer 样式

| 样式 | 颜色 | 用途 |
|------|------|------|
| `output_area` | `#1a1a2e` 背景 | 输出区域背景 |
| `input_area` | `#16213e` 背景 | 输入区域背景 |
| `prompt` | cyan bold | 提示符文本 |
| `tool_call` | red bold | 工具调用名称 |
| `tool_result` | blue | 工具结果 |
| `thinking` | gray italic | 思考内容 |
| `token_info` | green | Token 统计 |
| `user` | cyan bold | 用户输入 |
| `error` | red | 错误消息 |

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
- MCP 服务器：Tavily 搜索 + 任何 stdio/HTTP MCP 服务器
- 外部工具使用 PyInstaller 编译
- 自定义 `_OutputWindow(Window)` 子类处理 Agent 运行期间的鼠标事件屏蔽和同步光标+vertical_scroll 滚动

## UI 开发须知

对于所有 UI（TUI）相关的修改，必须先查阅 `manual/prompt_toolkit_MANUAL.md`（prompt_toolkit 3.0.52 API 手册）。

该手册覆盖：Application、Layout、Window、FormattedTextControl、BufferControl、ScrollOffsets、MouseEventType、KeyBindings、mouse_events、样式系统、Widgets 等。

## Python 开发须知

对于所有 Python 相关问题（标准库用法、语言语法、API 等），必须先查阅 `manual/python-3.14-docs-text/index.md` 索引定位到对应文档文件，再阅读手册内容获取答案，而非直接查看源码。

只有在手册未能解答时，才去查源码。

## 环境

- Windows 11 + PowerShell
