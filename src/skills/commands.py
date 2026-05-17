"""Skill execution handler and /skills command"""

import logging
import threading
from typing import TYPE_CHECKING, Callable

from ..commands.utils import output as _output
from ..config import config

if TYPE_CHECKING:
    from ..tui import SimpleTUI

from .definition import SkillDefinition

logger = logging.getLogger(__name__)


def _build_skill_prompt(skill_def: SkillDefinition, user_args: str) -> str:
    """Build the final prompt by combining skill body with argument substitution.

    Replaces $arg-name placeholders in the skill body with user-provided values.
    If the skill defines arguments, positional args are mapped by order.

    Args:
        skill_def: The skill definition
        user_args: Raw argument string from user input
    Returns:
        The final prompt string
    """
    body = skill_def.markdown_body

    if not skill_def.arguments:
        # No named arguments — if user provided args, append as additional context
        if user_args.strip():
            return f"{body}\n\n## Additional Input\n\n{user_args.strip()}"
        return body

    # Parse positional args
    arg_values = user_args.split() if user_args.strip() else []

    # Map positional to named arguments
    for idx, arg_name in enumerate(skill_def.arguments):
        placeholder = f"${arg_name}"
        if idx < len(arg_values):
            body = body.replace(placeholder, arg_values[idx])
        else:
            # Replace with empty string if not provided
            body = body.replace(placeholder, "")

    return body


def _run_skill_agent(
    tui: "SimpleTUI", prompt: str, skill_def: SkillDefinition
) -> None:
    """Run the agent with a skill prompt in a background thread.

    Follows the same pattern as TUI._run_agent.
    """
    try:
        tui.agent.run(prompt)
    except Exception as e:
        logger.error(f"Skill agent execution failed: {e}")
        tui._output_queue.put(("error", f"\n[Skill error]: {e}\n"))
    finally:
        # Clear allowed tools override
        if tui.agent:
            tui.agent._allowed_tools_override = None
        tui._output_queue.put(("_agent_done", ""))


def create_skill_handler(skill_def: SkillDefinition) -> Callable:
    """Create a handler function for a skill.

    Returns a handler(tui, args) compatible with SlashCommand.

    Args:
        skill_def: The skill definition to create a handler for
    Returns:
        Handler function
    """

    def handler(tui: "SimpleTUI", args: str) -> None:
        if not tui.agent:
            _output(tui, "\nAgent not initialized\n", "class:error")
            return

        # Build prompt from skill body + args
        prompt = _build_skill_prompt(skill_def, args)

        # Set allowed tools override
        if skill_def.allowed_tools:
            tui.agent._allowed_tools_override = skill_def.allowed_tools

        # Show skill activation message
        tools_info = ""
        if skill_def.allowed_tools:
            tools_info = f" [tools: {', '.join(skill_def.allowed_tools)}]"
        _output(
            tui,
            f"\n[Skill: {skill_def.name}] {skill_def.description}{tools_info}\n"
        )

        # Run agent with skill prompt (same pattern as TUI._run_agent)
        tui._agent_running = True
        tui._agent_stop_event.clear()
        tui._output_queue.put(("token_info", f" {config.thinking_indicator}... "))
        threading.Thread(
            target=_run_skill_agent,
            args=(tui, prompt, skill_def),
            daemon=True,
        ).start()

    return handler


def cmd_skills(tui: "SimpleTUI", args: str) -> None:
    """Handler for /skills command — list all available skills."""
    from .registry import skill_registry

    skills = skill_registry.list_skills()
    if not skills:
        _output(
            tui,
            "\nNo skills loaded.\n"
            "Place SKILL.md files in skills/<name>/ directories.\n"
        )
        return

    lines = [
        "\n┌─────────────────────────────────────────────┐",
        "│  Available Skills                            │",
        "├─────────────────────────────────────────────┤\n",
    ]
    for s in skills:
        hint = f" {s.argument_hint}" if s.argument_hint else ""
        tools_info = ""
        if s.allowed_tools:
            tools_info = f" [tools: {', '.join(s.allowed_tools)}]"
        # Truncate description to fit
        desc = s.description[:40] + "..." if len(s.description) > 40 else s.description
        lines.append(f"  /{s.name}{hint}{' ' * max(1, 20 - len(s.name) - len(hint))}{desc}{tools_info}\n")
    lines.append("└─────────────────────────────────────────────┘")
    lines.append("  Use /skill-name [args] to invoke a skill\n")
    _output(tui, "".join(lines))
