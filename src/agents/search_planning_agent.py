"""SearchPlanningAgent: derive search keywords / plans from a profile."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class SearchPlan:
    keywords: List[str]


class SearchPlanningAgent:
    """Simple planner that selects keywords from a profile.

    This is intentionally lightweight; it can be expanded into LangGraph later.
    """

    def plan_keywords(self, profile: dict, max_keywords: int = 10) -> SearchPlan:
        skills = profile.get("skills") or []
        # keep ordering and trim
        keywords = [str(s).strip() for s in skills][:max_keywords]
        return SearchPlan(keywords=keywords)

