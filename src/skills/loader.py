"""SKILL.md file loader and frontmatter parser"""

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .definition import SkillDefinition

logger = logging.getLogger(__name__)


def load_skills_from_dirs(skill_dirs: List[str]) -> List[SkillDefinition]:
    """Scan directories for SKILL.md files and return parsed SkillDefinitions.

    Each directory is resolved relative to the project root. Within each
    directory, subdirectories containing SKILL.md are loaded as skills.

    Args:
        skill_dirs: List of directory paths (relative to project root)
    Returns:
        List of successfully parsed SkillDefinition objects
    """
    from ..utils.path import resolve_path

    skills: List[SkillDefinition] = []
    seen_names: set = set()

    for dir_path_str in skill_dirs:
        try:
            base_dir = resolve_path(dir_path_str)
        except Exception as e:
            logger.warning(f"Failed to resolve skill dir '{dir_path_str}': {e}")
            continue

        if not base_dir.is_dir():
            logger.debug(f"Skill dir not found, skipping: {base_dir}")
            continue

        # Iterate over subdirectories
        for child in sorted(base_dir.iterdir()):
            if not child.is_dir():
                continue

            skill_md = child / "SKILL.md"
            if not skill_md.is_file():
                continue

            skill = parse_skill_md(skill_md)
            if skill is None:
                continue

            # Check for name collision with built-in commands
            if skill.name in seen_names:
                logger.warning(
                    f"Duplicate skill name '{skill.name}' at {skill_md}, skipping"
                )
                continue
            seen_names.add(skill.name)

            skills.append(skill)
            logger.info(f"Loaded skill: {skill.name} from {skill_md}")

    logger.info(f"Total skills loaded: {len(skills)}")
    return skills


def parse_skill_md(file_path: Path) -> Optional[SkillDefinition]:
    """Parse a SKILL.md file into a SkillDefinition.

    The file format is:
        ---\n
        YAML frontmatter\n
        ---\n
        Markdown body content\n

    Args:
        file_path: Path to the SKILL.md file
    Returns:
        SkillDefinition if parsed successfully, None otherwise
    """
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        logger.warning(f"Failed to read {file_path}: {e}")
        return None

    meta, body = _parse_frontmatter(content)
    if meta is None:
        logger.warning(f"No valid frontmatter in {file_path}")
        return None

    # Extract name: use frontmatter 'name', fallback to parent dir name
    name = meta.get("name", "").strip()
    if not name:
        name = file_path.parent.name

    if not name:
        logger.warning(f"Skill has no name and dir name is empty: {file_path}")
        return None

    # Parse list fields
    allowed_tools = _ensure_list(meta.get("allowed-tools", []))
    arguments = _ensure_list(meta.get("arguments", []))
    paths = _ensure_list(meta.get("paths", []))

    # Parse boolean fields
    user_invocable = _parse_bool(meta.get("user-invocable", True))

    return SkillDefinition(
        name=name,
        description=str(meta.get("description", "")).strip(),
        markdown_body=body.strip(),
        allowed_tools=allowed_tools,
        when_to_use=str(meta.get("when_to_use", "")).strip(),
        argument_hint=str(meta.get("argument-hint", "")).strip(),
        arguments=arguments,
        user_invocable=user_invocable,
        context=str(meta.get("context", "inline")).strip(),
        skill_dir=str(file_path.parent.resolve()),
        model=meta.get("model"),
        effort=meta.get("effort"),
        paths=paths,
    )


def _parse_frontmatter(content: str) -> Tuple[Optional[Dict[str, Any]], str]:
    """Parse YAML frontmatter from markdown content.

    Returns:
        (metadata_dict, body_text) or (None, full_content) if no frontmatter
    """
    # Match opening ---, content, closing ---
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)", content, re.DOTALL)
    if not match:
        return None, content

    yaml_text = match.group(1)
    body = match.group(2)

    meta = _parse_yaml_simple(yaml_text)
    return meta, body


def _parse_yaml_simple(text: str) -> Dict[str, Any]:
    """Lightweight YAML parser for simple frontmatter.

    Supports:
    - Scalar key-value pairs: `key: value`
    - List values: key followed by indented `- item` lines
    - Quoted strings (single and double)
    - Inline lists: `key: [item1, item2]`

    Does NOT support: nested objects, multi-line strings, anchors.
    """
    result: Dict[str, Any] = {}
    lines = text.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Skip empty lines and comments
        if not stripped or stripped.startswith("#"):
            i += 1
            continue

        # Check for key-value pair
        kv_match = re.match(r"^([A-Za-z_-]+)\s*:\s*(.*)", stripped)
        if not kv_match:
            i += 1
            continue

        key = kv_match.group(1)
        value_str = kv_match.group(2).strip()

        # Check if value is empty (potential list follows)
        if not value_str:
            # Collect list items
            list_items = []
            i += 1
            while i < len(lines):
                item_line = lines[i]
                item_stripped = item_line.strip()
                if item_stripped.startswith("- "):
                    item_val = item_stripped[2:].strip()
                    list_items.append(_strip_quotes(item_val))
                    i += 1
                elif item_stripped == "":
                    # Skip consecutive empty lines, continue if more list items follow
                    j = i + 1
                    while j < len(lines) and lines[j].strip() == "":
                        j += 1
                    if j < len(lines) and lines[j].strip().startswith("- "):
                        i = j
                        continue
                    break
                else:
                    break
            result[key] = list_items
        elif value_str.startswith("[") and value_str.endswith("]"):
            # Inline list: [item1, item2]
            inner = value_str[1:-1].strip()
            if inner:
                result[key] = [
                    _strip_quotes(item.strip()) for item in inner.split(",")
                ]
            else:
                result[key] = []
            i += 1
        else:
            result[key] = _strip_quotes(value_str)
            i += 1

    return result


def _strip_quotes(s: str) -> str:
    """Remove surrounding quotes from a string."""
    if len(s) >= 2:
        if (s[0] == '"' and s[-1] == '"') or (s[0] == "'" and s[-1] == "'"):
            return s[1:-1]
    return s


def _ensure_list(val: Any) -> List[str]:
    """Ensure value is a list of strings."""
    if isinstance(val, list):
        return [str(item) for item in val]
    if isinstance(val, str) and val:
        return [val]
    return []


def _parse_bool(val: Any) -> bool:
    """Parse a value as boolean."""
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.lower() in ("true", "yes", "1")
    return bool(val)
