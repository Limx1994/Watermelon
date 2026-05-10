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
│   │   ├── base.py          # Tool base class (BaseTool ABC, ToolResult, validate_args)
│   │   ├── registry.py      # Tool registry (ToolRegistry singleton)
│   │   ├── loader.py        # External tool loader (load_external_tools)
│   │   ├── external.py      # ExternalTool executor
│   │   └── sleep.py         # Sleep tool for autonomous idle waiting
│   ├── commands/
│   │   ├── __init__.py      # Package init
│   │   ├── registry.py      # Slash command registry (CommandRegistry, SlashCommand)
│   │   ├── core.py          # Built-in slash commands (/help, /model, /save, etc.)
│   │   └── completer.py     # Slash command tab completion (SlashCommandCompleter)
│   ├── cron/
│   │   └── scheduler.py     # Cron scheduler (CronScheduler, CronTask)
│   ├── mcp/
│   │   ├── base.py          # Abstract MCP client base class (BaseMCPClient)
│   │   ├── protocol.py      # JSON-RPC 2.0 protocol (MCPProtocol, MCPError)
│   │   ├── client.py        # MCP client factory (create_mcp_client)
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
│   ├── winshell/            # Shell executor with alias resolution
│   ├── grep/                # Content search tool
│   ├── glob/                 # File pattern matching tool
│   └── edit/                 # String replacement tool
├── memory/                  # Memory storage
├── logs/                    # Log files
├── prompts/                 # Prompt templates
│   ├── systsc.md                # System prompt
│   ├── compact_prompt.md        # Compact prompt template
│   ├── autonomous_instructions.md  # Autonomous mode behavior
│   ├── compact_resume.md           # Post-compaction resume
│   ├── max_tokens_recovery.md      # Output truncation recovery
│   ├── context_too_long.md         # Context overflow recovery
│   ├── token_budget_nudge.md       # Token budget nudge
│   ├── summary_system.md           # Summary generation system prompt
│   └── summary_template.md         # Summary template
├── config/                  # Configuration files
│   ├── mcp.json                 # MCP server configuration
│   ├── tools.json               # Tool definitions
│   └── scheduled_tasks.json     # Cron task state (auto-generated)
├── config.json              # Application configuration
├── LICENSE                  # License file
└── requirements.txt         # Dependencies
```

## Environment

- Windows 10 + PowerShell+windows Terminal

- Every time I modify a subproject, I have to recompile and then test it. 

## Configuration

### config.json — Application Settings

| Section         | Key                       | Description                                                                                                                                       | Default                                                        |
| --------------- | ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------- |
| `openai`        | `api_key`                 | API key                                                                                                                                           | -                                                              |
|                 | `base_url`                | API base URL                                                                                                                                      | `https://api.deepseek.com`                                     |
|                 | `model`                   | Model name                                                                                                                                        | `deepseek-v4-flash`                                            |
|                 | `fallback_model`          | Cross-provider fallback config (empty = disabled). Object: `{"model": "gpt-4o", "base_url": "...", "api_key": "..."}` — all three fields required | `""`                                                           |
|                 | `temperature`             | Sampling temperature                                                                                                                              | `0.7`                                                          |
|                 | `top_p`                   | Nucleus sampling                                                                                                                                  | `0.7`                                                          |
|                 | `reasoning_effort`        | Reasoning depth                                                                                                                                   | `max`                                                          |
|                 | `context_window`          | Max context window (in thousands, e.g. 128 = 128K)                                                                                                | `128`                                                          |
|                 | `max_output_tokens`       | Max output tokens                                                                                                                                 | `20000`                                                        |
| `agent`         | `max_turns`               | Max conversation turns                                                                                                                            | `50`                                                           |
|                 | `max_retries`             | Max retry count on failure                                                                                                                        | `3`                                                            |
|                 | `retry_interval_seconds`  | Retry interval in seconds (default 60s = 1 minute)                                                                                               | `60`                                                           |
|                 | `network_max_retries`     | Max retry count for network errors (default 10)                                                                                                  | `10`                                                           |
|                 | `network_retry_interval_seconds` | Network error retry interval in seconds (default 30)                                                                                      | `30`                                                           |
|                 | `memory_threshold`        | Turns before auto-summary                                                                                                                         | `20`                                                           |
|                 | `thinking_enabled`        | Enable thinking mode                                                                                                                              | `true`                                                         |
|                 | `nudge_threshold`         | Token usage ratio to inject nudge message (0.0-1.0)                                                                                               | `0.90`                                                         |
| `display`       | `show_thinking`           | Show thinking process                                                                                                                             | `true`                                                         |
|                 | `thinking_indicator`      | Thinking indicator text                                                                                                                           | `思考中`                                                          |
| `system_prompt` | `path`                    | Path to system prompt file                                                                                                                        | `./prompts/systsc.md`                                          |
| `tools`         | `enabled`                 | List of enabled external tools (configured in tools.json)                                                                                         | `["shell", "read_file", "write_file", "grep", "glob", "edit"]` |
| `memory`        | `path`                    | Conversation storage path                                                                                                                         | `./memory/conversation.json`                                   |
|                 | `auto_summary`            | Auto-summarize long history                                                                                                                       | `true`                                                         |
| `logs`          | `path`                    | Log file path                                                                                                                                     | `./logs/agent.log`                                             |
|                 | `level`                   | Log level                                                                                                                                         | `INFO`                                                         |
|                 | `max_bytes`               | Max size per log file before rotation                                                                                                             | `10485760` (10MB)                                              |
|                 | `backup_count`            | Number of backup log files to keep                                                                                                                | `5`                                                            |
| `prompts`       | `autonomous_instructions` | Path to autonomous mode instructions                                                                                                              | `""`                                                           |
|                 | `compact_resume`          | Path to post-compaction resume prompt                                                                                                             | `""`                                                           |
|                 | `max_tokens_recovery`     | Path to output truncation recovery prompt                                                                                                         | `""`                                                           |
|                 | `context_too_long`        | Path to context overflow recovery prompt                                                                                                          | `""`                                                           |
|                 | `token_budget_nudge`      | Path to token budget nudge prompt                                                                                                                 | `""`                                                           |
|                 | `summary_system`          | Path to summary system prompt                                                                                                                     | `""`                                                           |
|                 | `summary_template`        | Path to summary template                                                                                                                          | `""`                                                           |
|                 | `compact_prompt`          | Path to compact prompt template                                                                                                                   | `""`                                                           |

