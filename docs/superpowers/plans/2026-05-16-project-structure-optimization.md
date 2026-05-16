# Project Structure Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure the project directory for better readability and maintainability

**Architecture:** Move files to new locations following functional domain organization, update all import paths and configuration references, verify functionality at each step

**Tech Stack:** Python, file system operations, git

---

## File Structure

Before defining tasks, here's the target file structure:

```
AGImyCLI/
├── src/
│   ├── core/
│   │   ├── agent.py
│   │   ├── config.py
│   │   ├── main.py
│   │   └── tui.py
│   ├── llm/
│   │   └── client.py
│   ├── tools/
│   │   ├── base.py
│   │   ├── registry.py
│   │   ├── loader.py
│   │   ├── external.py
│   │   ├── sleep.py
│   │   ├── memory_tool.py
│   │   └── implementations/
│   │       ├── read_file/
│   │       ├── write_file/
│   │       ├── shell/
│   │       ├── grep/
│   │       ├── glob/
│   │       └── edit/
│   ├── commands/
│   │   ├── registry.py
│   │   ├── core.py
│   │   ├── completer.py
│   │   └── utils.py
│   ├── skills/
│   │   ├── definition.py
│   │   ├── loader.py
│   │   ├── registry.py
│   │   ├── commands.py
│   │   ├── tool.py
│   │   └── definitions/
│   │       └── code-review/
│   │           └── SKILL.md
│   ├── cron/
│   │   └── scheduler.py
│   ├── mcp/
│   │   ├── protocol.py
│   │   ├── manager.py
│   │   ├── base.py
│   │   ├── client.py
│   │   ├── http_client.py
│   │   ├── stdio_client.py
│   │   ├── index.py
│   │   └── persistence.py
│   ├── memory/
│   │   ├── memory.py
│   │   └── persistent_memory.py
│   ├── prompts/
│   │   ├── system/
│   │   ├── service/
│   │   ├── recovery/
│   │   └── autonomous/
│   └── utils/
│       ├── path.py
│       ├── token_counter.py
│       ├── logging.py
│       └── tool_result_persistence.py
├── config/
│   ├── config.json
│   ├── mcp.json
│   ├── mcp.json.example
│   ├── tools.json
│   └── scheduled_tasks.json
├── data/
│   ├── memory/
│   ├── logs/
│   └── mcpdata/
├── docs/
│   └── superpowers/
│       └── specs/
├── .gitignore
├── LICENSE
├── README.md
├── requirements.txt
└── config.json.example
```

---

## Task 1: Create Backup and New Directory Structure

**Files:**
- Create: `src/core/`, `src/memory/`, `src/prompts/`, `src/tools/implementations/`, `src/skills/definitions/`, `data/`

- [ ] **Step 1: Create backup of current state**

```bash
cd "E:\claude code\AGImyCLI"
git stash
```

- [ ] **Step 2: Create new directory structure**

```bash
mkdir -p src/core
mkdir -p src/memory
mkdir -p src/prompts
mkdir -p src/tools/implementations
mkdir -p src/skills/definitions
mkdir -p data/memory
mkdir -p data/logs
mkdir -p data/mcpdata
```

- [ ] **Step 3: Verify directory structure**

```bash
ls -la src/
ls -la data/
```

Expected: New directories exist

- [ ] **Step 4: Commit directory structure**

```bash
git add src/core/ src/memory/ src/prompts/ src/tools/implementations/ src/skills/definitions/ data/
git commit -m "feat: create new directory structure for project reorganization"
```

---

## Task 2: Move Core Files to src/core/

**Files:**
- Move: `src/agent.py` → `src/core/agent.py`
- Move: `src/config.py` → `src/core/config.py`
- Move: `src/main.py` → `src/core/main.py`
- Move: `src/tui.py` → `src/core/tui.py`

- [ ] **Step 1: Move agent.py**

```bash
mv src/agent.py src/core/agent.py
```

