#!/usr/bin/env python
"""grep - Search for text patterns in files within the project directory."""

import argparse
import json
import re
from pathlib import Path

# 文件类型到 glob 模式的映射
TYPE_TO_GLOB = {
    "js": ["*.js", "*.jsx", "*.mjs"],
    "ts": ["*.ts", "*.tsx", "*.mts"],
    "py": ["*.py", "*.pyw"],
    "rust": ["*.rs"],
    "go": ["*.go"],
    "java": ["*.java"],
    "c": ["*.c", "*.h"],
    "cpp": ["*.cpp", "*.cc", "*.hpp", "*.hh"],
    "cs": ["*.cs"],
    "rb": ["*.rb"],
    "php": ["*.php"],
    "swift": ["*.swift"],
    "kt": ["*.kt", "*.kts"],
    "scala": ["*.scala"],
    "html": ["*.html", "*.htm"],
    "css": ["*.css", "*.scss", "*.sass", "*.less"],
    "json": ["*.json"],
    "xml": ["*.xml"],
    "yaml": ["*.yaml", "*.yml"],
    "md": ["*.md", "*.markdown"],
    "sql": ["*.sql"],
    "sh": ["*.sh", "*.bash", "*.zsh"],
    "ps1": ["*.ps1"],
    "vue": ["*.vue"],
    "jsx": ["*.jsx"],
    "tsx": ["*.tsx"],
}


def get_project_root() -> Path:
    """Get the project root directory (where config.json is located)."""
    current = Path(__file__).resolve().parent
    while current != current.parent:
        if (current / "config.json").exists():
            return current
        current = current.parent
    return Path.cwd()


def should_search(file: Path) -> bool:
    """Check if file should be searched."""
    skip_dirs = {".git", "__pycache__", "node_modules", ".venv", "venv", ".claude", ".hg", ".svn"}
    skip_extensions = {".pyc", ".exe", ".dll", ".so", ".bin", ".pdb", ".class", ".o", ".obj"}
    skip_names = {".DS_Store", "thumbs.db"}

    if file.name in skip_names:
        return False
    if any(part in skip_dirs for part in file.parts):
        return False
    if file.suffix in skip_extensions:
        return False
    return True


def parse_glob_patterns(glob_str: str) -> list:
    """解析 glob 字符串，支持逗号分隔和空格分隔多模式。"""
    # 逗号分隔: "*.{js,ts}"
    comma_patterns = []
    for pattern in glob_str.split(","):
        pattern = pattern.strip()
        if not pattern:
            continue
        # 空格分隔: "src/**/*.tsx"
        for p in pattern.split():
            p = p.strip()
            if p:
                comma_patterns.append(p)
    return comma_patterns


def get_type_globs(type_filter: str) -> list:
    """根据文件类型获取 glob 模式列表。"""
    patterns = TYPE_TO_GLOB.get(type_filter, [f"*.{type_filter}"])
    return patterns


def build_file_list(root: Path, path: Path, glob_patterns: list, type_filter: str) -> list:
    """根据路径和过滤条件获取文件列表。"""
    files = []

    if not path.exists():
        return files

    if path.is_file():
        if should_search(path):
            files.append(path)
        return files

    # 收集所有候选文件
    candidates = []
    if glob_patterns:
        for gp in glob_patterns:
            candidates.extend(path.rglob(gp))
    elif type_filter:
        type_globs = get_type_globs(type_filter)
        for tg in type_globs:
            candidates.extend(path.rglob(tg))
    else:
        candidates = list(path.rglob("*"))
        candidates = [f for f in candidates if f.is_file()]

    # 过滤并排序
    for f in candidates:
        if f.is_file() and should_search(f):
            files.append(f)

    # 按修改时间排序（最近修改的在前）
    files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    return files


def search_file(file: Path, pattern: str, flags: int, multiline: bool, max_cols: int = 500) -> list:
    """搜索单个文件，返回匹配行列表（含行号）。"""
    results = []
    try:
        content = file.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return results

    if multiline:
        flags |= re.MULTILINE

    try:
        regex = re.compile(pattern, flags)
    except re.error:
        return results

    for i, line in enumerate(content.splitlines(), 1):
        # 限制单行长度
        if len(line) > max_cols:
            line = line[:max_cols] + "..."
        if regex.search(line):
            results.append((i, line.rstrip()))

    return results