### compact — Context Compression Settings

| Section   | Key                         | Description                            | Default                       |
| --------- | --------------------------- | -------------------------------------- | ----------------------------- |
| `compact` | `enabled`                   | Enable context compression             | `true`                        |
|           | `prompt_path`               | Path to compact prompt template        | `./prompts/compact_prompt.md` |
|           | `buffer_tokens`             | Target buffer size after compression   | `13000`                       |
|           | `micro_compact_streak`      | Streak threshold for micro compression | `3`                           |
|           | `micro_compact_gap_minutes` | Gap minutes for micro compression      | `5`                           |
|           | `auto_compact_threshold`    | Auto compact trigger ratio             | `0.85`                        |
|           | `full_compact_threshold`    | Full compact trigger ratio             | `0.95`                        |
|           | `preserve_recent_messages`  | Recent messages to preserve            | `10`                          |

### autonomous — Autonomous Mode Settings

| Section      | Key                     | Description                                   | Default |
| ------------ | ----------------------- | --------------------------------------------- | ------- |
| `autonomous` | `tick_interval_minutes` | Tick interval for proactive wake-up (minutes) | `10`    |
|              | `cron_tasks`            | List of cron task definitions                 | `[]`    |

#### Cron Task Format

```json
{
  "name": "task-name",
  "prompt": "What the AI should do",
  "cron_expression": "*/5 * * * *",
  "interval_minutes": 30,
  "enabled": true
}
```

