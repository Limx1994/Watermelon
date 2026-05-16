# AGImyCLI

A TUI (Text User Interface) AGI interaction tool inspired by Claude Code, built with Python.

## Features

- **REPL-style interaction**: Chat with AI through a terminal interface
- **Tool system**: All tools configured as external executables via tools.json (read_file, write_file, shell, grep, glob, edit)
- **MCP support**: Connect to Model Context Protocol servers (Sequential Thinking, etc.)
- **Mouse interaction**: Mouse wheel scrolling, text selection, click-to-focus input
- **Memory persistence**: Conversation history saved between sessions, auto-summary for long conversations
- **Cross-session memory**: Persistent file-based memory with global/project scopes, LLM-invokable memory tool, MEMORY.md index injection
- **Chinese input**: Optimized for Chinese language input with IME support
- **Streaming output**: Real-time token-by-token response display with styled fragments
- **Styled display**: Thinking in gray italic, answer with cyan separator, token bar fixed at bottom (independent row, right-aligned)
- **Token statistics**: Live token consumption displayed at bottom-right (upload/download/cumulative)
- **Autonomous mode**: Persistent agent loop with tick-based wake-up, proactive instructions, and Sleep tool for idle waiting
- **Model degradation recovery**: Auto-switch to fallback model on failure, auto-restore on success
- **Fast Ctrl+C cancellation**: Interruptible sleep during retries (0.2s response), SIGINT handler for reliable agent cancellation
- **Standard cron scheduling**: 5-field cron expressions via croniter, with jitter to avoid simultaneous triggers
- **Slash commands**: 16 built-in commands (/help, /model, /save, /compact, etc.) with Tab completion
- **Skill system**: Extensible prompt injection via SKILL.md files with YAML frontmatter, argument substitution, and tool filtering
- **Context usage bar**: Progress bar at >= 50% context usage with color coding (green/yellow/orange/red)
- **Project context injection**: Automatically injects project context and git status into each LLM call

## Prerequisites

- **Python** >= 3.10
- **Windows** (see Platform Support below)

### Platform Support

