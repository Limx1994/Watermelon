# 项目目录结构重构设计文档

**日期**: 2026-05-16
**作者**: Claude Code
**状态**: 待审核

---

## 1. 背景与目标

### 1.1 背景
当前项目目录结构存在以下问题：
- 根目录文件过多，结构不清晰
- 配置文件分散在根目录和 `config/` 目录
- 模块划分不合理，部分文件职责不清
- 功能模块分散，相关文件不在同一目录下

### 1.2 目标
重构项目目录结构，提高代码可读性和可维护性，遵循以下原则：
- 职责清晰：每个目录有明确的功能定义
- 易于理解：新开发者能快速定位相关代码
- 便于扩展：新增功能有明确的放置位置
- 减少认知负担：不需要在多个目录间跳转查找相关文件

---

## 2. 当前结构分析

### 2.1 当前目录结构
```
AGImyCLI/
├── src/                          # 核心代码
│   ├── agent.py
│   ├── config.py
│   ├── main.py
│   ├── tui.py
│   ├── memory.py
│   ├── persistent_memory.py
│   ├── llm/
│   ├── tools/
│   ├── commands/
│   ├── skills/
│   ├── cron/
│   ├── mcp/
│   └── utils/
├── config/                       # 配置文件
│   ├── mcp.json
│   ├── tools.json
│   └── scheduled_tasks.json
├── external_tools/               # 外部工具
├── prompts/                      # 提示词模板
├── skills/                       # 技能定义
├── memory/                       # 记忆存储
├── logs/                         # 日志
├── mcpdata/                      # MCP数据
├── config.json                   # 主配置（根目录）
├── CLAUDE.md
├── README.md
├── README_zh.md
├── requirements.txt
├── AGImyCLI.7z
└── config.json.example
```

### 2.2 问题点
1. **根目录文件过多**：`config.json`、`CLAUDE.md`、`README.md`、`README_zh.md`、`requirements.txt`、`AGImyCLI.7z` 都在根目录
2. **配置文件分散**：`config.json` 在根目录，`config/mcp.json` 在子目录
3. **模块划分不合理**：`external_tools/` 实际上是工具的实现代码，应该属于 `src/tools/` 的一部分
4. **功能模块分散**：`prompts/`、`skills/`、`external_tools/` 都在根目录，但实际是项目的一部分

---

## 3. 重构方案

### 3.1 目标目录结构
```
AGImyCLI/
├── src/                          # 核心代码
│   ├── core/                     # 核心模块
│   │   ├── agent.py              # Agent循环
│   │   ├── config.py             # 配置管理
│   │   ├── main.py               # 入口点
│   │   └── tui.py                # TUI界面
│   ├── llm/                      # LLM客户端
│   │   └── client.py
│   ├── tools/                    # 工具系统
│   │   ├── base.py
│   │   ├── registry.py
│   │   ├── loader.py
│   │   ├── external.py
│   │   ├── sleep.py
│   │   ├── memory_tool.py
│   │   └── implementations/      # 工具实现
│   │       ├── read_file/
│   │       ├── write_file/
│   │       ├── shell/
│   │       ├── grep/
│   │       ├── glob/
│   │       └── edit/
│   ├── commands/                 # 命令系统
│   │   ├── registry.py
│   │   ├── core.py
│   │   ├── completer.py
│   │   └── utils.py
│   ├── skills/                   # 技能系统
│   │   ├── definition.py
│   │   ├── loader.py
│   │   ├── registry.py
│   │   ├── commands.py
│   │   ├── tool.py
│   │   └── definitions/          # 技能定义文件
│   │       └── code-review/
│   │           └── SKILL.md
│   ├── cron/                     # 定时任务
│   │   └── scheduler.py
│   ├── mcp/                      # MCP协议
│   │   ├── protocol.py
│   │   ├── manager.py
│   │   ├── base.py
│   │   ├── client.py
│   │   ├── http_client.py
│   │   ├── stdio_client.py
│   │   ├── index.py
│   │   └── persistence.py
│   ├── memory/                   # 记忆系统
│   │   ├── memory.py             # 会话记忆
│   │   └── persistent_memory.py  # 持久化记忆
│   ├── prompts/                  # 提示词模板
│   │   ├── system/
│   │   ├── service/
│   │   ├── recovery/
│   │   └── autonomous/
│   └── utils/                    # 工具函数
│       ├── path.py
│       ├── token_counter.py
│       ├── logging.py
│       └── tool_result_persistence.py
├── config/                       # 配置文件
│   ├── config.json               # 主配置
│   ├── mcp.json                  # MCP配置
│   ├── mcp.json.example          # MCP配置示例
│   ├── tools.json                # 工具配置
│   └── scheduled_tasks.json      # 定时任务配置
├── data/                         # 运行时数据
│   ├── memory/                   # 记忆存储
│   ├── logs/                     # 日志文件
│   └── mcpdata/                  # MCP数据
├── docs/                         # 文档
│   └── superpowers/
│       └── specs/
├── .gitignore
├── LICENSE
├── README.md
├── requirements.txt
└── config.json.example           # 配置示例（根目录保留）
```

