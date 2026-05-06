# CLAUDE.md

This is a Python-based TUI AGI interaction tool inspired by Claude Code.

## Tech Stack

- **TUI Framework**: prompt_toolkit 3.0.52 (BufferControl + custom OutputLexer for styled output; FormattedTextControl for prompt/token display)
- **LLM Client**: OpenAI SDK (OpenAI compatible, tested with DeepSeek API)
- **Clipboard**: pyperclip (Windows system clipboard integration)
- **Architecture**: Agent Loop + MCP Protocol

## Project Structure

```
AGImyCLI/
├── src/
│   ├── main.py              # Entry point
│   ├── tui.py               # TUI interface (SimpleTUI class)
│   ├── agent.py             # Core agent loop (Agent class)
│   ├── config.py            # Configuration management (Config singleton)
│   ├── memory.py            # Memory and conversation history (Memory singleton)
│   ├── llm/
│   │   └── client.py        # LLM client (LLMClient class)
│   ├── tools/
│   │   ├── base.py          # Tool base class (BaseTool ABC, ToolResult)
│   │   ├── registry.py      # Tool registry (ToolRegistry singleton)
│   │   ├── loader.py        # External tool loader (load_external_tools)
│   │   └── external.py      # ExternalTool executor
│   ├── mcp/
│   │   ├── base.py          # Abstract MCP client base class (BaseMCPClient)
│   │   ├── protocol.py      # JSON-RPC 2.0 protocol (MCPProtocol, MCPError)
│   │   ├── server.py        # MCP server (MCPServer)
│   │   ├── manager.py       # MCP client manager (MCPManager)
│   │   ├── index.py         # Tool index (ToolIndex)
│   │   ├── persistence.py   # MCP data persistence (MCPDataStore)
│   │   ├── stdio_client.py  # Stdio MCP client (StdioMCPClient)
│   │   ├── http_client.py   # HTTP MCP client (HttpMCPClient)
│   │   └── tavily_client.py # Tavily MCP client (TavilyMCPClient)
│   └── utils/
│       ├── path.py          # Path utilities (get_project_root, resolve_path)
│       ├── token_counter.py # Token counting (count_tokens)
│       └── logging.py       # Logging utilities
├── external_tools/           # External compiled .exe tools
│   ├── read_file/           # File reading tool
│   ├── write_file/          # File writing tool
│   ├── winshell/            # Shell executor with whitelist validation
│   ├── grep/                # Content search tool
│   ├── glob/                 # File pattern matching tool
│   └── edit/                 # String replacement tool
├── manual/                  # Reference manuals
├── memory/                  # Memory storage
├── logs/                    # Log files
├── config.json              # Application configuration
├── mcp.json                 # MCP server configuration
├── tools.json                # Tool definitions
├── systsc.md                # System prompt
└── requirements.txt         # Dependencies
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
| `tools` | `enabled` | List of enabled external tools (configured in tools.json) | `["shell", "read_file", "write_file", "grep", "glob", "edit"]` |
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

## Tool System

All tools are external .exe programs defined in `tools.json` and loaded via `load_external_tools()`. Built-in Python tools have been removed.

### External Tools (external_tools/)

| Tool | Class | Description |
|------|-------|-------------|
| `read_file` | ExternalTool | Read file contents with multi-format support (text/image/PDF/notebook). Supports offset/limit for text, pages for PDF. Returns metadata with line count, file size, mtime. |
| `write_file` | ExternalTool | Write file contents (UTF-8, path safety check) |
| `shell` | ExternalTool | Execute PowerShell commands (alias resolution, .ps1 file execution for complex scripts, background tasks, exit code interpretation, image detection) |
| `grep` | ExternalTool | Regex search in files (output modes: content/files/count, context lines, type filter, head-limit/offset pagination, multiline mode) |
| `glob` | ExternalTool | Pattern matching for files (max 50 results) |
| `edit` | ExternalTool | Precise string replacement in files. old_string must match exactly, supports quote normalization (curly/straight quotes), supports replace_all for batch replacement. |

### Tool Base Classes (base.py)

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

    def get_definition() -> Dict[str, Any]  # Returns LLM function call format
```

### Tool Registry (registry.py)

Singleton registry for managing tools:
- `register(tool: BaseTool)` - Register a tool
- `unregister(name: str)` - Unregister a tool
- `get(name: str)` - Get a tool
- `list_tools()` - List all tools
- `get_all_definitions()` - Get all tool definitions
- `execute_tool(name, **kwargs)` - Execute a tool

### External Tools (external_tools/)

External tools are compiled .exe programs invoked via `ExternalTool` class:

```python
class ExternalTool:
    name: str
    description: str
    command: str  # Relative or absolute path
    schema: Dict[str, Any]
```

Path resolution:
- **Relative path**: Joined with project_root
- **Absolute path**: Used directly

Communication: JSON through stdin/stdout
- Input: `--key value` format
- Output: `{"success": bool, "content": str, "error": str, "metadata": {...}}`

Output types:
- **Text**: `{"success": true, "type": "text", "content": "1| line1\n2| line2...", "metadata": {"numLines": 10, "totalLines": 100, ...}}`
- **Image**: `{"success": true, "type": "image", "base64": "...", "dimensions": {"width": 800, "height": 600}}`
- **PDF**: `{"success": true, "type": "pdf", "base64": "...", "totalPages": 10}`
- **Notebook**: `{"success": true, "type": "notebook", "cells": [...]}`

### tools.json Format

```json
{
  "tools": [
    {
      "function": {
        "name": "tool_name",
        "description": "Tool description",
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

### read_file Tool Schema

```json
{
  "function": {
    "name": "read_file",
    "description": "Read file contents with multi-format support",
    "parameters": {
      "type": "object",
      "properties": {
        "path": { "type": "string", "description": "File path (absolute or relative to project root)" },
        "offset": { "type": "number", "description": "Starting line number (0-based, text files only)", "default": 0 },
        "limit": { "type": "number", "description": "Number of lines to read (text files only)" },
        "pages": { "type": "string", "description": "PDF page range like '1-5' (PDF only)" }
      },
      "required": ["path"]
    }
  }
}
```

### shell Tool Schema

```json
{
  "function": {
    "name": "shell",
    "description": "Execute PowerShell commands with alias resolution. Complex scripts (containing variables like $_, $(), etc.) are automatically executed via .ps1 files.",
    "parameters": {
      "type": "object",
      "properties": {
        "command": { "type": "string", "description": "PowerShell command to execute" },
        "timeout": { "type": "number", "description": "Timeout in milliseconds (max: 600000)", "default": 30000 },
        "description": { "type": "string", "description": "Command description (for logging)" },
        "run_in_background": { "type": "boolean", "description": "Run in background", "default": false },
        "dangerously_disable_sandbox": { "type": "boolean", "description": "Disable sandbox (dangerous - skips all validation)", "default": false }
      },
      "required": ["command"]
    }
  }
}
```

### edit Tool Schema

```json
{
  "function": {
    "name": "edit",
    "description": "Precise string replacement in files. File must be read first before editing.",
    "parameters": {
      "type": "object",
      "properties": {
        "file_path": { "type": "string", "description": "File absolute path (~ not supported)" },
        "old_string": { "type": "string", "description": "String to replace (must match file content exactly)" },
        "new_string": { "type": "string", "description": "Replacement string (must differ from old_string)" },
        "replace_all": { "type": "boolean", "description": "Replace all occurrences (default false)", "default": false }
      },
      "required": ["file_path", "old_string", "new_string"]
    }
  }
}
```

## MCP Protocol Implementation (src/mcp/)

### Protocol (protocol.py)

JSON-RPC 2.0 protocol utilities:
- `MCPProtocol.create_request()` - Create request
- `MCPProtocol.create_response()` - Create response
- `MCPProtocol.create_error()` - Create error response

Error codes:
- `PARSE_ERROR = -32700`
- `INVALID_REQUEST = -32600`
- `METHOD_NOT_FOUND = -32601`
- `INVALID_PARAMS = -32602`
- `INTERNAL_ERROR = -32603`

Methods:
- `initialize` - Initialize connection
- `notifications/initialized` - Initialization complete
- `tools/list` - List available tools
- `tools/call` - Call a tool
- `tools/definitions` - Get tool definitions

### MCP Clients

| Client | File | Description |
|--------|------|-------------|
| BaseMCPClient | base.py | Abstract base class |
| StdioMCPClient | stdio_client.py | Subprocess stdin/stdout |
| HttpMCPClient | http_client.py | HTTP/REST API |
| TavilyMCPClient | tavily_client.py | Tavily web search |

### MCP Manager (manager.py)

Manages all MCP client connections:
- `connect_all()` - Connect to all configured servers
- `disconnect_all()` - Disconnect all
- `get_client(name)` - Get specific client
- `get_all_tool_definitions()` - Aggregate tool definitions
- `call_tool(name, arguments)` - Route tool calls to appropriate client
- `reload()` - Reload configuration

### Tool Index (index.py)

O(1) tool name to client lookup:
- `register(server_name, client, tools)` - Register tools
- `find(tool_name)` - Find client for tool
- `has_tool(tool_name)` - Check if tool exists

### Persistence (persistence.py)

Stores MCP data in `mcpdata/` directory:
- `{server_name}_tools.json` - Tool definitions cache
- `{server_name}_status.json` - Connection status
- `errors.log` - Error logs

## LLM Client (src/llm/client.py)

DeepSeek API compatible client:
- `chat()` - Send chat request (streaming supported)
- `get_tool_calls()` - Extract tool calls from response

Message creation helpers:
- `create_system_message()` - System message
- `create_user_message()` - User message
- `create_assistant_message()` - Assistant message (with reasoning)
- `create_tool_result_message()` - Tool result message

Tools loading:
- `load_tools_from_json()` - Load tools from tools.json

## Memory System (src/memory.py)

Singleton for conversation management:
- `add_message(role, content, tool_calls)` - Add message
- `add_tool_result(tool_call_id, tool_name, result)` - Add tool result
- `get_messages()` - Get current session messages
- `get_conversation_for_llm(max_messages)` - Get LLM-formatted messages
- `clear()` - Clear current session
- `save_current_session()` - Save to history
- `load_session(session_path)` - Load historical session
- `list_sessions()` - List all sessions

## Key Design Decisions

1. **Single config file**: Application settings in `config.json`
2. **Separate MCP config**: Server connections in `mcp.json`
3. **Relative paths**: All paths relative to project root
4. **Local only**: Only works within project directory
5. **MCP protocol**: Tools exposed via JSON-RPC 2.0
6. **Styled streaming with BufferControl**: Real-time output via BufferControl with custom `OutputLexer` for per-line styling (thinking in gray italic, answer with cyan separator)
7. **Thinking mode**: `reasoning_effort` parameter controls reasoning depth
8. **Fixed token bar**: Token statistics displayed as a persistent widget at bottom-right
9. **Mouse event gating**: During agent runtime, all mouse events on the output window are suppressed by `_OutputWindow.mouse_handler`, preventing accidental scroll/selection interference with streaming
10. **Custom scroll handling**: `_OutputWindow` overrides `_scroll_up()`/`_scroll_down()` to always synchronize cursor movement with `vertical_scroll` (parent only moves cursor at viewport edges). Uses `ScrollOffsets(top=0, bottom=0)` for precise scroll wheel response

## Running

```bash
pip install -r requirements.txt
python -m src.main
```

## TUI Layout (src/tui.py)

```
┌─────────────────────────────────────┐
│         Output Area                  │
│  Dark blue background (#1a1a2e)     │
│  Scrollable, selectable text        │
├─────────────────────────────────────┤
│  > [Input (2 rows, multiline)]      │
│  Prompt + Multi-line input          │
├─────────────────────────────────────┤
│                    [Token: ⬆⬇∫]    │
│  Token display (bottom-right)        │
└─────────────────────────────────────┘
```

### OutputLexer Styles

| Style | Color | Usage |
|-------|-------|-------|
| `output_area` | `#1a1a2e` bg | Output background |
| `input_area` | `#16213e` bg | Input background |
| `prompt` | cyan bold | Prompt text |
| `tool_call` | red bold | Tool call names |
| `tool_result` | blue | Tool results |
| `thinking` | gray italic | Thinking content |
| `token_info` | green | Token statistics |
| `user` | cyan bold | User input |
| `error` | red | Error messages |

### Keyboard Shortcuts

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

## Token Counting

Token consumption displayed at bottom of screen (independent row, right-aligned):
- `⬆`: Upload tokens (system + memory + user)
- `⬇`: Download tokens (reasoning + response)
- `∫`: Cumulative total

Calculation rules:
- Chinese characters: 1.3 token/char
- English words: 1.1 token/word
- Punctuation, digits, other: 1.0 token/char

## Notes

- Chinese IME support enabled
- Memory auto-summary when conversation exceeds `memory_threshold`
- MCP servers: Tavily search + any stdio/HTTP MCP server
- External tools compiled with PyInstaller
- Custom `_OutputWindow(Window)` subclass handles mouse event gating during streaming and synchronized cursor+vertical_scroll scrolling

## UI Development

For any UI (TUI) related modifications, you MUST first read `manual/prompt_toolkit_MANUAL.md` (prompt_toolkit 3.0.52 API manual).

This manual covers: Application, Layout, Window, FormattedTextControl, BufferControl, ScrollOffsets, MouseEventType, KeyBindings, mouse_events, style system, Widgets, etc.

## Python Development

For all Python-related questions (standard library usage, language syntax, APIs, etc.), you MUST first consult `manual/python-3.14-docs-text/index.md` to locate the relevant documentation file, then read the manual content for answers instead of directly checking source code.

Only check source code when the manual fails to answer.

## Environment

- Windows 11 + PowerShell
