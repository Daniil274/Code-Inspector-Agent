from __future__ import annotations

import asyncio
from typing import Dict, Optional

from core.knowledge_base import FileAnalysisReport
from agents.file_analysis_agent import FileAnalysisAgent


class ProcessorAgent:
    """Wrapper around FileAnalysisAgent used for module processing."""

    def __init__(self, model_config: Dict):
        self.file_agent = FileAnalysisAgent(model_config)

    async def process(self, file_path: str, content: str) -> Optional[FileAnalysisReport]:
        """Process a file using FileAnalysisAgent."""
        # FileAnalysisAgent reads file itself, content is reserved for future use
        return await self.file_agent.analyze_file(file_path)