### 3.2 主要变化
1. **新增 `src/core/`**：将 `agent.py`、`config.py`、`main.py`、`tui.py` 移入
2. **新增 `src/tools/implementations/`**：将 `external_tools/` 移入
3. **新增 `src/memory/`**：将 `memory.py`、`persistent_memory.py` 移入
4. **新增 `src/prompts/`**：将 `prompts/` 移入
5. **新增 `src/skills/definitions/`**：将 `skills/` 的定义文件移入
6. **统一配置文件**：将 `config.json` 从根目录移入 `config/`，保留 `config.json.example` 在根目录
7. **新增 `data/`**：统一运行时数据（memory、logs、mcpdata）
8. **删除冗余文件**：`AGImyCLI.7z`、`README_zh.md`（合并到 `README.md`）

---

## 4. 迁移策略

### 4.1 迁移步骤
1. **创建新目录结构**
   - 创建 `src/core/`、`src/memory/`、`src/prompts/`、`src/tools/implementations/`、`src/skills/definitions/`、`data/`

2. **移动文件**
   - `src/agent.py` → `src/core/agent.py`
   - `src/config.py` → `src/core/config.py`
   - `src/main.py` → `src/core/main.py`
   - `src/tui.py` → `src/core/tui.py`
   - `src/memory.py` → `src/memory/memory.py`
   - `src/persistent_memory.py` → `src/memory/persistent_memory.py`
   - `external_tools/` → `src/tools/implementations/`
   - `prompts/` → `src/prompts/`
   - `skills/` → `src/skills/definitions/`
   - `memory/` → `data/memory/`
   - `logs/` → `data/logs/`
   - `mcpdata/` → `data/mcpdata/`

3. **更新导入路径**
   - 更新所有Python文件的import语句
   - 更新配置文件中的路径引用

4. **更新配置文件**
   - 将 `config.json` 移入 `config/` 目录
   - 更新代码中读取配置的路径

5. **更新文档**
   - 更新 `CLAUDE.md` 中的项目结构描述
   - 更新 `README.md`

### 4.2 导入路径更新示例
```python
# 旧路径
from src.agent import Agent
from src.config import Config

# 新路径
from src.core.agent import Agent
from src.core.config import Config
```

### 4.3 配置路径更新示例
```python
# 旧路径
config_path = "config.json"

# 新路径
config_path = "config/config.json"
```

---

## 5. 风险分析

### 5.1 主要风险
1. **导入路径变化**：需要更新所有Python文件的import语句，可能遗漏
2. **配置文件路径变化**：需要更新代码中读取配置的路径
3. **外部工具路径变化**：需要更新工具加载器的路径配置
4. **技能定义路径变化**：需要更新技能加载器的路径配置

### 5.2 缓解措施
1. **全面搜索替换**：使用IDE或脚本批量更新导入路径
2. **配置路径统一**：在 `config.py` 中统一管理配置路径
3. **工具路径配置**：在 `tools.json` 中配置工具实现路径
4. **技能路径配置**：在配置中指定技能定义目录

### 5.3 测试验证
1. 运行所有现有测试，确保功能正常
2. 手动测试关键功能：Agent循环、工具执行、技能调用
3. 验证配置文件读取正常
4. 验证记忆系统读写正常

---

## 6. 实施计划

### 6.1 阶段一：准备（1天）
1. 备份当前代码
2. 创建新目录结构
3. 更新 `.gitignore`

### 6.2 阶段二：迁移（2天）
1. 移动文件
2. 更新导入路径
3. 更新配置路径

### 6.3 阶段三：验证（1天）
1. 运行测试
2. 手动验证功能
3. 修复问题

### 6.4 阶段四：文档更新（0.5天）
1. 更新 `CLAUDE.md`
2. 更新 `README.md`
3. 更新 `.gitignore`

### 6.5 阶段五：清理（0.5天）
1. 删除冗余文件
2. 提交代码
3. 验证最终结构

---

## 7. 成功标准

1. **目录结构清晰**：每个目录有明确的功能定义
2. **导入路径正确**：所有Python文件的import语句正确
3. **配置路径正确**：所有配置文件读取正常
4. **功能正常**：所有现有功能正常工作
5. **文档更新**：项目文档与实际结构一致

---

## 8. 后续优化

1. **自动化测试**：添加目录结构检查测试，确保未来修改不会破坏结构
2. **CI/CD集成**：在CI中添加目录结构验证
3. **文档生成**：自动生成目录结构文档

---

**审核人**: 用户
**审核日期**: 2026-05-16
**批准状态**: 待审核
