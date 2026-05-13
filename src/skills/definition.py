"""Skill definition data class"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class SkillDefinition:
    """Represents a parsed SKILL.md file.

    Each skill is a prompt injection mechanism: when triggered via
    /skill-name, the markdown_body is injected as a user message
    into the agent conversation.
    """

    name: str                          # unique identifier, maps to /<name>
    description: str = ""              # short description for help text
    markdown_body: str = ""            # the prompt content (markdown)
    allowed_tools: List[str] = field(default_factory=list)  # tools allowed ([] = all)
    when_to_use: str = ""              # hint for when to trigger
    argument_hint: str = ""            # e.g. "[file-pattern]"
    arguments: List[str] = field(default_factory=list)  # named argument placeholders
    user_invocable: bool = True        # whether user can call via /
    context: str = "inline"            # execution mode: "inline"
    skill_dir: str = ""                # absolute path to the skill directory
    model: Optional[str] = None        # optional model override
    effort: Optional[str] = None       # optional effort override
    paths: List[str] = field(default_factory=list)  # conditional activation globs