This project currently supports **Windows only**. All external tools are compiled as Windows `.exe` executables, and the shell tool requires PowerShell.

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
| [tiktoken](https://github.com/openai/tiktoken) | 0.12.0 | Token counting |
| [croniter](https://github.com/kiorky/croniter) | 6.0.0 | Standard 5-field cron expression parsing |

2. Configure API credentials in `config.json` (note: `config.json` is gitignored for security; `config/` contains non-sensitive tool/MCP definitions and is tracked):
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
# or
python -m src
```

## Project Structure

```
AGImyCLI/
├── src/
│   ├── __init__.py            # Package init
│   ├── __main__.py            # Entry: python -m src
│   ├── core/
│   │   ├── agent.py           # Core agent loop
│   │   ├── config.py          # Configuration management
│   │   ├── main.py            # Main entry point
│   │   └── tui.py             # TUI interface
│   ├── llm/
│   │   └── client.py          # LLM client (DeepSeek API compatible, interruptible sleep)
│   ├── tools/
│   │   ├── base.py            # Tool base class and ToolResult
│   │   ├── registry.py        # Tool registry (singleton)
│   │   ├── loader.py          # External tool loader
│   │   ├── external.py        # External CLI tool executor
│   │   ├── sleep.py           # Sleep tool for autonomous idle waiting
│   │   ├── memory_tool.py     # Persistent memory tool (LLM-invokable)
│   │   └── implementations/   # Compiled .exe tools
│   │       ├── read_file/     # File reading tool
│   │       ├── write_file/    # File writing tool
│   │       ├── winshell/      # Shell executor with alias resolution
│   │       ├── grep/          # Content search tool
│   │       ├── glob/          # File pattern matching tool
│   │       └── edit/          # String replacement tool
│   ├── commands/
│   │   ├── __init__.py        # Package init
│   │   ├── registry.py        # Slash command registry (CommandRegistry, SlashCommand)
│   │   ├── core.py            # Built-in slash commands (/help, /model, /save, etc.)
│   │   └── completer.py       # Slash command tab completion (SlashCommandCompleter)
│   ├── cron/
│   │   └── scheduler.py       # Cron scheduler (CronScheduler, CronTask)
│   ├── mcp/
│   │   ├── base.py            # Abstract MCP client base class
│   │   ├── protocol.py        # JSON-RPC 2.0 protocol
│   │   ├── client.py          # MCP client factory (create_mcp_client)
│   │   ├── manager.py         # MCP client manager
│   │   ├── index.py           # Tool name to client index
│   │   ├── persistence.py     # MCP data persistence
│   │   ├── stdio_client.py    # Stdio-based MCP client
│   │   └── http_client.py     # HTTP-based MCP client
│   ├── skills/
│   │   ├── __init__.py        # Skill system init (init_skills)
│   │   ├── definition.py      # SkillDefinition dataclass
│   │   ├── loader.py          # SKILL.md parser and loader
│   │   ├── registry.py        # SkillRegistry singleton
│   │   ├── commands.py        # Skill execution handler + /skills command
│   │   ├── tool.py            # SkillTool (LLM-invokable skill tool)
│   │   └── definitions/       # SKILL.md files
│   │       └── code-review/   # Example: code review skill
│   │           └── SKILL.md
│   ├── memory/
│   │   ├── memory.py          # Memory and conversation history
│   │   └── persistent_memory.py # Cross-session persistent memory engine
│   ├── prompts/
│   │   ├── system/            # System prompt sections
│   │   │   ├── intro.md
│   │   │   ├── system_rules.md
│   │   │   ├── doing_tasks.md
│   │   │   ├── tool_usage.md
│   │   │   ├── tone_style.md
│   │   │   └── output_efficiency.md
│   │   ├── service/           # Service prompts
│   │   │   ├── compact_resume.md
│   │   │   ├── summary_system.md
│   │   │   └── summary_template.md
│   │   ├── recovery/          # Recovery prompts
│   │   │   ├── max_tokens_recovery.md
│   │   │   ├── context_too_long.md
│   │   │   └── token_budget_nudge.md
│   │   └── autonomous/
│   │       └── instructions.md # Autonomous mode behavior
│   └── utils/
│       ├── path.py            # Path utilities
│       ├── token_counter.py   # Token counting
│       ├── logging.py         # Logging utilities
│       └── tool_result_persistence.py # Tool result persistence
├── data/                      # Runtime data (gitignored)
│   ├── logs/                  # Log files
│   ├── memory/                # Session history and persistent memory files
│   │   └── tool_results/      # Cached tool results
│   └── mcpdata/               # MCP persistence data
├── config/                    # Configuration files
│   ├── config.json            # Application configuration (gitignored)
│   ├── mcp.json               # MCP server configuration (gitignored)
│   ├── mcp.json.example       # MCP config template
│   ├── tools.json             # Tool definitions
│   └── scheduled_tasks.json   # Cron task state (auto-generated)
├── config.json.example        # Configuration template (root copy)
├── requirements.txt           # Python dependencies
├── README.md                  # This file
├── README_zh.md               # Readme (Chinese)
└── LICENSE                    # License file
```

## Configuration

### config.json — Application Settings

| Section | Key | Description | Default |
|---------|-----|-------------|---------|
| `openai` | `api_key` | API key | - |
| | `base_url` | API base URL | `https://api.deepseek.com` |
| | `model` | Model name | `deepseek-v4-flash` |
| | `fallback_model` | Fallback model for degradation recovery (empty = disabled) | `""` |
| | `temperature` | Sampling temperature | `0.7` |
| | `top_p` | Nucleus sampling | `0.7` |
| | `reasoning_effort` | Reasoning depth | `max` |
| | `context_window` | Max context window (in thousands, e.g. 128 = 128K; values >= 1000 treated as raw tokens). Effective context = `context_window - max_output_tokens`. Code fallback default: 64K | `128` |
| | `max_output_tokens` | Max output tokens | `20000` |
| `agent` | `max_turns` | Max conversation turns | `50` |
| | `max_retries` | Max retry count on failure | `3` |
| | `network_max_retries` | Max retry count for network errors | `10` |
| | `network_retry_interval_seconds` | Network error retry interval in seconds | `30` |
| | `nudge_threshold` | Token usage ratio to inject nudge message (0.0-1.0) | `0.90` |
| `display` | `show_thinking` | Show thinking process | `true` |
| | `thinking_indicator` | Thinking indicator text | `思考中` |
| `tools` | `enabled` | List of enabled external tools (configured in tools.json) | `["shell", "read_file", "write_file", "grep", "glob", "edit"]` |
| `logs` | `path` | Log file path | `./logs/agent.log` |
| | `level` | Log level | `INFO` |
| | `max_bytes` | Max size per log file before rotation | `10485760` (10MB) |
| | `backup_count` | Number of backup log files to keep | `5` |
| `prompts` | `autonomous_instructions` | Path to autonomous mode instructions | `./prompts/autonomous/instructions.md` |
| | `compact_resume` | Path to post-compaction resume prompt | `./prompts/service/compact_resume.md` |
| | `max_tokens_recovery` | Path to output truncation recovery prompt | `./prompts/recovery/max_tokens_recovery.md` |
| | `context_too_long` | Path to context overflow recovery prompt | `./prompts/recovery/context_too_long.md` |
| | `token_budget_nudge` | Path to token budget nudge prompt | `./prompts/recovery/token_budget_nudge.md` |
| | `summary_system` | Path to summary system prompt | `./prompts/service/summary_system.md` |
| | `summary_template` | Path to summary template | `./prompts/service/summary_template.md` |
| | `system_intro` | Path to system prompt intro section | `./prompts/system/intro.md` |
| | `system_rules` | Path to system rules section | `./prompts/system/system_rules.md` |
| | `system_doing_tasks` | Path to task execution guidelines | `./prompts/system/doing_tasks.md` |
| | `system_tool_usage` | Path to tool usage rules | `./prompts/system/tool_usage.md` |
| | `system_tone_style` | Path to tone/style guidelines | `./prompts/system/tone_style.md` |
| | `system_output_efficiency` | Path to output efficiency rules | `./prompts/system/output_efficiency.md` |

Note: Prompt files have been moved to `src/prompts/`. Update the above paths in `config/config.json` to `./src/prompts/...` if needed.

### compact — Context Compression Settings

| Section | Key | Description | Default |
|---------|-----|-------------|---------|
| `compact` | `enabled` | Enable context compression | `true` |
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
| `skills` | `enabled` | Enable the skill system | `true` |
| | `dirs` | Directories to scan for SKILL.md files (relative to project root) | `["skills"]` |
| `persistent_memory` | `enabled` | Enable cross-session persistent memory | `true` |
| | `global_dir` | Global memory directory path (empty = disabled) | `""` |
| | `max_index_chars` | Max characters to inject from MEMORY.md into context | `4000` |
| | `types` | Allowed memory types | `["user", "feedback", "project", "reference"]` |

#### Cron Task Format

Each task in the `cron_tasks` list follows this format:

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

### Prompts — Prompt Template System

The `prompts` config section maps logical names to `.md` file paths. The system prompt is assembled from 6 section files:

| Template | Purpose |
|----------|---------|
| `system_intro` | Agent identity and role definition |
| `system_rules` | System behavior rules |
| `system_doing_tasks` | Task execution guidelines |
| `system_tool_usage` | Tool usage rules and conventions |
| `system_tone_style` | Tone and style guidelines |
| `system_output_efficiency` | Output conciseness rules |
| `autonomous_instructions` | Behavior directives for autonomous mode (appended to system prompt) |

Service and recovery prompts:

| Template | Purpose |
|----------|---------|
| `compact_resume` | Message sent after context compression to resume work |
| `max_tokens_recovery` | Recovery prompt when output hits token limit |
| `context_too_long` | Recovery prompt when context window is exceeded |
| `token_budget_nudge` | Warning injected at high context usage (supports `{pct:.0%}` placeholder) |
| `summary_system` | System prompt for summary generation |
| `summary_template` | Template for summary generation (supports `{messages}` placeholder) |

All prompts are customizable by editing the `.md` files in the `src/prompts/` directory. If a path is empty or the file is missing, a built-in default string is used.

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
| `read_file` | `src/tools/implementations/read_file/dist/read_file.exe` | Read file contents (text/image/PDF/notebook, offset/limit/papers support) |
| `write_file` | `src/tools/implementations/write_file/dist/write_file.exe` | Write file contents |
| `shell` | `src/tools/implementations/winshell/dist/winshell.exe` | Execute PowerShell commands (alias resolution, quote-aware operator conversion, .ps1 for complex scripts, timeout in seconds) |
| `grep` | `src/tools/implementations/grep/dist/grep.exe` | Search file contents (regex, output modes, context, type filter, pagination) |
| `glob` | `src/tools/implementations/glob/dist/glob.exe` | Find files by pattern (max 50 results) |
| `edit` | `src/tools/implementations/edit/dist/edit.exe` | Precise string replacement (quote normalization, replace_all support) |
| `memory` | Built-in | Cross-session persistent memory (save/load/list/search with global/project scopes) |

Example in `tools.json`:
```json
{
  "tools": [
    {
      "function": {
        "name": "read_file",
        "description": "Read file contents with multi-format support",
        "command": "src/tools/implementations/read_file/dist/read_file.exe",
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
        "command": "src/tools/implementations/winshell/dist/winshell.exe",
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
- `⬆`: Upload tokens (system prompt + memory)
- `⬇`: Download tokens (reasoning)
- `∫`: Cumulative total

Token calculation rules (results are rounded to integers):
- Chinese characters: 1.3 token/char
- English words: 1.1 token/word
- Punctuation, digits, other: 1.0 token/char

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Enter` | Send all content (multiline support) |
| `Ctrl+J` | Insert newline |
| `Left` / `Right` | Move cursor (cross-line navigation) |
| `Up` / `Down` | Input history |
| `Ctrl+V` | Paste from clipboard |
| `PageUp` / `PageDown` | Large scroll step |
| `Ctrl+Up` / `Ctrl+Down` | Single line scroll |
| `Home` / `End` | Jump to start/end |
| `Ctrl+C` | Copy selected text / Cancel agent or exit |
| `Ctrl+Q` | Exit |
| `Ctrl+L` | Clear screen |
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
| `/remember [name]` | Show persistent memories list or details |
| `/forget <name>` | Delete a persistent memory |
| `/compact` | Manually trigger context compression |
| `/mcp` | Show MCP server status |
| `/tools` | List available tools (configured + built-in) |
| `/system` | Show system prompt |
| `/version` | Show version info |
| `/skills` | List all available skills |

## Skill System

Skills are extensible prompt injection mechanisms. Each skill is a Markdown file (`SKILL.md`) with YAML frontmatter that defines metadata and a prompt body. When triggered via `/skill-name`, the skill's instructions are injected into the conversation context, guiding the model to execute specific tasks.

### Creating a Skill

1. Create a directory under `src/skills/definitions/`:
```
src/skills/definitions/
  my-skill/
    SKILL.md
```

2. Write the `SKILL.md` file with YAML frontmatter and markdown body:

```markdown
---
name: my-skill
description: Description of what this skill does
allowed-tools:
  - read_file
  - grep
  - shell
when_to_use: "Use when the user wants to..."
argument-hint: "[file-pattern]"
arguments:
  - file-pattern
user-invocable: true
context: inline
---

# Skill Name

## Inputs
- `$file-pattern`: Description of the input

## Goal
What this skill accomplishes.

## Steps

### 1. Step One
Instructions for the first step.

### 2. Step Two
Instructions for the second step.
```

### SKILL.md Frontmatter Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | string | directory name | Unique identifier (maps to `/name`) |
| `description` | string | - | Short description for help text |
| `allowed-tools` | list | `[]` (all tools) | Tools this skill may use |
| `when_to_use` | string | - | When to trigger (for model reference) |
| `argument-hint` | string | - | Parameter hint, e.g. `"[file]"` |
| `arguments` | list | `[]` | Named argument placeholders |
| `user-invocable` | boolean | `true` | Whether user can call via `/name` |
| `context` | string | `"inline"` | Execution mode (`"inline"` only) |
| `model` | string | - | Optional model override |
| `effort` | string | - | Optional reasoning effort override |
| `paths` | list | `[]` | Conditional activation glob patterns |

### Using Skills

- Type `/skill-name` to invoke a skill
- Type `/skills` to list all available skills
- Tab completion works for skill names
- Skills appear in `/help` output

### Argument Substitution

Use `$argument-name` placeholders in the markdown body. When the skill is invoked, positional arguments from the user input replace these placeholders:

```
/code-review src/main.py
```

If the skill defines `arguments: [file-pattern]`, then `$file-pattern` in the body is replaced with `src/main.py`.

### Allowed Tools

When a skill specifies `allowed-tools`, only those tools are available during skill execution. This prevents the model from using tools outside the skill's scope.

### Example: Code Review Skill

See `src/skills/definitions/code-review/SKILL.md` for a complete example that reviews code changes using git diff and provides feedback.

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