- `cron_expression`: Standard 5-field cron (via croniter). Takes precedence over `interval_minutes`.
- `interval_minutes`: Simple interval fallback if no cron_expression.

### prompts — Prompt Template System

The `prompts` config section maps logical names to `.md` file paths:

| Template                  | Purpose                                                                   |
| ------------------------- | ------------------------------------------------------------------------- |
| `autonomous_instructions` | Injected into system prompt for autonomous mode behavior directives       |
| `compact_resume`          | Message sent after context compression to resume work                     |
| `max_tokens_recovery`     | Recovery prompt when output hits token limit                              |
| `context_too_long`        | Recovery prompt when context window is exceeded                           |
| `token_budget_nudge`      | Warning injected at high context usage (supports `{pct:.0%}` placeholder) |
| `summary_system`          | System prompt for summary generation                                      |
| `summary_template`        | Template for summary generation (supports `{messages}` placeholder)       |

`Config._load_prompt(key, default)` loads and caches template content from the configured path. If the path is empty or missing, the built-in default string is used. Users can customize all behavior by editing `.md` files in the `prompts/` directory.

### config/mcp.json — MCP Server Configuration

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

Most tools are external .exe programs defined in `tools.json` and loaded via `load_external_tools()`. The `sleep` tool is a built-in Python tool registered directly via `ToolRegistry`.

### External Tools (external_tools/)

| Tool         | Class        | Description                                                                                                                                                                |
| ------------ | ------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `read_file`  | ExternalTool | Read file contents with multi-format support (text/image/PDF/notebook). Supports offset/limit for text, pages for PDF. Returns metadata with line count, file size, mtime. |
| `write_file` | ExternalTool | Write file contents (UTF-8, path safety check)                                                                                                                             |
| `shell`      | ExternalTool | Execute PowerShell commands (alias resolution, .ps1 file execution for complex scripts, background tasks, exit code interpretation, image detection)                       |
| `grep`       | ExternalTool | Regex search in files (output modes: content/files/count, context lines, type filter, head-limit/offset pagination, multiline mode)                                        |
| `glob`       | ExternalTool | Pattern matching for files (max 50 results)                                                                                                                                |
| `edit`       | ExternalTool | Precise string replacement in files. old_string must match exactly, supports quote normalization (curly/straight quotes), supports replace_all for batch replacement.      |

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

    def validate_args(args: Dict[str, Any]) -> List[str]  # Returns error list (empty = valid)

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

### ExternalTool Executor (external.py)

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

Stderr detection: If a tool returns `success: true` but has non-empty `stderr`, `ExternalTool` overrides `success` to `false` (winshell stderr = PowerShell errors).

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

### sleep Tool Schema

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

## MCP Protocol Implementation (src/mcp/)

### Protocol (protocol.py)

JSON-RPC 2.0 protocol utilities:

- `MCPProtocol.create_request()` - Create request
- `MCPProtocol.create_response()` - Create response
- `MCPProtocol.create_error()` - Create error response

Error codes:

- `METHOD_NOT_FOUND = -32601`

Methods:

- `initialize` - Initialize connection
- `notifications/initialized` - Initialization complete
- `tools/list` - List available tools
- `tools/call` - Call a tool
- `tools/definitions` - Get tool definitions

### MCP Clients

| Client          | File             | Description             |
| --------------- | ---------------- | ----------------------- |
| BaseMCPClient   | base.py          | Abstract base class     |
| StdioMCPClient  | stdio_client.py  | Subprocess stdin/stdout |
| HttpMCPClient   | http_client.py   | HTTP/REST API           |
| TavilyMCPClient | tavily_client.py | Tavily web search       |

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

- `chat()` - Send chat request, returns `(response_content, reasoning_content, usage_dict, finish_reason)` (streaming supported)
- `get_tool_calls()` - Extract tool calls from response
- `switch_model(model_name)` - Switch to a different model at runtime (for degradation)
- `restore_model()` - Restore the original model after degradation recovery

