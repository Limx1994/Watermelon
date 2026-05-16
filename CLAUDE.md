# CLAUDE.md

Python-based TUI AGI interaction tool inspired by Claude Code.

## Tech Stack

- **TUI**: prompt_toolkit 3.0.52 (BufferControl + custom OutputLexer)
- **LLM**: OpenAI SDK (DeepSeek API compatible)
- **Clipboard**: pyperclip (Windows)
- **Architecture**: Agent Loop + MCP Protocol

## Project Structure

```
src/
├── __init__.py            # Package init
├── __main__.py            # Entry: python -m src
├── core/
│   ├── agent.py           # Agent loop (concurrent tools, stop hooks)
│   ├── config.py          # Config singleton
│   ├── main.py            # Main entry point
│   └── tui.py             # TUI (SimpleTUI, BufferControl + OutputLexer)
├── llm/
│   └── client.py          # LLM client (streaming, model switching, interruptible sleep)
├── tools/
│   ├── base.py            # BaseTool, ToolResult
│   ├── registry.py        # Tool registry (singleton)
│   ├── loader.py          # External tool loader
│   ├── external.py        # External CLI tool executor
│   ├── sleep.py           # Sleep tool (autonomous idle)
│   ├── memory_tool.py     # Persistent memory tool (LLM-invokable)
│   └── implementations/   # Compiled .exe tools
│       ├── read_file/     # File reader
│       ├── write_file/    # File writer
│       ├── winshell/      # Shell executor (alias resolution)
│       ├── grep/          # Content search
│       ├── glob/          # File pattern matching
│       └── edit/          # String replacement
├── commands/              # registry.py, core.py, completer.py, utils.py
├── skills/
│   ├── definition.py      # SkillDefinition dataclass
│   ├── loader.py          # SKILL.md parser and loader
│   ├── registry.py        # SkillRegistry singleton
│   ├── commands.py        # Skill execution handler + /skills command
│   ├── tool.py            # SkillTool (LLM-invokable)
│   └── definitions/       # SKILL.md files
│       └── code-review/   # Example: code review skill
├── cron/
│   └── scheduler.py       # CronScheduler
├── memory/
│   ├── memory.py          # Memory + CompactEngine
│   └── persistent_memory.py # PersistentMemory (cross-session)
├── mcp/                   # protocol.py, manager.py, base.py, client.py, http_client.py, stdio_client.py, index.py, persistence.py
├── prompts/
│   ├── system/            # System prompt sections (6 files)
│   ├── service/           # Service prompts
│   ├── recovery/          # Recovery prompts
│   └── autonomous/        # Autonomous mode instructions
└── utils/                 # path.py, token_counter.py, logging.py, tool_result_persistence.py
data/                      # Runtime data (gitignored)
├── logs/                  # Log files
├── memory/                # Session history and persistent memory files
└── mcpdata/               # MCP persistence data
config/                    # Configuration files
├── config.json            # App configuration (gitignored, use config.json.example)
├── mcp.json               # MCP server configuration (gitignored, use mcp.json.example)
├── tools.json             # Tool definitions
└── scheduled_tasks.json   # Cron task state (auto-generated)
config.json.example        # Configuration template
requirements.txt           # Python dependencies
```

## Environment

- Windows 10 + PowerShell + Windows Terminal
- External tools: recompile after modification

## Configuration

All settings in `config.json`:

| Section | Key | Default | Description |
|---------|-----|---------|-------------|
| `openai` | `api_key` | - | API key |
| | `base_url` | `https://api.deepseek.com` | API base URL |
| | `model` | `deepseek-v4-flash` | Model name |
| | `fallback_model` | `""` | Fallback: `{"model", "base_url", "api_key"}` |
| | `temperature` / `top_p` | `0.7` | Sampling params |
| | `reasoning_effort` | `max` | Reasoning depth |
| | `context_window` | `64` | Max context (K tokens) |
| | `max_output_tokens` | `20000` | Max output tokens |
| `agent` | `max_turns` | `50` | Max conversation turns |
| | `max_retries` | `3` | Retry count |
| | `network_max_retries` | `10` | Network retry count |
| | `network_retry_interval_seconds` | `30` | Network retry interval |
| | `nudge_threshold` | `0.90` | Token budget nudge ratio |
| `display` | `show_thinking` | `true` | Show thinking process |
| | `thinking_indicator` | `思考中` | Thinking indicator |
| `tools` | `enabled` | `["shell","read_file",...]` | Enabled tools |
| `logs` | `path` | `./logs/agent.log` | Log path |
| | `level` | `INFO` | Log level |
| | `max_bytes` | `10485760` | Max log file size (bytes) |
| | `backup_count` | `5` | Log backup count |
| `skills` | `enabled` | `true` | Enable the skill system |
| | `dirs` | `["skills"]` | Directories to scan for SKILL.md files |
| `compact` | `enabled` | `true` | Enable context compression |
| | `buffer_tokens` | `13000` | Target buffer size after compression |
| | `micro_compact_streak` | `3` | Micro compact streak threshold |
| | `micro_compact_gap_minutes` | `5` | Micro compact gap (minutes) |
| | `auto_compact_threshold` | `0.85` | Auto compact trigger ratio |
| | `full_compact_threshold` | `0.95` | Full compact trigger ratio |
| | `preserve_recent_messages` | `10` | Recent messages to preserve |
| `persistent_memory` | `enabled` | `true` | Enable persistent memory system |
| | `global_dir` | `""` | Global memory directory (empty = disabled) |
| | `max_index_chars` | `4000` | Max chars injected from MEMORY.md into context |
| | `types` | `["user","feedback","project","reference"]` | Allowed memory types |
| `autonomous` | `tick_interval_minutes` | `10` | Proactive wake-up interval |
| | `cron_tasks` | `[]` | Cron task definitions |
| `prompts` | `system_intro` | `./prompts/system/intro.md` | System prompt intro section |
| | `system_rules` | `./prompts/system/system_rules.md` | System behavior rules |
| | `system_doing_tasks` | `./prompts/system/doing_tasks.md` | Task execution guidelines |
| | `system_tool_usage` | `./prompts/system/tool_usage.md` | Tool usage rules |
| | `system_tone_style` | `./prompts/system/tone_style.md` | Tone/style guidelines |
| | `system_output_efficiency` | `./prompts/system/output_efficiency.md` | Output efficiency rules |
| | `autonomous_instructions` | `./prompts/autonomous/instructions.md` | Autonomous mode directives |
| | `compact_resume` | `./prompts/service/compact_resume.md` | Post-compaction resume |
| | `summary_system` | `./prompts/service/summary_system.md` | Summary system prompt |
| | `summary_template` | `./prompts/service/summary_template.md` | Summary template |
| | `max_tokens_recovery` | `./prompts/recovery/max_tokens_recovery.md` | Output truncation recovery |
| | `context_too_long` | `./prompts/recovery/context_too_long.md` | Context overflow recovery |
| | `token_budget_nudge` | `./prompts/recovery/token_budget_nudge.md` | Token budget warning |

Note: Prompt files have been moved to `src/prompts/`. All paths in `config/config.json` must use `./src/prompts/...` format (as shown in `config.json.example`).

MCP config in `config/mcp.json`: `{"mcpServers": {"name": {"type": "stdio|http", "command": "...", "args": []}}}`

## Tool System

### External Tools (src/tools/implementations/)

| Tool | Description |
|------|-------------|
| `read_file` | Read files (text/image/PDF/notebook). Offset/limit for text, pages for PDF |
| `write_file` | Write files (UTF-8, path safety) |
| `shell` | Execute PowerShell (alias resolution, .ps1 for complex scripts) |
| `grep` | Regex search (content/files/count modes, context, type filter) |
| `glob` | Pattern matching (max 50 results) |
| `edit` | String replacement (exact match, replace_all, quote normalization) |
| `sleep` | Built-in: pause autonomous operation |
| `memory` | Built-in: save/load/list/search cross-session persistent memories |

Key interfaces: `BaseTool` (ABC), `ToolResult` (success/content/error/metadata), `ExternalTool` (JSON stdin/stdout I/O, stderr overrides success). Timeout parameter is in seconds. Tools defined in `config/tools.json`.

### Config API

`Config` singleton provides encapsulated access methods:
- `set_model(model_name)`: Set model name (thread-safe)
- `to_dict()`: Return deep copy of config dict (safe for display)

## MCP Protocol

JSON-RPC 2.0: `initialize`, `tools/list`, `tools/call`. Key classes: `MCPManager` (lifecycle, routing), `ToolIndex` (O(1) lookup).

## Agent Loop

