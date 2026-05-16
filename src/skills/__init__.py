"""Skill system — load and register skills from SKILL.md files"""

import logging

from .registry import skill_registry
from .loader import load_skills_from_dirs
from .commands import create_skill_handler, cmd_skills

logger = logging.getLogger(__name__)


def init_skills() -> None:
    """Load skills from configured directories and register as commands.

    Called once during TUI startup, after core commands are registered.
    Skills are loaded from SKILL.md files in subdirectories of each
    configured skill directory (default: skills/ relative to project root).
    """
    from ..core.config import config
    from ..commands.registry import command_registry

    if not config.skills_enabled:
        logger.info("Skills system disabled by config")
        return

    skill_dirs = config.skill_dirs
    logger.info(f"Loading skills from: {skill_dirs}")

    skills = load_skills_from_dirs(skill_dirs)

    registered = 0
    skipped = 0
    for skill in skills:
        # Check for collision with built-in commands
        existing = command_registry.get(skill.name)
        if existing is not None:
            logger.warning(
                f"Skill '{skill.name}' collides with built-in command, skipping"
            )
            skipped += 1
            continue

        # Register in skill registry (always, for LLM invocation via SkillTool)
        skill_registry.register(skill)

        # Register as slash command only if user-invocable
        if not skill.user_invocable:
            logger.debug(f"Skill '{skill.name}' is not user-invocable, skipping slash command")
            skipped += 1
            continue

        handler = create_skill_handler(skill)
        command_registry.register(
            name=skill.name,
            description=skill.description or f"Skill: {skill.name}",
            handler=handler,
            arg_spec=skill.argument_hint,
        )
        registered += 1

    # Register /skills command
    command_registry.register(
        name="skills",
        description="List all available skills",
        handler=cmd_skills,
    )

    logger.info(
        f"Skills initialized: {registered} registered, {skipped} skipped"
    )