Message creation helpers:

- `create_system_message()` - System message
- `create_user_message()` - User message
- `create_assistant_message()` - Assistant message (with reasoning)
- `create_tool_result_message()` - Tool result message

Tools loading:

- `load_tools_from_json()` - Load tools from tools.json

## Agent (src/agent.py)

Core agent loop orchestrating LLM and tool interaction:

- **Project context injection**: `_build_project_context()` injects CLAUDE.md content (first 3000 chars), current date, and `git status --short` as a `<system-reminder>` into every LLM call
- **Consecutive error tracking**: `MAX_CONSECUTIVE_ERRORS = 3` — stops after 3 consecutive API errors; context-too-long errors trigger full compact; model failures trigger fallback switching
- **Concurrent tool execution**: Read-only tools run in parallel via `ThreadPoolExecutor`; write tools run serially
- **Stop hooks**: `register_stop_hook(callback)` — callbacks run after each tool round; returning an error string injects it as a user message to force AI continuation

## Memory System (src/memory.py)

### Memory Class

Singleton for conversation management:

- `add_message(role, content, tool_calls)` - Add message
- `add_tool_result(tool_call_id, tool_name, result)` - Add tool result
- `get_messages()` - Get current session messages
- `get_context(max_messages)` - Get recent messages from current session
- `get_conversation_for_llm(max_messages)` - Get LLM-formatted messages
- `clear()` - Clear current session
- `save_current_session()` - Save to history
- `load_session(session_path)` - Load historical session
- `list_sessions()` - List all sessions

### CompactEngine Class

Three-layer context compression engine:

- **Level 1 (Micro)**: Clears old tool results when `tool_call_streak >= 3` or time gap >= 5min
- **Level 2 (Auto)**: LLM generates summary when usage ratio >= 85%
- **Level 3 (Full)**: Saves session and resets when usage ratio >= 95%

Compression is configurable via `config.json` `compact` section.
Customize compression prompts by editing `prompts/compact_prompt.md`.

## Key Design Decisions