- **Project context**: Injects CLAUDE.md (first 3000 chars), MEMORY.md index (persistent memories), date, `git status --short`
- **Error tracking**: `MAX_CONSECUTIVE_ERRORS = 3`; context-too-long → full compact; model failure → fallback
- **Concurrent execution**: Read-only tools parallel (`ThreadPoolExecutor`); write tools serial
- **Stop hooks**: `register_stop_hook(callback)` — run after tool rounds
- **Interruptible sleep**: Both `Agent._interruptible_sleep()` and `LLMClient._interruptible_sleep()` check `stop_event` every 0.2s, raising `AgentCancelledError` / `InterruptedError` for fast Ctrl+C cancellation during retries

## Memory System

Two independent subsystems sharing `memory/` directory:

**Session Memory** (`Memory` singleton): In-RAM conversation history with session save/load to `memory/history/`. `CompactEngine` three-layer compression:
- **Level 1 (Micro)**: Clear old tool results (streak ≥ 3 or gap ≥ 5min)
- **Level 2 (Auto)**: LLM summary (usage ≥ 85%)
- **Level 3 (Full)**: Save session & reset (usage ≥ 95%)

**Persistent Memory** (`PersistentMemory` singleton): Cross-session file-based memory in `memory/*.md` with YAML frontmatter. Dual scope: global (`config.persistent_memory_global_dir`) + project (`memory/`). Four types: `user`, `feedback`, `project`, `reference`. MEMORY.md index auto-generated per scope. Injected into project context at conversation start. LLM-invokable via `memory` tool (save/load/list/search).

## Slash Commands

`/help`, `/clear`, `/model [name]`, `/config`, `/history`, `/save`/`/load [id]`, `/memory [count]`, `/remember [name]`, `/forget <name>`, `/compact`, `/mcp`, `/tools`, `/system`, `/version`, `/skills`, `/exit`

## Skill System

Skills are `SKILL.md` files with YAML frontmatter:

```yaml
---
name: skill-name
description: Description
allowed-tools: [read_file, grep, shell]
when_to_use: "Use when..."
argument-hint: "[args]"
arguments: [arg-name]
user-invocable: true
context: inline
model: (reserved)
effort: (reserved)
paths: (reserved)
---
```

Body uses `$arg-name` for substitution. `SkillTool` makes skills LLM-invokable via `invoke_skill`.

## TUI Layout

```
┌─────────────────────────────────────┐
│         Output Area                  │
│  Dark blue background (#1a1a2e)     │
├─────────────────────────────────────┤
│  > [Input (2 rows, multiline)]      │
├─────────────────────────────────────┤
│               [████░░░░] 72%  ⬆⬇∫  │
└─────────────────────────────────────┘
```

Context bar: green (<50%), yellow (50-84%), orange (85-94%), red bold (≥95%)

Shortcuts: `Enter` send, `Ctrl+J` newline, `Up/Down` history, `PageUp/PageDown` large scroll, `Ctrl+Up/Ctrl+Down` single line scroll, `Home/End` jump, `Ctrl+C` copy/cancel, `Ctrl+V` paste, `Ctrl+Q` exit, `Ctrl+L` clear, `Tab` complete

## Key Design Decisions

1. **Single config**: `config.json` + `config/mcp.json`
2. **Relative paths**: All paths relative to project root
3. **MCP protocol**: JSON-RPC 2.0 for tool integration
4. **Styled streaming**: BufferControl + OutputLexer for rich output
5. **Concurrent tools**: Read-only parallel, write serial
6. **Model degradation**: Fallback → auto-restore on failure
7. **Schema validation**: Before tool execution
8. **Tick-based wake-up**: Proactive autonomous operation
9. **Cron expressions**: Standard format via croniter
10. **Error classification**: Auto-recovery with configurable retries
11. **Network monitoring**: State-aware retry logic
12. **Skill system**: SKILL.md + YAML frontmatter
13. **Interruptible cancellation**: SIGINT handler + interruptible sleep for fast Ctrl+C response
14. **Cross-session memory**: Persistent file-based memory with dual scope (global + project), MEMORY.md index injection, LLM-invokable memory tool
15. **Encapsulated config**: Config class exposes `set_model()` and `to_dict()` methods; external code must not access `_config` directly
16. **Integer token counting**: `count_tokens()` returns `int` (rounded) to avoid floating-point accumulation errors
17. **Thread-safe MCP**: `ToolIndex` and `MCPManager` use locks for concurrent access safety
18. **User-friendly errors**: Error messages shown to users never expose Python class names; details go to logs only

## Running

```bash
pip install -r requirements.txt
python -m src
```
