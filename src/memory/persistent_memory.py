"""跨会话持久化记忆系统

基于文件的双层（全局 + 项目）记忆存储。
文件格式：Markdown + YAML frontmatter。
"""

import logging
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .utils.path import get_project_root

logger = logging.getLogger(__name__)

# YAML frontmatter 解析器（无需 PyYAML 依赖）
_KV_RE = re.compile(r'^(\w+):\s*(.+)$', re.MULTILINE)
_SLUG_RE = re.compile(r'[^a-z0-9]+')
_VALID_SCOPES = frozenset({"global", "project"})
_SLUG_MAX_LEN = 64


def _slugify(name: str) -> str:
    slug = _SLUG_RE.sub('_', name.lower()).strip('_')
    return slug[:_SLUG_MAX_LEN] if slug else "unnamed"


def _parse_frontmatter(text: str) -> Dict[str, str]:
    """Parse YAML frontmatter using line-by-line scanning.

    Handles values containing '---' and quoted values correctly.
    """
    if not text.startswith("---"):
        return {}
    lines = text.split("\n")
    # Find the closing '---' line (a line that is exactly '---' after stripping)
    end_idx = -1
    for i, line in enumerate(lines[1:], 1):
        if line.strip() == "---":
            end_idx = i
            break
    if end_idx == -1:
        return {}
    meta_block = "\n".join(lines[1:end_idx])
    body = "\n".join(lines[end_idx + 1:]).strip()

    meta: Dict[str, str] = {}
    for km in _KV_RE.finditer(meta_block):
        key = km.group(1)
        val = km.group(2).strip()
        # Strip surrounding quotes (with escape handling)
        if len(val) >= 2 and val[0] == '"' and val[-1] == '"':
            val = val[1:-1].replace('\\\\', '\\').replace('\\"', '"').replace('\\n', '\n')
        meta[key] = val
    meta["_body"] = body
    return meta


def _build_frontmatter(fields: Dict[str, str]) -> str:
    lines = ["---"]
    for k, v in fields.items():
        if ":" in v or '"' in v or "\n" in v or "\\" in v:
            v = v.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
            v = f'"{v}"'
        lines.append(f"{k}: {v}")
    lines.append("---")
    return "\n".join(lines)


def _age_days(iso_str: str) -> int:
    try:
        dt = datetime.fromisoformat(iso_str)
        now = datetime.now(timezone.utc) if dt.tzinfo else datetime.now()
        delta = now - dt
        return max(0, delta.days)
    except (ValueError, TypeError):
        return 0


