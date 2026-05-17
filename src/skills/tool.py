"""SkillTool — allows the LLM to invoke skills programmatically"""

import logging
from typing import Any, Dict, List

from ..tools.base import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class SkillTool(BaseTool):
    """Tool that lets the LLM invoke a skill by name.

    When called, returns the skill's prompt content so the model
    can follow the skill's instructions.
    """

    def __init__(self):
        super().__init__(
            name="invoke_skill",
            description="Invoke a skill by name and return its instructions.",
        )

    def execute(self, skill_name: str = "", args: str = "") -> ToolResult:
        from .registry import skill_registry
        from .commands import _build_skill_prompt

        skill = skill_registry.get(skill_name)
        if not skill:
            logger.warning(f"Skill not found: {skill_name}")
            available = [s.name for s in skill_registry.list_skills()]
            return ToolResult(
                success=False,
                content="",
                error=f"Skill not found: {skill_name}. Available: {', '.join(available) or 'none'}",
            )

        prompt = _build_skill_prompt(skill, args)
        logger.info(f"SkillTool invoked: {skill_name} (args={args!r})")
        return ToolResult(success=True, content=prompt)

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "skill_name": {
                    "type": "string",
                    "description": "Name of the skill to invoke",
                },
                "args": {
                    "type": "string",
                    "description": "Arguments to pass to the skill",
                },
            },
            "required": ["skill_name"],
        }

    def validate_args(self, args: Dict[str, Any]) -> List[str]:
        errors = []
        if not args.get("skill_name"):
            errors.append("skill_name is required")
        return errors
