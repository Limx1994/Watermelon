# AGImyCLI

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
- **Autonomous mode**: Persistent agent loop with tick-based wake-up, proactive instructions, and Sleep tool for idle waiting
- **Model degradation recovery**: Auto-switch to fallback model on failure, auto-restore on success
- **Standard cron scheduling**: 5-field cron expressions via croniter, with jitter to avoid simultaneous triggers
- **Slash commands**: 13 built-in commands (/help, /model, /save, /compact, etc.) with Tab completion
- **Context usage bar**: Progress bar at >= 50% context usage with color coding (green/yellow/orange/red)
- **Project context injection**: Automatically injects CLAUDE.md and git status into each LLM call

## Quick Start

1. Install dependencies:
```bash
pip install -r requirements.txt
```

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| [prompt-toolkit](https://github.com/prompt-toolkit/prompt-toolkit) | 3.0.52 | TUI framework (BufferControl, FormattedTextControl) |
| [openai](https://github.com/openai/openai-python) | 1.109.1 | OpenAI-compatible LLM client (DeepSeek API) |
| [pyperclip](https://github.com/asweigart/pyperclip) | 1.11.0 | Windows clipboard integration |
| [requests](https://github.com/psf/requests) | 2.33.1 | HTTP client for MCP/HTTP clients |
| [tavily-python](https://github.com/tavily-ai/tavily-python) | 0.7.24 | Tavily web search MCP client |
| [tiktoken](https://github.com/openai/tiktoken) | 0.12.0 | Token counting |
| [croniter](https://github.com/kiorky/croniter) | 6.0.0 | Standard 5-field cron expression parsing |

2. Configure API credentials in `config.json` (note: `config.json` and `config/` are gitignored for security):
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
│   │   ├── external.py      # External CLI tool executor
│   │   └── sleep.py         # Sleep tool for autonomous idle waiting
│   ├── commands/
│   │   ├── __init__.py      # Package init
│   │   ├── registry.py      # Slash command registry (CommandRegistry, SlashCommand)
│   │   ├── core.py          # Built-in slash commands (/help, /model, /save, etc.)
│   │   └── completer.py     # Slash command tab completion (SlashCommandCompleter)
│   ├── cron/
│   │   └── scheduler.py     # Cron scheduler (CronScheduler, CronTask)
│   ├── mcp/
│   │   ├── base.py          # Abstract MCP client base class
│   │   ├── protocol.py      # JSON-RPC 2.0 protocol
│   │   ├── client.py        # MCP client factory (create_mcp_client)
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
│   ├── winshell/            # Shell executor with alias resolution
│   ├── grep/                # Content search tool
│   ├── glob/                 # File pattern matching tool
│   └── edit/                 # String replacement tool
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
├── memory/                  # Conversation storage
│   ├── conversation.json    # Current session history
│   └── history/             # Archived sessions
├── logs/                    # Log files
├── config/                  # Configuration files
│   ├── mcp.json                 # MCP server configuration
│   ├── tools.json               # Tool definitions
│   └── scheduled_tasks.json     # Cron task state (auto-generated)
├── config.json              # Application configuration
├── requirements.txt         # Python dependencies
├── CLAUDE.md                # Project instructions (EN)
├── CLAUDE_zh.md            # Project instructions (ZH)
├── README.md                # This file
├── README_zh.md            # Readme (Chinese)
└── LICENSE                  # License file
```

## Configuration

### config.json — Application Settings

| Section | Key | Description | Default |
|---------|-----|-------------|---------|
| `openai` | `api_key` | API key | - |
| | `base_url` | API base URL | `https://api.deepseek.com` |
| | `model` | Model name | `deepseek-v4-flash` |
| | `fallback_model` | Fallback model for degradation recovery (empty = disabled). Object: `{"model": "gpt-4o", "base_url": "...", "api_key": "..."}` — all three fields required | `""` |
| | `temperature` | Sampling temperature | `0.7` |
| | `top_p` | Nucleus sampling | `0.7` |
| | `reasoning_effort` | Reasoning depth | `max` |
| | `context_window` | Max context window (in thousands, e.g. 128 = 128K) | `128` |
| | `max_output_tokens` | Max output tokens | `20000` |
| `agent` | `max_turns` | Max conversation turns | `50` |
| | `max_retries` | Max retry count on failure | `3` |
| | `retry_interval_seconds` | Retry interval in seconds | `60` |
| | `network_max_retries` | Max retry count for network errors | `10` |
| | `network_retry_interval_seconds` | Network error retry interval in seconds | `30` |
| | `memory_threshold` | Turns before auto-summary | `20` |
| | `thinking_enabled` | Enable thinking mode | `true` |
| | `nudge_threshold` | Token usage ratio to inject nudge message (0.0-1.0) | `0.90` |
| `display` | `show_thinking` | Show thinking process | `true` |
| | `thinking_indicator` | Thinking indicator text | `思考中` |
| `system_prompt` | `path` | Path to system prompt file | `./prompts/systsc.md` |
| `tools` | `enabled` | List of enabled external tools (configured in tools.json) | `["shell", "read_file", "write_file", "grep", "glob", "edit"]` |
| `memory` | `path` | Conversation storage path | `./memory/conversation.json` |
| | `auto_summary` | Auto-summarize long history | `true` |
| `logs` | `path` | Log file path | `./logs/agent.log` |
| | `level` | Log level | `INFO` |
| | `max_bytes` | Max size per log file before rotation | `10485760` (10MB) |
| | `backup_count` | Number of backup log files to keep | `5` |
| `prompts` | `autonomous_instructions` | Path to autonomous mode instructions | `./prompts/autonomous_instructions.md` |
| | `compact_resume` | Path to post-compaction resume prompt | `./prompts/compact_resume.md` |
| | `max_tokens_recovery` | Path to output truncation recovery prompt | `./prompts/max_tokens_recovery.md` |
| | `context_too_long` | Path to context overflow recovery prompt | `./prompts/context_too_long.md` |
| | `token_budget_nudge` | Path to token budget nudge prompt | `./prompts/token_budget_nudge.md` |
| | `summary_system` | Path to summary system prompt | `./prompts/summary_system.md` |
| | `summary_template` | Path to summary template | `./prompts/summary_template.md` |
| | `compact_prompt` | Path to compact prompt template | `./prompts/compact_prompt.md` |

### compact — Context Compression Settings

| Section | Key | Description | Default |
|---------|-----|-------------|---------|
| `compact` | `enabled` | Enable context compression | `true` |
| | `prompt_path` | Path to compact prompt template | `./prompts/compact_prompt.md` |
| | `buffer_tokens` | Target buffer size after compression | `13000` |
| | `micro_compact_streak` | Streak threshold for micro compression | `3` |
| | `micro_compact_gap_minutes` | Gap minutes for micro compression | `5` |
| | `auto_compact_threshold` | Auto compact trigger ratio | `0.85` |
| | `full_compact_threshold` | Full compact trigger ratio | `0.95` |
| | `preserve_recent_messages` | Recent messages to preserve | `10` |

### autonomous — Autonomous Mode Settings

| Section | Key | Description | Default |
|---------|-----|-------------|---------|
| `autonomous` | `tick_interval_minutes` | Tick interval for proactive wake-up (minutes) | `10` |
| | `cron_tasks` | List of cron task definitions | `[]` |

### config/mcp.json — MCP Server Configuration

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
| `shell` | `external_tools/winshell/dist/winshell.exe` | Execute PowerShell commands (alias resolution, quote-aware operator conversion, .ps1 for complex scripts) |
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
| `Tab` | Complete slash command name (when input starts with /) |

## Slash Commands

Type `/` followed by a command name to execute it. Press Tab for completion. Commands are available even while the agent is processing.

| Command | Description |
|---------|-------------|
| `/help` | Show all available commands |
| `/clear` | Clear screen and memory |
| `/model [name]` | Show or switch current model |
| `/config` | Show current configuration |
| `/history` | Show conversation history |
| `/save` | Save current session |
| `/load [id]` | Load a saved session |
| `/memory [count]` | Show recent memory |
| `/compact` | Manually trigger context compression |
| `/mcp` | Show MCP server status |
| `/tools` | List available tools |
| `/system` | Show system prompt |
| `/version` | Show version info |

## Autonomous Workflow

After the first user interaction, the agent enters a persistent autonomous loop:

```
User sends input -> Agent processes -> Enters autonomous loop
                                          |
                              CronScheduler ticks every N minutes
                                          |
                              +--- <tick> received ------------+
                              | First tick: greet user         |
                              | Subsequent: autonomous work    |
                              | No work -> Sleep tool          |
                              +-------------------------------+
```

**Key behaviors:**
- **Tick wake-up**: `<tick>` prompts keep the agent alive between turns
- **Sleep state**: When Sleep tool is active, ticks are suppressed; cron tasks still fire
- **First tick**: Outputs a greeting, asks what the user wants
- **Subsequent ticks**: Agent looks for useful work (read files, search, test, commit)
- **Bias toward action**: Agent acts on judgment rather than asking confirmation
- **Model degradation**: Auto-switch to fallback model on failure, auto-restore on success
- **Autonomous compact resume**: After compression, agent continues its work loop

## License

BUSL-1.0
