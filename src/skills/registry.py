"""Skill registry — singleton for managing loaded skills"""

import logging
import threading
from typing import Dict, List, Optional

from .definition import SkillDefinition

logger = logging.getLogger(__name__)


class SkillRegistry:
    """Singleton registry for managing loaded skills."""

    _instance: Optional["SkillRegistry"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "SkillRegistry":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._skills: Dict[str, SkillDefinition] = {}
        return cls._instance

    def register(self, skill: SkillDefinition) -> None:
        """Register a skill. Overwrites if name already exists."""
        self._skills[skill.name] = skill
        logger.debug(f"Skill registered: {skill.name}")

    def get(self, name: str) -> Optional[SkillDefinition]:
        """Get a skill by name."""
        return self._skills.get(name)

    def list_skills(self) -> List[SkillDefinition]:
        """Return all registered skills sorted by name."""
        return sorted(self._skills.values(), key=lambda s: s.name)

    def is_loaded(self) -> bool:
        """Return True if any skills are registered."""
        return len(self._skills) > 0

    def clear(self) -> None:
        """Remove all registered skills."""
        self._skills.clear()
        logger.debug("Skill registry cleared")


skill_registry = SkillRegistry()
