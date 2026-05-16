"""持久化记忆工具 — LLM 可调用的记忆管理"""

import logging
from typing import Any, Dict

from .base import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class MemoryTool(BaseTool):
    """让 LLM 跨会话保存、读取、列出和搜索持久化记忆。"""

    def __init__(self):
        super().__init__(
            name="memory",
            description=(
                "Save, load, list, or search cross-session memories. "
                "Use 'save' to remember user preferences, feedback, or project info. "
                "Use 'list' to see all memories. Use 'load' to read a specific memory. "
                "Use 'search' to find relevant memories by keyword."
            ),
        )

    def execute(
        self,
        action: str = "list",
        name: str = "",
        content: str = "",
        mem_type: str = "user",
        description: str = "",
        query: str = "",
        scope: str = "",
    ) -> ToolResult:
        from ..persistent_memory import persistent_memory

        logger.info(f"[tool:memory] action={action} name={name} scope={scope}")

        if action == "save":
            save_scope = scope if scope in ("global", "project") else "project"
            return self._do_save(
                persistent_memory, name, content, mem_type, description, save_scope
            )
        elif action == "load":
            return self._do_load(persistent_memory, name, scope)
        elif action == "list":
            return self._do_list(persistent_memory, scope)
        elif action == "search":
            return self._do_search(persistent_memory, query, scope)
        elif action == "delete":
            return self._do_delete(persistent_memory, name, scope)
        else:
            return ToolResult(
                success=False,
                content="",
                error=f"Invalid action: {action}. Valid: save, load, list, search, delete",
            )

    def _do_save(
        self,
        pm: Any,
        name: str,
        content: str,
        mem_type: str,
        description: str,
        scope: str,
    ) -> ToolResult:
        if not name or not content:
            return ToolResult(
                success=False, content="", error="name and content are required"
            )
        ok = pm.save(
            name=name,
            content=content,
            mem_type=mem_type,
            description=description,
            scope=scope,
        )
        if ok:
            msg = f"Memory saved: '{name}' (type={mem_type}, scope={scope})"
            logger.debug(f"[tool:memory] save -> success")
            return ToolResult(success=True, content=msg)
        logger.debug("[tool:memory] save -> failed")
        return ToolResult(success=False, content="", error="Failed to save memory")

    def _do_load(self, pm: Any, name: str, scope: str) -> ToolResult:
        if not name:
            return ToolResult(
                success=False, content="", error="name is required for load"
            )
        effective_scope = scope if scope in ("global", "project") else None
        mem = pm.load(name, scope=effective_scope)
        if not mem:
            return ToolResult(
                success=False, content="", error=f"Memory not found: {name}"
            )
        lines = [
            f"Name: {mem.get('name')}",
            f"Type: {mem.get('type')}",
            f"Scope: {mem.get('scope')}",
            f"Description: {mem.get('description', '(none)')}",
            f"Created: {mem.get('created', '?')}",
            f"Updated: {mem.get('updated', '?')}",
            f"Age: {mem.get('age_days', 0)} days",
            "",
            mem.get("content", ""),
        ]
        logger.debug(f"[tool:memory] load -> found")
        return ToolResult(success=True, content="\n".join(lines))

    def _do_list(self, pm: Any, scope: str) -> ToolResult:
        effective_scope = scope if scope in ("global", "project") else None
        memories = pm.load_all(scope=effective_scope)
        if not memories:
            return ToolResult(success=True, content="No memories found.")
        lines = [f"Memories ({len(memories)} total):\n"]
        for m in memories:
            age = m.get("age_days", 0)
            age_str = f"{age}d ago" if age > 0 else "today"
            raw_content = m.get("content", "")
            preview = raw_content[:60].replace("\n", " ")
            if len(raw_content) > 60:
                preview += "..."
            scope_tag = m.get("scope", "?")
            lines.append(
                f"  [{m.get('type','?')}/{scope_tag}] {m.get('name')} "
                f"({age_str}) - {m.get('description', '')}"
            )
            if preview:
                lines.append(f"    {preview}")
        logger.debug(f"[tool:memory] list -> {len(memories)} results")
        return ToolResult(success=True, content="\n".join(lines))

    def _do_search(self, pm: Any, query: str, scope: str) -> ToolResult:
        if not query:
            return ToolResult(
                success=False, content="", error="query is required for search"
            )
        effective_scope = scope if scope in ("global", "project") else None
        results = pm.search(query, scope=effective_scope)
        if not results:
            return ToolResult(
                success=True, content=f"No memories match '{query}'."
            )
        lines = [f"Search results for '{query}' ({len(results)} matches):\n"]
        for m in results:
            score = m.get("_relevance", 0)
            lines.append(
                f"  [{m.get('type','?')}/{m.get('scope','?')}] "
                f"{m.get('name')} (relevance={score})"
            )
            lines.append(f"    {m.get('description', '')}")
        logger.debug(f"[tool:memory] search -> {len(results)} results")
        return ToolResult(success=True, content="\n".join(lines))

    def _do_delete(self, pm: Any, name: str, scope: str) -> ToolResult:
        if not name:
            return ToolResult(
                success=False, content="", error="name is required for delete"
            )
        effective_scope = scope if scope in ("global", "project") else None
        ok = pm.delete(name, scope=effective_scope)
        if ok:
            msg = f"Memory deleted: '{name}'"
            logger.debug(f"[tool:memory] delete -> success")
            return ToolResult(success=True, content=msg)
        logger.debug("[tool:memory] delete -> not found")
        return ToolResult(success=False, content="", error=f"Memory not found: {name}")

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["save", "load", "list", "search", "delete"],
                    "description": "Action: save/load/list/search/delete",
                },
                "name": {
                    "type": "string",
                    "description": "Memory name (for save/load)",
                },
                "content": {
                    "type": "string",
                    "description": "Memory content (for save)",
                },
                "mem_type": {
                    "type": "string",
                    "enum": ["user", "feedback", "project", "reference"],
                    "description": "Memory type (for save, default: user)",
                },
                "description": {
                    "type": "string",
                    "description": "Brief description of this memory (for save)",
                },
                "query": {
                    "type": "string",
                    "description": "Search keyword (for search)",
                },
                "scope": {
                    "type": "string",
                    "enum": ["global", "project"],
                    "description": "Scope (for save: default project; for load/list/search: "
                                    "omit to search both global and project)",
                },
            },
            "required": ["action"],
        }