1. **Single config file**: Application settings in `config.json`
2. **Separate MCP config**: Server connections in `config/mcp.json`
3. **Relative paths**: All paths relative to project root
4. **Local only**: Only works within project directory
5. **MCP protocol**: Tools exposed via JSON-RPC 2.0
6. **Styled streaming with BufferControl**: Real-time output via BufferControl with custom `OutputLexer` for per-line styling (thinking in gray italic, answer with cyan separator)
7. **Thinking mode**: `reasoning_effort` parameter controls reasoning depth
8. **Fixed token bar**: Token statistics displayed as a persistent widget at bottom-right
9. **Mouse event gating**: During agent runtime, all mouse events on the output window are suppressed by `_OutputWindow.mouse_handler`, preventing accidental scroll/selection interference with streaming
10. **Custom scroll handling**: `_OutputWindow` overrides `_scroll_up()`/`_scroll_down()` to always synchronize cursor movement with `vertical_scroll` (parent only moves cursor at viewport edges). Uses `ScrollOffsets(top=0, bottom=0)` for precise scroll wheel response
11. **Concurrent tool execution**: Read-only tools (`read_file`, `grep`, `glob`, `sleep`) execute in parallel via `ThreadPoolExecutor`; write tools (`shell`, `write_file`, `edit`) execute serially
12. **Token budget nudge**: When context usage reaches `nudge_threshold` (default 90%), a nudge message is injected to prevent premature summarization
13. **Stop hooks**: Registerable callbacks (`register_stop_hook`) that run after each tool execution round; returning an error string injects it as a user message to force AI continuation
14. **Model degradation**: Primary model fails → auto-switch to fallback (different API provider supported via `fallback_config`) → succeed → auto-restore. Two levels: retry-level (within `_call_with_retry`) and loop-level (agent continues with degraded model)
15. **Schema validation**: Tool arguments are validated against JSON schema before execution (required fields, basic type checking)
16. **Tick-based proactive wake-up**: CronScheduler sends periodic `<tick>` prompts to keep the autonomous agent alive. First tick greets the user; subsequent ticks trigger autonomous work
17. **Sleep state awareness**: When the Sleep tool is active, tick is suppressed but cron tasks can still wake the agent
18. **Proactive instructions**: Autonomous mode injects behavior directives (bias toward action, first wake-up greeting, pacing via Sleep) into the system prompt
19. **Standard cron expressions**: CronScheduler supports 5-field cron via `croniter`, with jitter to avoid simultaneous triggers
20. **Autonomous compact resume**: Post-compaction resume prompt includes autonomous mode awareness — AI continues its work loop rather than waiting for user input
21. **Slash command system**: `CommandRegistry` singleton manages `SlashCommand` dataclass instances, each with a `handler(tui, args)` callable. `SlashCommandCompleter` provides Tab completion via `DynamicCompleter` in the input `BufferControl`. Slash commands are intercepted in TUI's Enter handler and executed synchronously on the main thread, even during agent execution (via `enter_while_busy` key binding)
22. **Quote-aware operator conversion**: `convert_operators()` uses a state machine to skip `&&`/`||` inside quoted strings before splitting. The generated `if/else` blocks are valid PowerShell `-Command` input and do not force `.ps1` execution.
23. **Stderr success override**: `ExternalTool` overrides `success=true` to `false` when `stderr` is non-empty, ensuring PowerShell errors are properly reported even when the process exit code is 0.
24. **Error classification and auto-recovery**: Errors are classified by type (network, rate_limit, api_server, api_client, context, memory, disk, permission, mcp, tool, unknown) with specific recovery strategies. Retryable errors (network, rate_limit, api_server, api_timeout, context, memory, mcp) are automatically retried with exponential backoff. Non-retryable errors (api_client, api_auth, api_permission, api_not_found, disk, permission, tool) are reported immediately.
25. **Network state monitoring**: CronScheduler monitors network connectivity every 30 seconds. When network recovers after disconnection, an immediate tick is triggered to resume autonomous operations without waiting for the next scheduled tick.
26. **Configurable retry parameters**: Retry behavior is configurable via `retry_interval_seconds` (default 60s), `network_max_retries` (default 10), and `network_retry_interval_seconds` (default 30s) in `config.json`.

## Autonomous Workflow

After the first user interaction, the agent enters a persistent autonomous loop:

```
User sends input → Agent processes → Enters autonomous loop
                                          ↓
                              CronScheduler ticks every N minutes
                                          ↓
                              ┌─── <tick> received ───────────┐
                              │ First tick: greet user         │
                              │ Subsequent: autonomous work    │
                              │ No work → Sleep tool           │
                              └───────────────────────────────┘
```

**Key behaviors:**