- [ ] **Step 2: Move config.py**

```bash
mv src/config.py src/core/config.py
```

- [ ] **Step 3: Move main.py**

```bash
mv src/main.py src/core/main.py
```

- [ ] **Step 4: Move tui.py**

```bash
mv src/tui.py src/core/tui.py
```

- [ ] **Step 5: Verify moves**

```bash
ls -la src/core/
```

Expected: agent.py, config.py, main.py, tui.py in src/core/

- [ ] **Step 6: Commit moves**

```bash
git add src/core/
git commit -m "feat: move core files to src/core/"
```

---

## Task 3: Move Memory Files to src/memory/

**Files:**
- Move: `src/memory.py` → `src/memory/memory.py`
- Move: `src/persistent_memory.py` → `src/memory/persistent_memory.py`

- [ ] **Step 1: Move memory.py**

```bash
mv src/memory.py src/memory/memory.py
```

- [ ] **Step 2: Move persistent_memory.py**

```bash
mv src/persistent_memory.py src/memory/persistent_memory.py
```

- [ ] **Step 3: Verify moves**

```bash
ls -la src/memory/
```

Expected: memory.py, persistent_memory.py in src/memory/

- [ ] **Step 4: Commit moves**

```bash
git add src/memory/
git commit -m "feat: move memory files to src/memory/"
```

---

## Task 4: Move External Tools to src/tools/implementations/

**Files:**
- Move: `external_tools/read_file/` → `src/tools/implementations/read_file/`
- Move: `external_tools/write_file/` → `src/tools/implementations/write_file/`
- Move: `external_tools/grep/` → `src/tools/implementations/grep/`
- Move: `external_tools/glob/` → `src/tools/implementations/glob/`
- Move: `external_tools/edit/` → `src/tools/implementations/edit/`
- Move: `external_tools/winshell/` → `src/tools/implementations/winshell/`

- [ ] **Step 1: Move read_file**

```bash
mv external_tools/read_file/ src/tools/implementations/read_file/
```

- [ ] **Step 2: Move write_file**

```bash
mv external_tools/write_file/ src/tools/implementations/write_file/
```

- [ ] **Step 3: Move grep**

```bash
mv external_tools/grep/ src/tools/implementations/grep/
```

- [ ] **Step 4: Move glob**

```bash
mv external_tools/glob/ src/tools/implementations/glob/
```

- [ ] **Step 5: Move edit**

```bash
mv external_tools/edit/ src/tools/implementations/edit/
```

- [ ] **Step 6: Move winshell**

```bash
mv external_tools/winshell/ src/tools/implementations/winshell/
```

- [ ] **Step 7: Verify moves**

```bash
ls -la src/tools/implementations/
```

Expected: All tool directories moved

- [ ] **Step 8: Remove empty external_tools directory**

```bash
rmdir external_tools
```

- [ ] **Step 9: Commit moves**

```bash
git add src/tools/implementations/
git commit -m "feat: move external tools to src/tools/implementations/"
```

---

## Task 5: Move Prompts to src/prompts/

**Files:**
- Move: `prompts/system/` → `src/prompts/system/`
- Move: `prompts/service/` → `src/prompts/service/`
- Move: `prompts/recovery/` → `src/prompts/recovery/`
- Move: `prompts/autonomous/` → `src/prompts/autonomous/`

- [ ] **Step 1: Move system prompts**

```bash
mv prompts/system/ src/prompts/system/
```

- [ ] **Step 2: Move service prompts**

```bash
mv prompts/service/ src/prompts/service/
```

- [ ] **Step 3: Move recovery prompts**

```bash
mv prompts/recovery/ src/prompts/recovery/
```

- [ ] **Step 4: Move autonomous prompts**

```bash
mv prompts/autonomous/ src/prompts/autonomous/
```

- [ ] **Step 5: Verify moves**

```bash
ls -la src/prompts/
```

Expected: All prompt directories moved

