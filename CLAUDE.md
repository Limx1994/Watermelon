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
├── main.py              # Entry point
├── tui.py               # TUI (SimpleTUI, BufferControl + OutputLexer)
├── agent.py             # Agent loop (concurrent tools, stop hooks)
├── config.py            # Config singleton
├── memory.py            # Memory + CompactEngine
├── llm/client.py        # LLM client (streaming, model switching, interruptible sleep)
├── tools/               # base.py, registry.py, loader.py, external.py, sleep.py
├── commands/            # registry.py, core.py, completer.py, utils.py
├── skills/              # definition.py, loader.py, registry.py, commands.py, tool.py
├── cron/scheduler.py    # CronScheduler
├── mcp/                 # protocol.py, manager.py, index.py, persistence.py, clients
└── utils/               # path.py, token_counter.py, logging.py
external_tools/          # Compiled .exe tools (read_file, write_file, shell, grep, glob, edit)
skills/                  # SKILL.md definitions
prompts/                 # Prompt templates (.md) — system/, service/, recovery/, autonomous/
config/                  # mcp.json, tools.json
config.json              # App configuration
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
| | `context_window` | `128` | Max context (K tokens; code fallback: 64K) |
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
| | `compact_prompt` | `./prompts/service/compact_prompt.md` | Compression summary prompt |
| | `summary_system` | `./prompts/service/summary_system.md` | Summary system prompt |
| | `summary_template` | `./prompts/service/summary_template.md` | Summary template |
| | `max_tokens_recovery` | `./prompts/recovery/max_tokens_recovery.md` | Output truncation recovery |
| | `context_too_long` | `./prompts/recovery/context_too_long.md` | Context overflow recovery |
| | `token_budget_nudge` | `./prompts/recovery/token_budget_nudge.md` | Token budget warning |

MCP config in `config/mcp.json`: `{"mcpServers": {"name": {"type": "stdio|http", "command": "...", "args": []}}}`

## Tool System

### External Tools (external_tools/)

| Tool | Description |
|------|-------------|
| `read_file` | Read files (text/image/PDF/notebook). Offset/limit for text, pages for PDF |
| `write_file` | Write files (UTF-8, path safety) |
| `shell` | Execute PowerShell (alias resolution, .ps1 for complex scripts) |
| `grep` | Regex search (content/files/count modes, context, type filter) |
| `glob` | Pattern matching (max 50 results) |
| `edit` | String replacement (exact match, replace_all, quote normalization) |
| `sleep` | Built-in: pause autonomous operation |

Key interfaces: `BaseTool` (ABC), `ToolResult` (success/content/error/metadata), `ExternalTool` (JSON stdin/stdout I/O, stderr overrides success). Tools defined in `config/tools.json`.

## MCP Protocol

JSON-RPC 2.0: `initialize`, `tools/list`, `tools/call`. Key classes: `MCPManager` (lifecycle, routing), `ToolIndex` (O(1) lookup).

## Agent Loop

- **Project context**: Injects CLAUDE.md (first 3000 chars), date, `git status --short`
- **Error tracking**: `MAX_CONSECUTIVE_ERRORS = 3`; context-too-long → full compact; model failure → fallback
- **Concurrent execution**: Read-only tools parallel (`ThreadPoolExecutor`); write tools serial
- **Stop hooks**: `register_stop_hook(callback)` — run after tool rounds
- **Interruptible sleep**: Both `Agent._interruptible_sleep()` and `LLMClient._interruptible_sleep()` check `stop_event` every 0.2s, raising `AgentCancelledError` / `InterruptedError` for fast Ctrl+C cancellation during retries

## Memory System

`Memory` singleton (add/get/clear/session management). `CompactEngine` three-layer compression:
- **Level 1 (Micro)**: Clear old tool results (streak ≥ 3 or gap ≥ 5min)
- **Level 2 (Auto)**: LLM summary (usage ≥ 85%)
- **Level 3 (Full)**: Save session & reset (usage ≥ 95%)

## Slash Commands

`/help`, `/clear`, `/model [name]`, `/config`, `/history`, `/save`/`/load [id]`, `/memory [count]`, `/compact`, `/mcp`, `/tools`, `/system`, `/version`, `/skills`

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

## Running

```bash
pip install -r requirements.txt
python -m src.main
```