class PersistentMemory:
    """跨会话持久化记忆管理器（单例）。"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls) -> "PersistentMemory":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    inst = super().__new__(cls)
                    inst._initialized = False
                    inst._init_lock = threading.Lock()
                    cls._instance = inst
        return cls._instance

    def _initialize(self) -> None:
        if self._initialized:
            return
        from .config import config
        self._project_dir = get_project_root() / "memory"
        global_dir_str = config.persistent_memory_global_dir
        if global_dir_str:
            self._global_dir = Path(global_dir_str).expanduser().resolve()
        else:
            self._global_dir = None
        self._rw_lock = threading.RLock()
        try:
            self._ensure_dirs()
            self._initialized = True
        except Exception as e:
            logger.warning(f"Failed to create memory directories: {e}")
            return
        logger.info(
            "PersistentMemory initialized | project=%s global=%s",
            self._project_dir, self._global_dir,
        )

    def _ensure_dirs(self) -> None:
        self._project_dir.mkdir(parents=True, exist_ok=True)
        if self._global_dir:
            self._global_dir.mkdir(parents=True, exist_ok=True)

    def _ensure_initialized(self) -> None:
        """Ensure _initialize has been called (lazy init, thread-safe)."""
        if not self._initialized:
            with self._init_lock:
                if not self._initialized:
                    self._initialize()

    def _dir_for_scope(self, scope: str) -> Optional[Path]:
        if scope == "global":
            return self._global_dir
        return self._project_dir

    def _md_files(self, directory: Path) -> List[Path]:
        if not directory or not directory.exists():
            return []
        return sorted(
            p for p in directory.glob("*.md")
            if p.name != "MEMORY.md"
        )

    def _parse_file(self, filepath: Path) -> Optional[Dict[str, Any]]:
        try:
            text = filepath.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            logger.warning(f"Failed to read memory file {filepath}: {e}")
            return None
        meta = _parse_frontmatter(text)
        if not meta:
            return None
        return {
            "name": meta.get("name", filepath.stem),
            "description": meta.get("description", ""),
            "type": meta.get("type", "user"),
            "scope": meta.get("scope", "project"),
            "created": meta.get("created", ""),
            "updated": meta.get("updated", ""),
            "content": meta.get("_body", ""),
            "age_days": _age_days(meta.get("updated", "")),
            "_slug": filepath.stem,
            "_path": str(filepath),
        }

    def _load_from_dir(self, directory: Path) -> List[Dict[str, Any]]:
        results = []
        for fp in self._md_files(directory):
            mem = self._parse_file(fp)
            if mem:
                results.append(mem)
        return results

    def _index_for_dir(self, directory: Path) -> str:
        index_path = directory / "MEMORY.md"
        if not index_path.exists():
            return ""
        try:
            return index_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return ""

    def _update_index(self, scope: str) -> None:
        """重建指定作用域的 MEMORY.md 索引。"""
        directory = self._dir_for_scope(scope)
        if not directory:
            return
        memories = self._load_from_dir(directory)
        by_type: Dict[str, List[Dict]] = {}
        for m in memories:
            t = m.get("type", "user")
            by_type.setdefault(t, []).append(m)

        lines = ["# Memory Index\n"]
        for t in sorted(by_type.keys()):
            lines.append(f"\n## {t}\n")
            for m in by_type[t]:
                slug = m["_slug"]
                desc = m.get("description", "")
                lines.append(f"- [{m['name']}]({slug}.md) - {desc}")

        index_text = "\n".join(lines) + "\n"
        try:
            (directory / "MEMORY.md").write_text(index_text, encoding="utf-8")
            logger.debug(
                f"Memory index updated | scope={scope} entries={len(memories)}"
            )
        except OSError as e:
            logger.warning(f"Failed to write index for {scope}: {e}")

    def save(
        self,
        name: str,
        content: str,
        mem_type: str = "user",
        description: str = "",
        scope: str = "project",
    ) -> bool:
        """保存一条记忆。scope='global' 或 'project'。"""
        self._ensure_initialized()
        if scope not in _VALID_SCOPES:
            logger.warning(f"Invalid scope: {scope}")
            return False
        from .config import config
        valid_types = set(config.persistent_memory_types)
        if mem_type not in valid_types:
            logger.warning(f"Invalid memory type: {mem_type}")
            return False
        directory = self._dir_for_scope(scope)
        if not directory:
            logger.warning("Global memory dir not configured")
            return False

        slug = _slugify(name)
        now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        filepath = directory / f"{slug}.md"

        with self._rw_lock:
            # 检查 slug 碰撞：如果文件已存在但 name 不同，追加数字后缀
            existing = self._parse_file(filepath)
            if existing and existing.get("name") != name:
                counter = 1
                while True:
                    new_slug = f"{slug}_{counter}"
                    filepath = directory / f"{new_slug}.md"
                    existing = self._parse_file(filepath)
                    if not existing or existing.get("name") == name:
                        slug = new_slug
                        break
                    counter += 1

            created = now
            existing = self._parse_file(filepath)
            if existing and existing.get("created"):
                created = existing["created"]

            fm = _build_frontmatter({
                "name": name,
                "description": description,
                "type": mem_type,
                "scope": scope,
                "created": created,
                "updated": now,
            })
            file_text = f"{fm}\n{content}\n"
            try:
                filepath.write_text(file_text, encoding="utf-8")
                self._update_index(scope)
                logger.info(
                    f"Memory saved | slug={slug} type={mem_type} scope={scope}"
                )
                return True
            except OSError as e:
                logger.error(f"Memory save failed: {e}")
                return False

    def load(
        self, name: str, scope: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """加载一条记忆。scope=None 时先全局后项目。"""
        self._ensure_initialized()
        slug = _slugify(name)
        scopes = self._resolve_scopes(scope)
        with self._rw_lock:
            for s in scopes:
                directory = self._dir_for_scope(s)
                if not directory:
                    continue
                fp = directory / f"{slug}.md"
                if fp.exists():
                    mem = self._parse_file(fp)
                    if mem:
                        logger.debug(f"Memory loaded | name={name} scope={s}")
                        return mem
        logger.debug(f"Memory not found | name={name}")
        return None

    def load_all(self, scope: Optional[str] = None) -> List[Dict[str, Any]]:
        """加载所有记忆。scope=None 时合并全局+项目。"""
        self._ensure_initialized()
        scopes = self._resolve_scopes(scope)
        all_memories: List[Dict[str, Any]] = []
        with self._rw_lock:
            for s in scopes:
                directory = self._dir_for_scope(s)
                if directory:
                    all_memories.extend(self._load_from_dir(directory))
        all_memories.sort(key=lambda m: m.get("updated", ""), reverse=True)
        logger.debug(f"Loaded {len(all_memories)} memories")
        return all_memories

    def count(self, scope: Optional[str] = None) -> int:
        """轻量计数，不解析文件内容。"""
        self._ensure_initialized()
        scopes = self._resolve_scopes(scope)
        total = 0
        with self._rw_lock:
            for s in scopes:
                directory = self._dir_for_scope(s)
                if directory:
                    total += len(self._md_files(directory))
        return total

    def load_index(self) -> str:
        """合并两层 MEMORY.md 内容，用于注入上下文。"""
        self._ensure_initialized()
        parts = []
        with self._rw_lock:
            if self._global_dir:
                idx = self._index_for_dir(self._global_dir)
                if idx.strip():
                    parts.append(f"# Global Memory\n{idx}")
            proj_idx = self._index_for_dir(self._project_dir)
            if proj_idx.strip():
                parts.append(f"# Project Memory\n{proj_idx}")
        result = "\n\n".join(parts)
        if result:
            logger.debug(f"Memory index loaded | {len(result)} chars")
        return result

    def delete(self, name: str, scope: Optional[str] = None) -> bool:
        """删除一条记忆。scope=None 时先全局再项目，找到即停。"""
        self._ensure_initialized()
        slug = _slugify(name)
        scopes = self._resolve_scopes(scope)
        deleted = False
        with self._rw_lock:
            for s in scopes:
                directory = self._dir_for_scope(s)
                if not directory:
                    continue
                fp = directory / f"{slug}.md"
                if fp.exists():
                    try:
                        fp.unlink()
                        self._update_index(s)
                        logger.info(
                            f"Memory deleted | name={name} scope={s}"
                        )
                        deleted = True
                        break
                    except OSError as e:
                        logger.error(f"Memory delete failed: {e}")
        if not deleted:
            logger.debug(f"Memory not found for delete | name={name}")
        return deleted

    def search(
        self, query: str, scope: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """子串搜索记忆的 name、description、content。"""
        self._ensure_initialized()
        query_lower = query.lower()
        scopes = self._resolve_scopes(scope)
        results: List[Dict[str, Any]] = []
        with self._rw_lock:
            for s in scopes:
                directory = self._dir_for_scope(s)
                if not directory:
                    continue
                for mem in self._load_from_dir(directory):
                    score = 0
                    name_val = mem.get("name", "").lower()
                    desc_val = mem.get("description", "").lower()
                    content_val = mem.get("content", "").lower()
                    if query_lower in name_val:
                        score = 3
                    elif query_lower in desc_val:
                        score = 2
                    elif query_lower in content_val:
                        score = 1
                    if score > 0:
                        mem["_relevance"] = score
                        results.append(mem)
        results.sort(key=lambda m: m.get("_relevance", 0), reverse=True)
        logger.debug(f"Memory search | query='{query}' results={len(results)}")
        return results

    def _resolve_scopes(self, scope: Optional[str]) -> List[str]:
        if scope == "global":
            return ["global"]
        if scope == "project":
            return ["project"]
        # 默认：先全局后项目
        if self._global_dir:
            return ["global", "project"]
        return ["project"]


# 模块级单例（懒初始化：首次访问时触发 _initialize）
persistent_memory = PersistentMemory()
