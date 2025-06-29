from __future__ import annotations

"""Wrapper agent for generating project documentation."""

from typing import Dict

from src.agents import function_tool

from core.knowledge_base import KnowledgeBase
from .composer_agent import ComposerAgent


class WriterAgent(ComposerAgent):
    """Agent responsible for writing documentation."""

    def __init__(self, model_config: Dict):
        super().__init__(model_config)

    @function_tool
    async def write_documentation(self, kb: KnowledgeBase) -> str:
        """Generate full project documentation."""
        return await self.compose_documentation(kb)
