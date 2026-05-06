# WatermelonCLI

A TUI (Text User Interface) AGI interaction tool inspired by Claude Code, built with Python.

## Features

- **REPL-style interaction**: Chat with AI through a terminal interface
- **Tool system**: All tools configured as external executables via tools.json (read_file, write_file, shell, grep, glob, edit)
- **MCP support**: Connect to Model Context Protocol servers (Tavily search, Sequential Thinking, etc.)
- **Mouse interaction**: Mouse wheel scrolling, text selection, click-to-focus input
- **Memory persistence**: Conversation history saved between sessions, auto-summary for long conversations
- **Chinese input**: Optimized for Chinese language input with IME support
- **Streaming output**: Real-time token-by-token response display with styled fragments
- **Styled display**: Thinking in gray italic, answer with cyan separator, token bar fixed at bottom (independent row, right-aligned)
- **Token statistics**: Live token consumption displayed at bottom-right (upload/download/cumulative)

## Quick Start

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure API credentials in `config.json`:
```json
{
  "openai": {
    "api_key": "your-api-key",
    "base_url": "https://api.deepseek.com",
    "model": "deepseek-v4-flash"
  }
}
```

3. Run:
```bash
python -m src.main
```

## Project Structure

```
AGImyCLI/
├── src/
│   ├── main.py              # Entry point
│   ├── tui.py               # TUI interface
│   ├── agent.py             # Core agent loop
│   ├── config.py            # Configuration management
│   ├── memory.py            # Memory and conversation history
│   ├── llm/
│   │   └── client.py        # LLM client (DeepSeek API compatible)
│   ├── tools/
│   │   ├── base.py          # Tool base class and ToolResult
│   │   ├── registry.py      # Tool registry (singleton)
│   │   ├── loader.py        # External tool loader
│   │   └── external.py      # External CLI tool executor
│   ├── mcp/
│   │   ├── base.py          # Abstract MCP client base class
│   │   ├── protocol.py      # JSON-RPC 2.0 protocol
│   │   ├── server.py        # MCP server (expose built-in tools)
│   │   ├── manager.py       # MCP client manager
│   │   ├── index.py         # Tool name to client index
│   │   ├── persistence.py   # MCP data persistence
│   │   ├── stdio_client.py  # Stdio-based MCP client
│   │   ├── http_client.py   # HTTP-based MCP client
│   │   └── tavily_client.py # Tavily MCP client
│   └── utils/
│       ├── path.py          # Path utilities
│       ├── token_counter.py  # Token counting
│       └── logging.py       # Logging utilities
├── external_tools/           # External compiled .exe tools
│   ├── read_file/           # File reading tool
│   ├── write_file/          # File writing tool
│   ├── winshell/            # Shell executor with whitelist validation
│   ├── grep/                # Content search tool
│   └── glob/                 # File pattern matching tool
├── manual/                  # Reference manuals
│   ├── prompt_toolkit_MANUAL.md   # prompt_toolkit 3.0.52 API
│   └── python-3.14-docs-text/     # Python 3.14 documentation
├── memory/                  # Conversation storage
│   ├── conversation.json    # Current session history
│   └── history/             # Archived sessions
├── logs/                    # Log files
├── config.json              # Application configuration
├── mcp.json                 # MCP server configuration
├── tools.json                # Tool definitions (JSON format)
├── systsc.md                # System prompt
├── requirements.txt         # Python dependencies
├── CLAUDE.md                # Project instructions (EN)
├── CLAUDE_zh.md            # Project instructions (ZH)
├── README.md                # This file
└── README_zh.md            # Readme (Chinese)
```

## Configuration

### config.json — Application Settings

| Section | Key | Description | Default |
|---------|-----|-------------|---------|
| `openai` | `api_key` | API key | - |
| | `base_url` | API base URL | `https://api.deepseek.com` |
| | `model` | Model name | `deepseek-v4-flash` |
| | `temperature` | Sampling temperature | `0.7` |
| | `top_p` | Nucleus sampling | `0.7` |
| | `reasoning_effort` | Reasoning depth | `max` |
| | `context_window` | Max context window | `1000` |
| `agent` | `max_turns` | Max conversation turns | `10` |
| | `max_retries` | Max retry count on failure | `3` |
| | `memory_threshold` | Turns before auto-summary | `20` |
| | `thinking_enabled` | Enable thinking mode | `true` |
| `display` | `show_thinking` | Show thinking process | `true` |
| | `thinking_indicator` | Thinking indicator text | `思考中` |
| `system_prompt` | `path` | Path to system prompt file | `./systsc.md` |
| `tools` | `enabled` | List of enabled built-in tools | `["shell", "read_file", "write_file", "grep", "glob"]` |
| `memory` | `path` | Conversation storage path | `./memory/conversation.json` |
| | `auto_summary` | Auto-summarize long history | `true` |
| `logs` | `path` | Log file path | `./logs/agent.log` |
| | `level` | Log level | `INFO` |

