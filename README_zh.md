# AGImyCLI

一款受 Claude Code 启发，使用 Python 构建的 TUI（文本用户界面）AGI 交互工具。

## 功能特点

- **REPL 风格交互**：通过终端界面与 AI 对话
- **工具系统**：所有工具通过 tools.json 配置为外部可执行文件（read_file、write_file、shell、grep、glob）
- **MCP 支持**：连接 Model Context Protocol 服务器（Tavily 搜索、Sequential Thinking 等）
- **鼠标交互**：鼠标滚轮滚动、文本选择、点击聚焦输入
- **记忆持久化**：会话历史持久保存，长对话自动摘要
- **中文输入**：优化中文语言输入体验，支持 IME
- **流式输出**：实时逐 token 显示响应，带样式化片段
- **样式化显示**：思考内容灰色斜体显示，回答带青色分隔线，Token 栏固定在底部（独立行，靠右对齐）
- **Token 统计**：实时显示上传/下载/累计 Token，固定在底栏右下角

## 快速开始

1. 安装依赖：
```bash
pip install -r requirements.txt
```

2. 在 `config.json` 中配置 API 凭据：
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
│   │   ├── shell.py         # Shell 执行工具
│   │   ├── grep.py          # 内容搜索工具
│   │   ├── glob.py          # 文件模式匹配工具
│   │   ├── loader.py        # 外部工具加载器
│   │   └── external.py      # 外部 CLI 工具执行器
│   ├── mcp/
│   │   ├── base.py          # 抽象 MCP 客户端基类
│   │   ├── protocol.py      # JSON-RPC 2.0 协议
│   │   ├── server.py        # MCP 服务器（暴露内置工具）
│   │   ├── manager.py       # MCP 客户端管理器
│   │   ├── index.py         # 工具名到客户端的索引
│   │   ├── persistence.py   # MCP 数据持久化
│   │   ├── stdio_client.py  # 基于 Stdio 的 MCP 客户端
│   │   ├── http_client.py   # 基于 HTTP 的 MCP 客户端
│   │   └── tavily_client.py # Tavily MCP 客户端
│   └── utils/
│       ├── path.py          # 路径工具函数
│       └── token_counter.py # Token 计数
├── external_tools/           # 外部编译的 .exe 工具
│   ├── read_file/           # 文件读取工具
│   ├── write_file/          # 文件写入工具
│   ├── winshell/            # Shell 执行器（带白名单验证）
│   ├── grep/                # 内容搜索工具
│   └── glob/                 # 文件模式匹配工具
├── manual/                  # 参考手册
│   ├── prompt_toolkit_MANUAL.md   # prompt_toolkit 3.0.52 API
│   └── python-3.14-docs-text/     # Python 3.14 文档
├── memory/                  # 对话存储
│   ├── conversation.json    # 当前会话历史
│   └── history/             # 归档会话
├── logs/                    # 日志文件
├── config.json              # 应用配置
├── mcp.json                 # MCP 服务器配置
├── tools.json                # 工具定义（JSON 格式）
├── systsc.md                # 系统提示词
├── requirements.txt         # Python 依赖
├── CLAUDE.md                # 项目说明（英文）
├── CLAUDE_zh.md            # 项目说明（中文）
├── README.md                # 说明文档（英文）
└── README_zh.md            # 本文件
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

所有工具均为外部 .exe 程序，在 `tools.json` 中定义，通过 JSON 在 stdin/stdout 上通信。

外部工具是编译后的 .exe 程序，在 `tools.json` 中定义，通过 JSON 在 stdin/stdout 上通信。

| 工具 | 命令 | 说明 |
|------|------|------|
| `read_file` | `external_tools/read_file/dist/read_file.exe` | 读取文件内容（文本/图片/PDF/Notebook，支持 offset/limit/pages） |
| `write_file` | `external_tools/write_file/dist/write_file.exe` | 写入文件内容 |
| `shell` | `external_tools/winshell/dist/winshell.exe` | 执行 PowerShell 命令（白名单验证） |
| `grep` | `external_tools/grep/dist/grep.exe` | 搜索文件内容（正则，输出模式，上下文，类型过滤，分页） |
| `glob` | `external_tools/glob/dist/glob.exe` | 按模式查找文件（最多 50 条） |

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

## 许可证

BUSL-1.0