def grep_search(
    pattern: str,
    root: Path,
    path: Path,
    glob_patterns: list,
    output_mode: str,
    before_ctx: int,
    after_ctx: int,
    context: int,
    show_lineno: bool,
    ignore_case: bool,
    type_filter: str,
    head_limit: int,
    offset: int,
    multiline: bool,
) -> tuple:
    """执行 grep 搜索。"""
    if before_ctx and after_ctx is None:
        after_ctx = before_ctx
    if context and after_ctx is None:
        before_ctx = context
        after_ctx = context

    flags = re.IGNORECASE if ignore_case else 0

    # 获取文件列表
    files = build_file_list(root, path, glob_patterns, type_filter)

    if output_mode == "files_with_matches":
        # 只返回文件名列表
        matched_files = []
        for f in files:
            matches = search_file(f, pattern, flags, multiline)
            if matches:
                rel_path = f.relative_to(path) if path.is_dir() else f.relative_to(root)
                matched_files.append((rel_path, f.stat().st_mtime))

        # 排序并分页
        matched_files.sort(key=lambda x: x[1], reverse=True)
        total = len(matched_files)
        page = matched_files[offset:offset + head_limit] if head_limit > 0 else matched_files[offset:]
        return "\n".join(str(p) for p, _ in page), total

    elif output_mode == "count":
        # 每个文件的匹配次数
        counts = {}
        for f in files:
            matches = search_file(f, pattern, flags, multiline)
            if matches:
                rel_path = f.relative_to(path) if path.is_dir() else f.relative_to(root)
                counts[str(rel_path)] = len(matches)

        # 按文件路径排序
        sorted_counts = sorted(counts.items(), key=lambda x: x[0])
        total = sum(counts.values())
        content = "\n".join(f"{path}: {count}" for path, count in sorted_counts)
        return content, total

    else:  # content 模式
        # 收集所有匹配行（含上下文）
        all_matches = []
        for f in files:
            matches = search_file(f, pattern, flags, multiline)
            if matches:
                rel_path = f.relative_to(path) if path.is_dir() else f.relative_to(root)
                for lineno, line in matches:
                    all_matches.append((str(rel_path), lineno, line))

        # 上下文处理：合并相邻匹配（同一文件内）
        if before_ctx or after_ctx:
            enriched = []
            for filepath, lineno, line in all_matches:
                enriched.append({
                    "file": filepath,
                    "line": lineno,
                    "content": line,
                    "before": [],
                    "after": []
                })
            # 注意：上下文行需要从文件重新读取，此处简化处理
            for item in enriched:
                rel = Path(item["file"])
                if path.is_dir():
                    full_path = path / rel
                else:
                    full_path = root / rel
                if full_path.exists():
                    try:
                        lines = full_path.read_text(encoding="utf-8", errors="ignore").splitlines()
                        start = max(0, item["line"] - 1 - before_ctx)
                        end = min(len(lines), item["line"] + after_ctx)
                        if start < item["line"] - 1:
                            item["before"] = lines[start:item["line"] - 1]
                        if item["line"] < end:
                            item["after"] = lines[item["line"]:end]
                    except Exception:
                        pass
            all_matches = enriched
        else:
            all_matches = [{"file": f, "line": l, "content": c, "before": [], "after": []}
                          for f, l, c in all_matches]

        # 分页
        total = len(all_matches)
        page = all_matches[offset:offset + head_limit] if head_limit > 0 else all_matches[offset:]

        # 格式化输出
        lines_out = []
        for item in page:
            # Before context first
            for bc in item.get("before", []):
                bc_line = item['line'] - len(item['before']) + item['before'].index(bc)
                ctx_prefix = f"{item['file']}:{bc_line}:" if show_lineno else ""
                lines_out.append(f"{ctx_prefix} {bc}")
            # Match line
            prefix = f"{item['file']}:{item['line']}:" if show_lineno else ""
            lines_out.append(f"{prefix} {item['content']}")
            # After context with incrementing line numbers
            for i, ac in enumerate(item.get("after", [])):
                ctx_prefix = f"{item['file']}:{item['line'] + 1 + i}:" if show_lineno else ""
                lines_out.append(f"{ctx_prefix} {ac}")

        return "\n".join(lines_out), total


def main():
    parser = argparse.ArgumentParser(description="grep - Search for text patterns in files")
    parser.add_argument("--pattern", required=True, help="Pattern to search for (regex)")
    parser.add_argument("--path", default=".", help="Directory path to search in")
    parser.add_argument("--glob", default="", help="Glob pattern to filter files (e.g. *.py, *.{js,ts})")
    parser.add_argument("--output-mode", default="content",
                        choices=["content", "files_with_matches", "count"],
                        help="Output mode: content (default), files_with_matches, count")
    parser.add_argument("-B", "--before-context", type=int, default=0, help="Show N lines before match")
    parser.add_argument("-A", "--after-context", type=int, default=0, help="Show N lines after match")
    parser.add_argument("-C", "--context", type=int, default=0, help="Show N lines of context")
    parser.add_argument("-n", dest="show_lineno", action="store_true", default=True, help="Show line numbers")
    parser.add_argument("--no-line-number", dest="show_lineno", action="store_false", help="Hide line numbers")
    parser.add_argument("-i", "--ignore-case", action="store_true", help="Case-insensitive search")
    parser.add_argument("--type", default="", help="Filter by file type (js, py, rust, etc.)")
    parser.add_argument("--head-limit", type=int, default=250, help="Limit number of results (0=unlimited)")
    parser.add_argument("--offset", type=int, default=0, help="Skip first N results")
    parser.add_argument("--multiline", action="store_true", help="Enable multiline mode")

    args = parser.parse_args()

    root = get_project_root()
    path_arg = args.path.strip() if args.path != "." else ""

    # 支持外部路径：直接使用提供的路径
    if path_arg:
        resolved = Path(path_arg).resolve()
    else:
        resolved = root.resolve()

    # 解析 glob 模式
    glob_patterns = []
    if args.glob:
        glob_patterns = parse_glob_patterns(args.glob)

    # 处理路径
    search_path = resolved if resolved.is_dir() else resolved.parent

    try:
        content, total = grep_search(
            pattern=args.pattern,
            root=root,
            path=search_path,
            glob_patterns=glob_patterns,
            output_mode=args.output_mode,
            before_ctx=args.before_context,
            after_ctx=args.after_context,
            context=args.context,
            show_lineno=args.show_lineno,
            ignore_case=args.ignore_case,
            type_filter=args.type,
            head_limit=args.head_limit,
            offset=args.offset,
            multiline=args.multiline,
        )

        if not content:
            result = {"success": True, "content": "No matches found.", "error": ""}
        else:
            result = {"success": True, "content": content, "error": ""}
    except re.error as e:
        result = {"success": False, "content": "", "error": f"Invalid regex pattern: {e}"}
    except Exception as e:
        result = {"success": False, "content": "", "error": str(e)}

    print(json.dumps(result))


if __name__ == "__main__":
    main()