### mcp.json — MCP Server Configuration

```json
{
  "mcpServers": {
    "server-name": {
      "type": "stdio|streamable_http|http",
      "url": "https://...",           // Required for HTTP types
      "command": "mcp-server-xxx",  // Required for stdio type
      "args": [],
      "env": {},
      "headers": {},
      "api_key": "..."
    }
  }
}
```

Supported MCP server types:
- **stdio**: External MCP server via stdio (e.g., npx-based servers)
- **http** / **streamable_http**: HTTP/REST API communication

## External Tools

External tools are compiled .exe programs defined in `tools.json` and communicate via JSON through stdin/stdout.

| Tool | Command | Description |
|------|---------|-------------|
| `read_file` | `external_tools/read_file/dist/read_file.exe` | Read file contents (text/image/PDF/notebook, offset/limit/papers support) |
| `write_file` | `external_tools/write_file/dist/write_file.exe` | Write file contents |
| `shell` | `external_tools/winshell/dist/winshell.exe` | Execute PowerShell commands (alias resolution, .ps1 file execution for complex scripts) |
| `grep` | `external_tools/grep/dist/grep.exe` | Search file contents (regex, output modes, context, type filter, pagination) |
| `glob` | `external_tools/glob/dist/glob.exe` | Find files by pattern (max 50 results) |
| `edit` | `external_tools/edit/dist/edit.exe` | Precise string replacement (quote normalization, replace_all support) |

Example in `tools.json`:
```json
{
  "tools": [
    {
      "function": {
        "name": "read_file",
        "description": "Read file contents with multi-format support",
        "command": "external_tools/read_file/dist/read_file.exe",
        "parameters": {
          "type": "object",
          "properties": {
            "path": { "type": "string", "description": "File path (absolute or relative)" },
            "offset": { "type": "number", "description": "Starting line number (0-based)", "default": 0 },
            "limit": { "type": "number", "description": "Number of lines to read" },
            "pages": { "type": "string", "description": "PDF page range like '1-5'" }
          },
          "required": ["path"]
        }
      }
    },
    {
      "function": {
        "name": "shell",
        "description": "Execute PowerShell commands with alias resolution. Complex scripts are automatically executed via .ps1 files.",
        "command": "external_tools/winshell/dist/winshell.exe",
        "parameters": {
          "type": "object",
          "properties": {
            "command": { "type": "string", "description": "PowerShell command to execute" },
            "timeout": { "type": "number", "description": "Timeout in milliseconds (max: 600000)", "default": 30000 },
            "description": { "type": "string", "description": "Command description (for logging)" },
            "run_in_background": { "type": "boolean", "description": "Run in background", "default": false },
            "dangerously_disable_sandbox": { "type": "boolean", "description": "Disable sandbox (dangerous)", "default": false }
          },
          "required": ["command"]
        }
      }
    }
  ]
}
```

Path support:
- **Relative path**: Joined with project root
- **Absolute path**: Used directly

## Token Statistics

Token consumption is displayed at the bottom of the screen (independent row, right-aligned):
- `⬆`: Upload tokens (system prompt + memory + user input)
- `⬇`: Download tokens (reasoning + response)
- `∫`: Cumulative total

Token calculation rules:
- Chinese characters: 1.3 token/char
- English words: 1.1 token/word
- Punctuation, digits, other: 1.0 token/char

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Enter` | Send all content (multiline support) |
| `Ctrl+J` | Insert newline |
| `Left` / `Right` | Move cursor (cross-line navigation) |
| `Up` / `Down` | Input history / Output scroll (depends on focus) |
| `PageUp` / `PageDown` | Large scroll step |
| `Ctrl+Up` / `Ctrl+Down` | Single line scroll |
| `Home` / `End` | Jump to start/end |
| `Ctrl+C` | Copy selected text (if text selected) / Exit (if no selection) |
| `Ctrl+Q` | Exit |
| `Ctrl+L` | Clear screen and memory |

## License

BUSL-1.0