- [ ] **Step 6: Remove empty prompts directory**

```bash
rmdir prompts
```

- [ ] **Step 7: Commit moves**

```bash
git add src/prompts/
git commit -m "feat: move prompts to src/prompts/"
```

---

## Task 6: Move Skill Definitions to src/skills/definitions/

**Files:**
- Move: `skills/code-review/` → `src/skills/definitions/code-review/`

- [ ] **Step 1: Move skill definitions**

```bash
mv skills/ src/skills/definitions/
```

- [ ] **Step 2: Verify moves**

```bash
ls -la src/skills/definitions/
```

Expected: code-review directory with SKILL.md

- [ ] **Step 3: Commit moves**

```bash
git add src/skills/definitions/
git commit -m "feat: move skill definitions to src/skills/definitions/"
```

---

## Task 7: Move Runtime Data to data/

**Files:**
- Move: `memory/` → `data/memory/`
- Move: `logs/` → `data/logs/`
- Move: `mcpdata/` → `data/mcpdata/`

- [ ] **Step 1: Move memory data**

```bash
mv memory/ data/memory/
```

- [ ] **Step 2: Move logs**

```bash
mv logs/ data/logs/
```

- [ ] **Step 3: Move mcpdata**

```bash
mv mcpdata/ data/mcpdata/
```

- [ ] **Step 4: Verify moves**

```bash
ls -la data/
```

Expected: All runtime data directories moved

- [ ] **Step 5: Commit moves**

```bash
git add data/
git commit -m "feat: move runtime data to data/"
```

---

## Task 8: Move Configuration Files

**Files:**
- Move: `config.json` → `config/config.json`
- Move: `config/mcp.json.example` → `config/mcp.json.example` (already in place)
- Keep: `config.json.example` in root

- [ ] **Step 1: Move config.json**

```bash
mv config.json config/config.json
```

- [ ] **Step 2: Verify move**

```bash
ls -la config/
```

Expected: config.json in config/ directory

- [ ] **Step 3: Commit move**

```bash
git add config/config.json
git commit -m "feat: move config.json to config directory"
```

---

## Task 9: Update Import Paths in src/core/

**Files:**
- Modify: `src/core/agent.py`
- Modify: `src/core/config.py`
- Modify: `src/core/main.py`
- Modify: `src/core/tui.py`

- [ ] **Step 1: Update imports in agent.py**

Read `src/core/agent.py` and update all imports. Example changes:

```python
# Old imports
from src.config import Config
from src.memory import Memory
from src.persistent_memory import PersistentMemory

# New imports
from src.core.config import Config
from src.memory.memory import Memory
from src.memory.persistent_memory import PersistentMemory
```

- [ ] **Step 2: Update imports in config.py**

Read `src/core/config.py` and update all imports. Example changes:

```python
# Old imports
from src.utils.path import get_project_root

# New imports
from src.utils.path import get_project_root
```