- **Tick wake-up**: `<tick>` prompts keep the agent alive between turns
- **Sleep state**: When Sleep tool is active, ticks are suppressed; cron tasks still fire
- **First tick**: Outputs a greeting, asks what the user wants
- **Subsequent ticks**: Agent looks for useful work (read files, search, test, commit)
- **Bias toward action**: Agent acts on judgment rather than asking confirmation
- **Model degradation**: Auto-switch to fallback (cross-provider via `fallback_config`) on failure, auto-restore on success
- **Autonomous compact resume**: After compression, agent continues its work loop

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
│               [████░░░░] 72%  ⬆⬇∫  │
│  Context bar (>=50%) + Token display │
└─────────────────────────────────────┘
```

Context usage progress bar appears at >= 50% context usage with color coding:
green (< 50%), yellow (50-84%), orange (85-94%), red bold (>= 95%).

### OutputLexer Styles

| Style                          | Color          | Usage                        |
| ------------------------------ | -------------- | ---------------------------- |
| `output_area`                  | `#1a1a2e` bg   | Output background            |
| `input_area`                   | `#16213e` bg   | Input background             |
| `prompt`                       | cyan bold      | Prompt text                  |
| `divider`                      | `#444444`      | Divider line                 |
| `separator`                    | cyan           | Answer separator line        |
| `tool_call`                    | red bold       | Tool call names              |
| `tool_result`                  | blue           | Tool results                 |
| `thinking`                     | gray italic    | Thinking content / sleep     |
| `token_info`                   | green          | Token statistics             |
| `user`                         | cyan bold      | User input                   |
| `error`                        | red            | Error messages               |
| `context_usage_low`            | green          | Context < 50%                |
| `context_usage_medium`         | yellow         | Context 50-84%               |
| `context_usage_high`           | orange         | Context 85-94%               |
| `context_usage_critical`       | red bold       | Context >= 95%               |
| `compact_indicator`            | cyan italic    | Compact status indicator     |
| `autonomous`                   | magenta bold   | Cron/autonomous notifications |
| `command`                      | green bold     | Slash command output         |
| `command_header`               | cyan bold      | Slash command header         |
| `completion-menu`              | `#1a1a2e` bg   | Completion menu background   |
| `completion-menu.completion`   | white          | Completion items             |
| `completion-menu.completion.selected` | `#16213e` bg cyan bold | Selected completion |

### Keyboard Shortcuts

| Shortcut                | Action                                                         |
| ----------------------- | -------------------------------------------------------------- |
| `Enter`                 | Send all content (multiline support)                           |
| `Ctrl+J`                | Insert newline                                                 |
| `Left` / `Right`        | Move cursor (cross-line navigation)                            |
| `Up` / `Down`           | Input history / Output scroll (depends on focus)               |
| `PageUp` / `PageDown`   | Large scroll step                                              |
| `Ctrl+Up` / `Ctrl+Down` | Single line scroll                                             |
| `Home` / `End`          | Jump to start/end                                              |
| `Ctrl+C`                | Copy selected text (if text selected) / Exit (if no selection) |
| `Ctrl+Q`                | Exit                                                           |
| `Ctrl+L`                | Clear screen and memory                                        |

## Slash Command System (src/commands/)

### CommandRegistry (registry.py)

Singleton command registry for managing slash commands:

- `register(name, description, handler, arg_spec)` — Register a command
- `get(name)` — Get a command by name
- `list_commands()` — List all registered commands

### SlashCommand Dataclass

```python
@dataclass
class SlashCommand:
    name: str           # Command name (without /)
    description: str    # Command description
    handler: Callable   # handler(tui, args) -> None
    arg_spec: str       # Argument spec (e.g. "[name]")
    enabled: bool       # Whether command is enabled
```

### Built-in Commands (core.py)

| Command           | Description                          |
| ----------------- | ------------------------------------ |
| `/help`           | Show all available commands          |
| `/clear`          | Clear screen and conversation memory |
| `/model [name]`   | Show or switch current model         |
| `/config`         | Show current configuration           |
| `/history`        | Show conversation history            |
| `/save`           | Save current session                 |
| `/load [id]`      | Load a saved session                 |
| `/memory [count]` | Show recent memory content           |
| `/compact`        | Manually trigger context compression |
| `/mcp`            | Show MCP server status               |
| `/tools`          | List available tools                 |
| `/system`         | Show system prompt                   |
| `/version`        | Show version info                    |

### SlashCommandCompleter (completer.py)

Tab completion for slash commands. Triggers when input starts with `/`. Uses `DynamicCompleter` in the input `BufferControl`.

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
- **Customizable compression**: Edit `prompts/compact_prompt.md` to customize summary generation prompts
- MCP servers: Tavily search + any stdio/HTTP MCP server
- External tools compiled with PyInstaller
- Custom `_OutputWindow(Window)` subclass handles mouse event gating during streaming and synchronized cursor+vertical_scroll scrolling