(Note: utils imports don't change since utils stays in src/)

- [ ] **Step 3: Update imports in main.py**

Read `src/core/main.py` and update all imports. Example changes:

```python
# Old imports
from src.agent import Agent
from src.config import Config
from src.tui import SimpleTUI

# New imports
from src.core.agent import Agent
from src.core.config import Config
from src.core.tui import SimpleTUI
```

- [ ] **Step 4: Update imports in tui.py**

Read `src/core/tui.py` and update all imports. Example changes:

```python
# Old imports
from src.config import Config

# New imports
from src.core.config import Config
```

- [ ] **Step 5: Test imports**

```bash
cd "E:\claude code\AGImyCLI"
python -c "from src.core.main import main; print('Main imports OK')"
```

Expected: No import errors

- [ ] **Step 6: Commit import updates**

```bash
git add src/core/
git commit -m "fix: update import paths in src/core/"
```

---

## Task 10: Update Import Paths in src/memory/

**Files:**
- Modify: `src/memory/memory.py`
- Modify: `src/memory/persistent_memory.py`

- [ ] **Step 1: Update imports in memory.py**

Read `src/memory/memory.py` and update all imports. Example changes:

```python
# Old imports
from src.config import Config

# New imports
from src.core.config import Config
```

- [ ] **Step 2: Update imports in persistent_memory.py**

Read `src/memory/persistent_memory.py` and update all imports. Example changes:

```python
# Old imports
from src.config import Config

# New imports
from src.core.config import Config
```

- [ ] **Step 3: Test imports**

```bash
cd "E:\claude code\AGImyCLI"
python -c "from src.memory.memory import Memory; print('Memory imports OK')"
python -c "from src.memory.persistent_memory import PersistentMemory; print('PersistentMemory imports OK')"
```

Expected: No import errors

- [ ] **Step 4: Commit import updates**

```bash
git add src/memory/
git commit -m "fix: update import paths in src/memory/"
```

---

## Task 11: Update Import Paths in src/tools/

**Files:**
- Modify: `src/tools/external.py`
- Modify: `src/tools/loader.py`
- Modify: `src/tools/registry.py`

- [ ] **Step 1: Update imports in external.py**

Read `src/tools/external.py` and update all imports. Example changes:

```python
# Old imports
from src.config import Config

# New imports
from src.core.config import Config
```

Also update tool implementation paths:

```python
# Old paths
tool_dir = Path("external_tools") / tool_name

# New paths
tool_dir = Path("src/tools/implementations") / tool_name
```

- [ ] **Step 2: Update imports in loader.py**

Read `src/tools/loader.py` and update all imports. Example changes:

```python
# Old imports
from src.config import Config

# New imports
from src.core.config import Config
```

- [ ] **Step 3: Update imports in registry.py**

Read `src/tools/registry.py` and update all imports. Example changes:

```python
# Old imports
from src.config import Config

# New imports
from src.core.config import Config
```

- [ ] **Step 4: Test imports**

```bash
cd "E:\claude code\AGImyCLI"
python -c "from src.tools.external import ExternalTool; print('Tools imports OK')"
```

Expected: No import errors

- [ ] **Step 5: Commit import updates**

```bash
git add src/tools/
git commit -m "fix: update import paths in src/tools/"
```

---

## Task 12: Update Import Paths in src/commands/

**Files:**
- Modify: `src/commands/core.py`
- Modify: `src/commands/registry.py`
- Modify: `src/commands/completer.py`
- Modify: `src/commands/utils.py`

- [ ] **Step 1: Update imports in core.py**

Read `src/commands/core.py` and update all imports. Example changes:

```python
# Old imports
from src.config import Config
from src.memory import Memory

# New imports
from src.core.config import Config
from src.memory.memory import Memory
```

- [ ] **Step 2: Update imports in registry.py**

Read `src/commands/registry.py` and update all imports. Example changes:

```python
# Old imports
from src.config import Config

# New imports
from src.core.config import Config
```

- [ ] **Step 3: Update imports in completer.py**

Read `src/commands/completer.py` and update all imports. Example changes:

```python
# Old imports
from src.config import Config

# New imports
from src.core.config import Config
```

- [ ] **Step 4: Update imports in utils.py**

Read `src/commands/utils.py` and update all imports. Example changes:

```python
# Old imports
from src.config import Config

# New imports
from src.core.config import Config
```

- [ ] **Step 5: Test imports**

```bash
cd "E:\claude code\AGImyCLI"
python -c "from src.commands.core import CommandRegistry; print('Commands imports OK')"
```

Expected: No import errors

- [ ] **Step 6: Commit import updates**

```bash
git add src/commands/
git commit -m "fix: update import paths in src/commands/"
```

---

## Task 13: Update Import Paths in src/skills/

**Files:**
- Modify: `src/skills/loader.py`
- Modify: `src/skills/registry.py`
- Modify: `src/skills/commands.py`
- Modify: `src/skills/tool.py`

- [ ] **Step 1: Update imports in loader.py**

Read `src/skills/loader.py` and update all imports. Example changes:

```python
# Old imports
from src.config import Config

# New imports
from src.core.config import Config
```

Also update skill definition paths:

```python
# Old paths
skills_dir = Path("skills")

# New paths
skills_dir = Path("src/skills/definitions")
```

- [ ] **Step 2: Update imports in registry.py**

Read `src/skills/registry.py` and update all imports. Example changes:

```python
# Old imports
from src.config import Config

# New imports
from src.core.config import Config
```

- [ ] **Step 3: Update imports in commands.py**

Read `src/skills/commands.py` and update all imports. Example changes:

```python
# Old imports
from src.config import Config

# New imports
from src.core.config import Config
```

- [ ] **Step 4: Update imports in tool.py**

Read `src/skills/tool.py` and update all imports. Example changes:

```python
# Old imports
from src.config import Config

# New imports
from src.core.config import Config
```

- [ ] **Step 5: Test imports**

```bash
cd "E:\claude code\AGImyCLI"
python -c "from src.skills.loader import SkillLoader; print('Skills imports OK')"
```

Expected: No import errors

- [ ] **Step 6: Commit import updates**

```bash
git add src/skills/
git commit -m "fix: update import paths in src/skills/"
```

---

## Task 14: Update Import Paths in src/mcp/

**Files:**
- Modify: `src/mcp/manager.py`
- Modify: `src/mcp/client.py`
- Modify: `src/mcp/http_client.py`
- Modify: `src/mcp/stdio_client.py`
- Modify: `src/mcp/persistence.py`

- [ ] **Step 1: Update imports in manager.py**

Read `src/mcp/manager.py` and update all imports. Example changes:

```python
# Old imports
from src.config import Config

# New imports
from src.core.config import Config
```

- [ ] **Step 2: Update imports in client.py**

Read `src/mcp/client.py` and update all imports. Example changes:

```python
# Old imports
from src.config import Config

# New imports
from src.core.config import Config
```

- [ ] **Step 3: Update imports in http_client.py**

Read `src/mcp/http_client.py` and update all imports. Example changes:

```python
# Old imports
from src.config import Config

# New imports
from src.core.config import Config
```

- [ ] **Step 4: Update imports in stdio_client.py**

Read `src/mcp/stdio_client.py` and update all imports. Example changes:

```python
# Old imports
from src.config import Config

# New imports
from src.core.config import Config
```

- [ ] **Step 5: Update imports in persistence.py**

Read `src/mcp/persistence.py` and update all imports. Example changes:

```python
# Old imports
from src.config import Config

# New imports
from src.core.config import Config
```

- [ ] **Step 6: Test imports**

```bash
cd "E:\claude code\AGImyCLI"
python -c "from src.mcp.manager import MCPManager; print('MCP imports OK')"
```

Expected: No import errors

- [ ] **Step 7: Commit import updates**

```bash
git add src/mcp/
git commit -m "fix: update import paths in src/mcp/"
```

---

## Task 15: Update Configuration Path References

**Files:**
- Modify: `src/core/config.py`
- Modify: `src/tools/loader.py`
- Modify: `src/skills/loader.py`
- Modify: `src/mcp/manager.py`

- [ ] **Step 1: Update config.py path references**

Read `src/core/config.py` and update configuration file paths:

```python
# Old paths
config_path = "config.json"

# New paths
config_path = "config/config.json"
```

- [ ] **Step 2: Update tools loader path references**

Read `src/tools/loader.py` and update tool configuration path:

```python
# Old paths
tools_config_path = "config/tools.json"

# New paths
tools_config_path = "config/tools.json"
```

(Note: tools.json is already in config/ directory, so this may not need changing)

- [ ] **Step 3: Update skills loader path references**

Read `src/skills/loader.py` and update skill definition paths:

```python
# Old paths
skills_dirs = ["skills"]

# New paths
skills_dirs = ["src/skills/definitions"]
```

- [ ] **Step 4: Update MCP manager path references**

Read `src/mcp/manager.py` and update MCP configuration path:

```python
# Old paths
mcp_config_path = "config/mcp.json"

# New paths
mcp_config_path = "config/mcp.json"
```

(Note: mcp.json is already in config/ directory, so this may not need changing)

- [ ] **Step 5: Test configuration loading**

```bash
cd "E:\claude code\AGImyCLI"
python -c "from src.core.config import Config; c = Config(); print('Config loads OK')"
```

Expected: No errors loading configuration

- [ ] **Step 6: Commit configuration updates**

```bash
git add src/core/config.py src/tools/loader.py src/skills/loader.py src/mcp/manager.py
git commit -m "fix: update configuration path references"
```

---

## Task 16: Update Documentation

**Files:**
- Modify: `CLAUDE.md`
- Modify: `README.md`
- Modify: `.gitignore`

- [ ] **Step 1: Update CLAUDE.md project structure**

Read `CLAUDE.md` and update the project structure section to reflect the new layout.

- [ ] **Step 2: Update README.md**

Read `README.md` and update any path references to reflect the new structure.

- [ ] **Step 3: Update .gitignore**

Read `.gitignore` and update any path patterns that may have changed.

- [ ] **Step 4: Commit documentation updates**

```bash
git add CLAUDE.md README.md .gitignore
git commit -m "docs: update documentation for new project structure"
```

---

## Task 17: Clean Up Redundant Files

**Files:**
- Delete: `AGImyCLI.7z`
- Delete: `README_zh.md` (if content merged into README.md)

- [ ] **Step 1: Delete AGImyCLI.7z**

```bash
rm AGImyCLI.7z
```

- [ ] **Step 2: Check README_zh.md content**

Read `README_zh.md` to see if content is already in README.md.

- [ ] **Step 3: Merge content if needed**

If README_zh.md has unique content, merge it into README.md.

- [ ] **Step 4: Delete README_zh.md**

```bash
rm README_zh.md
```

- [ ] **Step 5: Commit cleanup**

```bash
git add .
git commit -m "chore: remove redundant files"
```

---

## Task 18: Final Verification

**Files:**
- Verify: All files in correct locations
- Verify: All imports work
- Verify: Application starts correctly

- [ ] **Step 1: Verify directory structure**

```bash
cd "E:\claude code\AGImyCLI"
ls -la src/
ls -la data/
ls -la config/
```

Expected: All directories and files in correct locations

- [ ] **Step 2: Test all imports**

```bash
python -c "from src.core.main import main; print('Main OK')"
python -c "from src.core.agent import Agent; print('Agent OK')"
python -c "from src.core.config import Config; print('Config OK')"
python -c "from src.memory.memory import Memory; print('Memory OK')"
python -c "from src.memory.persistent_memory import PersistentMemory; print('PersistentMemory OK')"
python -c "from src.tools.external import ExternalTool; print('ExternalTool OK')"
python -c "from src.skills.loader import SkillLoader; print('SkillLoader OK')"
python -c "from src.mcp.manager import MCPManager; print('MCPManager OK')"
```

Expected: All imports work without errors

- [ ] **Step 3: Test application startup**

```bash
cd "E:\claude code\AGImyCLI"
python -m src.core.main --version
```

Expected: Application starts and shows version

- [ ] **Step 4: Final commit**

```bash
git add .
git commit -m "feat: complete project structure optimization"
```

---

## Summary

This plan breaks the project restructuring into 18 tasks with a total of approximately 80 steps. Each task is self-contained and produces a working state. The TDD approach ensures that each change is verified before moving to the next step.

**Key points:**
1. Backup before starting
2. Move files in logical groups
3. Update imports after each move
4. Test after each change
5. Commit frequently with clear messages
6. Update documentation last
7. Clean up redundant files at the end

**Estimated time:** 5-8 hours depending on experience with the codebase
